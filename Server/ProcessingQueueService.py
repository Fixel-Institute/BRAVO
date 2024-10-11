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
            try:
                cache_file = job.cache_file.get()
            except:
                job.delete()
                continue
            cache_file = job.cache_file.get()
            MatchingData = False
            time_start = datetime.datetime.now().timestamp()
            
            if "batch_upload" in cache_file.metadata.keys():
                participant = DataDecoder.createParticipantFromMedtronicJSON(cache_file)
            else:
                participant = cache_file.experiment.get().participant.get()
                
            for experiment in participant.experiments:
                for existing_session in experiment.source_files:
                    if existing_session.type == cache_file.type and (not existing_session.uid == cache_file.uid) and existing_session.queue.get_or_none(status="complete"):
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

            try:
                result = DataDecoder.decodeMedtronicJSON(cache_file, participant=participant)
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

def processImageData():
    queue = models.ProcessingQueue.nodes.filter(job_type="MRImages", status="created").all()
    if len(queue) > 0:
        for job in queue:
            cache_file = job.cache_file[0]
            job.status = "in_progress"
            
            result = None
            try:
                participant = cache_file.experiment[0].participant[0]
                os.makedirs(DATABASE_PATH + "imaging" + os.path.sep + participant.uid, exist_ok=True)
                newFilePointer = cache_file.file_pointer.replace(DATABASE_PATH + "cache", DATABASE_PATH + "imaging" + os.path.sep + participant.uid)
                if os.path.exists(newFilePointer):
                    raise Exception("File Exists")
                
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

    if len(models.ProcessingQueue.nodes.filter(job_type="MRImages", status="created")) > 0:
        processImageData()

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
                if os.path.exists(newFilePointer):
                    raise Exception("File Exists")
                
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
    processImageData()
    processUniversalData()
    #processSummitZIPUpload()
    #processExternalRecordingUpload()
