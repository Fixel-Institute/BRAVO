import os
import sys
from pathlib import Path
import json
import datetime
import dateutil
import time

import websocket
from BRAVO import asgi

from Backend import models
from modules.Percept import Sessions
from modules import Database

def on_open(wsapp):
    print("on_open")
    wsapp.send(json.dumps({
        "Authorization": os.environ["ENCRYPTION_KEY"],
        "PersistentConnection": True
    }))

def processJSONUploads():
    ws = websocket.WebSocket()
    if models.ProcessingQueue.objects.filter(state="InProgress").exists():
        BatchQueues = models.ProcessingQueue.objects.filter(state="InProgress").all()
        for queue in BatchQueues:
            if not models.ProcessingQueue.objects.filter(state="InProgress", queue_id=queue.queue_id).exists():
                continue
            
            print(f"Start Processing {queue.descriptor['filename']}")
            newPatient = None
            ErrorMessage = ""
            ProcessingResult = ""
            try:
                user = models.PlatformUser.objects.get(unique_user_id=queue.owner)
                if user.is_clinician:
                    ProcessingResult, newPatient, _ = Sessions.processPerceptJSON(user, queue.descriptor["filename"]) 
                else:
                    if "device_deidentified_id" in queue.descriptor:
                        ProcessingResult, _, _ = Sessions.processPerceptJSON(user, queue.descriptor["filename"], device_deidentified_id=queue.descriptor["device_deidentified_id"])
                    elif "passkey" in queue.descriptor:
                        table = Database.getDeidentificationLookupTable(user, queue.descriptor["passkey"])
                        ProcessingResult, newPatient, _ = Sessions.processPerceptJSON(user, queue.descriptor["filename"], lookupTable=table)

            except Exception as e:
                ErrorMessage = str(e)
                print(ErrorMessage)

            print(f"End Processing {queue.descriptor['filename']}")
            if ProcessingResult == "Success":
                queue.state = "Complete"
                queue.save()
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Complete",
                        "Message": ErrorMessage,
                    }))

                    if newPatient:
                        newPatient = Database.extractPatientTableRow(str(queue.owner), newPatient)
                        ws.send(json.dumps({
                            "NotificationType": "NewPatient",
                            "TaskUser": str(queue.owner),
                            "NewPatient": newPatient,
                            "Authorization": os.environ["ENCRYPTION_KEY"],
                        }))

                    ws.close()
                except Exception as e:
                    print(e)
                    #print("Socket Not Active")
            else:
                queue.state = "Error"
                queue.save()

def on_close(wsapp, event, state):
    print("socket closed")

def on_error(ws, error):
    print("socket error")
    print(error)

def on_message(ws, message):
    processJSONUploads()

if __name__ == '__main__':
    processJSONUploads()
    while True:
        wsapp = websocket.WebSocketApp("ws://localhost:3001/socket/notification",
            on_open=on_open,
            on_close=on_close,
            on_error=on_error,
            on_message=on_message,
        )
        wsapp.run_forever()
        time.sleep(5)
