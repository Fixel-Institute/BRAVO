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

from modules import Database, ImageDatabase, AnalysisBuilder, WearableRecordingsDatabase, Therapy, RealtimeStream
from modules.Percept import Sessions, BrainSenseSurvey, BrainSenseEvent, BrainSenseStream, IndefiniteStream, ChronicBrainSense, TherapeuticPrediction, AdaptiveStimulation
from modules.Summit import ChronicLogs, StreamingData
from utility.PythonUtility import uniqueList
import json
import numpy as np
import nibabel as nib
import pytz
from datetime import datetime

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

class QueryPatientAccessTable(RestViews.APIView):
    """ Query list of accessible patients in database.

    **POST**: ``/api/queryPatientAccessTable``

    Returns:
      Response Code 200.
      Response Body contains list of patient object with access information. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Patients = Database.extractPatientAccessTable(request.user)
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
            deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id, deidentifiedId=PatientInfo.deidentified_id)
            Patient = Database.extractPatientInfo(request.user, PatientInfo.deidentified_id)
            Patient["Devices"] = deidentification["Devices"]
            Patient["AvailableTags"] = Database.extractTags("Patient", request.user.email)
            return Response(status=200, data=Patient)

class QueryProcessingQueue(RestViews.APIView):
    """ Query current processing queue list

    **POST**: ``/api/queryProcessingQueue``

    Returns:
      Response Code 200.
      Response Body contains list of processing queue items owned by the request owner.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "clearQueue" in request.data:
            if request.data["clearQueue"] == "All":
                queues = models.ProcessingQueue.objects.filter(owner=request.user.unique_user_id, type__in=["decodeJSON", "decodeSummitZIP", "externalCSVs"])
                for queue in queues:
                    try:
                        os.remove(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"])
                    except:
                        pass
                    queue.delete()
            else:
                queues = models.ProcessingQueue.objects.filter(owner=request.user.unique_user_id, type__in=["decodeJSON", "decodeSummitZIP", "externalCSVs"], state=request.data["clearQueue"]).delete()
            return Response(status=200)
        else:
            queues = models.ProcessingQueue.objects.all()
            data = []
            for i in range(len(queues)):
                if queues[i].owner == request.user.unique_user_id and queues[i].type in ["decodeJSON", "decodeSummitZIP", "externalCSVs"]:
                    data.append({
                        "currentIndex": i,
                        "taskId": queues[i].queue_id,
                        "type": queues[i].type,
                        "since": queues[i].datetime.timestamp(),
                        "state": queues[i].state,
                        "descriptor": queues[i].descriptor,
                    })

            return Response(status=200, data=data)

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
            Impedance = Therapy.queryImpedanceHistory(request.user, PatientID, Authority)
            return Response(status=200, data={"TherapyChangeLogs": TherapyChangeLogs, "TherapyConfigurations": TherapyConfigurations, "Impedance": Impedance})

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
            request.user.configuration["ProcessingSettings"], changed = Database.retrieveProcessingSettings(request.user.configuration)
            if not changed:
                request.user.save()

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseSurvey")
                data = BrainSenseSurvey.querySurveyResults(request.user, request.data["id"], request.user.configuration["ProcessingSettings"]["BrainSenseSurvey"], "requestRaw" in request.data, Authority)
                return Response(status=200, data={"data": data, "config": request.user.configuration["ProcessingSettings"]["BrainSenseSurvey"]})

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseSurvey")
                data = BrainSenseSurvey.querySurveyResults(request.user, PatientInfo.authorized_patient_id, request.user.configuration["ProcessingSettings"]["BrainSenseSurvey"], "requestRaw" in request.data, Authority)
                return Response(status=200, data={"data": data, "config": request.user.configuration["ProcessingSettings"]["BrainSenseSurvey"]})

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
        "stimulationReference": "(string)",
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
        request.user.configuration["ProcessingSettings"], changed = Database.retrieveProcessingSettings(request.user.configuration)
        if not changed:
            request.user.save()

        if "requestOverview" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = {}
                data["streamingData"] = RealtimeStream.queryRealtimeStreamOverview(request.user, request.data["id"], Authority)
                data["annotations"] = Database.extractTags("Annotations", request.user.email)
                data["configuration"] = request.user.configuration["ProcessingSettings"]["RealtimeStream"]
                return Response(status=200, data=data)
            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                data = {}
                data["streamingData"] = RealtimeStream.queryRealtimeStreamOverview(request.user, PatientInfo.authorized_patient_id, Authority)
                data["annotations"] = Database.extractTags("Annotations", request.user.email)
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
                BrainSenseData, _ = RealtimeStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                
                annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=request.data["id"], 
                                                                    event_time__gte=datetime.fromtimestamp(BrainSenseData["TimeDomain"]["StartTime"], tz=pytz.utc), 
                                                                    event_time__lte=datetime.fromtimestamp(BrainSenseData["TimeDomain"]["StartTime"]+BrainSenseData["TimeDomain"]["Duration"], tz=pytz.utc))
                BrainSenseData["Annotations"] = [{
                    "Name": item.event_name,
                    "Time": item.event_time.timestamp(),
                    "Duration": item.event_duration
                } for item in annotations]

                data = RealtimeStream.processRealtimeStreamRenderingData(BrainSenseData, request.user.configuration["ProcessingSettings"]["RealtimeStream"], centerFrequencies=centerFrequencies)
                data = RealtimeStream.processAnnotationAnalysis(data)
                return Response(status=200, data=data)

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])

                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                BrainSenseData, _ = RealtimeStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                
                annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=PatientInfo.authorized_patient_id, 
                                                                    event_time__gte=datetime.fromtimestamp(BrainSenseData["TimeDomain"]["StartTime"], tz=pytz.utc), 
                                                                    event_time__lte=datetime.fromtimestamp(BrainSenseData["TimeDomain"]["StartTime"]+BrainSenseData["TimeDomain"]["Duration"], tz=pytz.utc))
                BrainSenseData["Annotations"] = [{
                    "Name": item.event_name,
                    "Time": item.event_time.timestamp(),
                    "Duration": item.event_duration
                } for item in annotations]

                data = RealtimeStream.processRealtimeStreamRenderingData(BrainSenseData, request.user.configuration["ProcessingSettings"]["RealtimeStream"], centerFrequencies=centerFrequencies)
                data = RealtimeStream.processAnnotationAnalysis(data)
                return Response(status=200, data=data)

        elif "updateStimulationPSD" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                BrainSenseData, _ = RealtimeStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                
                if BrainSenseData["Info"]["Device"] == "Summit RC+S":
                    BrainSenseData["PowerDomain"]["Stimulation"] = StreamingData.processRealtimeStreamStimulationAmplitude(BrainSenseData["PowerDomain"])
                    ChannelName = request.data["channel"]["Hemisphere"].split(" ")[0] + " " + request.data["channel"]["Contacts"]
                    StimPSD = StreamingData.processRealtimeStreamStimulationPSD(BrainSenseData, ChannelName, method=request.user.configuration["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"], stim_label=request.data["stimulationReference"], centerFrequency=request.data["centerFrequency"])
                else:
                    BrainSenseData["PowerDomain"]["Stimulation"] = BrainSenseStream.processRealtimeStreamStimulationAmplitude(BrainSenseData["PowerDomain"])
                    ContactDict = {0: "ZERO", 1: "ONE", 2: "TWO", 3: "THREE"}
                    ChannelName = ContactDict[request.data["channel"]["Contacts"][0]] + "_" + ContactDict[request.data["channel"]["Contacts"][1]] + "_" + request.data["channel"]["Hemisphere"].split(" ")[0].upper()
                    
                    if request.user.configuration["ProcessingSettings"]["RealtimeStream"]["PSDMethod"]["value"] == "Time-Frequency Analysis":
                        StimPSD = BrainSenseStream.processRealtimeStreamStimulationPSD(BrainSenseData, ChannelName, method=request.user.configuration["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"], stim_label=request.data["stimulationReference"], centerFrequency=request.data["centerFrequency"])
                    else:
                        StimPSD = BrainSenseStream.processRealtimeStreamStimulationPSD(BrainSenseData, ChannelName, method=request.user.configuration["ProcessingSettings"]["RealtimeStream"]["PSDMethod"]["value"], stim_label=request.data["stimulationReference"], centerFrequency=request.data["centerFrequency"])

                return Response(status=200, data=StimPSD)

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])

                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                BrainSenseData, _ = RealtimeStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                BrainSenseData["PowerDomain"]["Stimulation"] = RealtimeStream.processRealtimeStreamStimulationAmplitude(BrainSenseData["PowerDomain"])
                StimPSD = RealtimeStream.processRealtimeStreamStimulationPSD(BrainSenseData, request.data["channel"], method=request.user.configuration["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"], stim_label=request.data["stimulationReference"], centerFrequency=request.data["centerFrequency"])
                return Response(status=200, data=StimPSD)

        elif "updateCardiacFilter" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0 or Authority["Level"] == 2:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")

            BrainSenseData, _ = RealtimeStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=True, cardiacFilter=request.data["updateCardiacFilter"])
            if BrainSenseData == None:
                return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
            
            annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=request.data["id"], 
                                                                    event_time__gte=datetime.fromtimestamp(BrainSenseData["TimeDomain"]["StartTime"], tz=pytz.utc), 
                                                                    event_time__lte=datetime.fromtimestamp(BrainSenseData["TimeDomain"]["StartTime"]+BrainSenseData["TimeDomain"]["Duration"], tz=pytz.utc))
            BrainSenseData["Annotations"] = [{
                "Name": item.event_name,
                "Time": item.event_time.timestamp(),
                "Duration": item.event_duration
            } for item in annotations]

            data = RealtimeStream.processRealtimeStreamRenderingData(BrainSenseData, request.user.configuration["ProcessingSettings"]["RealtimeStream"])
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

            BrainSenseData, _ = RealtimeStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority)
            if BrainSenseData == None:
                return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
            
            annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=request.data["id"], 
                                                                    event_time__gte=datetime.fromtimestamp(BrainSenseData["TimeDomain"]["StartTime"], tz=pytz.utc), 
                                                                    event_time__lte=datetime.fromtimestamp(BrainSenseData["TimeDomain"]["StartTime"]+BrainSenseData["TimeDomain"]["Duration"], tz=pytz.utc))
            BrainSenseData["Annotations"] = [{
                "Name": item.event_name,
                "Time": item.event_time.timestamp(),
                "Duration": item.event_duration
            } for item in annotations]
            
            data = RealtimeStream.processRealtimeStreamRenderingData(BrainSenseData, request.user.configuration["ProcessingSettings"]["RealtimeStream"])
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
        request.user.configuration["ProcessingSettings"], changed = Database.retrieveProcessingSettings(request.user.configuration)
        if not changed:
            request.user.save()

        if "requestOverview" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "IndefiniteStream")
                data = IndefiniteStream.queryMontageDataOverview(request.user, request.data["id"], Authority)
                if len(data) > 0:
                    data[0]["annotations"] = Database.extractTags("Annotations", request.user.email)
                return Response(status=200, data={
                    "data": data,
                    "config": request.user.configuration["ProcessingSettings"]["IndefiniteStream"]
                })
            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "IndefiniteStream")
                data = IndefiniteStream.queryMontageDataOverview(request.user, PatientInfo.authorized_patient_id, Authority)
                if len(data) > 0:
                    data[0]["annotations"] = Database.extractTags("Annotations", request.user.email)
                return Response(status=200, data={
                    "data": data,
                    "config": request.user.configuration["ProcessingSettings"]["IndefiniteStream"]
                })

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
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id, deidentifiedId=request.data["id"])
                DeviceIDs = [str(deidentification["Devices"][i]["ID"]) for i in range(len(deidentification["Devices"]))]
                for device in devices:
                    if not device in DeviceIDs:
                        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                
                PatientID = PatientInfo.authorized_patient_id

            Authority["Permission"] = Database.verifyPermission(request.user, PatientID, Authority, "IndefiniteStream")
            data = IndefiniteStream.queryMontageData(request.user, devices, timestamps, Authority)

            for i in range(len(data)):
                annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=PatientID, 
                                                                    event_time__gte=datetime.fromtimestamp(data[i]["Timestamp"], tz=pytz.utc), 
                                                                    event_time__lte=datetime.fromtimestamp(data[i]["Timestamp"]+data[i]["Duration"], tz=pytz.utc))
                data[i]["Annotations"] = [{
                    "Name": item.event_name,
                    "Time": item.event_time.timestamp(),
                    "Duration": item.event_duration
                } for item in annotations]
            EventPSDs, EventOnsetSpectrum = IndefiniteStream.processAnnotationAnalysis(data)

            if len(data) == 0:
                return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

            return Response(status=200, data={
                "data": data, 
                "eventPSDs": EventPSDs,
                "eventOnsetSpectrum": EventOnsetSpectrum
            })

        elif "requestEventData" in request.data:
            timestamps = request.data["timestamps"]
            devices = request.data["devices"]

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            PatientID = request.data["id"]
            if Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id, deidentifiedId=request.data["id"])
                DeviceIDs = [str(deidentification["Devices"][i]["ID"]) for i in range(len(deidentification["Devices"]))]
                for device in devices:
                    if not device in DeviceIDs:
                        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                
                PatientID = PatientInfo.authorized_patient_id

            Authority["Permission"] = Database.verifyPermission(request.user, PatientID, Authority, "IndefiniteStream")
            data = IndefiniteStream.queryMontageData(request.user, devices, timestamps, Authority)

            for i in range(len(data)):
                annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=PatientID, 
                                                                    event_time__gte=datetime.fromtimestamp(data[i]["Timestamp"], tz=pytz.utc), 
                                                                    event_time__lte=datetime.fromtimestamp(data[i]["Timestamp"]+data[i]["Duration"], tz=pytz.utc))
                data[i]["Annotations"] = [{
                    "Name": item.event_name,
                    "Time": item.event_time.timestamp(),
                    "Duration": item.event_duration
                } for item in annotations]
            EventPSDs, EventOnsetSpectrum = IndefiniteStream.processAnnotationAnalysis(data)

            return Response(status=200, data={
                "eventPSDs": EventPSDs,
                "eventOnsetSpectrum": EventOnsetSpectrum
            })

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
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id, deidentifiedId=request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
                PatientID = PatientInfo.authorized_patient_id

            data = dict()
            availableDevices = Database.getPerceptDevices(request.user, PatientID, Authority)
            DeviceTypes = [device.device_type for device in availableDevices]
            if "Summit RC+S" in DeviceTypes:
                TherapyHistory = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
                data["ChronicData"] = ChronicLogs.queryChronicLFPs(request.user, PatientID, TherapyHistory, Authority)
                data["ChronicData"] = ChronicLogs.processChronicLFPs(data["ChronicData"], int(request.data["timezoneOffset"]))
            else:
                TherapyHistory = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
                data["ChronicData"] = ChronicBrainSense.queryChronicLFPs(request.user, PatientID, TherapyHistory, Authority)
                data["EventPSDs"] = BrainSenseEvent.queryPatientEventPSDs(request.user, PatientID, TherapyHistory, Authority)
                data["ChronicData"] = ChronicBrainSense.processChronicLFPs(data["ChronicData"], int(request.data["timezoneOffset"]))
                data["EventPSDs"] = BrainSenseEvent.processEventPSDs(data["EventPSDs"])

            return Response(status=200, data=data)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class QueryAdaptiveStimulation(RestViews.APIView):
    """ Query all Chronic BrainSense Data.

    The Chronic BrainSense data includes single power-band recorded using BrainSense-enabled group,
    patient-reported events and event power spectrums. 

    **POST**: ``/api/queryAdaptiveStimulation``

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
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id, deidentifiedId=request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
                PatientID = PatientInfo.authorized_patient_id

            data = dict()
            TherapyHistory = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
            data["ChronicData"] = ChronicBrainSense.queryChronicLFPs(request.user, PatientID, TherapyHistory, Authority)
            data["ChronicData"] = AdaptiveStimulation.processAdaptiveDutyCycle(data["ChronicData"], int(request.data["timezoneOffset"]))
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
        if not (request.user.is_admin or request.user.is_clinician):
            return Response(status=400, data={"code": ERROR_CODE["NOT_AVAILABLE_TO_DEMO"]})

        if "requestOverview" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=404)
            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = RealtimeStream.queryRealtimeStreamOverview(request.user, request.data["id"], Authority)
                data = [item for item in data if item["Duration"] > 30]
                return Response(status=200, data=data)
            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                data = RealtimeStream.queryRealtimeStreamOverview(request.user, PatientInfo.authorized_patient_id, Authority)
                data = [item for item in data if item["Duration"] > 30]
                return Response(status=200, data=data)

        elif "updatePredictionModels" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=403)

            if Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.data["id"])
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id, deidentifiedId=request.data["id"])
                DeviceIDs = [str(deidentification["Devices"][i]["ID"]) for i in range(len(deidentification["Devices"]))]
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
            else:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")

            BrainSenseData, _ = RealtimeStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
            if BrainSenseData == None:
                return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
            BrainSenseData["PowerDomain"]["Stimulation"] = RealtimeStream.processRealtimeStreamStimulationAmplitude(BrainSenseData["PowerDomain"])

            data = list()
            for stimulationSide in BrainSenseData["PowerDomain"]["Stimulation"]:
                if len(np.unique(stimulationSide["Amplitude"])) > 3:
                    Features = TherapeuticPrediction.extractPredictionFeatures(BrainSenseData, stimulationSide["Hemisphere"])
                    #PredictionModel = models.PredictionModel(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"], model_details=Features)
                    #PredictionModel.save()
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
                BrainSenseData, RecordingID = RealtimeStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                BrainSenseData["PowerDomain"]["Stimulation"] = RealtimeStream.processRealtimeStreamStimulationAmplitude(BrainSenseData["PowerDomain"])
                
                data = dict()
                data["StimPSD"] = RealtimeStream.processRealtimeStreamStimulationPSD(BrainSenseData, request.data["channel"], method=request.user.configuration["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"], stim_label="Ipsilateral", centerFrequency=request.data["centerFrequency"])
                
                if not "CenterFrequency" in BrainSenseData["Info"]:
                    BrainSenseData["Info"]["CenterFrequency"] = dict()
                BrainSenseData["Info"]["CenterFrequency"][request.data["channel"]] = request.data["centerFrequency"]
                models.BrainSenseRecording.objects.filter(recording_id=RecordingID).update(recording_info=BrainSenseData["Info"])

                for stimulationSide in BrainSenseData["PowerDomain"]["Stimulation"]:
                    if len(np.unique(stimulationSide["Amplitude"])) > 3 and stimulationSide["Name"] == request.data["channel"]:
                        Features = TherapeuticPrediction.extractPredictionFeatures(BrainSenseData, stimulationSide["Hemisphere"], centerFrequency=request.data["centerFrequency"])
                        #PredictionModel = models.PredictionModel.objects.filter(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"]).first()
                        #PredictionModel.model_details = Features
                        #PredictionModel.save()
                        break
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
        if not (request.user.is_admin or request.user.is_clinician):
            return Response(status=400, data={"code": ERROR_CODE["NOT_AVAILABLE_TO_DEMO"]})

        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if Authority["Level"] == 1:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")

            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            Authority["Devices"] = PatientInfo.device_deidentified_id

            data = RealtimeStream.queryMultipleSegmentComparison(request.user, request.data["recordingIds"], Authority)
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

class QueryCustomAnnotations(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        elif Authority["Level"] == 1:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
            PatientID = request.data["id"]

        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
            PatientID = PatientInfo.authorized_patient_id
        
        if "requestOverview" in request.data:
            pass 

        elif "addEvent" in request.data:
            annotation = models.CustomAnnotations(patient_deidentified_id=PatientID, 
                                     event_name=request.data["name"], 
                                     event_time=datetime.fromtimestamp(request.data["time"],tz=pytz.utc),
                                     event_duration=request.data["duration"])
            models.SearchTags.objects.get_or_create(tag_name=request.data["name"], tag_type="Annotations", institute=request.user.email)
            annotation.save()
            return Response(status=200)

        elif "deleteEvent" in request.data:
            annotation = models.CustomAnnotations.objects.filter(patient_deidentified_id=PatientID, 
                                     event_name=request.data["name"], 
                                     event_time=datetime.fromtimestamp(request.data["time"],tz=pytz.utc)).first()
            if annotation:
                annotation.delete()
                return Response(status=200)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
    
class QueryCustomizedAnalysis(RestViews.APIView):
    """ Query Customized Analysis.

    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        request.user.configuration["ProcessingSettings"], changed = Database.retrieveProcessingSettings(request.user.configuration)
        if not changed:
            request.user.save()

        if "requestOverview" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = AnalysisBuilder.getExistingAnalysis(request.user, request.data["id"], Authority)
                return Response(status=200, data=data)

        elif "requestNewAnalysis" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                if request.data["requestNewAnalysis"]:
                    data = AnalysisBuilder.addNewAnalysis(request.user, request.data["id"], Authority)
                else:
                    data = AnalysisBuilder.deleteAnalysis(request.user, request.data["id"], request.data["analysisId"], Authority)
                return Response(status=200, data=data)

        elif "editAnalysis" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                analysis = models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=request.data["id"]).first()
                if not analysis:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                analysis.analysis_name = request.data["name"]
                analysis.save()
                return Response(status=200)

        elif "requestAnalysis" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = AnalysisBuilder.queryAnalysis(request.user, request.data["id"], request.data["requestAnalysis"], Authority)
                if not data:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                return Response(status=200, data=data)

        elif "requestResult" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data, options = AnalysisBuilder.queryResultData(request.user, request.data["id"], request.data["requestResult"], request.data["resultId"], Authority)
                if not data:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                return Response(status=200, data={"Data": data, "Options": options})

        elif "updateAnalysisSteps" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                AnalysisBuilder.updateAnalysis(request.user, request.data["id"], request.data["analysisId"], request.data["processingSteps"], Authority)
                return Response(status=200)

        elif "startAnalysis" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = AnalysisBuilder.startAnalysis(request.user, request.data["id"], request.data["analysisId"], Authority)
                if not data == "Success":
                    return Response(status=400, data={"message": data})
                return Response(status=200)

        elif "addRecording" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = AnalysisBuilder.addRecordingToAnalysis(request.user, request.data["id"], request.data["analysisId"], request.data["addRecording"], Authority)
                if not data:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                
                return Response(status=200, data=data)

        elif "removeRecording" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = AnalysisBuilder.removeRecordingFromAnalysis(request.user, request.data["id"], request.data["analysisId"], request.data["removeRecording"], Authority)
                if not data:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                
                return Response(status=200, data=data)

        elif "updateRecording" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = AnalysisBuilder.setRecordingConfiguration(request.user, request.data["id"], request.data["analysisId"], request.data["updateRecording"], request.data["configuration"], Authority)
                if not data:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                
                return Response(status=200, data=data)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class QueryMobileRecordings(RestViews.APIView):
    """ Query Customized Analysis.

    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        request.user.configuration["ProcessingSettings"], changed = Database.retrieveProcessingSettings(request.user.configuration)
        if not changed:
            request.user.save()

        if "requestOverview" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["patientId"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["patientId"], Authority, "BrainSenseStream")
                data = WearableRecordingsDatabase.queryAvailableRecordings(request.user, request.data["patientId"], Authority)
                return Response(status=200, data=data)
            
        elif "requestData" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["patientId"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["patientId"], Authority, "BrainSenseStream")
                data = WearableRecordingsDatabase.getRecordingData(request.user, request.data["patientId"], request.data["recordingId"], Authority)
                return Response(status=200, data=data)
        
        elif "deleteData" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["patientId"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["patientId"], Authority, "BrainSenseStream")
                Result = WearableRecordingsDatabase.removeRecordingData(request.user, request.data["patientId"], request.data["recordingId"], Authority)
                if Result:
                    return Response(status=200)
        
        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
    
class QueryRecordingsForAnalysis(RestViews.APIView):
    """ Query Recording Raw Data for Analysis.

    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        request.user.configuration["ProcessingSettings"], changed = Database.retrieveProcessingSettings(request.user.configuration)
        if not changed:
            request.user.save()

        if "requestRawData" in request.data:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                data = AnalysisBuilder.getRawRecordingData(request.user, request.data["id"], request.data["analysisId"], request.data["requestRawData"], Authority)
                if not data:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                
                return Response(status=200, data=data)

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class QueryImageModelDirectory(RestViews.APIView):
    """ Query all Image models store in the patient's imaging folder.

    This route will provide user with all model descriptor related to a specific patient, assuming 
    there are imaging models in the patient's imaging folder.

    **POST**: ``/api/queryImageDirectory``

    Args:
      id (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains ``descriptor``, a dictionary that describe initial rendered objects and their parameters, and
      ``availableModels``, an array of dictionary with field {file, type, mode}. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=404)

        elif Authority["Level"] == 1:
            Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "Imaging")
            PatientID = request.data["id"]

        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "Imaging")
            PatientID = PatientInfo.authorized_patient_id

        data = ImageDatabase.extractAvailableModels(PatientID, Authority)
        return Response(status=200, data=data)

class QueryImageModel(RestViews.APIView):
    """ Query all Image models store in the patient's imaging folder.

    This route will provide user with all model descriptor related to a specific patient, assuming 
    there are imaging models in the patient's imaging folder.

    **POST**: ``/api/queryImageModel``

    Args:
      Directory (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.
      FileMode (string): "single" or "multiple", define whether the API should return individual file or pagination for multiple requests.
      FileType (string): "stl", "tracts", or "electrode", define what kind of model the server should retrieve. This defines the decoder function.
      FileName (string): filename of the model.
      
    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains an octet-stream (binary buffer) for "stl" and "electrode", or array of points for tracts.
    """

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

            elif request.data["FileType"] == "points":
                tracts = ImageDatabase.pointsReader(PatientID, request.data["FileName"])
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

            elif request.data["FileType"] == "volume":
                file_data = ImageDatabase.niftiLoader(PatientID, request.data["FileName"])
                if len(file_data) == 0:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                return HttpResponse(bytes(file_data), status=200, headers={
                    "Content-Type": "application/octet-stream"
                })

        elif request.data["FileMode"] == "multiple":
            if request.data["FileType"] == "electrode":
                pages = ImageDatabase.electrodeReader(request.data["FileName"])
                return Response(status=200, data={"pages": pages, "color": "0x000000"})
            
            elif request.data["FileType"] == "volume":
                headers = ImageDatabase.niftiInfo(PatientID, request.data["FileName"])
                return Response(status=200, data={"headers": headers})

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
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id, deidentifiedId=request.data["id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
                PatientID = PatientInfo.authorized_patient_id

            data = dict()
            TherapyHistory = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
            data["ChronicData"] = ChronicBrainSense.queryChronicLFPs(request.user, PatientID, TherapyHistory, Authority)
            data["EventPSDs"] = BrainSenseEvent.queryPatientEventPSDs(request.user, PatientID, TherapyHistory, Authority)
            data["CircadianPower"] = ChronicBrainSense.processCircadianPower(data["ChronicData"], request.data["therapyInfo"], int(request.data["timezoneOffset"]))
            return Response(status=200, data=data["CircadianPower"])

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
