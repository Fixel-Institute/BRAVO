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
Data Queries Handler
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

from modules import Database, DataDecoder
from modules.Percept import Therapy as PerceptTherapy, BrainSenseSurvey, BrainSenseEvent
from modules import TimeSeriesAnalysis

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
        accepted_keys = ["participant_uid", "report_type"]
        required_keys = ["participant_uid", "report_type"]
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

        if request.data["report_type"] == "PerceptReport":
            TherapyHistory = PerceptTherapy.queryTherapyHistory(participant)
            return Response(status=200, data=TherapyHistory)
        
        return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

class QueryBaselinePSDs(RestViews.APIView):
    """ Query all baseline PSDs from desired participant.

    The baseline PSDs should be computed for each events/visits

    **POST**: ``/api/queryBaselinePSDs``

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
        accepted_keys = ["participant_uid", "report_type"]
        required_keys = ["participant_uid", "report_type"]
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

        if request.data["report_type"] == "PerceptReport":
            SurveyResults = BrainSenseSurvey.querySurveyResults(participant, options=request.user.configuration["ProcessingSettings"]["PowerSpectralDensity"])
            return Response(status=200, data={"data": SurveyResults, "config": request.user.configuration["ProcessingSettings"]["PowerSpectralDensity"]})
        
        return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
    
class QueryTimeSeriesAnalysis(RestViews.APIView):
    """ Query all baseline PSDs from desired participant.

    The baseline PSDs should be computed for each events/visits

    **POST**: ``/api/queryTimeSeriesAnalysis``

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
        accepted_keys = ["participant_uid", "report_type", "request_type", "name", "analysis_uid", "recording_uids", "config"]
        required_keys = ["participant_uid", "report_type", "request_type"]
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

        if request.data["report_type"] == "GeneralReport":
            if request.data["request_type"] == "overview":
                overview = TimeSeriesAnalysis.queryAvailableAnalysis(participant)
                return Response(status=200, data=overview)
            
            elif request.data["request_type"] == "create":
                analysis = models.CombinedAnalysis(name=request.data["name"], type="TimeseriesAnalysis", date=datetime.datetime.now().timestamp()).save()
                participant.analyses.connect(analysis)
                return Response(status=200, data={
                    "uid": analysis.uid,
                    "name": analysis.name,
                    "status": analysis.status,
                    "date": analysis.date,
                    "recordings": [recording.uid for recording in analysis.recordings]
                })
            
            elif request.data["request_type"] == "get_config":
                data = list()
                analysis = participant.analyses.get_or_none(uid=request.data["analysis_uid"])
                for recording in analysis.recordings:
                    rel = analysis.recordings.relationship(recording)
                    data.append({
                        "uid": recording.uid,
                        "shift": rel.time_shift,
                        "type": recording.type,
                        "date": recording.date,
                        "channels": recording.channel_names,
                        "data_type": rel.data_type
                    })
                    
                return Response(status=200, data=data)
            
            elif request.data["request_type"] == "set_config":
                analysis = participant.analyses.get_or_none(uid=request.data["analysis_uid"])
                for recording_uid in request.data["config"].keys():
                    recording = analysis.recordings.get_or_none(uid=recording_uid)
                    if recording:
                        rel = analysis.recordings.relationship(recording)
                        try:
                            rel.time_shift = float(request.data["config"][recording_uid]["shift"])
                            rel.data_type = request.data["config"][recording_uid]["data_type"]
                            rel.save()
                        except:
                            pass
                        
                return Response(status=200)
            
            elif request.data["request_type"] == "select_recordings":
                required_keys = ["participant_uid", "report_type", "request_type", "analysis_uid", "recording_uids"]
                if not checkAPIInput(request.data, required_keys, accepted_keys):
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                analysis = participant.analyses.get_or_none(uid=request.data["analysis_uid"])
                if not analysis:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                
                for i in range(len(request.data["recording_uids"])):
                    for device in participant.devices:
                        recording = device.recordings.get_or_none(uid=request.data["recording_uids"][i])
                        if recording:
                            analysis.recordings.connect(recording)
                            break
                
                analysis.status = "InProgress"
                analysis.save()
                return Response(status=200)
            
            elif request.data["request_type"] == "get_result":
                analysis = participant.analyses.get_or_none(uid=request.data["analysis_uid"])
                data = TimeSeriesAnalysis.processTimeSeriesAnalysis(analysis)
                return Response(status=200, data=data)
            
        return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

class QueryTimeSeriesRecording(RestViews.APIView):
    """ Query time-series recordings (list).

    **POST**: ``/api/queryTimeSeriesRecording``

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
        accepted_keys = ["participant_uid", "report_type", "request_type", "recording_uid", "channel", "labels", "name", "time", "duration"]
        required_keys = ["participant_uid", "report_type", "request_type", "recording_uid"]
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

        if request.data["report_type"] == "GeneralReport":
            if request.data["request_type"] == "update_labels":
                if not request.user.checkPermission(participant, "edit"):
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                for device in participant.devices:
                    recording = device.recordings.get_or_none(uid=request.data["recording_uid"])
                    if recording:
                        break 
                
                if not recording:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                recording.labels = request.data["labels"]
                recording.save()
                return Response(status=200)
            
            elif request.data["request_type"] == "view":
                for device in participant.devices:
                    recording = device.recordings.get_or_none(uid=request.data["recording_uid"])
                    if recording:
                        break 
                
                if not recording:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                if "channel" in request.data: 
                    data = TimeSeriesAnalysis.queryTimeSeriesRecording(recording, channel=request.data["channel"])
                else:
                    data = TimeSeriesAnalysis.queryTimeSeriesRecording(recording, info=True)
                return Response(status=200, data=data)
            
            elif request.data["request_type"] == "new_annotation":
                required_keys.extend(["name", "time", "duration"])
                if not checkAPIInput(request.data, required_keys, accepted_keys):
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
                
                for device in participant.devices:
                    recording = device.recordings.get_or_none(uid=request.data["recording_uid"])
                    if recording:
                        break 
                
                if not recording:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                annotation = models.Annotation(name=request.data["name"], date=request.data["time"], duration=request.data["duration"]).save()
                recording.annotations.connect(annotation)
                return Response(status=200)
            
        return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
    
    
    
    