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
from .WebSocketManager import BaseWebSocketConsumer

import numpy as np
from scipy import signal

from Backend import models
from Backend.authentication import ValidateAuthToken

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class NotificationSystem(BaseWebSocketConsumer):
    async def disconnect(self, close_code):
        pass

    # Receive message from WebSocket
    async def receive(self, text_data=None, bytes_data=None):
        if text_data:
            try:
                request = json.loads(text_data)
            except ValueError:
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
