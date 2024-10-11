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
Study Participant Manager
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

RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class CreateStudyParticipant(RestViews.APIView):
    """ Create Study Participant in BRAVO Database

    This API will manage study participant in the database. 
    Participant creation will be done via this API call with sufficient metadata provided to the database to uniquely identify a study participant. 

    **POST**: ``/api/createStudyParticipant``

    Args:
      name (string): Name of the study participant
      study (uuid/string): UUID of a study, or string if a new study is being created
      [dob] (float): (Optional) Date of Birth in floating point number (second)
      [sex] (string): ("Male", "Female", "Other") Default sex is Other. 
      [diagnosis] (string): (Optional) Diagnosis String. Primary diagnosis. If multiple, please add as tag. 
        This is customizable. If empty, standard participant will be created as Control (Healthy)
      [disease_start_time] (float): (Optional) Disease start time if known, floating point number (second)

    Returns:
      Response Code 200 if success or 400 if error.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = ["name", "study", "dob", "sex", "diagnosis", "disease_start_time"]
        required_keys = ["name", "study"]
        if not checkAPIInput(request.data, required_keys, accepted_keys):
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        try:
            UUID(request.data["study"]) # Will throw if it is not UUID
            study = models.Study.nodes.get_or_none(uid=request.data["study"])
        except:
            # uid is not a UUID, look for existing study with the same name to add, or try to create new study
            study = None
            for old_study in request.user.studies:
                if old_study.name == request.data["study"]:
                    study = old_study
                    break
            
            if not study:
                study = models.Study(name=request.data["study"]).save()
                study.managers.connect(request.user)
                request.user.studies.connect(study)
        
        # If UID provided does not match existing study. This is malicious attempt at the database. 
        if not study:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        
        # User has no permission to this study. This is malicious attempt at the database. 
        if not study.checkPermission(request.user.user_id):
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        for participant in study.participants:
            if participant.getName() == request.data["name"]:
                return Response(status=400, data={"message": "Duplicate Participant name"})

        if "diagnosis" in request.data:
            participant = models.Participant(name=request.data["name"], diagnosis=request.data["diagnosis"], type="Patient").save()
            if "disease_start_time" in request.data:
                participant.disease_start_time = request.data["disease_start_time"]
        else:
            participant = models.Participant(name=request.data["name"]).save()
        
        if "dob" in request.data:
            participant.date_of_birth = request.data["dob"]
        participant.sex = request.data["sex"] if "sex" in request.data else "Other"

        participant.studies.connect(study)
        study.participants.connect(participant)

        participant.save()
        study.save()
        
        ParticipantInfo = {"uid": participant.uid, "study": study.uid, "name": participant.name}
        try:
            ParticipantInfo["diagnosis"] = participant.diagnosis
        except:
            ParticipantInfo["diagnosis"] = "Control"
        ParticipantInfo["tags"] = [tag.name for tag in participant.tags]
        return Response(status=200, data=ParticipantInfo)

class QueryParticipantExperiments(RestViews.APIView):
    """ Create Experiment in Participant

    **POST**: ``/api/queryParticipantExperiments``

    Returns:
      Response Code 200 if success or 400 if error.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = []
        required_keys = ["request_type", "participant_uid"]
        if not checkAPIInput(request.data, required_keys, accepted_keys):
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        participant = models.Participant.nodes.get_or_none(uid=request.data["participant_uid"])
        if not participant:
            return Response(status=400, data={"message": "Participant not found"})
        
        if "study" in request.data.keys():
            try:
                UUID(request.data["study"]) # Will throw if it is not UUID
                study = participant.studies.get_or_none(uid=request.data["study"])
            except:
                # If UID provided does not match existing study. This is malicious attempt at the database. 
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
            
            # User has no permission to this study. This is malicious attempt at the database. 
            if not study.checkPermission(request.user.user_id):
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        else:
            has_permission = False
            for study in participant.studies:
                if study.checkPermission(request.user.user_id):
                    has_permission = True
                    break 
            if not has_permission:
                return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if request.data["request_type"] == "Create":
            required_keys.extend(["experiment", "metadata"])
            if not checkAPIInput(request.data, required_keys, accepted_keys):
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
            
            for experiment in participant.experiments:
                if experiment.name == request.data["experiment"]:
                    return Response(status=400, data={"message": "Experiment already exists"})
            
            experiment = models.Experiment(name=request.data["experiment"], metadata=json.loads(request.data["metadata"])).save()
            participant.experiments.connect(experiment)
            return Response(status=200, data={"value": experiment.uid, "label": experiment.name})
        
        elif request.data["request_type"] == "Query":
            data = []
            for experiment in participant.experiments:
                data.append({
                    "uid": experiment.uid, "name": experiment.name, "type": experiment.type, "metadata": experiment.metadata,
                    "recordings": 0, "events": 0
                })
                for source_file in experiment.source_files:
                    data[-1]["recordings"] += len(source_file.recordings)
                    data[-1]["events"] += len(source_file.events)
            return Response(status=200, data=data)
            
