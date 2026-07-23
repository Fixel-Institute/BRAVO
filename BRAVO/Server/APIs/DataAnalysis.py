""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under Open Source GPL-3.0 License

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Data Upload Handler Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os
import json
import time
import traceback
from copy import deepcopy
from pathlib import Path
import hmac, hashlib
import numpy as np

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from Server.renderers import BinaryRenderer

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings

from Server import models
from modules.HelperFunctions import sanitize_input, get_or_none, json_compliant_handler
from modules import Database, DataCurator, DataAnalysis
from modules.AsyncJobScheduler import ProcessingScheduler

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')

class QueryAnalysisConfigurations(RestViews.APIView):
    """
    API View for managing analysis processing configurations.
    
    This view handles user-specific processing configurations that control how 
    data analysis operations are performed across the platform.
    
    **URL:** ``/queryAnalysisConfigurations``
    
    **Methods:** POST
    
    **Permissions:** Authenticated users only
    
    **Request Types:**
    
    * ``QueryConfigurations`` - Retrieve current user processing settings
    * ``UpdateConfigurations`` - Update user processing configuration
    
    **Request Parameters:**
    
    :param RequestType: Type of operation to perform
    :type RequestType: str
    :param Configurations: Processing configuration data (for UpdateConfigurations only)
    :type Configurations: dict, optional
    
    **Default Processing Configuration:**
    
    .. code-block:: json
    
        {
            "TimeSeriesRecording": {
                "StandardFilter": {
                    "options": ["No Filter","Butterworth 1-100Hz"],
                    "value": "Butterworth 1-100Hz"
                },
                "NotchFilter": {
                    "options": ["No Filter","Notch 55-65Hz","Notch 45-55Hz"],
                    "value": "No Filter"
                },
                "WienerFilter": {
                    "options": ["No Filter","Use Wiener Filter"],
                    "value": "No Filter"
                },
                "CardiacFilter": {
                    "options": ["No Filter","Use Adaptive Template Matching"],
                    "value": "No Filter"
                },
                "SpectrogramMethod": {
                    "options": ["Welch's Periodogram","Short-time Fourier Transform","Medtronic Percept PSD","Wavelet","Autoregressive Model (Yule-Walker)"],
                    "value": "Welch's Periodogram"
                },
                "BaselineCorrection": {
                    "options": ["No Correction"],
                    "value": "No Correction"
                },
                "Normalization": {
                    "options": ["No Normalization", "1/f PSD Trend Removal"],
                    "value": "No Normalization"
                },
            },
            "PowerSpectralDensity": {
                "PSDMethod": {
                    "options": ["Estimated Medtronic PSD","Welch's Periodogram","Autoregressive Model (Yule-Walker)","Short-time Fourier Transform"],
                    "value": "Welch's Periodogram"
                },
                "MonopolarEstimation": {
                    "options": ["No Estimation", "DETEC Algorithm (Strelow et. al., 2022)"],
                    "value": "No Estimation"
                },
            }
        }
    
    **HTTP Status Codes:**
    
    * ``200`` - Success
    * ``400`` - Malformed input data
    * ``401`` - Unauthorized access
    * ``500`` - Internal server error (Check Server logs for details)

    **MATLAB API Example Usage:**
    
    .. code-block:: matlab

        % Query current analysis configurations
        Config = requester.QueryAnalysisConfiguration();

        % Update analysis configurations
        Config.TimeSeriesRecording.StandardFilter.value = "No Filter";
        Config.TimeSeriesRecording.CardiacFilter.value = "Use Adaptive Template Matching";
        requester.QueryAnalysisConfiguration(Config);

    """
    
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        if request.data["RequestType"] == "QueryConfigurations":
            userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            return Response(status=200, data=userConfig)

        elif request.data["RequestType"] == "UpdateConfigurations":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "Configurations"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["Configurations"]})
            request.user.configuration["ProcessingConfiguration"] = userConfig
            request.user.save()
            return Response(status=200, data=userConfig)

