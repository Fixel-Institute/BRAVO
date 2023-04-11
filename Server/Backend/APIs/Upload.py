""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Data Upload/Preprocessing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

import os, sys, pathlib
import json
import base64
import datetime, pytz
import websocket

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

def processJSONUploads(BatchQueues):
    ws = websocket.WebSocket()
    for queue in BatchQueues:
        print(f"Start Processing {queue.descriptor['filename']}")
        newPatient = None
        ErrorMessage = ""
        ProcessingResult = ""
        try:
            user = models.PlatformUser.objects.get(unique_user_id=queue.owner)
            if user.is_clinician:
                ProcessingResult, newPatient, _ = Sessions.processPerceptJSON(user, queue.descriptor["filename"]) 
            else:
                if "device_deidentified_id" in queue.descriptor:
                    ProcessingResult, _, _ = Sessions.processPerceptJSON(user, queue.descriptor["filename"], device_deidentified_id=queue.descriptor["device_deidentified_id"])
                elif "passkey" in queue.descriptor:
                    table = Database.getDeidentificationLookupTable(user, queue.descriptor["passkey"])
                    ProcessingResult, newPatient, _ = Sessions.processPerceptJSON(user, queue.descriptor["filename"], lookupTable=table)

        except Exception as e:
            ErrorMessage = str(e)
            print(ErrorMessage)

        print(f"End Processing {queue.descriptor['filename']}")
        if ProcessingResult == "Success":
            queue.state = "Complete"
            queue.save()
            try:
                ws.connect("ws://localhost:3001/socket/notification")
                ws.send(json.dumps({
                    "NotificationType": "TaskComplete",
                    "TaskUser": str(queue.owner),
                    "TaskID": str(queue.queue_id),
                    "Authorization": os.environ["ENCRYPTION_KEY"],
                    "State": "Complete",
                    "Message": ErrorMessage,
                }))

                if newPatient:
                    newPatient = Database.extractPatientTableRow(str(queue.owner), newPatient)
                    ws.send(json.dumps({
                        "NotificationType": "NewPatient",
                        "TaskUser": str(queue.owner),
                        "NewPatient": newPatient,
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                    }))

                ws.close()
            except Exception as e:
                print(e)
                #print("Socket Not Active")
        else:
            queue.state = "Error"
            queue.save()

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
        for key in request.data.keys():
            if not (key.startswith("file") or key == "deviceId" or key == "patientId" or key == "decryptionKey" or key == "batchSessionId"):
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        if request.user.is_clinician:
            for key in request.data.keys():
                if key.startswith("file"):
                    rawBytes = request.data[key].read()
                    queueItem = models.ProcessingQueue(owner=request.user.unique_user_id, type="decodeJSON", state="WaitToStart", descriptor={
                        "filename": request.data[key].name,
                        "batchSessionId": request.data["batchSessionId"]
                    })
                    Sessions.saveCacheJSON(request.data[key].name, rawBytes)
                    queueItem.save()
            
        else:
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

                for key in request.data.keys():
                    if key.startswith("file"):
                        rawBytes = request.data[key].read()
                        queueItem = models.ProcessingQueue(owner=request.user.unique_user_id, type="decodeJSON", state="InProgress", descriptor={
                            "filename": request.data[key].name,
                            "device_deidentified_id": deviceId
                        })
                        Sessions.saveCacheJSON(request.data[key].name, rawBytes)
                        queueItem.save()

            else:
                hashedEncrpytionKey = hashlib.sha256(request.data["decryptionKey"].encode("utf-8")).hexdigest()[:32]
                passkey = base64.b64encode(hashedEncrpytionKey.encode("utf-8"))
                for key in request.data.keys():
                    if key.startswith("file"):
                        rawBytes = request.data[key].read()
                        queueItem = models.ProcessingQueue(owner=request.user.unique_user_id, type="decodeJSON", state="InProgress", descriptor={
                            "filename": request.data[key].name,
                            "passkey": passkey
                        })
                        Sessions.saveCacheJSON(request.data[key].name, rawBytes)
                        queueItem.save()

        return Response(status=200)

class RequestProcessingQueue(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        models.ProcessingQueue.objects.filter(owner=request.user.unique_user_id, state="WaitToStart", descriptor__batchSessionId=request.data["batchSessionId"]).update(state="InProgress")
        return Response(status=200)

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
            DeviceIDs = [str(deidentification["Devices"][i]["ID"]) for i in range(len(deidentification["Devices"]))]

            for device in DeviceIDs:
                device = models.PerceptDevice.objects.filter(deidentified_id=device).first()
                Sessions.deleteDevice(device.deidentified_id)
                patient.removeDevice(device)
                device.delete()

            patient.delete()
            return Response(status=200)
        
        elif "deleteDevice" in request.data:
            deidentification = Database.extractPatientInfo(request.user, request.data["patientId"])
            DeviceIDs = [str(deidentification["Devices"][i]["ID"]) for i in range(len(deidentification["Devices"]))]
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
