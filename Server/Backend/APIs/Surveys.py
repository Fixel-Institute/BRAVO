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
Survey Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

import json
import uuid
from copy import deepcopy
import datetime
from Backend import models
import random, string

import requests
from xml.dom import minidom

from modules import SurveyScheduler

import pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

class AddNewSurvey(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
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
            return Response(status=200, data={
                    "id": survey.survey_id,
                    "url": survey.url,
                    "name": survey.name,
                    "date": survey.date.timestamp()
                })

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class RequestSurveyAccessCode(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if not "id" in request.data or not "tokenModification" in request.data:
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        survey = models.CustomizedSurvey.objects.filter(creator=request.user.unique_user_id, survey_id=request.data["id"]).first()
        if survey:
            if request.data["tokenModification"] == "view":
                if len(survey.authorized_users) > 0:
                    return Response(status=200, data={
                            "token": survey.authorized_users[0]
                        })
                else: 
                    return Response(status=200, data={
                            "token": ""
                        })

            elif request.data["tokenModification"] == "new":
                survey.authorized_users = [str(uuid.uuid4())]
                survey.save()
                return Response(status=200, data={
                        "token": survey.authorized_users[0]
                    })

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QuerySurveyResults(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [AllowAny]
    def post(self, request):
        if not "token" in request.data:
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        survey = models.CustomizedSurvey.objects.filter(authorized_users=[request.data["token"]]).first()
        if survey:
            results = models.SurveyResults.objects.filter(survey_id=survey.survey_id, responder=request.data["passcode"]).all()
            if "delete" in request.data:
                results.delete()
                return Response(status=200)

            return Response(status=200, data=[{"value": results[i].values, "date": results[i].date.timestamp()} for i in range(len(results))])

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryAvailableSurveys(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.is_authenticated:
            surveys = models.CustomizedSurvey.objects.filter(creator=request.user.unique_user_id, archived=False)
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

class QueryAvailableRedcapSchedule(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.is_authenticated:
            redcapSchedule = models.RedcapSurveyLink.objects.filter(owner=request.user.unique_user_id)
            data = list()
            for schedule in redcapSchedule:
                services = models.TwilioService.objects.filter(linkage_id=schedule.linkage_id).all()
                survey = models.CustomizedSurvey.objects.filter(survey_id=schedule.survey_id).first()

                for service in services:
                    if survey: 
                        data.append({
                            "id": schedule.linkage_id,
                            "surveyId": survey.url,
                            "reportId": service.report_id,
                            "redcapSurveyName": schedule.redcap_survey_name,
                            "twilioLink": {
                                "repeat": service.repeat,
                                "enabled": service.enabled,
                                "timestamps": service.timestamps,
                                "receiver": service.patient_id,
                            }
                        })
                    else:
                        data.append({
                            "id": schedule.linkage_id,
                            "surveyId": schedule.survey_id,
                            "redcapSurveyName": schedule.redcap_survey_name,
                        })

            return Response(status=200, data=data)
        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QuerySurveyContent(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [AllowAny]
    def post(self, request):
        survey = models.CustomizedSurvey.objects.filter(url=request.data["id"], archived=False).first()
        if survey:
            if request.user.is_authenticated:
                return Response(status=200, data={"contents": survey.contents, "id": survey.url, "version": survey.version, "title": survey.name, "date": survey.date.timestamp(), "editable": request.user.unique_user_id == survey.creator})
            else:
                return Response(status=200, data={"contents": survey.contents, "id": survey.url, "version": survey.version, "title": survey.name, "date": survey.date.timestamp(), "editable": False})

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class UpdateSurveyContent(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.is_authenticated:
            survey = models.CustomizedSurvey.objects.filter(url=request.data["id"], creator=request.user.unique_user_id, archived=False).first()
            if survey:
                survey.name = request.data["title"]
                survey.contents = request.data["contents"]
                survey.date = datetime.datetime.now()
                survey.version = survey.version + 1
                survey.save()
                return Response(status=200)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class ArchiveSurvey(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.is_authenticated:
            survey = models.CustomizedSurvey.objects.filter(url=request.data["id"], creator=request.user.unique_user_id, archived=False).first()
            if survey:
                survey.archived = True
                survey.save()
                return Response(status=200)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class SubmitSurveyResults(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [AllowAny]
    def post(self, request):
        if request.user.is_authenticated:
            survey = models.CustomizedSurvey.objects.filter(url=request.data["id"], archived=False).first()
            if survey:
                result = models.SurveyResults(survey_id=survey.survey_id, version=request.data["version"], responder=request.user.email, values=request.data["results"], date=datetime.datetime.fromtimestamp(request.data["date"]/1000))
                result.save()
                return Response(status=200)

        elif "passcode" in request.data:
            survey = models.CustomizedSurvey.objects.filter(url=request.data["id"], archived=False).first()
            result = models.SurveyResults(survey_id=survey.survey_id, version=request.data["version"], responder=request.data["passcode"], values=request.data["results"], date=datetime.datetime.fromtimestamp(request.data["date"]/1000))
            result.save()
            
            service = models.TwilioService.objects.filter(report_id=request.data["passcode"]).first()
            linkage = models.RedcapSurveyLink.objects.filter(linkage_id=service.linkage_id).first()
            if linkage.survey_id == survey.survey_id:
                resultingCSV = linkage.redcap_record_id + ","
                respondRow = service.patient_id + ","

                resultingCSV += "redcap_repeat_instance,"
                resultingCSV += "redcap_repeat_instrument,"

                response = requests.post(linkage.redcap_server, data={
                    "token": linkage.redcap_token,
                    "content": "record",
                    "format": "json",
                    "type": "flat",
                    "records": service.patient_id,
                    "forms": linkage.redcap_survey_name,
                    "exportSurveyFields": True
                })
                respondRow += f"{len(response.json())},"
                respondRow += linkage.redcap_survey_name + ","

                for page in range(len(survey.contents)):
                    for questionId in range(len(survey.contents[page]["questions"])):
                        question = survey.contents[page]["questions"][questionId]

                        if not question["variableName"]:
                            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
                        resultingCSV += question["variableName"] + ","

                        if not question["show"]:
                            if question["validation"] == "datetime_seconds_ymd":
                                respondRow += datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S") + ","
                        else:
                            if question["type"] == "text":
                                respondRow += "\"" + str(request.data["results"][page][questionId]) + "\","
                            else:
                                respondRow += str(request.data["results"][page][questionId]) + ","
                
                resultingCSV += linkage.redcap_survey_name + "_complete"
                respondRow += "2"

                response = requests.post(linkage.redcap_server, data={
                    "token": linkage.redcap_token,
                    "content": "record",
                    "format": "csv",
                    "type": "flat",
                    "overwriteBehavior": "normal",
                    "forceAutoNumber": False,
                    "data": resultingCSV + "\n" + respondRow
                })

                if response.status_code == 200:
                    return Response(status=200)
                else:
                    print(response.content)
                    
        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class RedcapVerification(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.is_authenticated:
            if not "redcapServer" in request.data or not "redcapSurveyName" in request.data or not "redcapToken" in request.data:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            survey = models.CustomizedSurvey.objects.filter(url=request.data["surveyId"], archived=False).first()
            if not survey:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            linkage = models.RedcapSurveyLink.objects.filter(owner=request.user.unique_user_id, survey_id=survey.survey_id, redcap_server=request.data["redcapServer"], redcap_token=request.data["redcapToken"], redcap_survey_name=request.data["redcapSurveyName"]).first()
            if linkage:
                return Response(status=200, data={"linkageId": linkage.linkage_id})

            try:
                response = requests.post(request.data["redcapServer"], data={
                    "token": request.data["redcapToken"],
                    "content": "project_xml",
                })

                if response.status_code != 200:
                    print(response)
                    return Response(status=500)

                dom = minidom.parseString(response.text)
                MetaDataVersion = dom.getElementsByTagName("MetaDataVersion")[0]
                if MetaDataVersion.hasAttribute("redcap:RecordIdField"):
                    recordIdField = MetaDataVersion.getAttribute("redcap:RecordIdField")
                else:
                    recordIdField = "record_id"
                
                response = requests.post(request.data["redcapServer"], data={
                    "token": request.data["redcapToken"],
                    "content": "metadata",
                    "format": "json",
                })

                availableFields = []
                data = response.json()
                for field in data:
                    if (field["form_name"] == request.data["redcapSurveyName"]):
                        availableFields.append(field["field_name"])

                for page in survey.contents:
                    for question in page["questions"]:
                        if question["variableName"] in availableFields:
                            availableFields.remove(question["variableName"]) 
                        else:
                            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
                
                if len(availableFields) > 0:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                linkage = models.RedcapSurveyLink(owner=request.user.unique_user_id, survey_id=survey.survey_id, redcap_server=request.data["redcapServer"], redcap_token=request.data["redcapToken"], redcap_survey_name=request.data["redcapSurveyName"], redcap_record_id=recordIdField)
                linkage.save()
                return Response(status=200, data={"linkageId": linkage.linkage_id})

            except Exception as e:
                print(e)
                return Response(status=500)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class SetupSurveyScheduler(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.is_authenticated:
            if not "linkageId" in request.data:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            linkage = models.RedcapSurveyLink.objects.filter(linkage_id=request.data["linkageId"], owner=request.user.unique_user_id).first()
            if not linkage:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if "removeSchedule" in request.data:
                try:
                    models.ScheduledSurveys.objects.filter(linkage_id=linkage.linkage_id, report_id=request.data["removeSchedule"]).delete()
                    models.TwilioService.objects.filter(linkage_id=linkage.linkage_id, report_id=request.data["removeSchedule"]).delete()
                    if not models.TwilioService.objects.filter(linkage_id=linkage.linkage_id).exists():
                        linkage.delete()
                    return Response(status=200)

                except Exception as e:
                    print(e)
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            else:
                try:
                    expectedTimestamps = []
                    if request.data["frequency"]["repeat"] == "daily":
                        for timestamp in request.data["frequency"]["timestamps"]:
                            expectedTimestamps.append(datetime.datetime.fromisoformat(timestamp.replace("Z","+00:00")).timestamp() % (24*3600))
                    elif request.data["frequency"]["repeat"] == "weekly":
                        for timestamp in request.data["frequency"]["timestamps"]:
                            expectedTimestamps.append(datetime.datetime.fromisoformat(timestamp.replace("Z","+00:00")).timestamp() % (7*24*3600))

                    models.TwilioService(linkage_id=linkage.linkage_id, account_id=request.data["twilio"]["accountId"],
                                        service_id=request.data["twilio"]["serviceId"], authToken=request.data["twilio"]["authToken"],
                                        repeat=request.data["frequency"]["repeat"], timestamps=expectedTimestamps, 
                                        receiver={
                                            "messageFormat": request.data["receiver"]["messageFormat"],
                                            "value": request.data["receiver"]["value"],
                                            "type": request.data["receiver"]["type"]
                                        }, patient_id=request.data["receiver"]["patientId"], enabled=False).save()
                    return Response(status=200)

                except Exception as e:
                    print(e)
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})


        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class SurveySchedulerStatus(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if request.user.is_authenticated:
            if not "linkageId" in request.data and not "reportId" in request.data:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            linkage = models.RedcapSurveyLink.objects.filter(linkage_id=request.data["linkageId"], owner=request.user.unique_user_id).first()
            if not linkage:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            service = models.TwilioService.objects.filter(linkage_id=request.data["linkageId"], report_id=request.data["reportId"]).first()
            if not service:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if "enabledState" in request.data:
                if request.data["enabledState"] != service.enabled:
                    service.enabled = request.data["enabledState"]
                service.save()

                if not request.data["enabledState"]:
                    models.ScheduledSurveys.objects.filter(linkage_id=request.data["linkageId"], report_id=service.report_id).delete()
                else:
                    allSchedules = []
                    currentTime = datetime.datetime.now().timestamp()
                    if service.repeat == "daily":
                        currentTime = currentTime - (currentTime % (24*3600))
                        for i in range(365):
                            for timestamp in service.timestamps:
                                allSchedules.append(models.ScheduledSurveys(linkage_id=request.data["linkageId"], report_id=service.report_id, date=datetime.datetime.fromtimestamp(currentTime + i * 24*3600 + timestamp)))
                    models.ScheduledSurveys.objects.bulk_create(allSchedules)
                return Response(status=200)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
