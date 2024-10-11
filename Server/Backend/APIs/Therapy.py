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
from modules import Database, DataDecoder, Therapy

RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class QueryTherapyHistory(RestViews.APIView):
    """ Query all therapy histories from desired participant.

    The therapy histories include both therapy change logs and clinician configurations. 

    **POST**: ``/api/queryTherapyHistory``

    Args:
      report_type (string): Format data for different report type
      participant_uid (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains list of all Therapy Change Logs and Therapy Configurations.
    """
    
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        accepted_keys = ["participant_uid"]
        required_keys = ["participant_uid"]
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

        TherapyHistory = Therapy.queryTherapyHistory(participant)
        return Response(status=200, data=TherapyHistory)
