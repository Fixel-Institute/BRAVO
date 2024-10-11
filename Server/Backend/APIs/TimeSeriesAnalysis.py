""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2024 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Thye Manager
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings
from django.urls import path

import os, pathlib
import json
import base64
import datetime, pytz
import websocket

import hashlib, random, string
from uuid import UUID

from Backend import models
from .HelperFunctions import checkAPIInput
from modules import Database, DataDecoder, TimeSeriesAnalysis

RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class QueryTherapeuticEffectAnalysis(RestViews.APIView):
    """ Query Therapeutic Effect Analysis.

    **POST**: ``/api/queryTherapeuticEffectAnalysis``

    Args:
      participant_uid (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.
      experiment (uuid): Experiment Identifier

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains list of all Therapy Change Logs and Therapy Configurations.
    """
    
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        accepted_keys = []
        required_keys = ["participant_uid", "experiment_uid", "request_type"]
        if not checkAPIInput(request.data, required_keys, accepted_keys):
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        try:
            UUID(request.data["participant_uid"]) # Will throw if it is not UUID
            participant = models.Participant.nodes.get(uid=request.data["participant_uid"])
        except:
            # uid is not a UUID
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        if not request.user.checkPermission(participant, "view"):
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        try:
            UUID(request.data["experiment_uid"]) # Will throw if it is not UUID
            experiment = participant.experiments.get(uid=request.data["experiment_uid"])
        except:
            # uid is not a UUID
            return Response(status=400, data={"message": "Experiment ID Incorrect. Please Selected Experiment in Participant Overview Page."})
        
        if request.data["request_type"] == "Overview":
            data = TimeSeriesAnalysis.queryAvailableAnalysis(experiment, "therapeutic-effect")
            return Response(status=200, data=data)
        
        elif request.data["request_type"] == "QueryData":
            required_keys.extend(["analysis_uid"])
            if not checkAPIInput(request.data, required_keys, accepted_keys):
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
            
            analysis = experiment.analyses.get_or_none(uid=request.data["analysis_uid"])
            if not analysis:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            request.user.configuration["ProcessingConfiguration"], updated = Database.retrieveProcessingSettings(request.user.configuration)
            if updated:
                request.user.save()
            
            models.CachedResult.clearCaches()
            #cache = models.CachedResult.nodes.get_or_none(type="QueryTherapeuticEffectAnalysis", metadata={**request.data, **request.user.configuration["ProcessingConfiguration"]})
            cache = None
            if not cache:
                data = TimeSeriesAnalysis.queryAnalysisResult(analysis, request.user.configuration["ProcessingConfiguration"])
                data = TimeSeriesAnalysis.extractTherapeuticPowerSpectrum(data)
                
                cache = models.CachedResult(type="QueryTherapeuticEffectAnalysis", metadata={**request.data, **request.user.configuration["ProcessingConfiguration"]})
                cache.createCache(request.user, data)
                cache.save()
            else:
                data = Database.loadSourceDataPointer(cache.data_pointer, cache.hashed, dataType="visualization")
            
            data = TimeSeriesAnalysis.extractVisualizationChannel(data)
            return Response(status=200, data=data)

        elif request.data["request_type"] == "QueryChannel":
            required_keys.extend(["analysis_uid","channel"])
            if not checkAPIInput(request.data, required_keys, accepted_keys):
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
            
            analysis = experiment.analyses.get_or_none(uid=request.data["analysis_uid"])
            if not analysis:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            request.user.configuration["ProcessingConfiguration"], updated = Database.retrieveProcessingSettings(request.user.configuration)
            if updated:
                request.user.save()
            
            models.CachedResult.clearCaches()
            cache = models.CachedResult.nodes.get_or_none(type="QueryTherapeuticEffectAnalysis", metadata={**request.data, **request.user.configuration["ProcessingConfiguration"]})
            if not cache:
                data = TimeSeriesAnalysis.queryAnalysisResult(analysis, request.user.configuration["ProcessingConfiguration"])
            
                cache = models.CachedResult(type="QueryTherapeuticEffectAnalysis", metadata={**request.data, **request.user.configuration["ProcessingConfiguration"]})
                cache.createCache(request.user, data)
                cache.save()
            else:
                data = Database.loadSourceDataPointer(cache.data_pointer, cache.hashed, dataType="visualization")
            
            data = TimeSeriesAnalysis.extractVisualizationChannel(data, channel_name=request.data["channel"])
            return Response(status=200, data=data)
        
        return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

