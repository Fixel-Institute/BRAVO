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
import shutil
import time
import numpy as np
import pytz
from cryptography.fernet import Fernet
from zipfile import ZipFile

import websocket
from BRAVO import asgi

from Backend import models
from modules.Percept import Sessions as PerceptSessions
from modules.Summit import Sessions as SummitSessions
from modules import Database, AnalysisBuilder
from decoder import Percept, Summit

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

def processJSONUploads():
    ws = websocket.WebSocket()
    if models.ProcessingQueue.objects.filter(type="decodeJSON", state="InProgress").exists():
        print(datetime.datetime.now())
        BatchQueues = models.ProcessingQueue.objects.filter(type="decodeJSON", state="InProgress").order_by("datetime").all()
        for queue in BatchQueues:
            if not models.ProcessingQueue.objects.filter(state="InProgress", queue_id=queue.queue_id).exists():
                continue
            queue.state = "Processing"
            queue.save()
            try:
                ws.connect("ws://localhost:3001/socket/notification")
                ws.send(json.dumps({
                    "NotificationType": "TaskProcessing",
                    "TaskUser": str(queue.owner),
                    "TaskID": str(queue.queue_id),
                    "Authorization": os.environ["ENCRYPTION_KEY"],
                    "State": "Processing",
                    "Message": "",
                }))
                ws.close()
            except Exception as e:
                print(e)

            print(f"Start Processing {queue.descriptor['filename']}")
            newPatient = None
            ErrorMessage = ""
            ProcessingResult = ""
            
            try:
                JSON = Percept.decodeEncryptedJSON(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"], os.environ.get('ENCRYPTION_KEY'))
            except:
                queue.state = "Error"
                queue.descriptor["Message"] = "JSON Format Error"
                print(queue.descriptor["Message"])
                queue.save()
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)

                continue

            try:
                user = models.PlatformUser.objects.get(unique_user_id=queue.owner)
                if (user.is_admin or user.is_clinician):
                    ProcessingResult, newPatient, _ = PerceptSessions.processPerceptJSON(user, queue.descriptor["filename"]) 
                else:
                    if "device_deidentified_id" in queue.descriptor:
                        ProcessingResult, _, _ = PerceptSessions.processPerceptJSON(user, queue.descriptor["filename"], device_deidentified_id=queue.descriptor["device_deidentified_id"])
                    elif "passkey" in queue.descriptor:
                        table = Database.getDeidentificationLookupTable(user, queue.descriptor["passkey"])
                        ProcessingResult, newPatient, _ = PerceptSessions.processPerceptJSON(user, queue.descriptor["filename"], lookupTable=table)

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
                print(ErrorMessage)
                queue.state = "Error"
                queue.descriptor["Message"] = ErrorMessage
                queue.save()
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)
                
                PerceptSessions.saveCacheJSON(queue.descriptor["filename"], json.dumps(JSON).encode('utf-8'))

def processAnnotations():
    ws = websocket.WebSocket()
    if models.ProcessingQueue.objects.filter(type="annotations", state="Error").exists():
        print(datetime.datetime.now())
        BatchQueues = models.ProcessingQueue.objects.filter(type="annotations", state="Error").order_by("datetime").all()
        for queue in BatchQueues:
            if not models.ProcessingQueue.objects.filter(state="Error", queue_id=queue.queue_id).exists():
                continue
            queue.state = "Processing"
            queue.save()
            ErrorMessage = ""
            try:
                ws.connect("ws://localhost:3001/socket/notification")
                ws.send(json.dumps({
                    "NotificationType": "TaskProcessing",
                    "TaskUser": str(queue.owner),
                    "TaskID": str(queue.queue_id),
                    "Authorization": os.environ["ENCRYPTION_KEY"],
                    "State": "Processing",
                    "Message": "",
                }))
                ws.close()
            except Exception as e:
                print(e)

            print(f"Start Processing {queue.descriptor['filename']}")
            try:
                AnalysisBuilder.processAnnotations(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"], queue.descriptor['patientId'])
            except Exception as e:
                queue.state = "Error"
                queue.descriptor["Message"] = str(e)
                print(queue.descriptor["Message"])
                queue.save()
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)
                continue

            print(f"End Processing {queue.descriptor['filename']}")
            if ErrorMessage == "":
                queue.state = "Complete"
                queue.save()
            else:
                print(ErrorMessage)
                queue.state = "Error"
                queue.descriptor["Message"] = ErrorMessage
                queue.save()
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)

