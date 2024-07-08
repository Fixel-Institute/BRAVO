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
from modules import Database, DataDecoder

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')
secureEncoder = Fernet(key)

def checkFiles(file1, file2):
    with open(file1, "rb") as file:
        File1Content = secureEncoder.decrypt(file.read())
    with open(file2, "rb") as file:
        File2Content = secureEncoder.decrypt(file.read())
    return File1Content == File2Content

def processJSONUploads():
    queue = models.ProcessingQueue.nodes.filter(job_type="MedtronicJSON", status="created").all()
    if len(queue) > 0:
        for job in queue:
            cache_file = job.cache_file[0]
            MatchingData = False

            time_start = datetime.datetime.now().timestamp()
            for existing_session in models.SourceFile.getAllSessionFilesForParticipant(cache_file.participant[0]):
                if (not existing_session.uid == cache_file.uid):
                    if existing_session.file_pointer == DATABASE_PATH + "raws" + os.path.sep + existing_session.participant[0].uid + os.path.sep + existing_session.uid + ".json":
                        if checkFiles(existing_session.file_pointer, cache_file.file_pointer):
                            MatchingData = True 
                            break
            time_end = datetime.datetime.now().timestamp()
            print(f"Time to Check: {time_end-time_start}")

            if MatchingData:
                print("Duplicated File")
                job.status = "error"
                job.result = "Duplicated File"
                job.save()
                continue

            job.status = "in_progress"
            try:
                result = DataDecoder.decodeMedtronicJSON(cache_file)
            except Exception as e:
                result = {"error": str(e)}

            if result:
                job.status = "error"
                job.result = result["error"]
                print(result)
            else:
                job.status = "complete"
            job.save()

    if len(models.ProcessingQueue.nodes.filter(job_type="MedtronicJSON", status="created")) > 0:
        processJSONUploads()

def processUniversalData():
    queue = models.ProcessingQueue.nodes.filter(job_type="RawData", status="created").all()
    if len(queue) > 0:
        for job in queue:
            cache_file = job.cache_file[0]
            job.status = "in_progress"
            
            result = None
            try:
                participant = cache_file.participant[0]
                os.makedirs(DATABASE_PATH + "raws" + os.path.sep + participant.uid, exist_ok=True)
                newFilePointer = cache_file.file_pointer.replace(DATABASE_PATH + "cache", DATABASE_PATH + "raws" + os.path.sep + participant.uid)
                os.rename(cache_file.file_pointer, newFilePointer) 
                cache_file.file_pointer = newFilePointer
                cache_file.save()
            except Exception as e:
                result = {"error": str(e)}

            if result:
                job.status = "error"
                job.result = result["error"]
                print(result)
            else:
                job.status = "complete"
            job.save()

    if len(models.ProcessingQueue.nodes.filter(job_type="RawData", status="created")) > 0:
        processUniversalData()

if __name__ == '__main__':
    processJSONUploads()
    processUniversalData()
    #processSummitZIPUpload()
    #processExternalRecordingUpload()
