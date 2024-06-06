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
from rest_framework.permissions import IsAuthenticated
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
            # uid is not a UUID, try to create new study
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
            participant = models.Patient(name=request.data["name"], diagnosis=request.data["diagnosis"]).save()
            if "disease_start_time" in request.data:
                participant.setDiseaseStartTime(request.data["disease_start_time"])
        else:
            participant = models.Participant(name=request.data["name"]).save()
        
        if "dob" in request.data:
            participant.setDateOfBirth(request.data["dob"])
        participant.sex = request.data["sex"] if "sex" in request.data else "Other"

        participant.studies.connect(study)
        study.participants.connect(participant)

        participant.save()
        study.save()
        return Response(status=200, data={"uid": participant.uid, "study": study.uid})

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

        device = participant.devices.get_or_none(uid=request.data["device"])
        if not device:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        
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
        accepted_keys = ["name", "study"]
        required_keys = ["name", "study"]
        if not checkAPIInput(request.data, required_keys, accepted_keys):
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        try:
            UUID(request.data["study"]) # Will throw if it is not UUID
            study = models.Study.nodes.get_or_none(uid=request.data["study"])
        except:
            # uid is not a UUID
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        # If UID provided does not match existing study. This is malicious attempt at the database. 
        if not study:
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        
        # User has no permission to this study. This is malicious attempt at the database. 
        if not study.checkPermission(request.user.user_id):
            return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        
        for participant in study.participants:
            if participant.uid == request.data["name"]:
                participant.delete()
                return Response(status=200, data={"uid": participant.uid, "study": study.uid})
        return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

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
                ParticipantInfo = {"uid": participant.uid, "name": participant.name}
                ParticipantInfo["diagnosis"] = participant.diagnosis if participant.diagnosis else "Control"
                ParticipantInfo["tags"] = [tag.name for tag in participant.tags]
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
        info["diagnosis"] = participant.diagnosis if participant.diagnosis else "Control"
        info["dob"] = participant.date_of_birth
        info["sex"] = participant.sex

        info["devices"] = list()
        info["tags"] = [tag.name for tag in participant.tags]

        for device in participant.devices:
            deviceInfo = dict()
            deviceInfo["uid"] = device.uid
            deviceInfo["location"] = device.implanted_location
            if device.implanted_date:
                deviceInfo["implant_date"] = device.implanted_date
            deviceInfo["name"] = device.getDeviceName()
            deviceInfo["type"] = device.type
            deviceInfo["leads"] = [{"type": lead.type, "name": lead.name, "custom_name": lead.custom_name}for lead in device.electrodes]
            info["devices"].append(deviceInfo)

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