def processExternalRecordingUpload():
    ws = websocket.WebSocket()
    if models.ProcessingQueue.objects.filter(type="externalCSVs", state="InProgress").exists():
        print(datetime.datetime.now())
        BatchQueues = models.ProcessingQueue.objects.filter(type="externalCSVs", state="InProgress").order_by("datetime").all()
        for queue in BatchQueues:
            if not models.ProcessingQueue.objects.filter(state="InProgress", queue_id=queue.queue_id).exists():
                continue
            queue.state = "Processing"
            queue.save()
            ErrorMessage = ""
            try:
                ws.connect("ws://localhost:3001/socket/notification")
                ws.send(json.dumps({
                    "NotificationType": "TaskProcessing",
                    "TaskUser": str(queue.owner),
                    "TaskID": str(queue.queue_id),
                    "Authorization": os.environ["ENCRYPTION_KEY"],
                    "State": "Processing",
                    "Message": "",
                }))
                ws.close()
            except Exception as e:
                print(e)

            print(f"Start Processing {queue.descriptor['filename']}")
            try:
                ProcessedData = AnalysisBuilder.processExternalRecordings(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"])
            except:
                queue.state = "Error"
                queue.descriptor["Message"] = "CSV Format Error"
                print(queue.descriptor["Message"])
                queue.save()
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)
                continue

            try:
                ProcessedData["SamplingRate"] = float(queue.descriptor["descriptor"]["SamplingRate"])
                ProcessedData["StartTime"] = float(queue.descriptor["descriptor"]["StartTime"])/1000 # Javascript Time is in Milliseconds
                ProcessedData["Missing"] = np.zeros(ProcessedData["Data"].shape)
                ProcessedData["Duration"] = ProcessedData["Data"].shape[0]/ProcessedData["SamplingRate"]
                recording = models.ExternalRecording(patient_deidentified_id=queue.descriptor["patientId"], 
                                         recording_type=queue.descriptor["descriptor"]["Label"], 
                                         recording_date=datetime.datetime.fromtimestamp(ProcessedData["StartTime"]).astimezone(pytz.utc),
                                         recording_duration=ProcessedData["Duration"])
                
                filename = Database.saveSourceFiles(ProcessedData, "ExternalRecording", "Raw", recording.recording_id, recording.patient_deidentified_id)
                recording.recording_datapointer = filename
                recording.save()
                
            except Exception as e:
                ErrorMessage = str(e)

            print(f"End Processing {queue.descriptor['filename']}")
            if ErrorMessage == "":
                queue.state = "Complete"
                queue.save()
            else:
                print(ErrorMessage)
                queue.state = "Error"
                queue.descriptor["Message"] = ErrorMessage
                queue.save()
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)
                
    if models.ProcessingQueue.objects.filter(type="externalMDATs", state="InProgress").exists():
        print(datetime.datetime.now())
        BatchQueues = models.ProcessingQueue.objects.filter(type="externalMDATs", state="InProgress").order_by("datetime").all()
        for queue in BatchQueues:
            if not models.ProcessingQueue.objects.filter(state="InProgress", queue_id=queue.queue_id).exists():
                continue
            queue.state = "Processing"
            queue.save()
            ErrorMessage = ""
            try:
                ws.connect("ws://localhost:3001/socket/notification")
                ws.send(json.dumps({
                    "NotificationType": "TaskProcessing",
                    "TaskUser": str(queue.owner),
                    "TaskID": str(queue.queue_id),
                    "Authorization": os.environ["ENCRYPTION_KEY"],
                    "State": "Processing",
                    "Message": "",
                }))
                ws.close()
            except Exception as e:
                print(e)

            print(f"Start Processing {queue.descriptor['filename']}")
            try:
                ProcessedDataList = AnalysisBuilder.processMDATRecordings(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"])
            except Exception as e:
                print(e)
                queue.state = "Error"
                queue.descriptor["Message"] = str(e)
                print(queue.descriptor["Message"])
                queue.save()
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)
                continue

            try:
                for ProcessedData in ProcessedDataList:
                    recording = models.ExternalRecording(patient_deidentified_id=queue.descriptor["patientId"], 
                                            recording_type="DelsysMDAT." + ProcessedData["ChannelNames"][0].split(".")[0], 
                                            recording_date=datetime.datetime.fromtimestamp(ProcessedData["StartTime"]).astimezone(pytz.utc),
                                            recording_duration=ProcessedData["Duration"])
                    filename = Database.saveSourceFiles(ProcessedData, "ExternalRecording", "Raw", recording.recording_id, recording.patient_deidentified_id)
                    recording.recording_datapointer = filename
                    recording.save()
                
            except Exception as e:
                ErrorMessage = str(e)

            print(f"End Processing {queue.descriptor['filename']}")
            if ErrorMessage == "":
                queue.state = "Complete"
                queue.save()
            else:
                print(ErrorMessage)
                queue.state = "Error"
                queue.descriptor["Message"] = ErrorMessage
                queue.save()
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)
                
