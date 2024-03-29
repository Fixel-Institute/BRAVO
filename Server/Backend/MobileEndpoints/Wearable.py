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
Wearable Application Processing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from email.policy import default
import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

import datetime
import pytz
from modules import Database
import json
from copy import deepcopy

from django.middleware.csrf import get_token
from asgiref.sync import async_to_sync, sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response

import numpy as np
from scipy import signal

from decoder import BRAVOWearableApp
from Backend import models

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class QueryMobileAccount(RestViews.APIView):
    """ Query associated mobile account.

    **POST**: ``/mobile/wearable/queryMobileAccount``

    Args:
      id (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.

    Returns:
      Response Code 200.
      Response Body contains a single patient object with detailed information.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["patientId"])
        if Authority["Level"] == 0 or Authority["Level"] == 2:
            return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        
        if "queryMobileAccount" in request.data:
            if models.MobileUser.objects.filter(linked_patient_id=request.data["patientId"]).exists():
                mobileUser = models.MobileUser.objects.filter(linked_patient_id=request.data["patientId"]).first()
                return Response(status=200, data=[{
                    "Username": mobileUser.user_name,
                    "Token": mobileUser.active_token,
                }])
            else:
                return Response(status=200, data=[])
        
        elif "createMobileAccount" in request.data:
            if not models.MobileUser.objects.filter(linked_patient_id=request.data["patientId"]).exists():
                mobileUser = models.MobileUser(user_name=request.data["username"], linked_patient_id=request.data["patientId"])
                mobileUser.set_password(request.data["password"])
                mobileUser.save()
                return Response(status=200, data=[{
                    "Username": mobileUser.user_name,
                    "Password": "",
                }])
            else:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
        
        elif "deleteMobileAccount" in request.data:
            if models.MobileUser.objects.filter(linked_patient_id=request.data["patientId"]).exists():
                mobileUser = models.MobileUser.objects.filter(linked_patient_id=request.data["patientId"]).delete()
                return Response(status=200, data=[{
                    "Username": "",
                    "Password": "",
                    "New": True
                }])
            else:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class RequestPairingDevice(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        if "deviceMac" in request.data and "deviceName" in request.data and "PairingID" in request.data:
            models.ExternalSensorPairing.objects.filter(device_mac=request.data["deviceMac"], paired=False).delete()
            newDevice = models.ExternalSensorPairing(device_mac=request.data["deviceMac"], device_name=request.data["deviceName"], pairing_code=request.data["PairingID"])
            newDevice.save()

            return Response(status=200, data={})

        return Response(status=404, data={})

class QueryPairedDevice(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if Authority["Level"] == 1:
            Patient = Database.extractPatientInfo(request.user, request.data["id"])
            
        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
            Patient = Database.extractPatientInfo(request.user, PatientInfo.deidentified_id)
            Patient["Devices"] = deidentification["Devices"]
        
        availableDevice = models.ExternalSensorPairing.objects.filter(patient_deidentified_id=request.data["id"], paired=True).order_by("-pairing_date")
        data = []
        for device in availableDevice:
            data.append({
                "DeviceMac": device.device_mac,
                "DeviceName": device.device_name,
                "PairingDate": device.pairing_date.timestamp()
            })
        return Response(status=200, data=data)
        
class VerifyPairing(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]
    def post(self, request):
        Authority = {}
        Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
        if Authority["Level"] == 0:
            return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

        if Authority["Level"] == 1:
            Patient = Database.extractPatientInfo(request.user, request.data["id"])
            
        elif Authority["Level"] == 2:
            PatientInfo = Database.extractAccess(request.user, request.data["id"])
            deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
            Patient = Database.extractPatientInfo(request.user, PatientInfo.deidentified_id)
            Patient["Devices"] = deidentification["Devices"]
        
        availableDevice = models.ExternalSensorPairing.objects.filter(pairing_code=request.data["PairingCode"], paired=False).order_by("-pairing_date").first()
        if not availableDevice:
            return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        availableDevice.patient_deidentified_id = request.data["id"]
        availableDevice.paired = True
        availableDevice.save()

        return Response(status=200, data={
            "DeviceMac": availableDevice.device_mac,
            "DeviceName": availableDevice.device_name,
            "PairingDate": availableDevice.pairing_date.timestamp()
        })

class UploadRecording(RestViews.APIView):
    parser_classes = [RestParsers.MultiPartParser, RestParsers.FormParser]
    permission_classes = [AllowAny]

    def post(self, request):
        if not "file" in request.data or not "authToken" in request.data:
            return Response(status=403, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        mobileUser = models.MobileUser.objects.filter(active_token=request.data["authToken"]).first()
        if not mobileUser:
            return Response(status=401)

        associatedPatient = models.Patient.objects.filter(deidentified_id=mobileUser.linked_patient_id).first()
        if not associatedPatient:
            return Response(status=401)

        try:
            os.mkdir(DATABASE_PATH + "recordings" + os.path.sep + str(mobileUser.linked_patient_id))
        except Exception:
            pass

        rawBytes = request.data["file"].read()
        header = rawBytes[:72].decode("utf-8")
        
        if header.strip().startswith("DATA:APPLEWATCH"):
            Data = BRAVOWearableApp.decodeAppleWatchStructureRaw(rawBytes)
            startTime = 0
            endTime = 0
            for key in ["Accelerometer","TremorSeverity","DyskineticProbability","HeartRate","HeartRateVariability","SleepState"]:
                if len(Data[key]["Time"]) > 0:
                    if startTime == 0 or Data[key]["Time"][0] < startTime:
                        startTime = Data[key]["Time"][0]
                    
                    if endTime == 0 or Data[key]["Time"][-1] > endTime:
                        endTime = Data[key]["Time"][-1]
            
            if models.ExternalRecording.objects.filter(patient_deidentified_id=mobileUser.linked_patient_id, 
                                         recording_type="BRAVOWearableApp_AppleWatch", 
                                         recording_date=datetime.datetime.fromtimestamp(startTime).astimezone(pytz.utc),
                                         recording_duration=endTime - startTime).exists():
                return Response(status=200)

            recording = models.ExternalRecording(patient_deidentified_id=mobileUser.linked_patient_id, 
                                         recording_type="BRAVOWearableApp_AppleWatch", 
                                         recording_date=datetime.datetime.fromtimestamp(startTime).astimezone(pytz.utc),
                                         recording_duration=endTime - startTime)
            
            filename = Database.saveSourceFiles(Data, "ExternalRecording", "BRAVOWearableApp_AppleWatch", recording.recording_id, recording.patient_deidentified_id)
            recording.recording_datapointer = filename
            recording.save()
            return Response(status=200)
        
        elif header.strip().startswith("DATA:"):
            Data = BRAVOWearableApp.decodeMetaMotionStructureRaw(rawBytes)

            startTime = 0
            endTime = 0
            for key in ["Accelerometer","RSSAccelerometer","Gyroscope","AmbientLight"]:
                if len(Data[key]["Time"]) > 0:
                    if startTime == 0 or Data[key]["Time"][0] < startTime:
                        startTime = Data[key]["Time"][0]
                    
                    if endTime == 0 or Data[key]["Time"][-1] > endTime:
                        endTime = Data[key]["Time"][-1]

            if models.ExternalRecording.objects.filter(patient_deidentified_id=mobileUser.linked_patient_id, 
                                         recording_type="BRAVOWearableApp_MetaMotionS", 
                                         recording_date=datetime.datetime.fromtimestamp(startTime).astimezone(pytz.utc),
                                         recording_duration=endTime - startTime).exists():
                return Response(status=200)

            recording = models.ExternalRecording(patient_deidentified_id=mobileUser.linked_patient_id, 
                                         recording_type="BRAVOWearableApp_MetaMotionS", 
                                         recording_date=datetime.datetime.fromtimestamp(startTime).astimezone(pytz.utc),
                                         recording_duration=endTime - startTime)
            
            filename = Database.saveSourceFiles(Data, "ExternalRecording", "BRAVOWearableApp_MetaMotionS", recording.recording_id, recording.patient_deidentified_id)
            recording.recording_datapointer = filename
            recording.recording_info = {
                "DeviceID": header.strip()
            }
            recording.save()
            return Response(status=200)
        
        return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

class StreamRelay(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    # Receive message from WebSocket
    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            config = json.loads(text_data)
            if "streamState" in config.keys():
                if config["streamState"]:
                    self.currentConfig = config
                    self.streamChannel = config["deviceId"].replace(":","-")
                    await self.channel_layer.group_add(self.streamChannel, self.channel_name)
                    await self.channel_layer.group_send(self.streamChannel, {
                        "type": "broadcast_config",
                        "message": {
                            "SetConfig": True,
                            "SamplingRate": config["SamplingRate"],
                            "DataRange": config["DataRange"]
                        }
                    })

                else:
                    await self.channel_layer.group_discard(self.streamChannel, self.channel_name)
                    
            if "joinStream" in config.keys():
                self.streamChannel = config["joinStream"].replace(":","-")
                await self.channel_layer.group_add(self.streamChannel, self.channel_name)
                await self.channel_layer.group_send(self.streamChannel, {
                    "type": "broadcast_config",
                    "message": {
                        "GetConfig": True,
                    }
                })

            elif "leaveStream" in config.keys():
                await self.channel_layer.group_discard(self.streamChannel, self.channel_name)

        elif bytes_data:
            data = np.frombuffer(bytes_data, dtype="<i2")
            await self.channel_layer.group_send(self.streamChannel, {
                "type": "broadcast_stream",
                "data": data.tobytes()
            })

    # Broadcast Configurations
    async def broadcast_config(self, event):
        if "SetConfig" in event["message"]:
            await self.send(text_data=json.dumps(event["message"]))

        if "GetConfig" in event["message"]:
            if hasattr(self, "currentConfig"):
                await self.channel_layer.group_send(self.streamChannel, {
                    "type": "broadcast_config",
                    "message": {
                        "SetConfig": True,
                        "SamplingRate": self.currentConfig["SamplingRate"],
                        "DataRange": self.currentConfig["DataRange"]
                    }
                })
        #data = event["data"]
        #await self.send(bytes_data=data)

    # Broadcast Streams
    async def broadcast_stream(self, event):
        data = event["data"]
        await self.send(bytes_data=data)
