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
Data Upload/Preprocessing Handler
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import HttpResponse

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

from Backend import models, tasks
from .HelperFunctions import checkAPIInput
from modules import Database, DataDecoder

RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class DataUpload(RestViews.APIView):
    """ Upload Data with accompanying metadata

    .. note::

        This is the only route in the server that uses MultiPart/Form Parser instead of JSON object. 

    This is the primary route that allow users to upload any accepted data file to BRAVO Database. 

    **POST**: ``/api/uploadData``

    Args:
      file (io): File object whose content can be read into raw bytes array.
      data_type (string): Descriptor for data type. Different decoder will be used for the data provided. 
      participant (uuid): Participant UUID. Permission will be checked. 
      study (uuid): Study UUID. Permission will be checked. 

    Returns:
      Response Code 200 if success or 400 if error. 
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.MultiPartParser, RestParsers.FormParser]
    
    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = ["file*", "data_type", "participant", "event", "study", "metadata"]
        required_keys = ["data_type", "participant", "study", "metadata"]
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
        
        metadata = json.loads(request.data["metadata"])
        for participant in study.participants:
            if participant.uid == request.data["participant"]:
                event = None
                if "event" in request.data.keys():
                    event = participant.events.get_or_none(uid=request.data["event"])

                queueCreated = []
                for key in request.data.keys():
                    if key.startswith("file"):
                        try:
                          rawBytes = request.data[key].read()
                          sourceFile, queue = DataDecoder.saveCacheFile(rawBytes, request.data[key].name, request.data["data_type"], metadata, event=event)
                          queueCreated.append(queue.uid)
                          sourceFile.uploader.connect(request.user)
                          sourceFile.participant.connect(participant)
                          request.user.files.connect(sourceFile)
                        except:
                            pass

                #tasks.ProcessUploadQueue.apply_async(countdown=3)
                return Response(status=200, data={"queue_created": queueCreated})
        
        return Response(status=200)

class QueryAvailableRecordings(RestViews.APIView):
    """ Query current processing queue list

    **POST**: ``/api/retrieveDataList``

    Returns:
      Response Code 200.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = ["participant", "study", "event"]
        required_keys = ["participant", "study", "event"]
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
        
        participant = study.participants.get_or_none(uid=request.data["participant"])
        if not participant:
            return Response(status=400, data={"message": "Participant not found"})

        event = participant.events.get_or_none(uid=request.data["event"])
        if not event:
            return Response(status=400, data={"message": "Event not found"})
        
        source_files = event.retrieveSourceFiles()
        return Response(status=200, data=[file.getInfo() for file in source_files])

class DataRetrieve(RestViews.APIView):
    """ Upload Data with accompanying metadata

    .. note::

        This is the only route in the server that uses MultiPart/Form Parser instead of JSON object. 

    This is the primary route that allow users to upload any accepted data file to BRAVO Database. 

    **POST**: ``/api/retrieveData``

    Returns:
      Response Code 200 if success or 400 if error. 
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.MultiPartParser, RestParsers.FormParser]
    
    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = ["participant", "study", "recording_uid"]
        required_keys = ["participant", "study", "recording_uid"]
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
        
        participant = study.participants.get_or_none(uid=request.data["participant"])
        if not participant:
            return Response(status=400, data={"message": "Participant not found"})
        
        try:
            sourceFile = participant.retrieveRecording(request.data["recording_uid"])[0]
            with open(sourceFile.file_pointer, "rb") as file:
                rawBytes = file.read()
            return HttpResponse(bytes(rawBytes), status=200, headers={
                "Content-Type": "application/octet-stream"
            })
        except:
            return Response(status=400, data={"message": "File not found"})

class QueryProcessingQueue(RestViews.APIView):
    """ Query current processing queue list

    **POST**: ``/api/queryProcessingQueue``

    Returns:
      Response Code 200.
      Response Body contains list of processing queue items owned by the request owner.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        queues = models.ProcessingQueue.uploadedBy(request.user.user_id)
        data = [{   "uid": queue.uid,
                    "filename": queue.cache_file[0].name,
                    "job_id": queue.job_id,
                    "job_type": queue.job_type,
                    "since": queue.date,
                    "state": queue.status,
                    "descriptor": queue.result,
                } for queue in queues]
        data = sorted(data, key=lambda queue: queue["since"])
        #tasks.ProcessUploadQueue.delay()

        return Response(status=200, data=data)

