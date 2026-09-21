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
import traceback
from copy import deepcopy
import pickle
from pathlib import Path
import hmac, hashlib
from io import BytesIO
import datetime
import pandas as pd
import numpy as np
from filelock import Timeout, FileLock

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings

from Server import models
from modules.HelperFunctions import sanitize_input, get_or_none, current_time
from modules import Database, DataCurator, DataAnalysis, ImageDatabase, Therapy

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')

class DataDownloadHandler(RestViews.APIView):

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def get(self, request):
        CacheType = self.request.query_params.get('CacheType')
        if CacheType == "ClearDataUpload":
            models.SourceFile.objects.filter(metadata__contains={"Uploader": request.user.pk}, owner=None).delete()
            return Response(status=200)

        ParticipantId = self.request.query_params.get('ParticipantId')
        Permissions = Database.checkAccessPermission(request.user, ParticipantId, 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)

        if CacheType == "queryTimeSeriesData":
            RecordingId = self.request.query_params.get('RecordingId')
            Channel = self.request.query_params.get('Channel')
            userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            rawBytes = DataAnalysis.downloadRawRecordings(ParticipantId, RecordingId, Channel, userConfig)
            
            response = HttpResponse(bytes(rawBytes), status=200, headers={
                "Content-Type": "application/octet-stream"
            })
            response["Content-Disposition"] = "attachment; filename=" + ParticipantId + "_" + RecordingId + ".dat"
            return response

        elif CacheType == "queryPowerSeriesData":
            RecordingId = self.request.query_params.get('RecordingId')
            Channel = self.request.query_params.get('Channel')
            userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            rawBytes = DataAnalysis.downloadRawRecordings(ParticipantId, RecordingId, Channel, userConfig)
            
            response = HttpResponse(bytes(rawBytes), status=200, headers={
                "Content-Type": "application/octet-stream"
            })
            response["Content-Disposition"] = "attachment; filename=" + ParticipantId + "_" + RecordingId + ".dat"
            return response

        elif CacheType == "queryNeuralActivitySnapshot":
            userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            Snapshots = DataAnalysis.downloadRawRecordings(ParticipantId, userConfig)
            file_data = pickle.dumps(Snapshots)
            
            response = HttpResponse(bytes(file_data), status=200, headers={
                "Content-Type": "application/octet-stream"
            })
            response["Content-Disposition"] = "attachment; filename=NeuralActivitySnapshots_" + ParticipantId + ".pkl"
            return response
