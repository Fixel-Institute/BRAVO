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
Session JSON Processing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib

RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(os.environ.get("PYTHON_UTILITY"))

from datetime import datetime, date, timedelta
import pickle, joblib
import dateutil, pytz
import numpy as np
import pandas as pd
from cryptography.fernet import Fernet
import hashlib
import shutil

from Backend import models
from modules import Database
#from modules.Summit import Therapy, BrainSenseSurvey, BrainSenseStream, IndefiniteStream, BrainSenseEvent, ChronicBrainSense
from modules.Summit import Therapy, StreamingData, ChronicLogs
from decoder import Summit

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

def saveCacheZIP(filename, rawBytes):
    with open(DATABASE_PATH + "cache" + os.path.sep + filename, "wb+") as file:
        file.write(rawBytes)

def processSummitSession(user, filename, device_deidentified_id="", process=True):
    secureEncoder = Fernet(key)
    
    try:
        Data = Summit.LoadData(filename)
    except:
        return "Summit Decoding Error: ", None, None
    
    DeviceName = [itemname for itemname in os.listdir(filename) if itemname.startswith("Device") and os.path.isdir(filename + "/" + itemname)]
    DeviceName = DeviceName[0]
    DeviceSettings = Summit.decodeJSON(filename + "/" + DeviceName + "/" + "DeviceSettings.json", fileType="DeviceSettings")

    DeviceSerialNumber = secureEncoder.encrypt(DeviceName.encode("utf-8")).decode("utf-8")
    deviceHashfield = hashlib.sha256(DeviceName.encode("utf-8")).hexdigest()
    
    SessionDate = datetime.fromtimestamp(int(filename.split("/")[-1].replace("Session",""))/1000,tz=pytz.utc)
    deviceID = models.PerceptDevice.objects.filter(deidentified_id=device_deidentified_id, authority_level="Research", authority_user=user.email).first()
    if deviceID == None:
        return "Device ID Error: ", None, None
    patient = models.Patient.objects.filter(deidentified_id=deviceID.patient_deidentified_id).first()
    
    if models.PerceptSession.objects.filter(device_deidentified_id=deviceID.deidentified_id, session_source_filename=filename, session_date=SessionDate).exists():
        return "Existing Session File: ", None, None
    
    ImplantDate = datetime.fromtimestamp(DeviceSettings[0]["GeneralData"]["implantDate"]["seconds"] + 946702800).astimezone(pytz.utc)
    deviceID.implant_date = ImplantDate
    deviceID.device_location = "Unknown"
    deviceID.device_type = "Summit RC+S"

    if SessionDate >= deviceID.device_last_seen:
        deviceID.device_last_seen = SessionDate

        LeadLocation = []
        for i in range(len(Data["Config"])):
            if "LeadLocation" in Data["Config"][i].keys():
                LeadLocation = Data["Config"][i]["LeadLocation"]

        LeadConfigurations = list()
        for i in range(len(LeadLocation)):
            LeadConfiguration = dict()
            if LeadLocation[i] != " ":
                LeadConfiguration["TargetLocation"] = LeadLocation[i]
            else:
                continue

            if i < 2:
                LeadConfiguration["ElectrodeNumber"] = "E00-E07"
                LeadConfiguration["TargetLocation"] = "Left " + LeadConfiguration["TargetLocation"]
            else:
                LeadConfiguration["ElectrodeNumber"] = "E08-E15"
                LeadConfiguration["TargetLocation"] = "Right " + LeadConfiguration["TargetLocation"]
            LeadConfiguration["ElectrodeType"] = "Medtronic"
            LeadConfigurations.append(LeadConfiguration)

        if len(LeadConfigurations) == len(deviceID.device_lead_configurations):
            for i in range(len(LeadConfigurations)):
                if "CustomName" in deviceID.device_lead_configurations[i].keys():
                    LeadConfigurations[i]["CustomName"] = deviceID.device_lead_configurations[i]["CustomName"]

        deviceID.device_lead_configurations = LeadConfigurations

    deviceID.save()
    if models.PerceptSession.objects.filter(device_deidentified_id=deviceID.deidentified_id, session_date=SessionDate).exists():
        return "Summit Duplicate Data Error: ", None, None
    
    session = models.PerceptSession(device_deidentified_id=deviceID.deidentified_id, session_source_filename=filename, session_date=SessionDate)
    session.session_file_path = "sessions" + os.path.sep + str(session.device_deidentified_id)+"_"+str(session.deidentified_id) + ".zip"
    sessionUUID = str(session.deidentified_id)

    TherapyHistory = Summit.TherapyReconstruction(Data)
    Therapy.saveTherapySettings(deviceID.deidentified_id, TherapyHistory, SessionDate, "SummitTherapy", sessionUUID)

    if "TherapyChangeHistory" in Data.keys():
        pass 

    # Process Realtime Streams
    StreamingData.saveRealtimeStreams(deviceID.deidentified_id, Data, sessionUUID)

    if "Power" in Data.keys():
        StreamingData.savePowerStreams(deviceID.deidentified_id, Data["Power"], sessionUUID)

    if "AdaptiveLogs" in Data.keys():
        ChronicLogs.saveChronicLogs(deviceID.deidentified_id, Data["AdaptiveLogs"], sessionUUID)

    session.save()
    shutil.make_archive(DATABASE_PATH + session.session_file_path, 'zip', filename)
    return "Success", patient, Data

