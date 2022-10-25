import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response

import json
from copy import deepcopy
import datetime
from Backend import models
import random, string

import pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

class AddNewSurvey(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not "name" in request.data:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if len(request.data["name"]) == 0:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            while True:
                uniqueUrl = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
                surveys = models.CustomizedSurvey.objects.filter(url=uniqueUrl).all()
                if len(surveys) == 0:
                    break
            
            survey = models.CustomizedSurvey(creator=request.user.unique_user_id, name=request.data["name"], url=uniqueUrl)
            survey.save()
            return Response(status=200, data={"url": uniqueUrl, "name": survey.name, "date": survey.date.timestamp()})

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryAvailableSurveys(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            surveys = models.CustomizedSurvey.objects.filter(creator=request.user.unique_user_id)
            data = list()
            for survey in surveys:
                data.append({
                    "id": survey.survey_id,
                    "url": survey.url,
                    "name": survey.name,
                    "date": survey.date.timestamp()
                })
            return Response(status=200, data=data)
        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QuerySurveyContent(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        survey = models.CustomizedSurvey.objects.filter(url=request.data["id"]).first()
        if survey:
            if request.user.is_authenticated:
                return Response(status=200, data={"contents": survey.contents, "title": survey.name, "date": survey.date.timestamp(), "editable": request.user.unique_user_id == survey.creator})
            else:
                return Response(status=200, data={"contents": survey.contents, "title": survey.name, "date": survey.date.timestamp(), "editable": False})

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class UpdateSurveyContent(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            survey = models.CustomizedSurvey.objects.filter(url=request.data["id"], creator=request.user.unique_user_id).first()
            if survey:
                survey.name = request.data["title"]
                survey.contents = request.data["contents"]
                survey.date = datetime.datetime.now()
                survey.save()
                return Response(status=200)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
