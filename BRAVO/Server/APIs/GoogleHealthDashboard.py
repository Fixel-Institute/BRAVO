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
Fitbit Dashboard APIs
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os
import json
import traceback
from copy import deepcopy
from pathlib import Path
import hmac, hashlib, base64
from urllib.parse import urlencode, parse_qs
import pickle

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings

from Server import models
from modules.HelperFunctions import sanitize_input, get_or_none
from modules import Database, DataCurator
from modules.GoogleHealth import DataQuery

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')

class GoogleHealthAuthHandler(RestViews.APIView):

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "ParticipantId"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        Participant = models.Participant.find(uid=request.data["ParticipantId"])
        if not Participant:
            return Response(status=403)

        device = models.GoogleHealth.find(owner=Participant)
        if not device:
            device = models.GoogleHealth.create(owner=Participant)
        
        if request.data["RequestType"] == "RequestURL":
            if len(device.auth.keys()) > 0:
                return Response(status=200, data=device.date_periods)
            
            GoogleHealth_CLIENT_ID = os.environ["GoogleHealth_CLIENT_ID"]
            redirect_uri = os.environ["GoogleHealth_CLIENT_REDIRECT_URI"]
            scopes = [
                "https://www.googleapis.com/auth/googlehealth.activity_and_fitness.readonly",
                "https://www.googleapis.com/auth/googlehealth.health_metrics_and_measurements.readonly",
                "https://www.googleapis.com/auth/googlehealth.nutrition.readonly",
                "https://www.googleapis.com/auth/googlehealth.sleep.readonly",
            ]
            GoogleHealthAuthURL = "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
                "client_id": GoogleHealth_CLIENT_ID,
                "redirect_uri": redirect_uri,
                "response_type": "code",
                "access_type": "offline",
                "prompt": "consent",
                "scope": ' '.join(scopes)
            })
            return Response(status=200, data={"OAuthURL": GoogleHealthAuthURL})
        
        elif request.data["RequestType"] == "VerifyToken":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "ParticipantId", "TokenURL"]):
                return Response(status=400, data={"message": "Malformed Input"})

            redirect_uri = os.environ["GoogleHealth_CLIENT_REDIRECT_URI"]
            print(request.data["TokenURL"])
            if not request.data["TokenURL"].startswith(redirect_uri+"?"):
                return Response(status=400, data={"message": "Malformed Input"})
            print("test")
            if not Participant.institute.has_permission(request.user, "Upload"):
                return Response(status=403)
            
            tokenURL = parse_qs(request.data["TokenURL"].replace(redirect_uri+"?",""))
            if not len(tokenURL.keys()) > 2:
                return Response(status=400, data={"message": "Malformed Input"})
            
            code = tokenURL["code"][0]
            data = DataQuery.retrieveToken(code)
            if not data:
                return Response(status=400, data={"message": "Verification Failed"})

            device.auth = data
            device.save()
            return Response(status=200)
            
        elif request.data["RequestType"] == "DeleteAuthentication":
            device.delete()
            return Response(status=200)
            
        elif request.data["RequestType"] == "SetAuthPeriod":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "ParticipantId", "DatePeriods"]):
                return Response(status=400, data={"message": "Malformed Input"})

            if len(device.auth.keys()) == 0:
                return Response(status=400, data={"message": "Verification Failed"})

            if not Participant.institute.has_permission(request.user, "Upload"):
                return Response(status=403)
            
            if not type(request.data["DatePeriods"]) == list:
                return Response(status=400, data={"message": "Malformed Input"})
            for i in range(len(request.data["DatePeriods"])):
                if not type(request.data["DatePeriods"][i]) == list:
                    return Response(status=400, data={"message": "Malformed Input"})
                for j in range(len(request.data["DatePeriods"])):
                    request.data["DatePeriods"][i][j] = float(request.data["DatePeriods"][i][j])

            device.date_periods = request.data["DatePeriods"]
            device.save()
            return Response(status=200)
        
        return Response(status=400, data={"message": "Malformed Input"})

class QueryGoogleHealthData(RestViews.APIView):

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
        
        Participant = models.Participant.find(uid=request.data["ParticipantId"])
        device = models.GoogleHealth.find(owner=Participant)
        if not device:
            device = models.GoogleHealth.create(owner=Participant)
        
        if len(device.auth.keys()) == 0:
            return Response(status=400, data={"message": "Verification Failed"})

        if request.data["RequestType"] == "RequestOverview":
            Data = DataQuery.loadGoogleHealthData(Participant)
            return Response(status=200, data={})
            return Response(status=200, data=Data)
        elif request.data["RequestType"] == "RefreshGoogleHealthData":
            DataQuery.refreshGoogleHealthData(device)
            return Response(status=200)

        return Response(status=200)

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def get(self, request):
        ParticipantId = self.request.query_params.get('ParticipantId')
        Permissions = Database.checkAccessPermission(request.user, ParticipantId, 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        Participant = models.Participant.find(uid=ParticipantId)
        device = models.FitbitDevice.find(owner=Participant)
        if not device:
            device = models.FitbitDevice.create(owner=Participant)
        
        if len(device.auth.keys()) == 0:
            return Response(status=400, data={"message": "Verification Failed"})

        Data = DataManager.loadFitbitData(Participant)
        result = pickle.dumps(Data)
        return HttpResponse(bytes(result), status=200, headers={
            "Content-Type": "application/octet-stream"
        })