def queryAvailableSessionFiles(user, patient_id, authority):
    availableDevices = Database.getPerceptDevices(user, patient_id, authority)

    sessions = list()
    for device in availableDevices:
        availableSessions = models.PerceptSession.objects.filter(device_deidentified_id=device.deidentified_id).all()
        for session in availableSessions:
            sessionInfo = dict()
            if device.device_name == "":
                if not (user.is_admin or user.is_clinician):
                    sessionInfo["DeviceName"] = str(device.deidentified_id)
                else:
                    sessionInfo["DeviceName"] = device.getDeviceSerialNumber(key)
            else:
                sessionInfo["DeviceName"] = device.device_name
            
            sessionInfo["SessionFilename"] = session.session_file_path.split(os.path.sep)[-1]
            sessionInfo["SessionID"] = session.deidentified_id
            sessionInfo["SessionTimestamp"] = session.session_date.timestamp()
            sessionInfo["AvailableRecording"] = {
                "BrainSenseStreaming": models.BrainSenseRecording.objects.filter(source_file=session.deidentified_id, recording_type="BrainSenseStreamTimeDomain").count(),
                "IndefiniteStreaming": models.BrainSenseRecording.objects.filter(source_file=session.deidentified_id, recording_type="IndefiniteStream").count(),
                "BrainSenseSurvey": models.BrainSenseRecording.objects.filter(source_file=session.deidentified_id, recording_type="BrainSenseSurvey").count(),
                "TherapyHistory": models.TherapyHistory.objects.filter(source_file=session.deidentified_id).count(),
            }
            sessions.append(sessionInfo)
    return sessions

def deleteDevice(device_id):
    recordings = models.BrainSenseRecording.objects.filter(device_deidentified_id=device_id).all()
    for recording in recordings:
        try:
            os.remove(DATABASE_PATH + "recordings" + os.path.sep + recording.recording_datapointer)
        except:
            pass
    recordings.delete()

    Sessions = models.PerceptSession.objects.filter(device_deidentified_id=device_id).all()
    models.TherapyChangeLog.objects.filter(device_deidentified_id=str(device_id)).delete()
    for session in Sessions:
        models.TherapyHistory.objects.filter(source_file=str(session.deidentified_id)).delete()
        models.TherapyChangeLog.objects.filter(source_file=str(session.deidentified_id)).delete()
        models.PatientCustomEvents.objects.filter(source_file=str(session.deidentified_id)).delete()
        models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=str(device_id)).delete()
        models.ImpedanceHistory.objects.filter(session_date=session.session_date).delete()
        try:
            os.remove(DATABASE_PATH + session.session_file_path)
        except:
            pass
    Sessions.delete()

def deleteSessions(user, patient_id, session_ids, authority):
    availableDevices = Database.getPerceptDevices(user, patient_id, authority)

    for i in range(len(session_ids)):
        for device in availableDevices:
            if models.PerceptSession.objects.filter(device_deidentified_id=device.deidentified_id, deidentified_id=str(session_ids[i])).exists():
                models.TherapyHistory.objects.filter(source_file=str(session_ids[i])).delete()
                models.TherapyChangeLog.objects.filter(source_file=str(session_ids[i])).delete()
                models.PatientCustomEvents.objects.filter(source_file=str(session_ids[i])).delete()
                recordings = models.BrainSenseRecording.objects.filter(source_file=str(session_ids[i])).all()
                for recording in recordings:
                    try:
                        os.remove(DATABASE_PATH + "recordings" + os.path.sep + recording.recording_datapointer)
                    except:
                        pass
                recordings.delete()
                session = models.PerceptSession.objects.filter(deidentified_id=session_ids[i]).first()
                models.ImpedanceHistory.objects.filter(session_date=session.session_date).delete()
                try:
                    os.remove(DATABASE_PATH + session.session_file_path)
                except:
                    pass
                session.delete()