class UpdateStudyParticipant(RestViews.APIView):
    """ Update Study Participant in BRAVO Database

    This API will manage study participant in the database. 
    Participant creation will be done via this API call with sufficient metadata provided to the database to uniquely identify a study participant. 

    **POST**: ``/api/updateStudyParticipant``

    Args:
      participant_uid (uuid): Participant name. Update API must utilize UUID as input for name to reduce error.
      [name] (string): (Optional) Name of the participant (in readable text)
      [dob] (float): (Optional) Date of Birth in floating point number (second)
      [sex] (string): ("Male", "Female", "Other") Default sex is Other. 
      [tag] (string): (Optional) Comma-separated tag list. 
      [diagnosis] (string): (Optional) Diagnosis String. Primary diagnosis. If multiple, please add as tag. 
        This is customizable. If empty, standard participant will be created as Control (Healthy)
      [disease_start_time] (float): (Optional) Disease start time if known, floating point number (second)

    Returns:
      Response Code 200 if success or 400 if error.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = ["participant_uid", "name", "dob", "sex", "diagnosis", "disease_start_time", "tags"]
        required_keys = ["participant_uid"]
        if not checkAPIInput(request.data, required_keys, accepted_keys):
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        try:
            UUID(request.data["participant_uid"]) # Will throw if it is not UUID
            participant = models.Participant.nodes.get(uid=request.data["participant_uid"])
        except:
            # uid is not a UUID
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        if not request.user.checkPermission(participant, "edit"):
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if "diagnosis" in request.data:
            participant.diagnosis = request.data["diagnosis"]
            if "disease_start_time" in request.data:
                participant.setDiseaseStartTime(request.data["disease_start_time"])
        
        if "dob" in request.data:
            participant.setDateOfBirth(request.data["dob"])
        if "sex" in request.data:
            participant.sex = request.data["sex"]

        if "tags" in request.data:
            for tag in request.data["tags"]:
                tagModel = models.Tag.nodes.get_or_none(name=tag)
                if not tagModel:
                    tagModel = models.Tag(name=tag).save()
                tagModel.participants.connect(participant)
                participant.tags.connect(tagModel)
        
        participant.save()
        return Response(status=200)

class UpdateDeviceInformation(RestViews.APIView):
    """ Update Study Device in BRAVO Database

    This API will manage devices in the database. 

    **POST**: ``/api/updateDeviceInformation``

    Args:
      participant_uid (uuid): Participant name. Update API must utilize UUID as input for name to reduce error.
      device (uuid): Device UUID. Update API must utilize UUID as input for device to reduce error.
      [name] (string): (Optional) Name of the participant (in readable text)
      [leads] (list): (Optional) List of new lead names
      
    Returns:
      Response Code 200 if success or 400 if error.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = ["participant_uid", "device", "name", "leads"]
        required_keys = ["participant_uid", "device"]
        if not checkAPIInput(request.data, required_keys, accepted_keys):
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        try:
            UUID(request.data["participant_uid"]) # Will throw if it is not UUID
            participant = models.Participant.nodes.get(uid=request.data["participant_uid"])
        except:
            # uid is not a UUID
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        if not request.user.checkPermission(participant, "edit"):
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        devices = participant.getDevices(device_uid=request.data["device"])
        if len(devices) == 0:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        device = devices[0]
        
        if "name" in request.data:
            if not request.data["name"] == "":
                device.name = request.data["name"]
        
        if "leads" in request.data:
            for leadInfo in request.data["leads"]:
                lead = device.electrodes.get(name=leadInfo["name"])
                if leadInfo["custom_name"] == "":
                    lead.custom_name = lead.name
                else:
                    lead.custom_name = leadInfo["custom_name"]
                lead.save()

        device.save()
        return Response(status=200)

