""""""""""""
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
Update Recording SQL Table
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from email.policy import default
import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from Backend import models

import os
from modules import Database
from modules.Percept import Sessions, BrainSenseStream
import json
import random, string
import datetime
import pytz
from copy import deepcopy

from utility import PythonUtility

import pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

key = os.environ.get('ENCRYPTION_KEY')

class PatientInformationUpdate(RestViews.APIView):
    """ Update Patient Information in SQL Table

    The Patient Information Update has multiple functions implemented for the route, depending on the command sent. 

    **POST**: ``/api/updatePatientInformation``

    **Manually creating a new Patient entry in database**
    
    .. code-block:: json

      {
        "createNewPatientInfo": true,
        "StudyID": "(string)",
        "PatientID": "(string)",
        "Diagnosis": "(string)",
        "StudyID": "(string)",
        "DeviceName": "(string)",
      }

    Respond body will contain new patient object if successful. 

    **Add new Device entry for specific patient**
    
    ``updatePatientInfo`` is the unique identifier for a specific Patient object. 
    The ``saveDeviceID`` is a human readable identifier for the device. A random 32-byte unique identifier for the device will be randomly generated.

    .. code-block:: json

      {
        "updatePatientInfo": "(uuid)",
        "saveDeviceID": "(string)",
        "newDeviceLocation": "(string)",
      }

    **Change Device Name**
    
    ``updatePatientInfo`` is the unique identifier for a specific Patient object. 
    ``updateDeviceID`` is the unique identifier for the device that name should be changed. 

    .. code-block:: json

      {
        "updatePatientInfo": "(uuid)",
        "updateDeviceID": "(uuid)",
        "newDeviceName": "(string)",
        "leadAnnotations": "[(string)]"
      }

    **Update Patient Information**
    
    ``updatePatientInfo`` is the unique identifier for a specific Patient object. 

    .. code-block:: json

      {
        "updatePatientInfo": "(uuid)",
        "FirstName": "(string)",
        "LastName": "(string)",
        "Diagnosis": "(string)",
        "MRN": "(string)",
      }

    Returns:
      Response Code 200 if success or 400 if error. 
    """

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
                    "PatientGender": "Unknown",
                    "PatientDateOfBirth": 0,
                    "PatientId": "Unknown",
                }, request.user.email)
                
                if not isNewPatient:
                    return Response(status=404)

                if not (request.user.is_admin or request.user.is_clinician):
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
            if "saveDeviceID" in request.data and not (request.user.is_admin or request.user.is_clinician):
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
                    for index in range(len(device.device_lead_configurations)):
                        device.device_lead_configurations[index]["CustomName"] = request.data["leadAnnotations"][index]
                    device.save()
                    return Response(status=200)

            elif "FirstName" in request.data:
                patient.setPatientFirstName(request.data["FirstName"], key)
                patient.setPatientLastName(request.data["LastName"], key)
                patient.diagnosis = request.data["Diagnosis"]
                patient.setPatientMRN(request.data["MRN"], key)
                patient.tags = request.data["Tags"]
                patient.save()

                if (request.user.is_admin or request.user.is_clinician):
                  for i in range(len(request.data["Tags"])):
                      models.SearchTags.objects.get_or_create(tag_name=request.data["Tags"][i], tag_type="Patient", institute=request.user.institute)
                else:
                  for i in range(len(request.data["Tags"])):
                      models.SearchTags.objects.get_or_create(tag_name=request.data["Tags"][i], tag_type="Patient", institute=request.user.email)

                return Response(status=200)

        elif "mergePatientInfo" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["mergePatientInfo"])
            if not Authority["Level"] == 1:
                return Response(status=404)
            
            SourcePatient = models.Patient.objects.filter(deidentified_id=request.data["targetPatientInfo"]).first()
            MergePatient = models.Patient.objects.filter(deidentified_id=request.data["mergePatientInfo"]).first()

            if MergePatient and SourcePatient:
                for device_id in SourcePatient.device_deidentified_id:
                    device = models.PerceptDevice.objects.filter(deidentified_id=device_id).first()
                    device.patient_deidentified_id = MergePatient.deidentified_id
                    device.save()
                    MergePatient.addDevice(str(device.deidentified_id))

            SourcePatient.delete()
            return Response(status=200)

        return Response(status=400)

