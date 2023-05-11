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
Crontab Queue Processor
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
@date: Thu Sep 16 12:05:09 2021
"""

import os
import sys
from pathlib import Path
import json
import datetime
import dateutil
import time
from cryptography.fernet import Fernet

import websocket
from BRAVO import wsgi

from Backend import models
from modules.Percept import Sessions
from modules import Database
from decoder import Percept

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

def processJSONUploads():
    ws = websocket.WebSocket()
    if models.ProcessingQueue.objects.filter(state="InProgress").exists():
        print(datetime.datetime.now())
        BatchQueues = models.ProcessingQueue.objects.filter(state="InProgress").order_by("datetime").all()
        for queue in BatchQueues:
            if not models.ProcessingQueue.objects.filter(state="InProgress", queue_id=queue.queue_id).exists():
                continue
            queue.state = "Processing"
            queue.save()
            
            print(f"Start Processing {queue.descriptor['filename']}")
            newPatient = None
            ErrorMessage = ""
            ProcessingResult = ""

            try:
                JSON = Percept.decodeEncryptedJSON(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"], os.environ.get('ENCRYPTION_KEY'))
            except:
                queue.state = "Error"
                queue.descriptor["Message"] = "JSON Format Error"
                queue.save()
                continue

            try:
                user = models.PlatformUser.objects.get(unique_user_id=queue.owner)
                if (user.is_admin or user.is_clinician):
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
            else:
                print(ProcessingResult)
                queue.state = "Error"
                queue.descriptor["Message"] = ErrorMessage
                queue.save()
                
                Sessions.saveCacheJSON(queue.descriptor["filename"], json.dumps(JSON))

if __name__ == '__main__':
    processJSONUploads()
