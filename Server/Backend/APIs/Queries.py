""""""
"""
All Queries Routes
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import HttpResponse

from Backend import models

from modules import Database, ImageDatabase
from modules.Percept import Therapy, Sessions, BrainSenseSurvey, BrainSenseEvent, BrainSenseStream, IndefiniteStream, ChronicBrainSense, TherapeuticPrediction
from utility.PythonUtility import uniqueList
import json
import numpy as np

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class QueryDatabaseInfo(RestViews.APIView):
    """ Query current database information.

    **POST**: ``/api/queryDatabaseInfo``

    Returns:
      Response Code 200.
      Response Body contains number of unique patients in database and size of data the user has access to. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        databaseInfo = Database.getDatabaseInfo(request.user)
        return Response(status=200, data=databaseInfo)

class QueryPatientList(RestViews.APIView):
    """ Query list of accessible patients in database.

    **POST**: ``/api/queryPatients``

    Returns:
      Response Code 200.
      Response Body contains list of patient object. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Patients = Database.extractPatientList(request.user)
        return Response(status=200, data=Patients)

class QueryPatientInfo(RestViews.APIView):
    """ Query detailed patient information.

    **POST**: ``/api/queryPatientInfo``

    Args:
      id (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.

    Returns:
      Response Code 200.
      Response Body contains a single patient object with detailed information.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if Authority["Level"] == 1:
            Patient = Database.extractPatientInfo(request.user, request.data["id"])
            Patient["AvailableTags"] = Database.extractTags("Patient", request.user.institute)
            return Response(status=200, data=Patient)

        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
            Patient = Database.extractPatientInfo(request.user, PatientInfo.deidentified_id)
            Patient["Devices"] = deidentification["Devices"]
            Patient["AvailableTags"] = Database.extractTags("Patient", request.user.email)
            return Response(status=200, data=Patient)

class QueryTherapyHistory(RestViews.APIView):
    """ Query all therapy histories from desired patient.

    The therapy histories include both therapy change logs and clinician configurations. 

    The therapy histories do not include how patient adjust their stimulation amplitude within range 
    because this information is not saved.
    If BrainSense is enabled, user may query the stimulation amplitude changes through Chronic BrainSense.

    **POST**: ``/api/queryTherapyHistory``

    Args:
      id (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains list of all Therapy Change Logs and Therapy Configurations.
    """
    
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "id" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            PatientID = request.data["id"]
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, PatientID, Authority, "TherapyHistory")
            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, PatientID)
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "TherapyHistory")
                PatientID = PatientInfo.authorized_patient_id

            TherapyChangeLogs = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
            TherapyConfigurations = Therapy.queryTherapyConfigurations(request.user, PatientID, Authority, therapyType="")
            TherapyConfigurations = Therapy.extractTherapyDetails(TherapyConfigurations, TherapyChangeLog=TherapyChangeLogs, resolveConflicts=False)
            return Response(status=200, data={"TherapyChangeLogs": TherapyChangeLogs, "TherapyConfigurations": TherapyConfigurations})

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class QueryBrainSenseSurveys(RestViews.APIView):
    """ Query all BrainSense Survey data.

    The BrainSense Survey query will return processed power spectral density calculated from time-domain data. 
    This is not the same as the on-board FFT result shown on Medtronic Tablet. 

    Raw time-domain data will not be returned from this route.

    **POST**: ``/api/queryBrainSenseSurveys``

    Args:
      id (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains list of all BrainSense Surveys.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "id" in request.data:
            Authority = {}

            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseSurvey")
                data = BrainSenseSurvey.querySurveyResults(request.user, request.data["id"], Authority)
                return Response(status=200, data=data)

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseSurvey")
                data = BrainSenseSurvey.querySurveyResults(request.user, PatientInfo.authorized_patient_id, Authority)
                return Response(status=200, data=data)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})


class QueryBrainSenseStreaming(RestViews.APIView):
    """ Query BrainSense Streaming Data.

    The BrainSense Streaming query allows for multiple type of requests, based on what is sent in request body. 

    **POST**: ``/api/queryBrainSenseStreaming``

    **Request List of Available BrainSense Streaming Data**
    
    .. code-block:: json

      {
        "requestOverview": true,
        "id": "(uuid)",
      }

    **Request specific BrainSense Streaming Recording based on recording ID**
    
    ``requestFrequency`` is optional if user want to request power value from different frequency instead of the automated algorithm
      
    .. code-block:: json

      {
        "requestData": true,
        "id": "(uuid)",
        "recordingId": "(uuid)",
        "[requestFrequency]": "(int)"
      }

    **Request update on power spectrum data for rendering**

    .. Note::
      
      Version 1.0.0 support ipsilateral/contralateral request, but 2.0.0-alpha has not implemented it yet. 
    
    ``channel`` is the Medtronic convention of channel identification, which is usually CONTACT_CONTACT_HEMISPHERE (i.e.: ZERO_TWO_LEFT)

    This is a faster operation than request BrainSense Streaming Recording using ``requestFrequency`` because
    this operation does not transmit raw data.

    .. code-block:: json

      {
        "updateStimulationPSD": true,
        "id": "(uuid)",
        "recordingId": "(uuid)",
        "channel": "(string)",
        "centerFrequency": "(int)",
      }

    **Update BrainSense Streaming result with or without cardiac filter**

    Permission denied unless you are the data owner (Permission == 1)

    .. code-block:: json

      {
        "updateCardiacFilter": "(boolean)",
        "id": "(uuid)",
        "recordingId": "(uuid)"
      }

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains requested data, often large due to time-domain data transmission.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not "ProcessingSettings" in request.user.configuration:
            request.user.configuration["ProcessingSettings"] = Database.retrieveProcessingSettings(request.user.configuration)
            request.user.save()

        if "requestOverview" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = {}
                data["streamingData"] = BrainSenseStream.queryRealtimeStreamOverview(request.user, request.data["id"], Authority)
                data["configuration"] = request.user.configuration["ProcessingSettings"]["RealtimeStream"]
                return Response(status=200, data=data)
            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                data = {}
                data["streamingData"] = BrainSenseStream.queryRealtimeStreamOverview(request.user, PatientInfo.authorized_patient_id, Authority)
                data["configuration"] = request.user.configuration["ProcessingSettings"]["RealtimeStream"]
                return Response(status=200, data=data)

        elif "requestData" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if "requestFrequency" in request.data:
                centerFrequencies = request.data["requestFrequency"]
            else:
                centerFrequencies = [0,0]

            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                data = BrainSenseStream.processRealtimeStreamRenderingData(BrainSenseData, request.user.configuration["ProcessingSettings"]["RealtimeStream"], centerFrequencies=centerFrequencies)
                return Response(status=200, data=data)

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])

                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                if not request.data["recordingId"] in Authority["Permission"]:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                data = BrainSenseStream.processRealtimeStreamRenderingData(BrainSenseData, request.user.configuration["ProcessingSettings"]["RealtimeStream"], centerFrequencies=centerFrequencies)
                return Response(status=200, data=data)

        elif "updateStimulationPSD" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                BrainSenseData["Stimulation"] = BrainSenseStream.processRealtimeStreamStimulationAmplitude(BrainSenseData)
                StimPSD = BrainSenseStream.processRealtimeStreamStimulationPSD(BrainSenseData, request.data["channel"], method=request.user.configuration["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"], stim_label="Ipsilateral", centerFrequency=request.data["centerFrequency"])
                return Response(status=200, data=StimPSD)

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])

                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                if not request.data["recordingId"] in Authority["Permission"]:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                BrainSenseData["Stimulation"] = BrainSenseStream.processRealtimeStreamStimulationAmplitude(BrainSenseData)
                StimPSD = BrainSenseStream.processRealtimeStreamStimulationPSD(BrainSenseData, request.data["channel"], method=request.user.configuration["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"], stim_label="Ipsilateral", centerFrequency=request.data["centerFrequency"])
                return Response(status=200, data=StimPSD)

        elif "updateCardiacFilter" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0 or Authority["Level"] == 2:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")

            BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=True, cardiacFilter=request.data["updateCardiacFilter"])
            if BrainSenseData == None:
                return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
            data = BrainSenseStream.processRealtimeStreamRenderingData(BrainSenseData, request.user.configuration["ProcessingSettings"]["RealtimeStream"])
            return Response(status=200, data=data)

        elif "updateWaveletTransform" in request.data:
            request.user.configuration["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"] = request.data["updateWaveletTransform"]
            request.user.save()

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0 or Authority["Level"] == 2:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")

            BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority)
            if BrainSenseData == None:
                return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
            data = BrainSenseStream.processRealtimeStreamRenderingData(BrainSenseData, request.user.configuration["ProcessingSettings"]["RealtimeStream"])
            return Response(status=200, data=data)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class QueryIndefiniteStreaming(RestViews.APIView):
    """ Query all Indefinite Streaming Data.

    The Indefinite Streaming query allows for multiple type of requests, based on what is sent in request body. 

    **POST**: ``/api/queryIndefiniteStreaming``

    **Request List of Available Indefinite Streaming Data**
    
    .. code-block:: json

      {
        "requestOverview": true,
        "id": "(uuid)",
      }

    **Request specific Indefinite Streaming Recording based on list of provided devices and timestamps**
    
    .. code-block:: json

      {
        "requestData": true,
        "id": "(uuid)",
        "timestamps": ["(int)"],
        "devices": ["(uuid)"]
      }

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains requested data, often large due to time-domain data transmission.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "requestOverview" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "IndefiniteStream")
                data = IndefiniteStream.queryMontageDataOverview(request.user, request.data["id"], Authority)
                return Response(status=200, data=data)
            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "IndefiniteStream")
                data = IndefiniteStream.queryMontageDataOverview(request.user, PatientInfo.authorized_patient_id, Authority)
                return Response(status=200, data=data)

        elif "requestData" in request.data:
            timestamps = request.data["timestamps"]
            devices = request.data["devices"]

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            PatientID = request.data["id"]
            if Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                DeviceIDs = [deidentification["Devices"][i]["ID"] for i in range(len(deidentification["Devices"]))]
                for device in devices:
                    if not device in DeviceIDs:
                        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                PatientID = PatientInfo.authorized_patient_id

            Authority["Permission"] = Database.verifyPermission(request.user, PatientID, Authority, "IndefiniteStream")
            data = IndefiniteStream.queryMontageData(request.user, devices, timestamps, Authority)
            return Response(status=200, data=data)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class QueryChronicBrainSense(RestViews.APIView):
    """ Query all Chronic BrainSense Data.

    The Chronic BrainSense data includes single power-band recorded using BrainSense-enabled group,
    patient-reported events and event power spectrums. 

    **POST**: ``/api/queryChronicBrainSense``

    Args:
      id (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.
      requestData (boolean): Always true to request data.
      timezoneOffset (int): seconds offset compare to Universal Time Coordinate. 
        You can request this value from your browser through ``new Date().getTimezoneOffset()*60``.

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains Chronic BrainSense and Event PSDs. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "requestData" in request.data and "timezoneOffset" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=404)

            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
                PatientID = request.data["id"]

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
                PatientID = PatientInfo.authorized_patient_id

            data = dict()
            TherapyHistory = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
            data["ChronicData"] = ChronicBrainSense.queryChronicLFPs(request.user, PatientID, TherapyHistory, Authority)
            data["EventPSDs"] = BrainSenseEvent.queryPatientEventPSDs(request.user, PatientID, TherapyHistory, Authority)

            data["ChronicData"] = ChronicBrainSense.processChronicLFPs(data["ChronicData"], int(request.data["timezoneOffset"]))
            data["EventPSDs"] = BrainSenseEvent.processEventPSDs(data["EventPSDs"])

            return Response(status=200, data=data)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class QuerySessionOverview(RestViews.APIView):
    """ Query all JSON sessions related to a patient.

    This route will provide user with all JSON files uploaded related to a specific patient ID. 
    This is useful to identify raw unprocessed file for analysis outside of the web platform.

    User may also request deletion of session file (and all associated data) by requesting deletion.

    **POST**: ``/api/querySessionOverview``

    Args:
      id (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains nothing if deleteSession is requested, otherwise contain list of available session files.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not "id" in request.data:
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=404)

        elif Authority["Level"] == 1:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
            PatientID = request.data["id"]

        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
            PatientID = PatientInfo.authorized_patient_id

        data = dict()
        data["AvailableSessions"] = Sessions.queryAvailableSessionFiles(request.user, PatientID, Authority)
        return Response(status=200, data=data)

class QueryPredictionModel(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Force Error
        if not request.user.is_clinician:
            return Response(status=400, data={"code": ERROR_CODE["NOT_AVAILABLE_TO_DEMO"]})

        if "requestOverview" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=404)
            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = BrainSenseStream.queryRealtimeStreamOverview(request.user, request.data["id"], Authority)
                return Response(status=200, data=data)
            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                data = BrainSenseStream.queryRealtimeStreamOverview(request.user, PatientInfo.authorized_patient_id, Authority)
                return Response(status=200, data=data)

        elif "updatePredictionModels" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=403)

            if Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                DeviceIDs = [deidentification["Devices"][i]["ID"] for i in range(len(deidentification["Devices"]))]
                if not request.data["requestData"] in DeviceIDs:
                    return Response(status=403)
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
            else:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")

            BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
            if BrainSenseData == None:
                return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
            BrainSenseData["Stimulation"] = BrainSenseStream.processRealtimeStreamStimulationAmplitude(BrainSenseData)

            data = list()
            for stimulationSide in BrainSenseData["Stimulation"]:
                if len(np.unique(stimulationSide["Amplitude"])) > 3:
                    if not models.PredictionModel.objects.filter(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"]).exists():
                        Features = TherapeuticPrediction.extractPredictionFeatures(BrainSenseData, stimulationSide["Hemisphere"])
                        PredictionModel = models.PredictionModel(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"], model_details=Features)
                        PredictionModel.save()
                    else:
                        PredictionModel = models.PredictionModel.objects.filter(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"]).first()
                        Features = PredictionModel.model_details
                        Features = TherapeuticPrediction.extractPredictionFeatures(BrainSenseData, stimulationSide["Hemisphere"])
                        PredictionModel.model_details = Features
                        PredictionModel.save()
                    data.append(Features)
                else:
                    data.append({"NoPrediction": True})
                
            return Response(status=200, data=data)

        elif "updateStimulationPSD" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                BrainSenseData, RecordingID = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                BrainSenseData["Stimulation"] = BrainSenseStream.processRealtimeStreamStimulationAmplitude(BrainSenseData)
                
                data = dict()
                data["StimPSD"] = BrainSenseStream.processRealtimeStreamStimulationPSD(BrainSenseData, request.data["channel"], method=request.session["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"], stim_label="Ipsilateral", centerFrequency=request.data["centerFrequency"])
                
                if not "CenterFrequency" in BrainSenseData["Info"]:
                    BrainSenseData["Info"]["CenterFrequency"] = dict()
                BrainSenseData["Info"]["CenterFrequency"][request.data["channel"]] = request.data["centerFrequency"]
                models.BrainSenseRecording.objects.filter(recording_id=RecordingID).update(recording_info=BrainSenseData["Info"])

                for stimulationSide in BrainSenseData["Stimulation"]:
                    if len(np.unique(stimulationSide["Amplitude"])) > 3 and stimulationSide["Name"] == request.data["channel"]:
                        Features = TherapeuticPrediction.extractPredictionFeatures(BrainSenseData, stimulationSide["Hemisphere"], centerFrequency=request.data["centerFrequency"])
                        PredictionModel = models.PredictionModel.objects.filter(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"]).first()
                        PredictionModel.model_details = Features
                        PredictionModel.save()
                    else:
                        Features = {"NoPrediction": True}

                data["PredictionModel"] = Features
                return Response(status=200, data=data)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class QueryMultipleSegmentComparison(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        # Force Error
        if not request.user.is_clinician:
            return Response(status=400, data={"code": ERROR_CODE["NOT_AVAILABLE_TO_DEMO"]})

        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if Authority["Level"] == 1:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")

            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            Authority["Devices"] = PatientInfo.device_deidentified_id

            data = BrainSenseStream.queryMultipleSegmentComparison(request.user, request.data["recordingIds"], Authority)
            return Response(status=200, data=data)

        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["id"])

            Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
            if not request.data["recordingId"] in Authority["Permission"]:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            data ={}
            # DO SOMETHING

            return Response(status=200, data=data)
        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class QueryPatientEvents(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=404)

        elif Authority["Level"] == 1:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
            PatientID = request.data["id"]

        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
            PatientID = PatientInfo.authorized_patient_id

        data = dict()
        data["EventPSDs"] = BrainSenseEvent.getAllPatientEvents(request.user, PatientID, Authority)
        return Response(status=200, data=data)

class QueryImageModelDirectory(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=404)

        elif Authority["Level"] == 1:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
            PatientID = request.data["id"]

        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "Imaging")
            PatientID = PatientInfo.authorized_patient_id

        data = ImageDatabase.extractAvailableModels(PatientID, Authority)
        return Response(status=200, data=data)

class QueryImageModel(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["Directory"])
        if Authority["Level"] == 0:
            return Response(status=404)

        elif Authority["Level"] == 1:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["Directory"], Authority, "ChronicLFPs")
            PatientID = request.data["Directory"]

        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["Directory"])
            Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "Imaging")
            if not request.data["FileName"] in Authority["Permission"]:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            PatientID = PatientInfo.authorized_patient_id

        if request.data["FileMode"] == "single":
            if request.data["FileType"] == "stl":
                file_data = ImageDatabase.stlReader(PatientID, request.data["FileName"])
                if not file_data:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                return HttpResponse(bytes(file_data), status=200, headers={
                    "Content-Type": "application/octet-stream"
                })

            elif request.data["FileType"] == "tracts":
                tracts = ImageDatabase.tractReader(PatientID, request.data["FileName"])
                if not tracts:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                return Response(status=200, data={
                    "points": tracts
                })
            
            elif request.data["FileType"] == "electrode":
                file_data = ImageDatabase.stlReader("Electrodes/" + request.data["ElectrodeName"], request.data["FileName"])
                if not file_data:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                return HttpResponse(bytes(file_data), status=200, headers={
                    "Content-Type": "application/octet-stream"
                })

        elif request.data["FileMode"] == "multiple":
            if request.data["FileType"] == "electrode":
                pages = ImageDatabase.electrodeReader(request.data["FileName"])
                return Response(status=200, data={"pages": pages, "color": "0x000000"})
            

class QueryAdaptiveGroups(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not "id" in request.data:
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0 or Authority["Level"] == 2:
            return Response(status=404)

        elif Authority["Level"] == 1:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
            PatientID = request.data["id"]

        data = Therapy.queryAdaptiveGroupForThreshold(request.user, PatientID, Authority)
        return Response(status=200, data=data)

class QueryCircadianPower(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "id" in request.data and "timezoneOffset" in request.data and "therapyInfo" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=404)

            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
                PatientID = request.data["id"]

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
                PatientID = PatientInfo.authorized_patient_id

            data = dict()
            TherapyHistory = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
            data["ChronicData"] = ChronicBrainSense.queryChronicLFPs(request.user, PatientID, TherapyHistory, Authority)
            data["EventPSDs"] = BrainSenseEvent.queryPatientEventPSDs(request.user, PatientID, TherapyHistory, Authority)
            data["CircadianPower"] = ChronicBrainSense.processCircadianPower(data["ChronicData"], request.data["therapyInfo"], int(request.data["timezoneOffset"]))
            return Response(status=200, data=data["CircadianPower"])

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