class BrainSenseStreamUpdate(RestViews.APIView):
    """ Update Stream recording information.

    Currently only recording contact change is implemented because this is the only information not stored in Percept JSON. 
    
    **POST**: ``/api/updateBrainSenseStream``

    Args:
      requestData (uuid): Device Unique Identifier.
      updateRecordingContactType (uuid): Recording Unique Identifier.
      contactIndex (int): Indicate for Left/Right hemisphere.
      contactType (string): Contact Type (Segment, Ring, A/B/C)

    Returns:
      Response Code 200 if success or 400 if error. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "updateRecordingContactType" in request.data:
            if (request.user.is_admin or request.user.is_clinician):
                if not models.PerceptDevice.objects.filter(deidentified_id=request.data["requestData"], authority_level="Clinic", authority_user=request.user.institute).exists():
                  return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            else:
                if not models.PerceptDevice.objects.filter(deidentified_id=request.data["requestData"], authority_level="Research", authority_user=request.user.email).exists():
                  return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            recording = models.NeuralActivityRecording.objects.filter(device_deidentified_id=request.data["requestData"], recording_id__in=request.data["updateRecordingContactType"], recording_type="BrainSenseStreamPowerDomain").first()
            recording.recording_info["ContactType"][request.data["contactIndex"]] = request.data["contactType"]
            recording.save()
            return Response(status=200)
        
        elif "updateRecordingName" in request.data:
            AuthorityLevel = Database.verifyAccess(request.user, request.data["id"])
            if AuthorityLevel == 0:
                return Response(status=404)
            elif AuthorityLevel == 1:
                PatientID = request.data["id"]
            elif AuthorityLevel == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                PatientID = PatientInfo.authorized_patient_id

            availableDevices = Database.getPerceptDevices(request.user, PatientID, {"Level": AuthorityLevel})
            analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=request.data["updateRecordingName"]).first()
            if not analysis:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            
            if not str(analysis.device_deidentified_id) in [str(device.deidentified_id) for device in availableDevices]:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            
            analysis.analysis_label = request.data["recordingName"]
            recordings = models.NeuralActivityRecording.objects.filter(recording_id__in=analysis.recording_list).all()
            for recording in recordings:
                recording.recording_info["RecordingName"] = request.data["recordingName"]
                recording.save()
            analysis.save()
            return Response(status=200)
        
        elif "adjustAlignment" in request.data:
            AuthorityLevel = Database.verifyAccess(request.user, request.data["id"])
            if AuthorityLevel != 1:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            availableDevices = Database.getPerceptDevices(request.user, request.data["id"], {"Level": 1})
            analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=request.data["recordingId"]).first()
            if not analysis:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            
            if not str(analysis.device_deidentified_id) in [str(device.deidentified_id) for device in availableDevices]:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            allRecordings = models.NeuralActivityRecording.objects.filter(recording_id__in=analysis.recording_list)
            for recording in allRecordings:
                if recording.recording_type == "BrainSenseStreamPowerDomain":
                    recording.recording_info["Alignment"] = float(request.data["alignment"])
                    recording.save()

            return Response(status=200)
        
        elif "mergeRecordings" in request.data:
            recordings = models.NeuralActivityRecording.objects.filter(recording_id__in=request.data["mergeRecordings"], recording_type="BrainSenseStream").all()
            if not len(recordings) == len(request.data["mergeRecordings"]):
                return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
            
            deviceIds = PythonUtility.uniqueList([recording.device_deidentified_id for recording in recordings])
            if len(deviceIds) > 1 or len(deviceIds) == 0:
                return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
            
            if request.user.is_admin or request.user.is_clinician:
                if not models.PerceptDevice.objects.filter(deidentified_id=deviceIds[0], authority_level="Clinic", authority_user=request.user.institute).exists():
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            else:
                if not models.PerceptDevice.objects.filter(deidentified_id=deviceIds[0], authority_level="Research", authority_user=request.user.email).exists():
                  return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            
            recordings = sorted(recordings, key=lambda recording: recording.recording_date)
            result = BrainSenseStream.mergeRealtimeStreamData(recordings)
            if result:
                return Response(status=200)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class UpdatePatientAccess(RestViews.APIView):
    """ Update Patient Access Table.

    Currently only recording contact change is implemented because this is the only information not stored in Percept JSON. 
    
    **POST**: ``/api/updatePatientAccess``

    Args:
      requestData (uuid): Device Unique Identifier.
      updateRecordingContactType (uuid): Recording Unique Identifier.
      contactIndex (int): Indicate for Left/Right hemisphere.
      contactType (string): Contact Type (Segment, Ring, A/B/C)

    Returns:
      Response Code 200 if success or 400 if error. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "createLink" in request.data and "patientList" in request.data:
            for patientId in request.data["patientList"]:
                if not Database.verifyAccess(request.user, patientId) == 1:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            
            authorization_time_range = request.data["patientsConfiguration"]
            shareLink = ''.join(random.choice(string.ascii_uppercase) for i in range(32))
            models.ResearchAccessShareLink(share_link=shareLink, 
                                           authorized_patient_list=request.data["patientList"], 
                                           expiration_time=datetime.datetime.fromtimestamp(datetime.datetime.now().timestamp() + 3600),
                                           authorized_time_range=authorization_time_range).save()
            return Response(status=200, data={
                "shareLink": shareLink
            })
        
        elif "requestAccess" in request.data and "accessCode" in request.data:
            if not models.ResearchAccessShareLink.objects.filter(share_link=request.data["accessCode"], expiration_time__gt=datetime.datetime.now()).exists():
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            
            access = models.ResearchAccessShareLink.objects.filter(share_link=request.data["accessCode"], expiration_time__gt=datetime.datetime.now()).first()
            for patientId in access.authorized_patient_list:
                if not patientId in access.authorized_time_range.keys():
                    authorized_time_range = [0, datetime.datetime.utcnow().timestamp()]
                else:
                    authorized_time_range = [datetime.datetime.fromisoformat(timestamp[:-1]+"+00:00").timestamp() for timestamp in access.authorized_time_range[patientId]]

                Database.AuthorizeResearchAccess(request.user, request.user.unique_user_id, patientId, True, authorized_time_range=authorized_time_range)
                Database.AuthorizeRecordingAccess(request.user, request.user.unique_user_id, patientId, recording_type="TherapyHistory")
                Database.AuthorizeRecordingAccess(request.user, request.user.unique_user_id, patientId, recording_type="BrainSenseSurvey")
                Database.AuthorizeRecordingAccess(request.user, request.user.unique_user_id, patientId, recording_type="BrainSenseStreamTimeDomain")
                Database.AuthorizeRecordingAccess(request.user, request.user.unique_user_id, patientId, recording_type="BrainSenseStreamPowerDomain")
                Database.AuthorizeRecordingAccess(request.user, request.user.unique_user_id, patientId, recording_type="IndefiniteStream")
                Database.AuthorizeRecordingAccess(request.user, request.user.unique_user_id, patientId, recording_type="ChronicLFPs")

            access.delete()
            return Response(status=200)
        
        elif "deleteAccess" in request.data and "patientId" in request.data and "authorizedId" in request.data:
            if not Database.verifyAccess(request.user, request.data["patientId"]) == 1:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            
            Database.AuthorizeResearchAccess(request.user, request.data["authorizedId"], request.data["patientId"], False)
            return Response(status=200)
         
        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
