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
    if "patient_deidentified_id" in session.keys():
        formattedSession["patientID"] = session["patient_deidentified_id"]

    for key in defaultSessionConfigs.keys():
        if key in session.keys():
            formattedSession[key] = session[key]
        else:
            formattedSession[key] = deepcopy(defaultSessionConfigs[key])

    if "ProcessingSettings" in session.keys():
        formattedSession["processingConfiguration"] = session["ProcessingSettings"]

    return formattedSession

class QuerySessionConfigs(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [AllowAny]
    def post(self, request):
        if request.user.is_authenticated:
            request.user.configuration["ProcessingSettings"], changed = Database.retrieveProcessingSettings(request.user.configuration)
            if not changed:
                request.user.save()

            userSession = formatRequestSession(request.user.configuration)
            for key in request.data["session"].keys():
                if not key in userSession.keys():
                    userSession[key] = request.data["session"][key]
            return Response(status=200, data={"session": userSession, "user": Database.extractUserInfo(request.user)})
        
        userSession = formatRequestSession({})
        return Response(status=200, data={"session": userSession, "user": {}})

class UpdateSessionConfig(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [AllowAny]
    def post(self, request):
        if request.user.is_authenticated:
            request.user.configuration["ProcessingSettings"], _ = Database.retrieveProcessingSettings(request.user.configuration)

            for key in request.data.keys():
                if key in ["language","miniSidenav","darkMode"]:
                    request.user.configuration[key] = request.data[key]

                if key in ["BrainSenseSurvey"]:
                    for subkey in request.data[key]:
                        if request.data[key][subkey]["value"] in request.user.configuration["ProcessingSettings"]["BrainSenseSurvey"][subkey]["options"]:
                            request.user.configuration["ProcessingSettings"]["BrainSenseSurvey"][subkey]["value"] = request.data[key][subkey]["value"]

            request.user.save()
        return Response(status=200)

class SetPatientID(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.is_authenticated:
            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if Authority["Level"] == 1:
                return Response(status=200)

            elif Authority["Level"] == 2:
                return Response(status=200)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})