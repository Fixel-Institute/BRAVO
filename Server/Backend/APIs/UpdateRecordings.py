from email.policy import default
import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from Backend import models

import os
from modules import Database
from modules.Percept import Sessions
import json
import random, string
import datetime
import pytz
from copy import deepcopy

import pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

key = os.environ.get('ENCRYPTION_KEY')

class PatientInformationUpdate(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "createNewPatientInfo" in request.data:
            if "StudyID" in request.data and "PatientID" in request.data and "Diagnosis" in request.data and "DeviceName" in request.data:
                if request.data["StudyID"] == "" or request.data["PatientID"] == "":
                    return Response(status=400)
                data = dict()
                
                patient, isNewPatient = Sessions.retrievePatientInformation({
                    "PatientFirstName": request.data["PatientID"],
                    "PatientLastName": request.data["StudyID"],
                    "Diagnosis": request.data["Diagnosis"],
                    "PatientDateOfBirth": 0,
                    "PatientId": "Unknown",
                }, request.user.email)
                
                if not isNewPatient:
                    return Response(status=404)

                if not request.user.is_clinician:
                    serial_number = "".join(random.choices(string.ascii_uppercase + string.digits, k=32))
                    device = models.PerceptDevice(patient_deidentified_id=patient.deidentified_id, serial_number=serial_number, device_name=request.data["DeviceName"], device_location="")
                    device.device_eol_date = datetime.datetime.fromtimestamp(0, tz=pytz.utc)
                    device.device_last_seen = datetime.datetime.fromtimestamp(0, tz=pytz.utc)
                    device.authority_level = "Research"
                    device.authority_user = request.user.email
                    device.save()
                    patient.addDevice(str(device.deidentified_id))
                    data["deviceID"] = str(device.deidentified_id)

                patient.save()
                models.ResearchAuthorizedAccess(researcher_id=request.user.unique_user_id, authorized_patient_id=patient.deidentified_id, can_edit=True).save()
                data["newPatient"] = Database.extractPatientTableRow(request.user, patient)
                return Response(status=200, data=data)
            else:
                return Response(status=404)

        elif "updatePatientInfo" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["updatePatientInfo"])
            if Authority["Level"] == 0:
                return Response(status=404)

            patient = models.Patient.objects.get(deidentified_id=request.data["updatePatientInfo"])
            if "saveDeviceID" in request.data and not request.user.is_clinician:
                serial_number = "".join(random.choices(string.ascii_uppercase + string.digits, k=32))
                device = models.PerceptDevice(patient_deidentified_id=patient.deidentified_id, serial_number=serial_number, device_name=request.data["saveDeviceID"], device_location=request.data["newDeviceLocation"])
                device.device_eol_date = datetime.datetime.fromtimestamp(0, tz=pytz.utc)
                device.authority_level = "Research"
                device.authority_user = request.user.email
                device.save()
                patient.addDevice(str(device.deidentified_id))
                return Response(status=200)

            elif "updateDeviceID" in request.data:
                if request.data["updateDeviceID"] in patient.device_deidentified_id:
                    device = models.PerceptDevice.objects.get(deidentified_id=request.data["updateDeviceID"])
                    device.device_name = request.data["newDeviceName"]
                    device.save()
                    return Response(status=200)

            elif "FirstName" in request.data:
                patient.setPatientFirstName(request.data["FirstName"], key)
                patient.setPatientLastName(request.data["LastName"], key)
                patient.diagnosis = request.data["Diagnosis"]
                patient.setPatientMRN(request.data["MRN"], key)
                patient.save()
                return Response(status=200)

        return Response(status=400)

class BrainSenseStreamUpdate(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]

    def post(self, request):
        if not request.user.is_authenticated:
          return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if "updateRecordingContactType" in request.data:
            if request.user.is_admin or request.user.is_clinician:
                if not models.PerceptDevice.objects.filter(deidentified_id=request.data["requestData"], authority_level="Clinic", authority_user=request.user.institute).exists():
                  return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            else:
                if not models.PerceptDevice.objects.filter(deidentified_id=request.data["requestData"], authority_level="Research", authority_user=request.user.email).exists():
                  return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=request.data["requestData"], recording_id=request.data["updateRecordingContactType"], recording_type="BrainSenseStream").first()
            recording.recording_info["ContactType"][request.data["contactIndex"]] = request.data["contactType"]
            recording.save()
            return Response(status=200)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
