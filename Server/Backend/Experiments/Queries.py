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
All Queries Routes
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import HttpResponse

from Backend import models

from modules import Database, ImageDatabase, AnalysisBuilder, WearableRecordingsDatabase, Therapy, RealtimeStream
from modules.Percept import Sessions, BrainSenseSurvey, BrainSenseEvent, BrainSenseStream, IndefiniteStream, ChronicBrainSense, TherapeuticPrediction, AdaptiveStimulation
from modules.Summit import ChronicLogs, StreamingData
from utility.PythonUtility import uniqueList
import json
import numpy as np
import nibabel as nib
import pytz
from datetime import datetime

from Backend.Experiments import TremorStudy

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class QueryTremorStudyResults(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0 or Authority["Level"] == 2:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")

        PatientInfo = Database.extractAccess(request.user, request.data["id"])
        Authority["Devices"] = PatientInfo.device_deidentified_id

        if "requestOverview" in request.data:
            ExistingAnalysis = AnalysisBuilder.getExistingAnalysis(request.user, request.data["id"], Authority)
            for analysis in ExistingAnalysis:
                analysisOverview = AnalysisBuilder.queryAnalysis(request.user, request.data["id"], analysis["AnalysisID"], Authority)
                if "Results" in analysisOverview["Configuration"].keys():
                    for i in range(len(analysisOverview["Configuration"]["Results"])):
                        if analysisOverview["Configuration"]["Results"][i]["Type"] == "AlignedData":
                            
                            result = {
                                "ResultID": analysisOverview["Configuration"]["Results"][i]["ProcessedData"],
                                "AnalysisID": analysis["AnalysisID"]
                            }
                            annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=request.data["id"],  event_type="Streaming")
                            result["Annotations"] = ["All Periods"]
                            result["Annotations"].extend([item.event_name for item in annotations])
                            result["Annotations"] = np.unique(result["Annotations"]).tolist()

                            return Response(status=200, data=result)

        if "requestAccelerometerData" in request.data:
            if request.data["eventPeriod"] == "All Periods":
                eventPeriod = []
            else:
                annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=request.data["id"], event_name=request.data["eventPeriod"], event_type="Streaming").all()
                eventPeriod = [{
                    "EventTime": item.event_time.timestamp(),
                    "EventDuration": item.event_duration
                } for item in annotations]
            result, _ = AnalysisBuilder.queryResultData(request.user, request.data["id"], request.data["analysisId"], request.data["resultId"], False, Authority)
            result = TremorStudy.ExtractAlignedDataOverview(result, eventPeriod=eventPeriod)
            if not result:
                return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
            return Response(status=200, data=result)

        elif "requestCorrelation" in request.data:
            if request.data["eventPeriod"] == "All Periods":
                eventPeriod = []
            else:
                annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=request.data["id"], event_name=request.data["eventPeriod"], event_type="Streaming").all()
                eventPeriod = [{
                    "EventTime": item.event_time.timestamp(),
                    "EventDuration": item.event_duration
                } for item in annotations]
            result, _ = AnalysisBuilder.queryResultData(request.user, request.data["id"], request.data["analysisId"], request.data["resultId"], False, Authority)
            result = TremorStudy.ExtractSpectrogramData(result, sensorName=request.data["sensor"], channelName=request.data["dataChannel"], eventPeriod=eventPeriod)
            return Response(status=200, data=result)

        return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})