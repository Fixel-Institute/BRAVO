import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

import os, sys, pathlib
import json
import base64
import datetime, pytz

RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

import queue
import hashlib, random, string
from uuid import UUID
processingQueue = queue.Queue()

from Backend import models
from modules import Database
from modules.Percept import Sessions

class DeidentificationTable(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not request.user.is_authenticated:
            return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if "UpdateTable" in request.data:
            if not "passkey" in request.data:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if len(request.data["passkey"]) < 4:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
            
            hashedKey = hashlib.sha256(request.data["passkey"].encode("utf-8")).hexdigest()[:32]
            passkey = base64.b64encode(hashedKey.encode("utf-8"))
            Database.saveDeidentificationLookupTable(request.user, request.data["UpdateTable"], passkey)
            return Response(status=200) 

        elif "QueryTable" in request.data:
            if not "passkey" in request.data:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            hashedKey = hashlib.sha256(request.data["passkey"].encode("utf-8")).hexdigest()[:32]
            passkey = base64.b64encode(hashedKey.encode("utf-8"))
            table = Database.getDeidentificationLookupTable(request.user, passkey)
            if len(table) > 0:
                return Response(status=200, data=table) 
            else:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        else:
            exists = models.DeidentifiedPatientTable.objects.filter(researcher_id=request.user.unique_user_id).exists()
            return Response(status=200, data={"Exist": exists})

class SessionUpload(RestViews.APIView):
    """ Upload JSON Session File.

    .. note::

        This is the only route in the server that uses MultiPart/Form Parser instead of JSON object. 

    This is the primary route that allow users to upload Medtronic JSON Session file. 
    Due to read/write conflict, this route currently implemented a simple queue system. 
    Only one file is being processed at a time, meaning that you can batch upload multiple files, 
    but they will still be processed individually to avoid read/write conflict if files belong to the same patient which 
    access the same cache folder and recording file.

    **POST**: ``/api/uploadSessionFiles``

    Args:
      file (io): File object whose content can be read into raw bytes array.
      [deviceId] (uuid): Device Unique Identifier if the uploader is not clinician/admin. 
        this is to ensure deidentified JSON file will be properly organized to their own folder.
        If ``deviceId`` is not provided, the server will attempt to use ``deidentificationLookupTable`` to deidentify batch files.

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body may contain "newPatient" object if a new Patient object is created because the patient information is new. 
    """

    parser_classes = [RestParsers.MultiPartParser, RestParsers.FormParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not "file" in request.data:
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        rawBytes = request.data["file"].read()
        if request.user.is_clinician:
            
            randomSalt = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
            hashedKey = hashlib.sha256(randomSalt.encode("utf-8")).hexdigest()
            processingQueue.put(hashedKey)
            while processingQueue.queue[0] != hashedKey:
                pass
            
            result = "Failed"
            try:
                result, patient, JSON = Sessions.processPerceptJSON(request.user, request.data["file"].name, rawBytes)
            except Exception as e:
                print(e)
            hashedKey = processingQueue.get()
            
            if result == "Success":
                data = dict()
                if not patient == None:
                    data["newPatient"] = Database.extractPatientTableRow(request.user, patient)
                return Response(status=200, data=data)
            else:
                print(result)
        
        else:
            randomSalt = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
            hashedKey = hashlib.sha256(randomSalt.encode("utf-8")).hexdigest()

            result = "Failed"
            if "deviceId" in request.data:
                AuthorityLevel = Database.verifyAccess(request.user, request.data["patientId"])
                if not AuthorityLevel == 1:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                deviceId = request.data["deviceId"]
                device = models.PerceptDevice.objects.filter(patient_deidentified_id=request.data["patientId"], deidentified_id=request.data["deviceId"]).first()
                if not device:
                    serial_number = "".join(random.choices(string.ascii_uppercase + string.digits, k=32))
                    patient = models.Patient.objects.get(deidentified_id=request.data["patientId"])
                    device = models.PerceptDevice(patient_deidentified_id=request.data["patientId"], serial_number=serial_number, deidentified_id=UUID(request.data["deviceId"]), device_location="")
                    device.device_eol_date = datetime.datetime.fromtimestamp(0, tz=pytz.utc)
                    device.device_last_seen = datetime.datetime.fromtimestamp(0, tz=pytz.utc)
                    device.authority_level = "Research"
                    device.authority_user = request.user.email
                    device.save()
                    patient.addDevice(str(device.deidentified_id))
                
                processingQueue.put(hashedKey)
                while processingQueue.queue[0] != hashedKey:
                    pass
                try:
                    result, patient, JSON = Sessions.processPerceptJSON(request.user, request.data["file"].name, rawBytes, device_deidentified_id=deviceId)
                except Exception as e:
                    print(e)
                hashedKey = processingQueue.get()
                
            else:
                hashedEncrpytionKey = hashlib.sha256(request.data["decryptionKey"].encode("utf-8")).hexdigest()[:32]
                passkey = base64.b64encode(hashedEncrpytionKey.encode("utf-8"))
                table = Database.getDeidentificationLookupTable(request.user, passkey)

                processingQueue.put(hashedKey)
                while processingQueue.queue[0] != hashedKey:
                    pass
                try:
                    result, patient, JSON = Sessions.processPerceptJSON(request.user, request.data["file"].name, rawBytes, lookupTable=table)
                except Exception as e:
                    print(e)
                hashedKey = processingQueue.get()

            if result == "Success":
                data = dict()
                if not patient == None:
                    data["newPatient"] = Database.extractPatientTableRow(request.user, patient)
                return Response(status=200, data=data)
            else:
                print(result)
                
        return Response(status=404)

class SessionRemove(RestViews.APIView):
    """ Delete JSON Session File.

    User may delete JSON session file and all recordings associated with that JSON session file. 
    This is useful for purging database. 

    **POST**: ``/api/deleteSessionFiles``

    Args:
      patientId (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.
      [deletePatient] (bool): (Optional) Requesting all JSON files associate with a specific patient are to be deleted. 
        This will also delete all devices and patient object entry.
      [deleteDevice] (uuid): (Optional) Requesting all JSON files associate with a specific device are to be deleted. 
        This will also delete one device but not patient object.
      [deleteSession] (list): (Optional) Requesting all JSON files in the list to be deleted.

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body may contain "newPatient" object if a new Patient object is created because the patient information is new. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["patientId"])
        if Authority["Level"] != 1:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        patient = models.Patient.objects.get(deidentified_id=request.data["patientId"])

        if "deletePatient" in request.data:
            deidentification = Database.extractPatientInfo(request.user, request.data["patientId"])
            DeviceIDs = [deidentification["Devices"][i]["ID"] for i in range(len(deidentification["Devices"]))]

            for device in DeviceIDs:
                device = models.PerceptDevice.objects.filter(deidentified_id=device).first()
                Sessions.deleteDevice(device.deidentified_id)
                patient.removeDevice(device)
                device.delete()

            patient.delete()
            return Response(status=200)
        
        elif "deleteDevice" in request.data:
            deidentification = Database.extractPatientInfo(request.user, request.data["patientId"])
            DeviceIDs = [deidentification["Devices"][i]["ID"] for i in range(len(deidentification["Devices"]))]
            if not request.data["deviceId"] in DeviceIDs:
                return Response(status=404)

            if not models.PerceptDevice.objects.filter(deidentified_id=request.data["deviceId"]).exists():
                return Response(status=404)

            device = models.PerceptDevice.objects.filter(deidentified_id=request.data["deviceId"]).first()
            Sessions.deleteDevice(device.deidentified_id)
            patient.removeDevice(str(device.deidentified_id))
            device.delete()
            return Response(status=200)
        
        elif "deleteSession" in request.data:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["patientId"], Authority, "ChronicLFPs")
            Sessions.deleteSessions(request.user, request.data["patientId"], [request.data["deleteSession"]], Authority)
            return Response(status=200)

        return Response(status=404)

class ExtractSessionEMR(RestViews.APIView):
    """ Extract EMR from Session JSON File

    **POST**: ``/api/extractSessionEMR``

    Args:
      id (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.
      sessionId (uuid): Session Unique Identifier as provided from ``QuerySessionOverview`` route.

    Returns:
      Response Code 200 if success or 400 if error. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] != 1:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
        Overview = Sessions.viewSession(request.user, request.data["id"], request.data["sessionId"], Authority)
        return Response(status=200, data=Overview)