class QueryTherapeuticEffectAnalysis(RestViews.APIView):
    """
    DEPRECATED: Use `QueryTimeseriesAnalysis` instead.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "Overview":
            Overview = DataAnalysis.queryAvailableAnalyses(request.data["ParticipantId"], "TherapeuticAnalysis")
            return Response(status=200, data=Overview)

        elif request.data["RequestType"] == "AddNewAnalysis":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "TherapyIds", "RecordingIds"]):
                return Response(status=400, data={"message": "Malformed Input"})

            if len(request.data["RecordingIds"]) == 0 or len(request.data["TherapyIds"]) == 0:
                return Response(status=400, data={"message": "Malformed Input"})

            AllRecordings = []
            AllRecordings.extend(request.data["RecordingIds"])
            AllRecordings.extend(request.data["TherapyIds"])
            result = DataAnalysis.createAnalysis(request.data["ParticipantId"], "TherapeuticAnalysis", AllRecordings)
            if result:
                return Response(status=200, data=result.get_info())
            else:
                return Response(status=400, data={"message": "Fail to create analysis"})
                
        elif request.data["RequestType"] == "DeleteAnalysis":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "AnalysisId"]):
                return Response(status=400, data={"message": "Malformed Input"})

            result = DataAnalysis.deleteAnalysis(request.data["ParticipantId"], request.data["AnalysisId"])
            if result:
                return Response(status=200)
            else:
                return Response(status=400, data={"message": "Fail to delete analysis"})

        elif request.data["RequestType"] == "RequestData":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "AnalysisId", "ActiveChannels"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if "ProcessingConfiguration" in request.data.keys():
                userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["ProcessingConfiguration"]})
            else:
                userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)

            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            result = Database.getCachedResult("/queryTherapeuticEffectAnalysis", request.data["ParticipantId"], {**userConfig, **request.data})
            if result:
                return Response(status=200, data=result)

            metadata = {**userConfig, **request.data, **{
                "ActiveChannels": ""
            }}
            Analysis = Database.getCachedResult("/queryTherapeuticEffectAnalysis", request.data["ParticipantId"], metadata)
            if not Analysis:
                Analysis = DataAnalysis.processTherapeuticAnalysis(request.data["ParticipantId"], request.data["AnalysisId"], userConfig)
                #Database.saveCachedResult(Analysis, "/queryTherapeuticEffectAnalysis", request.data["ParticipantId"], metadata)
                         
            if not request.data["ActiveChannels"] == "RequestAllChannel":
                Analysis = DataAnalysis.selectRecordingChannel(Analysis, request.data["ActiveChannels"])

            Analysis = json_compliant_handler(Analysis)
            Analysis["ProcessingConfiguration"] = userConfig
            Database.saveCachedResult(Analysis, "/queryTherapeuticEffectAnalysis", request.data["ParticipantId"], {**userConfig, **request.data})
            return Response(status=200, data=Analysis)

        elif request.data["RequestType"] == "UpdateData":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "AnalysisId", "RecordingName", "RecordingTags", "StimulationLabel"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            analysis = models.Analysis.find(uid=request.data["AnalysisId"])
            for recording in analysis.recordings.all():
                if not recording.source.owner.uid == request.data["ParticipantId"]:
                    return Response(status=400, data={"message": "Permission Denied"})

                if recording.type == "MedtronicBrainSenseTimeDomain":
                    recording.name = request.data["RecordingName"]
                    recording.save()
                elif recording.type == "MedtronicBrainSensePowerDomain":
                    recording.name = request.data["RecordingName"]
                    sideN = 0
                    for side in ["Left", "Right"]:
                        if side in recording.metadata["Therapy"].keys():
                            recording.metadata["Therapy"][side]["SegmentMode"] = request.data["StimulationLabel"][sideN]
                            sideN += 1
                    recording.save()

            analysis.name = request.data["RecordingName"]
            analysis.metadata["Tags"] = request.data["RecordingTags"]
            analysis.save()
            return Response(status=200)

        elif request.data["RequestType"] == "DeleteCache":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "AnalysisId"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            analysis = models.Analysis.find(uid=request.data["AnalysisId"])
            for recording in analysis.recordings.all():
                if not recording.source.owner.uid == request.data["ParticipantId"]:
                    return Response(status=400, data={"message": "Permission Denied"})
                
                Database.deleteCachedResult(request.data["ParticipantId"], url="/queryTherapeuticEffectAnalysis")
                DataAnalysis.deleteProcessedData(recording=[recording])

            return Response(status=200)

        return Response(status=400, data={"message": "Malformed Input"})
    
class QueryTimeseriesAnalysis(RestViews.APIView):
    """
    API View for time series analysis of neural recordings.
    
    This API is the central endpoint for requesting data from BRAVO Platform.

    **URL:** ``/queryTimeseriesAnalysis``
    
    **Methods:** POST
    
    **Permissions:** Authenticated users with participant access permissions
    
    **Request Types:**
    
    * ``Overview`` - Get available time series analyses for a participant
    * ``RequestData`` - Get processed time series analysis data
    * ``UpdateData`` - Update recording metadata and tags
    * ``DeleteCache`` - Clear cached analysis results
    
    **Request Parameters:**
    
    :param ParticipantId: Unique identifier for the participant
    :type ParticipantId: str
    :param RequestType: Type of operation to perform
    :type RequestType: str

    **-RequestData-**
    
    :param AnalysisId: Unique identifier for the time series recording
    :type AnalysisId: str
    :param TherapyId: Optional therapy recording Id, if a corresponding therapy is available. Put "" if not available.
    :type TherapyId: str
    :param ActiveChannels: Channel selection for data retrieval. Use "RequestAllChannel" to retrieve all channels.
    :type ActiveChannels: str or list
    :param ProcessingConfiguration: Custom processing settings
    :type ProcessingConfiguration: dict, optional
    
    **-UpdateData-**

    :param AnalysisId: Unique identifier for the analysis/recording
    :type AnalysisId: str
    :param RecordingName: New name for the recording (for UpdateData)
    :type RecordingName: str, optional
    :param RecordingTags: Metadata tags for the recording (for UpdateData)
    :type RecordingTags: list, optional
    
    **Response Format:**
    
    For Overview request:
    
    .. code-block:: json
    
        [
            {
                "Id": "<AnalysisId>",
                "SourceId": "<SourceId>",
                "Name": "MEDOFF_THRESHOLD",
                "Type": "MedtronicBrainSenseTimeDomain",
                "Date": 1753732685,
                "Alignment": 0,
                "Metadata": {
                    "Key1": "Value1",
                    "Key2": "Value2"
                },
                "Device": "DeviceName",
                "Timezone": "UTC-04:00",
            }
        ]
    
    For RequestData:
    
    .. code-block:: json
    
        {
            "Signal": [
                {
                    "Type": "Signal",
                    "RecordingId": "",
                    "SignalSeries": [
                        {
                            "Time": [...],
                            "Data": [...],
                            "StartTime": 0,
                            "SamplingRate": 250
                        }
                    ],
                    "Alignment": 0
                }
            ],
            "Therapy": [
                ...
            ],
            "ProcessingConfiguration": {...}
        }
    
    **HTTP Status Codes:**
    
    * ``200`` - Success
    * ``400`` - Malformed input or operation failed
    * ``401`` - Unauthorized access
    * ``403`` - Insufficient permissions
    
    **MATLAB API Example Usage:**
    
    .. code-block:: matlab

        % Get time series list
        Recordings = requester.QueryTimeseriesAnalysis(Participant.Id).Recordings;

        % Request specific time series data (with Therapy data)
        response = requester.QueryTimeseriesAnalysis(Participant.Id, 'analysis_uid', Recordings(1).Id, 'therapy_uid', Recordings(1).Therapy(1).Id);

        % Request specific time series data (without Therapy data)
        response = requester.QueryTimeseriesAnalysis(Participant.Id, 'analysis_uid', Recordings(1).Id);
        
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    renderer_classes = [BinaryRenderer]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "Overview":
            Overview = DataAnalysis.queryAvailableAnalyses(request.data["ParticipantId"], "TimeSeriesAnalysis")
            return Response(status=200, data=Overview)

        elif request.data["RequestType"] == "RequestData":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "AnalysisId", "ActiveChannels"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if "ProcessingConfiguration" in request.data.keys():
                userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["ProcessingConfiguration"]})
            else:
                userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)

            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            result = Database.getCachedResult("/queryTimeseriesAnalysis", request.data["ParticipantId"], {**userConfig, **request.data})
            if result:
                return Response(status=200, data=result)
            
            Analysis = DataAnalysis.processTimeseriesAnalysis(request.data["ParticipantId"], request.data["AnalysisId"], userConfig)
            if request.data["TherapyId"]:
                Analysis["Therapy"] = DataAnalysis.processTimeseriesAnalysis(request.data["ParticipantId"], request.data["TherapyId"], userConfig)["Therapy"]
                Analysis = DataAnalysis.computeTherapeuticEffects(Analysis)

            Analysis["ProcessingConfiguration"] = userConfig

            if not request.data["ActiveChannels"] == "RequestAllChannel":
                Analysis = DataAnalysis.selectRecordingChannel(Analysis, request.data["ActiveChannels"])
            Analysis = json_compliant_handler(Analysis)

            Database.saveCachedResult(Analysis, "/queryTimeseriesAnalysis", request.data["ParticipantId"], {**userConfig, **request.data})
            return Response(status=200, data=Analysis)

        elif request.data["RequestType"] == "UpdateData":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "AnalysisId", "RecordingName", "RecordingTags"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            recording = models.Recording.find(uid=request.data["AnalysisId"])
            if not recording.source.owner.uid == request.data["ParticipantId"]:
                return Response(status=400, data={"message": "Permission Denied"})

            recording.name = request.data["RecordingName"]
            recording.metadata["Tags"] = request.data["RecordingTags"]
            recording.save()
            return Response(status=200)

        elif request.data["RequestType"] == "DeleteCache":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "AnalysisId"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            recording = models.Recording.find(uid=request.data["AnalysisId"])
            if not recording.source.owner.uid == request.data["ParticipantId"]:
                return Response(status=400, data={"message": "Permission Denied"})
            
            DataAnalysis.deleteProcessedData(recording=[recording])
            Database.deleteCachedResult(request.data["ParticipantId"], url="/queryTimeseriesAnalysis")
            return Response(status=200)

        return Response(status=400, data={"message": "Malformed Input"})
    
    def get(self, request):
        ParticipantId = request.GET.get("ParticipantId", None)
        RecordingId = request.GET.get("RecordingId", None)
        StartTime = int(request.GET.get("StartTime", 0))
        StopTime = int(request.GET.get("StopTime", 0))
        Step = int(request.GET.get("Step", 0))
        ChannelName = request.GET.get("ChannelName", None)

        ProcessingConfiguration = {key: request.GET.get(key, None) for key in request.GET.dict().keys() if key not in ["ParticipantId", "RecordingId", "StartTime", "StopTime", "Step", "ChannelName"]}
        Permissions = Database.checkAccessPermission(request.user, ParticipantId, 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        start_time = time.time()
        Data, Metadata = DataAnalysis.getTimeseriesData(ParticipantId, RecordingId, {**ProcessingConfiguration, **{
            "ChannelName": ChannelName,
            "StartTime": StartTime,
            "StopTime": StopTime,
            "Step": Step
        }})
        stop_time = time.time()
        print(len(Data))
        print(f"Time series data loaded in {stop_time - start_time:.2f} seconds.")

        response = Response(Data.tobytes(), status=200, content_type='application/octet-stream')
        response["X-Metadata"] = json.dumps(Metadata)
        return response
    

class QueryNeuralActivitySnapshot(RestViews.APIView):
    """
    API View for neural activity snapshots (PSD from short recordings) analysis.
    
    This view provides functionality for analyzing brief snapshots of neural
    activity data, typically used for baseline measurements and short-term
    neural state assessments.
    
    **URL:** ``/queryNeuralActivitySnapshot``
    
    **Methods:** POST
    
    **Permissions:** Authenticated users with participant access permissions
    
    **Request Types:**
    
    * ``RequestAll`` - Get all neural activity snapshot data for a participant
    * ``DeleteCache`` - Clear cached snapshot analysis results
    
    **Request Parameters:**
    
    :param ParticipantId: Unique identifier for the participant
    :type ParticipantId: str
    :param RequestType: Type of operation to perform
    :type RequestType: str
    :param ProcessingConfiguration: Custom processing settings
    :type ProcessingConfiguration: dict, optional
    
    **Response Format:**
    
    For RequestAll:
    
    .. code-block:: json
    
        {
            "Recordings": [
                {
                    "Id": "<RecordingId>",
                    "SourceId": "<SourceId>",
                    "Name": "",
                    "Type": "NeuralActivitySnapshot",
                    "Date": 1753732685,
                    "Alignment": 0,
                    "Metadata": {...},
                    "Device": "<DeviceId>",
                    "Timezone": "UTC-04:00",
                    "RecordingId": "<RecordingId>",
                    "Channels": ["Channel1", "Channel2"],
                    "PSDs": [
                        {
                            "Frequency": [...],
                            "Power": [...],
                            "StdPower": [...],
                            "nObservation": 51,
                            "Config": {...}
                        }
                    ],
                }
            ],
            "AnalysisType": "NeuralActivitySnapshot",
            "ProcessingConfiguration": {
                ...
            }
        }
    
    **HTTP Status Codes:**
    
    * ``200`` - Success
    * ``400`` - Malformed input
    * ``401`` - Unauthorized access
    * ``403`` - Insufficient permissions
    
    **MATLAB API Example Usage:**
    
    .. code-block:: matlab
    
        % Get all neural activity snapshots
        Surveys = requester.QueryParticipantSurveyRecords(Participant.Id);

    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "RequestAll":
            if "ProcessingConfiguration" in request.data.keys():
                userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["ProcessingConfiguration"]})
            else:
                userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)

            result = Database.getCachedResult("/queryNeuralActivitySnapshot", request.data["ParticipantId"], {**userConfig, **request.data})
            if result:
                return Response(status=200, data=result)

            Analysis = DataAnalysis.queryNeuralActivitySnapshot(request.data["ParticipantId"], userConfig)
            Analysis = json_compliant_handler(Analysis)

            Analysis["ProcessingConfiguration"] = userConfig
            Database.saveCachedResult(Analysis, "/queryNeuralActivitySnapshot", request.data["ParticipantId"], {**userConfig, **request.data})
            return Response(status=200, data=Analysis)
        
        elif request.data["RequestType"] == "DeleteCache":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            Participant = models.Participant.find(uid=request.data["ParticipantId"])
            SourceFiles = models.SourceFile.find_all(owner=Participant)
            Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages"])
            DataAnalysis.deleteProcessedData(recording=Recordings, type="NeuralActivitySnapshot")
            Database.deleteCachedResult(request.data["ParticipantId"], url="/queryNeuralActivitySnapshot")
            return Response(status=200)

        return Response(status=400, data={"message": "Malformed Input"})
        
class QueryBurstAnalysis(RestViews.APIView):
    """
    API View for neural burst analysis. 
    
    **URL:** ``/queryBurstAnalysis``
    
    **Methods:** POST
    
    **Permissions:** Authenticated users with participant access permissions
    
    **Request Types:**
    
    * ``RequestData`` - Process and retrieve burst analysis data
    
    **Request Parameters:**
    
    :param ParticipantId: Unique identifier for the participant
    :type ParticipantId: str
    :param RequestType: Type of operation to perform
    :type RequestType: str
    :param RecordingIds: List of recording identifiers to analyze
    :type RecordingIds: list
    :param Channel: Channel name for burst analysis
    :type Channel: str
    :param CenterFrequency: Center frequency for burst detection (Hz)
    :type CenterFrequency: float
    :param ProcessingConfiguration: Custom processing settings
    :type ProcessingConfiguration: dict, optional
    
    **Response Format:**
    
    .. code-block:: json
    
        {
            "Signal": [
                {
                    "Type": "Signal",
                    "RecordingId": "",
                    "SignalSeries": {
                        "Time": [...],
                        "Data": [...],
                        "StartTime": 0,
                        "SamplingRate": 250
                        "BurstEnvelop": [
                            {
                                "Wavelet": [...],
                                "Frequency": [...],
                                "Method": "Morlet",
                            }
                        ]
                    },
                    "Alignment": 0
                }
            ],
            "ProcessingConfiguration": {...}
        }
    
    **HTTP Status Codes:**
    
    * ``200`` - Success
    * ``400`` - Malformed input
    * ``401`` - Unauthorized access
    * ``403`` - Insufficient permissions
    
    **Example Usage:**
    
    .. code-block:: matlab
    
        # Analyze burst patterns
        Recording = requester.QueryTimeseriesAnalysis(Participant.Id, "analysis_uid", Recordings{20}.Id);
        BetaBurst = requester.QueryBurstAnalysis(Participant.Id, {Recording.Signal(1).RecordingId}, Recording.Signal(1).SignalSeries.ChannelNames{1}, 22);
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "RequestData":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "RecordingIds", "Channel", "CenterFrequency"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if "ProcessingConfiguration" in request.data.keys():
                userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["ProcessingConfiguration"]})
            else:
                userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)

            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            
            AnalysisResults = []
            BurstWaveform = []
            for recordingId in request.data["RecordingIds"]:
                recording = models.Recording.find(uid=recordingId)
                ProcessedData = models.Recording.find(original=recording, type="BurstActivityPreprocessing", metadata=userConfig)
                if not ProcessedData:
                    job = ProcessingScheduler.ScheduleSlurmJob(request.user, recordingId, "BurstAnalysis", {
                        **userConfig,
                        "ParticipantId": request.data["ParticipantId"],
                    })

                else:
                    Analysis = DataAnalysis.processBurstAnalysis(request.data["ParticipantId"], recordingId, userConfig, centerFreq=request.data["CenterFrequency"])
                    if not request.data["Channel"] == "RequestAllChannel":
                        Analysis = DataAnalysis.selectRecordingChannel(Analysis, request.data["Channel"])
                    Analysis = json_compliant_handler(Analysis)
                    Analysis["ProcessingConfiguration"] = userConfig
                    AnalysisResults.append(Analysis)

                    for i in range(len(Analysis["Signal"])):
                        if Analysis["Signal"][i]["SignalSeries"]["ChannelNames"] == request.data["Channel"]:
                            fs = Analysis["Signal"][i]["SignalSeries"]["SamplingRate"]
                            BurstWaveform.extend(Analysis["Signal"][i]["SignalSeries"]["BurstEnvelop"]["Wavelet"])

            if len(AnalysisResults) < len(request.data["RecordingIds"]):
                return Response(status=200, data=[])
            
            Parameters = DataAnalysis.calculateBurstParameters(BurstWaveform, fs)
            for j in range(len(AnalysisResults)):
                for i in range(len(AnalysisResults[j]["Signal"])):
                    if AnalysisResults[j]["Signal"][i]["SignalSeries"]["ChannelNames"] == request.data["Channel"]:
                        AnalysisResults[j]["Signal"][i]["SignalSeries"]["BurstEnvelop"]["Parameters"] = Parameters

            return Response(status=200, data=AnalysisResults)

        return Response(status=400, data={"message": "Malformed Input"})
    
