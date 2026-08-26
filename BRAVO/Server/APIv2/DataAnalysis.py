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
from django.http import HttpResponse

from Server import models
from modules.HelperFunctions import sanitize_input, get_or_none, json_compliant_handler
from modules import Database, DataCurator, DataAnalysis
from modules.AsyncJobScheduler import ProcessingScheduler

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')

class QueryTimeseriesAnalysis(RestViews.APIView):
    """
    API Endpoint for querying available timeseries analyses and requesting processed data.
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
            return Response(status=200, data=Overview["Recordings"])

        elif request.data["RequestType"] == "RequestData":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "RecordingId", "ActiveChannels"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if "ProcessingConfiguration" in request.data.keys():
                userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["ProcessingConfiguration"]})
            else:
                userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)

            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            Analysis = Database.getCachedResult("/v2/queryTimeseriesAnalysis", request.data["ParticipantId"], {**userConfig, **request.data})
            if not Analysis:
                Analysis = DataAnalysis.retrieveTimeseriesData(request.data["ParticipantId"], request.data["RecordingId"], userConfig)
                Database.saveCachedResult(Analysis, "/v2/queryTimeseriesAnalysis", request.data["ParticipantId"], {**userConfig, **request.data})

            response = HttpResponse(Analysis["Payload"], content_type='application/octet-stream')
            response['X-Timeseries-Metadata'] = json.dumps(Analysis["Metadata"])
            response['Access-Control-Expose-Headers'] = 'X-Timeseries-Metadata'
            return response

        elif request.data["RequestType"] == "RequestSpectrogram":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "RecordingId", "ActiveChannels"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if "ProcessingConfiguration" in request.data.keys():
                userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": request.data["ProcessingConfiguration"]})
            else:
                userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)

            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            #Analysis = Database.getCachedResult("/v2/queryTimeseriesAnalysis", request.data["ParticipantId"], {**userConfig, **request.data})
            #if not Analysis:
            Analysis = DataAnalysis.retrieveSpectrogramData(request.data["ParticipantId"], request.data["RecordingId"], userConfig)
            #    Database.saveCachedResult(Analysis, "/v2/queryTimeseriesAnalysis", request.data["ParticipantId"], {**userConfig, **request.data})
            if not Analysis:
                return Response(status=400, data={"message": "Failed to retrieve spectrogram data"})

            response = HttpResponse(Analysis["Payload"], content_type='application/octet-stream')
            response['X-Spectrogram-Metadata'] = json.dumps(Analysis["Metadata"])
            response['Access-Control-Expose-Headers'] = 'X-Spectrogram-Metadata'
            return response

        return Response(status=400, data={"message": "Malformed Input"})
    