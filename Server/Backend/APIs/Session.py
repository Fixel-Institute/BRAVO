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
            if not "ProcessingSettings" in request.user.configuration:
                request.user.configuration["ProcessingSettings"] = Database.retrieveProcessingSettings(request.user.configuration)
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
            for key in request.data.keys():
                if key in ["language","miniSidenav","darkMode"]:
                    request.user.configuration[key] = request.data[key]
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