class QueryChronicTimeline(RestViews.APIView):
    """
    API View for chronic timeline analysis.
    
    This view provides functionality for analyzing long-term temporal patterns
    in neural recordings, tracking changes in neural activity over extended
    periods (days to months). This is the generic timeline data query, which applys to all wearable data as well. 
    
    **URL:** ``/queryChronicTimeline``
    
    **Methods:** POST
    
    **Permissions:** Authenticated users with participant access permissions
    
    **Request Types:**
    
    * ``RequestAll`` - Get complete chronic timeline data for a participant
    * ``DeleteCache`` - Clear cached timeline analysis results
    
    **Request Parameters:**
    
    :param ParticipantId: Unique identifier for the participant
    :type ParticipantId: str
    :param RequestType: Type of operation to perform
    :type RequestType: str
    :param ProcessingConfiguration: Custom processing settings
    :type ProcessingConfiguration: dict, optional
    
    **Response Format:**
    
    For RequestAll:
    
    .. code-block:: json
    
        {
            "Timelines": [
                {
                    "AnalysisType": "CustomizedTimelineData",
                    "Time": [...],
                    "Duration": [...],
                    "ChannelNames": [...],
                    "ChannelUnits": ["", ...],
                    "Data": [...], # Shape with (Channels, Time)
                }
            ],
            "ProcessingConfiguration": {...}
        }
    
    **HTTP Status Codes:**
    
    * ``200`` - Success
    * ``400`` - Malformed input
    * ``401`` - Unauthorized access
    * ``403`` - Insufficient permissions
    
    **Example Usage:**
    
    .. code-block:: matlab
    
        # Get chronic timeline data
        response = requests.post('/queryChronicTimeline', {
            "ParticipantId": "<ParticipantId>",
            "RequestType": "RequestAll"
        })
        
        # Clear timeline cache
        response = requests.post('/queryChronicTimeline', {
            "ParticipantId": "<ParticipantId>",
            "RequestType": "DeleteCache"
        })
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "RequestAll":
            if "ProcessingConfiguration" in request.data.keys():
                userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["ProcessingConfiguration"]})
            else:
                userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            
            #result = Database.getCachedResult("/queryChronicTimeline", request.data["ParticipantId"], {**userConfig, **request.data})
            #if result:
            #    return Response(status=200, data=result)
            
            Analysis = {}
            Analysis["Timelines"], Analysis["Annotations"] = DataAnalysis.queryChronicTimeline(request.data["ParticipantId"], userConfig)
            Analysis["ProcessingConfiguration"] = userConfig
            Analysis = json_compliant_handler(Analysis)
            Database.saveCachedResult(Analysis, "/queryChronicTimeline", request.data["ParticipantId"], {**userConfig, **request.data})
            return Response(status=200, data=Analysis)

        elif request.data["RequestType"] == "RequestData":
            if "ProcessingConfiguration" in request.data.keys():
                userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["ProcessingConfiguration"]})
            else:
                userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            
            Data = DataAnalysis.queryChronicTimelineData(request.data["ParticipantId"], request.data["DataIds"], request.data["Channel"], userConfig)
            return Response(status=200, data=Data)

        elif request.data["RequestType"] == "DeleteCache":
            Recording = models.Recording.find(type="ProcessedCustomizedStreamingData", source__owner__uid=request.data["ParticipantId"])
            if Recording:
                Recording.delete()
            Database.deleteCachedResult(request.data["ParticipantId"], url="/queryChronicTimeline")
            return Response(status=200)

class QueryChronicNeuralActivity(RestViews.APIView):
    """
    API View for chronic neural activity analysis.
    
    This view provides functionality for analyzing chronic neural activity patterns,
    focusing on long-term neural signal characteristics and trends over extended
    monitoring periods. This is different from the Chronic Timeline because the data here is more specific 
    to Medtronic Percept data type. 
    
    **URL:** ``/queryChronicNeuralActivity``
    
    **Methods:** POST
    
    **Permissions:** Authenticated users with participant access permissions
    
    **Request Types:**
    
    * ``RequestAll`` - Get all chronic neural activity data for a participant
    * ``DeleteCache`` - Clear cached chronic neural activity results
    
    **Request Parameters:**
    
    :param ParticipantId: Unique identifier for the participant
    :type ParticipantId: str
    :param RequestType: Type of operation to perform
    :type RequestType: str
    :param ProcessingConfiguration: Custom processing settings
    :type ProcessingConfiguration: dict, optional
    
    **Response Format:**
    
    For RequestAll:
    
    .. code-block:: json
    
        {
            "AnalysisType": "MedtronicChronicBrainSense",
            "ChronicNeuralActivity": [
                {
                    "Device": {
                        "Id": "<DeviceId>",
                        ...
                    },
                    "TherapyWindow": [StartDate, EndDate],
                    "TherapyNote": {...},
                    "TherapyString": "125Hz 120uS [E01-A|E01-B|E01-C]",
                    "RecordingString": "33.2Hz",
                    "Time": [...],
                    "ChannelNames": ["Left GPi LFP", "Left GPi Amplitude"],
                    "ChannelNamesFix": [...] # Fixed channel names for Medtronic Percept Formatting
                    "ChannelUnits": ["", ""],
                    "Data": [
                        [...], # Shape with (Channels, Time)
                        [...]
                    ],
                    "AnalysisType": ["MedtronicChronicBrainSense", ...]
                }
            ],
            "Annotations": [...],
            "ProcessingConfiguration": {...}
        }
    
    **HTTP Status Codes:**
    
    * ``200`` - Success
    * ``400`` - Malformed input
    * ``401`` - Unauthorized access
    * ``403`` - Insufficient permissions
    
    **Example Usage:**
    
    .. code-block:: python
    
        # Get chronic neural activity
        response = requests.post('/queryChronicNeuralActivity', {
            "ParticipantId": "<ParticipantId>",
            "RequestType": "RequestAll"
        })
        
        # Clear cache
        response = requests.post('/queryChronicNeuralActivity', {
            "ParticipantId": "<ParticipantId>",
            "RequestType": "DeleteCache"
        })
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "RequestAll":
            if "ProcessingConfiguration" in request.data.keys():
                userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["ProcessingConfiguration"]})
            else:
                userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            
            result = Database.getCachedResult("/queryChronicNeuralActivity", request.data["ParticipantId"], {**userConfig, **request.data})
            if result:
                return Response(status=200, data=result)

            Analysis = DataAnalysis.queryChronicNeuralActivity(request.data["ParticipantId"], userConfig)
            Analysis = json_compliant_handler(Analysis)

            Analysis["ProcessingConfiguration"] = userConfig
            Database.saveCachedResult(Analysis, "/queryChronicNeuralActivity", request.data["ParticipantId"], {**userConfig, **request.data})
            return Response(status=200, data=Analysis)

        elif request.data["RequestType"] == "DeleteCache":
            Participant = models.Participant.find(uid=request.data["ParticipantId"])
            if models.Recording.find(type="MedtronicChronicNeuralActivity", source__owner=Participant):
                models.Recording.find(type="MedtronicChronicNeuralActivity", source__owner=Participant).delete()

            Database.deleteCachedResult(request.data["ParticipantId"], url="/queryChronicNeuralActivity")
            return Response(status=200)

