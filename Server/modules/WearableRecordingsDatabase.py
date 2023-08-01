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
Wearable Recordings Database
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())

from datetime import datetime, date, timedelta
import pickle
import dateutil, pytz
import numpy as np
import pandas as pd
from cryptography.fernet import Fernet
import json
from io import BytesIO
import websocket
from scipy import signal

from Backend import models
from modules import Database
from modules.Percept import BrainSenseStream

from utility import PythonUtility

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

def queryAvailableRecordings(user, patientId, authority):
    AvailableRecordings = list()
    if not authority["Permission"]:
        return AvailableRecordings
    
    recordings = models.ExternalRecording.objects.filter(patient_deidentified_id=patientId).all()
    for recording in recordings:
        if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
            continue
        
        # Currently does not support Wearable Sensor Before Parsing 
        if recording.recording_type == "BRAVOWearableApp_AppleWatch":
            AvailableRecordings.append({
                "RecordingId": recording.recording_id,
                "RecordingType": recording.recording_type,
                "Time": recording.recording_date.timestamp(),
                "Duration": recording.recording_duration,
                "RecordingLabel": recording.recording_type
            })
            
    return AvailableRecordings

def getRecordingData(user, patientId, recordingId, authority):
    if not authority["Permission"]:
        return None
    
    recording = models.ExternalRecording.objects.filter(patient_deidentified_id=patientId, recording_id=recordingId).first()
    if not recording:
        return None
    
    Data = Database.loadSourceDataPointer(recording.recording_datapointer)
    Data["Time"] = recording.recording_date.timestamp()
    return Data

def removeRecordingData(user, patientId, recordingId, authority):
    if not authority["Permission"]:
        return None
    
    recording = models.ExternalRecording.objects.filter(patient_deidentified_id=patientId, recording_id=recordingId).first()
    if not recording:
        return None
    
    Database.deleteSourceDataPointer(recording.recording_datapointer)
    recording.delete()
    return True