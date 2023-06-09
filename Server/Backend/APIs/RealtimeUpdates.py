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
Realtime Update Module (Websockets)
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from modules import Database
import json

from asgiref.sync import sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

import numpy as np
from scipy import signal

from Backend import models
from .Auth import ValidateAuthToken

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class NotificationSystem(AsyncWebsocketConsumer):
    async def connect(self):
        self.scope["authorization"] = False
        await self.accept()

    async def disconnect(self, close_code):
        pass

    # Receive message from WebSocket
    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                request = json.loads(text_data)
            except ValueError:
                return await self.close()
            
            # Authorization Flows
            if not self.scope["authorization"] and "Authorization" in request.keys():
                token = request["Authorization"]

                # Root User Broadcasting Messages
                if token == os.environ["ENCRYPTION_KEY"]:
                    if "PersistentConnection" in request.keys():
                        await self.channel_layer.group_add("ProcessingQueueManager", self.channel_name)
                        return

                    if request["NotificationType"] == "RequestProcessing":
                        await self.channel_layer.group_send("ProcessingQueueManager", {
                            "type": "request_processing_queue",
                            "message": {}
                        })

                    elif request["NotificationType"] == "NewPatient":
                        await self.channel_layer.group_send("BroadcastChannel", {
                            "type": "broadcast_new_patient",
                            "message": {
                                "UserID": request["TaskUser"],
                                "NewPatient": request["NewPatient"],
                            }
                        })

                    elif request["NotificationType"] == "TaskComplete":
                        await self.channel_layer.group_send("BroadcastChannel", {
                            "type": "broadcast_queue_complete",
                            "message": {
                                "UserID": request["TaskUser"],
                                "TaskID": request["TaskID"],
                                "State": request["State"],
                                "Message": request["Message"],
                            }
                        })

                    elif request["NotificationType"] == "TaskProcessing":
                        await self.channel_layer.group_send("BroadcastChannel", {
                            "type": "broadcast_queue_update",
                            "message": {
                                "UserID": request["TaskUser"],
                                "TaskID": request["TaskID"],
                                "State": request["State"],
                                "Message": request["Message"],
                            }
                        })

                    elif request["NotificationType"] == "AnalysisProcessing":
                        await self.channel_layer.group_send("BroadcastChannel", {
                            "type": "broadcast_analysis_processing",
                            "message": {
                                "UserID": request["TaskUser"],
                                "TaskID": request["TaskID"],
                                "State": request["State"],
                                "Message": request["Message"],
                            }
                        })
                    
                    return

                user = await sync_to_async(ValidateAuthToken)(token)
                if user:
                    self.scope["user"] = user
                    self.scope["authorization"] = True
                    await self.channel_layer.group_add("BroadcastChannel", self.channel_name)

                    return
                return await self.close()
            
    async def request_processing_queue(self, event):
        await self.send(text_data=json.dumps({
            "Notification": "ProcessQueue",
        }))

    # Broadcast Queue Update
    async def broadcast_queue_update(self, event):
        if "UserID" in event["message"]:
            if str(self.scope["user"].unique_user_id) == event["message"]["UserID"]:
                await self.send(text_data=json.dumps({
                    "Notification": "QueueUpdate",
                    "UpdateType": "JobUpdate",
                    "TaskID": event["message"]["TaskID"],
                    "State": event["message"]["State"],
                    "Message": event["message"]["Message"],
                }))

            await self.send(text_data=json.dumps({
                "Notification": "QueueUpdate",
                "UpdateType": "QueueReduced",
            }))
        pass

    # Broadcast Queue Compeltion
    async def broadcast_queue_complete(self, event):
        if "UserID" in event["message"]:
            if str(self.scope["user"].unique_user_id) == event["message"]["UserID"]:
                await self.send(text_data=json.dumps({
                    "Notification": "QueueUpdate",
                    "UpdateType": "JobCompletion",
                    "TaskID": event["message"]["TaskID"],
                    "State": event["message"]["State"],
                    "Message": event["message"]["Message"],
                }))

            await self.send(text_data=json.dumps({
                "Notification": "QueueUpdate",
                "UpdateType": "QueueReduced",
            }))
        pass

    # Broadcast New Patient Table
    async def broadcast_new_patient(self, event):
        if "UserID" in event["message"]:
            if str(self.scope["user"].unique_user_id) == event["message"]["UserID"]:
                await self.send(text_data=json.dumps({
                    "Notification": "PatientTableUpdate",
                    "UpdateType": "NewPatient",
                    "NewPatient": event["message"]["NewPatient"],
                }))
        pass

    # Broadcast Streams
    async def broadcast_stream(self, event):
        pass

    async def broadcast_analysis_processing(self, event):
        if "UserID" in event["message"]:
            if str(self.scope["user"].unique_user_id) == event["message"]["UserID"]:
                await self.send(text_data=json.dumps({
                    "Notification": "AnalysisUpdate",
                    "TaskID": event["message"]["TaskID"],
                    "State": event["message"]["State"],
                    "Message": event["message"]["Message"],
                }))
        pass