class QueryCustomizedAnalysis(RestViews.APIView):
    """
    NOT RECOMMENDED FOR API USE. 

    This API is designed for simplified data analysis using the Web interface. If you are writing code in API already, 
    the data analysis should be handled by you for maximum controls.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "RequestList":
            analysis = models.Analysis.find_all(type="CustomizedAnalysis", metadata__ParticipantId= request.data["ParticipantId"])
            return Response(status=200, data=[i.get_info() for i in analysis])

        elif request.data["RequestType"] == "ProcessingNodes":
            nodes = DataAnalysis.queryProcessingNodes()
            return Response(status=200, data=nodes)

        elif request.data["RequestType"] == "NewAnalysis":
            analysis = models.Analysis.create(name="Unnamed", type="CustomizedAnalysis", metadata={
                "ParticipantId": request.data["ParticipantId"]
            })
            
            info = analysis.get_info()
            return Response(status=200, data=info)

        elif request.data["RequestType"] == "EditAnalysis":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "AnalysisId", "AnalysisName", "RequestType"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            analysis = models.Analysis.find(uid=request.data["AnalysisId"], type="CustomizedAnalysis", metadata__ParticipantId=request.data["ParticipantId"])
            if not analysis:
                return Response(status=403)

            analysis.name = request.data["AnalysisName"]
            analysis.save()
            return Response(status=200)
        
        elif request.data["RequestType"] == "SaveAnalysisPipeline":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "AnalysisId", "Nodes", "Edges", "StartProcessing", "RequestType"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            analysis = models.Analysis.find(uid=request.data["AnalysisId"], type="CustomizedAnalysis", metadata__ParticipantId=request.data["ParticipantId"])
            if not analysis:
                return Response(status=403)
            
            analysis.metadata["Results"] = False
            analysis.metadata["Nodes"] = request.data["Nodes"]
            
            Participant = models.Participant.find(uid=analysis.metadata["ParticipantId"])
            source = models.SourceFile.find(name=analysis.uid, type="CustomizedPipelineSource", owner=Participant)
            models.Recording.find_all(source=source).delete()

            try:
                if request.data["StartProcessing"]:
                    DataAnalysis.processCustomizedPipeline(analysis)
                    analysis.metadata["results"] = True
                else:
                    # Reset Results
                    for i in range(len(analysis.metadata["Nodes"])):
                        for j in range(len(analysis.metadata["Nodes"][i])):
                            if "result" in analysis.metadata["Nodes"][i][j].keys():
                                del analysis.metadata["Nodes"][i][j]["result"]
                    analysis.metadata["results"] = False

            except Exception as e:
                print(traceback.format_exc())
                return Response(status=400, data={"message": str(e)})
            
            analysis.save()
            Overview = DataAnalysis.queryCustomizedAnalysis(request.data["ParticipantId"], analysis)
            return Response(status=200, data=Overview)

        elif request.data["RequestType"] == "DeleteAnalysis":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "AnalysisId", "RequestType"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            analysis = models.Analysis.find(uid=request.data["AnalysisId"], type="CustomizedAnalysis", metadata__ParticipantId=request.data["ParticipantId"])
            if not analysis:
                return Response(status=403)
            
            source = models.SourceFile.find(name=analysis.uid, type="CustomizedPipelineSource", owner__uid=request.data["ParticipantId"])
            if source:
                source.delete()
            analysis.delete()
            return Response(status=200)

        elif request.data["RequestType"] == "AnalysisOverview":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "AnalysisId", "RequestType"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            analysis = models.Analysis.find(uid=request.data["AnalysisId"], type="CustomizedAnalysis", metadata__ParticipantId=request.data["ParticipantId"])
            if not analysis:
                return Response(status=403)
            
            Overview = DataAnalysis.queryCustomizedAnalysis(request.data["ParticipantId"], analysis)
            return Response(status=200, data=Overview)
        
        elif request.data["RequestType"] == "AnalysisOutput":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "AnalysisId", "RequestType", "ResultId"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            analysis = models.Analysis.find(uid=request.data["AnalysisId"], type="CustomizedAnalysis", metadata__ParticipantId=request.data["ParticipantId"])
            if not analysis:
                return Response(status=403)
            
            result = None
            for group in analysis.metadata["Nodes"]:
                for node in group:
                    if "result" in node.keys():
                        if node["result"] == request.data["ResultId"]:
                            result = DataAnalysis.extractAnalysisOutput(node)
                            result = DataAnalysis.selectRecordingChannel(result, request.data["ActiveChannels"] if "ActiveChannels" in request.data.keys() else [])
            #Overview = DataAnalysis.queryCustomizedAnalysis(request.data["ParticipantId"], analysis)
            result = json_compliant_handler(result)
            return Response(status=200, data=result)
        
        return Response(status=400, data={"message": "Malformed Input"})
    
class QueryAIModels(RestViews.APIView):
    """
    DEPRECATED. Use AIModels.RequestPrediction API Instead.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "RequestAll":
            models = DataAnalysis.extractMachineLearningModels(request.data["ParticipantId"])
            return Response(status=200, data=models)

        else:
            result = DataAnalysis.extractMachineLearningModels(request.data["ParticipantId"], model_key=request.data["ModelType"], config=request.data)
            return Response(status=200, data=result)

        return Response(status=400, data={"message": "Malformed Input"})
    
