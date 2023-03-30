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
Speech Mobile Application Processing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from email.policy import default
import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from modules import Database
import json
from copy import deepcopy

from django.middleware.csrf import get_token
from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response

import numpy as np
from scipy import signal

from Backend import models

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class UploadRecording(RestViews.APIView):
    parser_classes = [RestParsers.MultiPartParser, RestParsers.FormParser]
    permission_classes = [AllowAny]

    def post(self, request):
        if not "file" in request.data or not "authorization" in request.data:
            return Response(status=403, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        if not request.data["authorization"] == "ufbravospeechupload":
            return Response(status=401)

        rawBytes = request.data["file"].read()
        with open(DATABASE_PATH + "cache" + os.path.sep + request.data["file"].name, "wb+") as file:
            file.write(rawBytes)
            
        return Response(status=200)