class DeleteStudyParticipant(RestViews.APIView):
    """ Delete Study Participant in BRAVO Database

    This API will manage study participant in the database. 
    Participant will be removed if participant is in a study managed by the user. 

    **POST**: ``/api/deleteStudyParticipant``

    Args:
      name (uuid): Participant name. Delete API must utilize UUID as input for name to reduce error. 
      study (uuid): UUID of a study

    Returns:
      Response Code 200 if success or 400 if error.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = ["participant_uid"]
        required_keys = ["participant_uid"]
        if not checkAPIInput(request.data, required_keys, accepted_keys):
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        try:
            UUID(request.data["participant_uid"]) # Will throw if it is not UUID
            participant = models.Participant.nodes.get_or_none(uid=request.data["participant_uid"])
        except:
            # uid is not a UUID
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        # If UID provided does not match existing participant. This is malicious attempt at the database. 
        if not participant:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        
        if not request.user.checkPermission(participant, "edit"):
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        for experiment in participant.experiments:
            for source_file in experiment.source_files:
                source_file.purge()
            experiment.delete()
        participant.delete()

        for analysis in models.CombinedAnalysis.nodes.all():
            analysis.delete()
            
        return Response(status=200)

class QueryStudyParticipant(RestViews.APIView):
    """ Query Study Participant in BRAVO Database

    This API will manage study participant in the database. Retrieve accessible studies and participants.

    **POST**: ``/api/queryStudyParticipant``

    Returns:
      Response Code 200 if success or 400 if error.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        data = {"studies": [], "participants": {}}
        for study in request.user.studies:
            data["studies"].append({"uid": study.uid, "name": study.name})
            data["participants"][study.uid] = []
            for participant in study.participants:
                ParticipantInfo = {"uid": participant.uid, "name": participant.getName()}
                try:
                    ParticipantInfo["diagnosis"] = participant.diagnosis
                except:
                    ParticipantInfo["diagnosis"] = "Control"
                ParticipantInfo["tags"] = [tag.name for tag in participant.tags]
                ParticipantInfo["experiments"] = [{"name": experiment.name, "uid": experiment.uid} for experiment in participant.experiments]
                data["participants"][study.uid].append(ParticipantInfo)

        return Response(status=200, data=data)

class QueryParticipantInformation(RestViews.APIView):
    """ Query Study Participant in BRAVO Database

    This API will manage study participant in the database. Retrieve accessible studies and participants.

    **POST**: ``/api/queryParticipantInformation``

    Returns:
      Response Code 200 if success or 400 if error.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
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

        info = dict()
        info["name"] = participant.getName()
        try:
            info["diagnosis"] = participant.diagnosis
        except:
            info["diagnosis"] = "Control"
        info["dob"] = participant.date_of_birth
        info["sex"] = participant.sex

        info["dbsDevices"] = list()
        info["tags"] = [tag.name for tag in participant.tags]

        UniqueDevices = []
        for experiment in participant.experiments:
            for sourceFile in experiment.source_files:
                for device in sourceFile.device:
                    if type(device) == models.DBSDevice and not device.uid in UniqueDevices:
                        UniqueDevices.append(device.uid)
                        deviceInfo = dict()
                        deviceInfo["uid"] = device.uid
                        deviceInfo["location"] = device.implanted_location
                        if device.implanted_date:
                            deviceInfo["implant_date"] = device.implanted_date
                        deviceInfo["name"] = device.getName()
                        deviceInfo["type"] = device.type
                        deviceInfo["leads"] = [{"type": lead.type, "name": lead.name, "custom_name": lead.custom_name} for lead in device.electrodes]
                        info["dbsDevices"].append(deviceInfo)
                        print(deviceInfo)

        return Response(status=200, data=info)

class CheckAccessPermission(RestViews.APIView):
    """ Check if a study participant is permitted for viewing

    **POST**: ``/api/checkAccessPermission``

    Returns:
      Response Code 200 if success or 400 if error.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
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

        return Response(status=200)