class ClearProcessingQueue(RestViews.APIView):
    """ Query current processing queue list

    **POST**: ``/api/clearProcessingQueue``

    Args:
      type (string): File type.

    Returns:
      Response Code 200.
      Response Body contains list of processing queue items owned by the request owner.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        queues = models.ProcessingQueue.uploadedBy(request.user.user_id)
        for queue in queues:
            if not queue.status == "complete":
              os.remove(queue.cache_file[0].file_pointer)
              queue.cache_file[0].delete()
            queue.delete()
        return Response(status=200)

class GetSecretKeyFromPassword(RestViews.APIView):
    """ Get Fernet Keys

    **POST**: ``/api/getFernetKey``

    Args:
      password (string): Password to convert to Fernet Key.

    Returns:
      Response Code 200.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = ["password"]
        required_keys = ["password"]
        if not checkAPIInput(request.data, required_keys, accepted_keys):
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        hashedName = hashlib.sha256(request.data["password"].encode("utf-8")).hexdigest()[::2]
        shiftTime = int.from_bytes(base64.b64encode(hashedName.encode("utf-8"))[8:13], "little")
        fernetKey = base64.b64encode(hashedName.encode("utf-8"))
        return Response(status=200, data={"key": fernetKey, "shift": shiftTime})

def getDirectorySize(path):
    total = 0
    if not os.path.exists(path):
        return total 
        
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += getDirectorySize(entry.path)
    return total

class QueryDatabaseInfo(RestViews.APIView):
    """ Query current database information.

    **POST**: ``/api/queryDatabaseInfo``

    Returns:
      Response Code 200.
      Response Body contains number of unique patients in database and size of data the user has access to. 
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        availableParticipants = 0
        databaseSize = 0
        for study in request.user.studies:
            for participant in study.participants:
                databaseSize += getDirectorySize(DATABASE_PATH + "recordings" + os.path.sep + participant.uid)
                availableParticipants += 1
                
        if databaseSize > 1024*1024*1024:
            databaseInfo = {"participants": availableParticipants, "totalStorage": f"{databaseSize/1024/1024/1024:.2f} GBytes"}
        else:
            databaseInfo = {"participants": availableParticipants, "totalStorage": f"{databaseSize/1024/1024:.2f} MBytes"}

        return Response(status=200, data=databaseInfo)

class DeleteData(RestViews.APIView):
    """ Request Deletion of Data Uploaded

    **POST**: ``/api/deleteData``

    Args:
      participant_uid (uuid): Participant UUID
      device (uuid): The device and its associated file to be removed.
      session (uuid): The session and its associated file to be removed.

    Returns:
      Response Code 200.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        accepted_keys = ["participant_uid", "device", "session"]
        required_keys = ["participant_uid"]
        if not checkAPIInput(request.data, required_keys, accepted_keys):
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        try:
            UUID(request.data["participant_uid"]) # Will throw if it is not UUID
            participant = models.Participant.nodes.get(uid=request.data["participant_uid"])
        except:
            # uid is not a UUID
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
        
        for study in participant.studies:
            if study.checkPermission(request.user.user_id):
                if "device" in request.data:
                    device = participant.devices.get_or_none(uid=request.data["device"])
                    if not device:
                        return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                    device.purge()
                    return Response(status=200)
                
                elif "session" in request.data:
                    return Response(status=200)
                else:
                    sourcefiles = models.SourceFile.getAllSessionFilesForParticipant(participant)
                    for sourcefile in sourcefiles:
                        sourcefile.purge()

                    participant.purge()
                    return Response(status=200)

        return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
