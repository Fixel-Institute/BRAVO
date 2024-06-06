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
Session Configuration Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from email.policy import default
import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings

from modules import Database
import json
from copy import deepcopy

import pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

defaultSessionConfigs = {
    "language": "en",
    "miniSidenav": False,
    "darkMode": False
}

def formatRequestSession(session):
    formattedSession = dict()
    #TODO: Verify all patient_deidentified_id will be updated in final version
    if "subject_deidentified_id" in session.keys():
        formattedSession["subjectID"] = session["subject_deidentified_id"]

    for key in defaultSessionConfigs.keys():
        if key in session.keys():
            formattedSession[key] = session[key]
        else:
            formattedSession[key] = deepcopy(defaultSessionConfigs[key])

    if "ProcessingSettings" in session.keys():
        formattedSession["processingConfiguration"] = session["ProcessingSettings"]

    return formattedSession

class QuerySessionConfigs(RestViews.APIView):
    permission_classes = [AllowAny]
    parser_classes = [RestParsers.JSONParser]
    
    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if request.user.is_authenticated:
            userConfig = request.user.getConfiguration()
            userConfig["ProcessingSettings"], changed = Database.retrieveProcessingSettings(userConfig)
            if changed:
                request.user.setConfiguration(userConfig)

            userSession = formatRequestSession(userConfig)
            for key in request.data["session"].keys():
                if not key in userSession.keys():
                    userSession[key] = request.data["session"][key]
            return Response(status=200, data={"session": userSession, "user": Database.extractUserInfo(request.user)})
        
        userSession = formatRequestSession({})

        response = Response(status=200)
        response.delete_cookie("refreshToken")
        response.delete_cookie("accessToken")
        response.data = {"session": userSession, "user": {}}
        return response

class UpdateSessionConfig(RestViews.APIView):
    permission_classes = [AllowAny]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if request.user.is_authenticated:
            userConfig = request.user.getConfiguration()
            userConfig["ProcessingSettings"], _ = Database.retrieveProcessingSettings(userConfig)

            for key in request.data.keys():
                if key in defaultSessionConfigs.keys():
                    if key in request.data.keys():
                        userConfig[key] = request.data[key]

            request.user.setConfiguration(userConfig)
        return Response(status=200)
