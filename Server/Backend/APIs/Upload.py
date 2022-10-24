import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response

import os, sys, pathlib
import json

RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

import queue
import hashlib, random, string
processingQueue = queue.Queue()

from Backend import models
from modules import Database
from modules.Percept import Sessions

class SessionUpload(RestViews.APIView):
    parser_classes = [RestParsers.MultiPartParser, RestParsers.FormParser]

    def post(self, request):
        if not request.user.is_authenticated:
            return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if not "file" in request.data:
            return Response(status=403, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

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
            if not "deviceId" in request.data:
                return Response(status=403, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            randomSalt = ''.join(random.choices(string.ascii_uppercase + string.digits, k=32))
            hashedKey = hashlib.sha256(randomSalt.encode("utf-8")).hexdigest()

            processingQueue.put(hashedKey)
            while processingQueue.queue[0] != hashedKey:
                pass
            
            result = "Failed"
            try:
                result, patient, JSON = Sessions.processPerceptJSON(request.user, request.data["file"].name, rawBytes, device_deidentified_id=request.data["deviceId"])
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
    parser_classes = [RestParsers.JSONParser]
    
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["patientId"])
        if Authority["Level"] != 1:
            return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

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

        return Response(status=404)
