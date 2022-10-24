from email.policy import default
import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response

from modules import Database
import json
from copy import deepcopy

from Backend import models

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class RequestPairingDevice(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if "DeviceMac" in request.data and "DeviceName" in request.data and "PairingID" in request.data:
            models.ExternalSensorPairing.objects.filter(device_mac=request.data["DeviceMac"], paired=False).delete()
            newDevice = models.ExternalSensorPairing(device_mac=request.data["DeviceMac"], device_name=request.data["DeviceName"], pairing_code=request.data["PairingID"])
            newDevice.save()

            return Response(status=200, data={})

        return Response(status=404, data={})

class QueryPairedDevice(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not request.session["patient_deidentified_id"] == request.data["PatientID"]:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.session["patient_deidentified_id"])
            if Authority["Level"] == 0:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if Authority["Level"] == 1:
                Patient = Database.extractPatientInfo(request.user, request.session["patient_deidentified_id"])
                
            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.session["patient_deidentified_id"])
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                Patient = Database.extractPatientInfo(request.user, PatientInfo.deidentified_id)
                Patient["Devices"] = deidentification["Devices"]
            
            availableDevice = models.ExternalSensorPairing.objects.filter(patient_deidentified_id=request.session["patient_deidentified_id"], paired=True).order_by("-pairing_date")
            data = []
            for device in availableDevice:
                data.append({
                    "DeviceMac": device.device_mac,
                    "DeviceName": device.device_name,
                    "PairingDate": device.pairing_date.timestamp()
                })
            return Response(status=200, data=data)
        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        
class VerifyPairing(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not request.session["patient_deidentified_id"] == request.data["PatientID"]:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.session["patient_deidentified_id"])
            if Authority["Level"] == 0:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if Authority["Level"] == 1:
                Patient = Database.extractPatientInfo(request.user, request.session["patient_deidentified_id"])
                
            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.session["patient_deidentified_id"])
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                Patient = Database.extractPatientInfo(request.user, PatientInfo.deidentified_id)
                Patient["Devices"] = deidentification["Devices"]
            
            availableDevice = models.ExternalSensorPairing.objects.filter(pairing_code=request.data["PairingCode"], paired=False).order_by("-pairing_date").first()
            availableDevice.patient_deidentified_id = request.session["patient_deidentified_id"]
            availableDevice.paired = True
            availableDevice.save()

            return Response(status=200, data={
                "DeviceMac": availableDevice.device_mac,
                "DeviceName": availableDevice.device_name,
                "PairingDate": availableDevice.pairing_date.timestamp()
            })

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})