def processSummitZIPUpload():
    ws = websocket.WebSocket()
    if models.ProcessingQueue.objects.filter(type="decodeSummitZIP", state="InProgress").exists():
        print(datetime.datetime.now())
        BatchQueues = models.ProcessingQueue.objects.filter(type="decodeSummitZIP", state="InProgress").order_by("datetime").all()
        for queue in BatchQueues:
            if not models.ProcessingQueue.objects.filter(state="InProgress", queue_id=queue.queue_id).exists():
                continue
            queue.state = "Processing"
            queue.save()
            ErrorMessage = ""
            try:
                ws.connect("ws://localhost:3001/socket/notification")
                ws.send(json.dumps({
                    "NotificationType": "TaskProcessing",
                    "TaskUser": str(queue.owner),
                    "TaskID": str(queue.queue_id),
                    "Authorization": os.environ["ENCRYPTION_KEY"],
                    "State": "Processing",
                    "Message": "",
                }))
                ws.close()
            except Exception as e:
                print(e)

            print(f"Start Processing {queue.descriptor['filename']}")
            try:
                with ZipFile(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"]) as zObject:
                    zObject.extractall(path=DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"].replace(".zip",""))
                
            except:
                queue.state = "Error"
                queue.descriptor["Message"] = "ZipFile Format Error"
                print(queue.descriptor["Message"])
                queue.save()
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)
                continue
            
            try:
                user = models.PlatformUser.objects.get(unique_user_id=queue.owner)
                if "device_deidentified_id" in queue.descriptor:
                    ProcessingResult, _, _ = SummitSessions.processSummitSession(user, DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"].replace(".zip",""), device_deidentified_id=queue.descriptor["device_deidentified_id"])
                    if not ProcessingResult == "Success":
                        raise Exception(ProcessingResult)
                    
            except Exception as e:
                ErrorMessage = str(e)
                print(ErrorMessage)

            print(f"End Processing {queue.descriptor['filename']}")
            if ErrorMessage == "":
                queue.state = "Complete"
                queue.save()

                shutil.rmtree(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"].replace(".zip",""))
                os.remove(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"])

            else:
                queue.state = "Error"
                queue.descriptor["Message"] = ErrorMessage
                queue.save()

                shutil.rmtree(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"].replace(".zip",""))
                os.remove(DATABASE_PATH + "cache" + os.path.sep + queue.descriptor["filename"])
                
                try:
                    ws.connect("ws://localhost:3001/socket/notification")
                    ws.send(json.dumps({
                        "NotificationType": "TaskComplete",
                        "TaskUser": str(queue.owner),
                        "TaskID": str(queue.queue_id),
                        "Authorization": os.environ["ENCRYPTION_KEY"],
                        "State": "Error",
                        "Message": queue.descriptor["Message"],
                    }))
                    ws.close()
                except Exception as e:
                    print(e)
                



if __name__ == '__main__':
    processJSONUploads()
    processSummitZIPUpload()
    processExternalRecordingUpload()
    processAnnotations()