class QueryMedicationCycleAnalysis(RestViews.APIView):
    """
    API View for medication cycle analysis.
    
    This API view provides simplified way to aggregate multiple recordings' BrainSense Power Domain data 
    during medication cycles across different stimulation parameters. 

    **URL:** ``/queryMedicationCycleAnalysis``
    
    **Methods:** POST
    
    **Permissions:** Authenticated users with participant access permissions
    
    **Request Types:**
    
    * ``RequestAll`` - Get all medication cycle recordings for a participant
    * ``RequestAnalysis`` - Analyze specific medication cycle recordings
    
    **Request Parameters:**
    
    :param ParticipantId: Unique identifier for the participant
    :type ParticipantId: str
    :param RequestType: Type of operation to perform
    :type RequestType: str
    :param RecordingIds: List of recording identifiers to analyze (for RequestAnalysis)
    :type RecordingIds: list, optional
    
    **Response Format:**
    
    For RequestAll:
    
    .. code-block:: json
    
        {
            "MedicationCycles": [
                {
                    "RecordingId": "med_cycle_123",
                    "StartDate": "2025-01-01T08:00:00Z",
                    "EndDate": "2025-01-01T20:00:00Z",
                    "MedicationInfo": {
                        "Name": "Levodopa",
                        "Dosage": "100mg",
                        "AdministrationTime": "2025-01-01T08:00:00Z"
                    },
                    "RecordingType": "MedtronicBrainSensePowerDomain"
                }
            ]
        }
    
    For RequestAnalysis:
    
    .. code-block:: json
    
        {
            "Recordings": [
                {
                    "Id": "<RecordingId>",
                    "SourceId": "<SourceId>",
                    "Name": "",
                    "Type": "MedtronicBrainSensePowerDomain",
                    "Date": 1753732685,
                    "Alignment": 0,
                    "Metadata": {...},
                    "Device": "<DeviceId>",
                    "Timezone": "UTC-04:00",
                },
                ...
            ],
            "PowerBands": {
                "Left1_5MA_Right1_2MA": {
                    "MEDON": {
                        "ZERO_THREE_LEFTPower": [...],
                        "ZERO_THREE_RIGHTPower: [...]
                    }
                }
            }
        }
    
    **HTTP Status Codes:**
    
    * ``200`` - Success
    * ``400`` - Malformed input
    * ``401`` - Unauthorized access
    * ``403`` - Insufficient permissions
    
    **Example Usage:**
    
    .. code-block:: matlab
    
        # Get all medication cycle recordings
        Overview = requester.QueryMedicationCycleAnalysis(Participant.Id);
        Data = requester.QueryMedicationCycleAnalysis(Participant.Id, 'recording_ids', {Overview.Recordings.Id});

    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "RequestAll":
            recordings = DataAnalysis.extractMedtronicPowerBands(request.data["ParticipantId"], "MedicationCycle")
            return Response(status=200, data=recordings)

        elif request.data["RequestType"] == "RequestAnalysis":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "RecordingIds"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            result = DataAnalysis.extractMedtronicPowerBands(request.data["ParticipantId"], "MedicationCycle", request.data["RecordingIds"])
            return Response(status=200, data=result)

        return Response(status=400, data={"message": "Malformed Input"})