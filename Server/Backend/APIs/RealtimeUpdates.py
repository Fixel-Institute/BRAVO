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
                    await self.channel_layer.group_send("BroadcastChannel", {
                        "type": "broadcast_queue_complete",
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
            
            if self.scope["authorization"]:
                if self.scope["user"] == "LocalAdmin":
                    print(request)

    # Broadcast Configurations
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

        pass

    # Broadcast Streams
    async def broadcast_stream(self, event):
        pass
