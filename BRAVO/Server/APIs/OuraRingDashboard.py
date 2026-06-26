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
from modules.HelperFunctions import sanitize_input, get_or_none, PKCE_code_challenger
from modules import Database, DataCurator
from modules.OURA import DataManager as OuraDataManager

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')

class OuraRingAuthHandler(RestViews.APIView):

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

        device = models.OuraRingDevice.find(owner=Participant)
        if not device:
            device = models.OuraRingDevice.create(owner=Participant)

        if request.data["RequestType"] == "RequestURL":
            if len(device.auth.keys()) > 0:
                return Response(status=200, data=device.date_periods)
            
        if request.data["RequestType"] == "RequestURL":
            if len(device.auth.keys()) > 0:
                return Response(status=200, data=device.date_periods)

            OuraAuthURL = "https://cloud.ouraring.com/oauth/authorize?" + urlencode({
                "response_type": "code",
                "client_id": os.environ["OURA_CLIENT_ID"],
                "state": device.uid,
                "redirect_uri": os.environ["OURA_CLIENT_REDIRECT_URI"],
                "scope": "email personal daily heartrate tag workout session spo2 ring_configuration stress heart_health"
            })
            return Response(status=200, data={"OAuthURL": OuraAuthURL})

        elif request.data["RequestType"] == "VerifyToken":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "ParticipantId", "AccessToken"]):
                return Response(status=400, data={"message": "Malformed Input"})

            if not Participant.institute.has_permission(request.user, "Upload"):
                return Response(status=403)
            
            if not request.data["AccessToken"].startswith("https://bravo-redirect.jcagle.solutions/oauth/redirect?"):
                return Response(status=400, data={"message": "Malformed Input"})
            
            tokenURL = parse_qs(request.data["AccessToken"].replace("https://bravo-redirect.jcagle.solutions/oauth/redirect?",""))
            if not len(tokenURL.keys()) == 3:
                return Response(status=400, data={"message": "Malformed Input"})

            if not tokenURL["state"][0] == device.uid:
                return Response(status=400, data={"message": "Verification Failed"})
            
            OuraRing = OuraDataManager.OuraRingAPI(tokenURL["code"][0])
            verified = False
            try:
                OuraRing.refreshToken(auth_code=tokenURL["code"][0])
                verified = OuraRing.verifyToken()
            except Exception as e:
                return Response(status=400, data={"message": "Verification Failed"})
            
            if not verified:
                return Response(status=400, data={"message": "Verification Failed"})
            
            device.auth["refresh_token"] = OuraRing.refresh_token
            device.auth["token"] = tokenURL["code"][0]
            device.save()
            return Response(status=200)
        
            
        elif request.data["RequestType"] == "DeleteAuthentication":
            #DataManager.deleteFitbitData(Participant)
            device.auth = {}
            device.save()
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
                for j in range(len(request.data["DatePeriods"][i])):
                    request.data["DatePeriods"][i][j] = float(request.data["DatePeriods"][i][j])

            device.date_periods = request.data["DatePeriods"]
            device.save()
            return Response(status=200)
        
        return Response(status=400, data={"message": "Malformed Input"})

class QueryOuraRingData(RestViews.APIView):

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
        device = models.OuraRingDevice.find(owner=Participant)
        if not device:
            device = models.OuraRingDevice.create(owner=Participant)

        if len(device.auth.keys()) == 0:
            return Response(status=400, data={"message": "Verification Failed"})

        if request.data["RequestType"] == "RequestOverview":
            Data = OuraDataManager.loadOuraRingData(Participant)
            return Response(status=200, data=Data)
        elif request.data["RequestType"] == "RefreshOuraRingData":
            OuraDataManager.refreshOuraRingData(device)
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
        device = models.OuraRingDevice.find(owner=Participant)
        if not device:
            return Response(status=403)
        
        if len(device.auth.keys()) == 0:
            return Response(status=400, data={"message": "Verification Failed"})

        Data = OuraDataManager.loadOuraRingData(Participant)
        result = pickle.dumps(Data)
        return HttpResponse(bytes(result), status=200, headers={
            "Content-Type": "application/octet-stream"
        })
