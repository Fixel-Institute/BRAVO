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
Customized Analysis Builder Module
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
import copy
import websocket
from scipy import signal, io, stats, optimize, interpolate
from specparam import SpectralModel

from Backend import models
from modules import Database
from modules.Percept import BrainSenseStream

from decoder import DelsysTrigno
from utility import PythonUtility
from utility import SignalProcessingUtility as SPU

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

def getExistingAnalysis(user, patientId, authority):
    AvailableAnalysis = list()
    if not authority["Permission"]:
        return AvailableAnalysis

    analysisList = models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=patientId).all()
    AvailableAnalysis.extend([{
        "AnalysisName": analysis.analysis_name,
        "AnalysisDate": analysis.analysis_date.timestamp(),
        "RecordingList": analysis.recording_list,
        "RecordingType": analysis.recording_type,
        "AnalysisID": analysis.deidentified_id,
    } for analysis in analysisList if not analysis.analysis_name == "DefaultBrainSenseStreaming"])
    
    return AvailableAnalysis

def addNewAnalysis(user, patientId, authority):
    if not authority["Permission"]:
        return None

    analysis = models.CombinedRecordingAnalysis(analysis_name="DefaultAnalysis", device_deidentified_id=patientId)
    if not "AnalysisConfiguration" in analysis.recording_type:
        Data = dict()
        Data["Descriptor"] = {}
        analysisConfig = saveAnalysisConfiguration(Data, user, patientId, analysis.deidentified_id)
        analysis.recording_type.append(analysisConfig.recording_type)
        analysis.recording_list.append(str(analysisConfig.recording_id))
    analysis.save()
    return {
        "AnalysisName": analysis.analysis_name,
        "AnalysisDate": analysis.analysis_date.timestamp(),
        "RecordingList": analysis.recording_list,
        "RecordingType": analysis.recording_type,
        "AnalysisID": analysis.deidentified_id,
    }

def deleteAnalysis(user, patientId, analysisId, authority):
    if not authority["Permission"]:
        return None
    
    if models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=patientId, deidentified_id=analysisId).exists():
        analysis = models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=patientId, deidentified_id=analysisId).first()
        if "AnalysisConfiguration" in analysis.recording_type:
            deleteAnalysisConfiguration(user, patientId, analysisId)
        analysis.delete()

    return True

def queryAvailableRecordings(user, patientId, authority):
    AvailableRecordings = list()
    if not authority["Permission"]:
        return AvailableRecordings
    
    availableDevices = Database.getPerceptDevices(user, patientId, authority)
    for device in availableDevices:
        if device.device_name == "":
            if not (user.is_admin or user.is_clinician):
                deviceName = str(device.deidentified_id)
            else:
                deviceName = device.getDeviceSerialNumber(key)
        else:
            deviceName = device.device_name

        recordings = models.NeuralActivityRecording.objects.filter(device_deidentified_id=device.deidentified_id).all()
        for recording in recordings:
            # Currently does not support BrainSense Survey unless new analysis is designed around it
            #if recording.recording_type == "BrainSenseSurvey":
            #    continue
            
            if not "Channel" in recording.recording_info.keys() and not (recording.recording_type == "ChronicLFPs" or recording.recording_type == "SummitChronicLogs"):
                RecordingData = Database.loadSourceDataPointer(recording.recording_datapointer)
                recording.recording_info = {
                    "Channel": RecordingData["ChannelNames"]
                }
                recording.save()
            
            AvailableRecordings.append({
                "RecordingId": recording.recording_id,
                "RecordingName": recording.recording_info["RecordingName"] if "RecordingName" in recording.recording_info else "",
                "RecordingType": recording.recording_type,
                "RecordingChannels": recording.recording_info["Hemisphere"].replace("HemisphereLocationDef.","") if (recording.recording_type == "ChronicLFPs" or recording.recording_type == "SummitChronicLogs") else recording.recording_info["Channel"],
                "Time": recording.recording_date.timestamp(),
                "Duration": recording.recording_duration,
                "RecordingLabel": deviceName + " " + recording.recording_info["Hemisphere"].replace("HemisphereLocationDef.","") if recording.recording_type == "ChronicLFPs" else deviceName
            })
    
    recordings = models.ExternalRecording.objects.filter(patient_deidentified_id=patientId).all()
    for recording in recordings:
        if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
            continue
        
        # Skipping Processed Results
        if recording.recording_type == "AnalysisOutput":
            continue

        # Currently does not support Wearable Sensor Before Parsing 
        if recording.recording_type == "BRAVOWearableApp_AppleWatch":
            continue
            
        # Currently does not support Wearable Sensor Before Parsing 
        if recording.recording_type == "BRAVOWearableApp_MetaMotionS":
            continue
            
        if not recording.recording_info:
            RecordingData = Database.loadSourceDataPointer(recording.recording_datapointer)
            recording.recording_info = {
                "Channel": RecordingData["ChannelNames"]
            }
            recording.save()
        
        if not "Channel" in recording.recording_info.keys():
            RecordingData = Database.loadSourceDataPointer(recording.recording_datapointer)
            recording.recording_info = {
                "Channel": RecordingData["ChannelNames"]
            }
            recording.save()

        AvailableRecordings.append({
            "RecordingId": recording.recording_id,
            "RecordingType": recording.recording_type,
            "RecordingChannels": recording.recording_info["Channel"],
            "Time": recording.recording_date.timestamp(),
            "Duration": recording.recording_duration,
            "RecordingLabel": recording.recording_type
        })

    return AvailableRecordings

def queryAnalysis(user, patientId, analysisId, authority):
    if not authority["Permission"]:
        return None
    
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId, device_deidentified_id=patientId).first()
    if not analysis:
        return None
    ProcessingQueued = models.ProcessingQueue.objects.filter(type="ProcessAnalysis", state="InProgress", descriptor__analysisId=str(analysis.deidentified_id)).exists()

    Data = {"Configuration": {}, "Recordings": [], "Analysis": {
        "AnalysisName": analysis.analysis_name,
        "AnalysisDate": analysis.analysis_date.timestamp(),
        "AnalysisID": analysis.deidentified_id,
        "ProcessingQueued": ProcessingQueued
    }}
    
    if "DeidentifiedID" in authority.keys():
        AvailableRecordings = queryAvailableRecordings(user, authority["DeidentifiedID"], authority)
    else:
        AvailableRecordings = queryAvailableRecordings(user, patientId, authority)

    Data["AvailableRecordings"] = AvailableRecordings
    for i in range(len(analysis.recording_type)):
        if analysis.recording_type[i] == "AnalysisConfiguration": 
            Data["Configuration"] = loadAnalysisConfiguration(user, patientId, analysisId)
        else:
            recording = [item for item in AvailableRecordings if str(item["RecordingId"]) == analysis.recording_list[i]]
            if not len(recording) == 0:
                Data["Recordings"].append(recording[0])
    
    return Data

def saveAnalysisConfiguration(Data, user, patientId, analysisId):
    if models.NeuralActivityRecording.objects.filter(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)}).exists():
        recording = models.NeuralActivityRecording.objects.filter(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)}).first()
        filename = Database.saveSourceFiles(Data, "AnalysisConfiguration", "Raw", recording.recording_id, recording.device_deidentified_id)
    else:
        recording = models.NeuralActivityRecording(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)})
        filename = Database.saveSourceFiles(Data, "AnalysisConfiguration", "Raw", recording.recording_id, recording.device_deidentified_id)
        recording.recording_datapointer = filename
        recording.save()
    return recording

def loadAnalysisConfiguration(user, patientId, analysisId):
    analysisConfig = models.NeuralActivityRecording.objects.filter(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)}).first()
    Data = Database.loadSourceDataPointer(analysisConfig.recording_datapointer)
    return Data

def deleteAnalysisConfiguration(user, patientId, analysisId):
    analysisConfig = models.NeuralActivityRecording.objects.filter(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)}).first()
    try: 
        os.remove(DATABASE_PATH + "recordings" + os.path.sep + analysisConfig.recording_datapointer)
    except:
        pass
    analysisConfig.delete()

def updateAnalysis(user, patientId, analysisId, steps, authority):
    Configuration = loadAnalysisConfiguration(user, patientId, analysisId)
    
    Configuration["AnalysisSteps"] = steps
    if "Results" in Configuration.keys():
        analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId, device_deidentified_id=patientId).first()
        for k in range(len(Configuration["Results"])):
            if "ProcessedData" in Configuration["Results"][k].keys():
                removeResultDataFile(Configuration["Results"][k]["ProcessedData"])
                index = [i for i in range(len(analysis.recording_list)) if analysis.recording_list[i] == Configuration["Results"][k]["ProcessedData"]]
                if len(index) > 0:
                    del(analysis.recording_type[index[0]])
                    del(analysis.recording_list[index[0]])
        Configuration["Results"] = []
        analysis.save()

    saveAnalysisConfiguration(Configuration, user, patientId, analysisId)

def removeRecordingFromAnalysis(user, patientId, analysisId, recordingId, authority):
    if not authority["Permission"]:
        return None
    
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId, device_deidentified_id=patientId).first()
    if not analysis:
        return None
    
    if not recordingId in analysis.recording_list:
        return None

    if not "AnalysisConfiguration" in analysis.recording_type:
        Data = dict()
        Data["Descriptor"] = {}
        analysisConfig = saveAnalysisConfiguration(Data, user, patientId, analysisId)
        analysis.recording_type.append(analysisConfig.recording_type)
        analysis.recording_list.append(str(analysisConfig.recording_id))
    else:
        Data = loadAnalysisConfiguration(user, patientId, analysisId)
    
    if recordingId in Data["Descriptor"].keys():
        del(Data["Descriptor"][recordingId])

    saveAnalysisConfiguration(Data, user, patientId, analysisId)

    index = [i for i in range(len(analysis.recording_list)) if analysis.recording_list[i] == recordingId]
    if len(index) > 0:
        del(analysis.recording_type[index[0]])
        del(analysis.recording_list[index[0]])

    analysis.save()
    return True

def addRecordingToAnalysis(user, patientId, analysisId, recordingId, recordingType, authority):
    if not authority["Permission"]:
        return None
    
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId, device_deidentified_id=patientId).first()
    if not analysis:
        return None
    
    if recordingId in analysis.recording_list:
        return None

    isExternalRecording = False
    recording = models.NeuralActivityRecording.objects.filter(recording_id=recordingId).first()
    if not recording:
        recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
        isExternalRecording = True

    if not recording:
        return None
    
    if isExternalRecording:
        if not "AnalysisConfiguration" in analysis.recording_type:
            Data = dict()
            Data["Descriptor"] = {}
            analysisConfig = saveAnalysisConfiguration(Data, user, patientId, analysisId)
            analysis.recording_type.append(analysisConfig.recording_type)
            analysis.recording_list.append(str(analysisConfig.recording_id))
        else:
            Data = loadAnalysisConfiguration(user, patientId, analysisId)
        
        Data["Descriptor"][recordingId] = {
            "TimeShift": 0,
            "Label": "",
            "Type": recordingType,
            "Version": 1,
            "Channels": {}
        }
        saveAnalysisConfiguration(Data, user, patientId, analysisId)

        analysis.recording_type.append(recording.recording_type)
        analysis.recording_list.append(str(recordingId))
        analysis.save()
        return {
            "recording": {
                "RecordingId": recording.recording_id,
                "RecordingType": recording.recording_type,
                "Time": recording.recording_date.timestamp(),
                "RecordingChannels": recording.recording_info["Channel"],
                "Duration": recording.recording_duration,
                "RecordingLabel": recording.recording_type
            },
            "configuration": Data["Descriptor"][recordingId]
        }
    
    else:
        if "DeidentifiedID" in authority.keys():
            availableDevices = Database.getPerceptDevices(user, authority["DeidentifiedID"], authority)
        else:
            availableDevices = Database.getPerceptDevices(user, patientId, authority)

        for device in availableDevices:
            if recording.device_deidentified_id == device.deidentified_id:
                if device.device_name == "":
                    if not (user.is_admin or user.is_clinician):
                        deviceName = str(device.deidentified_id)
                    else:
                        deviceName = device.getDeviceSerialNumber(key)
                else:
                    deviceName = device.device_name

                if not "AnalysisConfiguration" in analysis.recording_type:
                    Data = dict()
                    Data["Descriptor"] = {}
                    analysisConfig = saveAnalysisConfiguration(Data, user, patientId, analysisId)
                    analysis.recording_type.append(analysisConfig.recording_type)
                    analysis.recording_list.append(str(analysisConfig.recording_id))
                else:
                    Data = loadAnalysisConfiguration(user, patientId, analysisId)
                
                Data["Descriptor"][recordingId] = {
                    "TimeShift": 0,
                    "Label": "",
                    "Type": recordingType,
                    "Version": 1,
                    "Channels": {}
                }
                saveAnalysisConfiguration(Data, user, patientId, analysisId)

                analysis.recording_type.append(recording.recording_type)
                analysis.recording_list.append(str(recordingId))
                analysis.save()
                return {
                    "recording": {
                        "RecordingId": recording.recording_id,
                        "RecordingType": recording.recording_type,
                        "RecordingChannels": recording.recording_info["Hemisphere"].replace("HemisphereLocationDef.","") if recording.recording_type == "ChronicLFPs" else recording.recording_info["Channel"],
                        "Time": recording.recording_date.timestamp(),
                        "Duration": recording.recording_duration,
                        "RecordingLabel": deviceName + " " + recording.recording_info["Hemisphere"].replace("HemisphereLocationDef.","") if recording.recording_type == "ChronicLFPs" else deviceName
                    },
                    "configuration": Data["Descriptor"][recordingId]
                }
        
def setRecordingConfiguration(user, patientId, analysisId, recordingId, configuration, authority):
    if not authority["Permission"]:
        return None
    
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId, device_deidentified_id=patientId).first()
    if not analysis:
        return None
    
    if not recordingId in analysis.recording_list:
        return None

    if not "AnalysisConfiguration" in analysis.recording_type:
        Data = dict()
        Data["Descriptor"] = {}
        analysisConfig = saveAnalysisConfiguration(Data, user, patientId, analysisId)
        analysis.recording_type.append(analysisConfig.recording_type)
        analysis.recording_list.append(str(analysisConfig.recording_id))
        analysis.save()
    else:
        Data = loadAnalysisConfiguration(user, patientId, analysisId)
    
    Data["Descriptor"][recordingId] = configuration
    saveAnalysisConfiguration(Data, user, patientId, analysisId)
    return True

def saveCacheFile(filename, rawBytes):
    secureEncoder = Fernet(key)
    with open(DATABASE_PATH + "cache" + os.path.sep + filename, "wb+") as file:
        file.write(secureEncoder.encrypt(rawBytes))

def processAnnotations(filename, patientId):
    secureEncoder = Fernet(key)
    with open(filename, "rb") as file:
        csvFile = secureEncoder.decrypt(file.read())
    
    df = pd.read_csv(BytesIO(csvFile))
    for i in df.index:
        annotation = models.CustomAnnotations(patient_deidentified_id=patientId, 
                                    event_name=df["Annotation"][i], 
                                    event_time=datetime.fromisoformat(df["Time"][i]),
                                    event_type="Streaming",
                                    event_duration=df["Duration"][i])
        annotation.save()
    return True

def processExternalRecordings(filename):
    secureEncoder = Fernet(key)
    with open(filename, "rb") as file:
        csvFile = secureEncoder.decrypt(file.read())
    
    Data = {"ChannelNames": []}
    df = pd.read_csv(BytesIO(csvFile))
    Data["ChannelNames"] = df.keys().to_list()
    Data["Data"] = np.zeros((len(df[Data["ChannelNames"][0]]), len(Data["ChannelNames"])))
    for i in range(len(Data["ChannelNames"])):
        Data["Data"][:,i] = df[Data["ChannelNames"][i]]
    return Data

def processMDATRecordings(filename):
    secureEncoder = Fernet(key)
    with open(filename, "rb") as file:
        mdatFile = secureEncoder.decrypt(file.read())

    Trigno = DelsysTrigno.decodeBMLDelsysFormat(mdatFile)
    TrignoSensorList = []
    
    Data = {"ChannelNames": []}
    for i in range(len(Trigno["EMG"])):
        if len(Trigno["EMG"][i]) > 0:
            Data["ChannelNames"].append("EMG." + str(i+1))
    
    Data["Data"] = np.zeros((len(Trigno["EMGTime"]), len(Data["ChannelNames"])))
    Counter = 0
    for i in range(len(Trigno["EMG"])):
        if len(Trigno["EMG"][i]) > 0:
            Data["Data"][:len(Trigno["EMG"][i]),Counter] = Trigno["EMG"][i].flatten()
            Counter += 1
    Data["SamplingRate"] = np.around(1/np.median(np.diff(Trigno["EMGTime"])),3)
    Data["StartTime"] = Trigno['Triggers']["Time"][0] # Javascript Time is in Milliseconds
    Data["Missing"] = np.zeros(Data["Data"].shape)
    Data["Duration"] = Data["Data"].shape[0]/Data["SamplingRate"]
    TrignoSensorList.append(Data)

    for sensorKey in ["Acc", "Gyro", "Mag"]:
        Data = {"ChannelNames": []}
        for i in range(len(Trigno[sensorKey])):
            if len(Trigno[sensorKey][i]) > 0:
                Data["ChannelNames"].append(sensorKey + "." + str(i+1) + ".X")
                Data["ChannelNames"].append(sensorKey + "." + str(i+1) + ".Y")
                Data["ChannelNames"].append(sensorKey + "." + str(i+1) + ".Z")
    
        Data["Data"] = np.zeros((len(Trigno["IMUTime"]), len(Data["ChannelNames"])))
        Counter = 0
        for i in range(len(Trigno[sensorKey])):
            if Trigno[sensorKey][i].shape[0] > 0:
                for j in range(3):
                    Data["Data"][:Trigno[sensorKey][i].shape[0],Counter] = Trigno[sensorKey][i][:,j].flatten()
                    Counter += 1
        Data["SamplingRate"] = np.around(1/np.median(np.diff(Trigno["IMUTime"])),3)
        Data["StartTime"] = Trigno['Triggers']["Time"][0] # Javascript Time is in Milliseconds
        Data["Missing"] = np.zeros(Data["Data"].shape)
        Data["Duration"] = Data["Data"].shape[0]/Data["SamplingRate"]
        TrignoSensorList.append(Data)

    return TrignoSensorList

def getRawRecordingData(user, patientId, analysisId, recordingId, authority):
    if not authority["Permission"]:
        return None
    
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId, device_deidentified_id=patientId).first()
    if not analysis:
        return None
    
    if not recordingId in analysis.recording_list:
        return None

    isExternalRecording = False
    recording = models.NeuralActivityRecording.objects.filter(recording_id=recordingId).first()
    if not recording:
        recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
        isExternalRecording = True

    if not recording:
        return None
    
    Configuration = loadAnalysisConfiguration(user, patientId, analysisId)
    ChannelConfiguration = Configuration["Descriptor"][recordingId]["Channels"]
    
    if isExternalRecording:
        Data = Database.loadSourceDataPointer(recording.recording_datapointer)
        ChannelSelection = np.ones(len(Data["ChannelNames"]), dtype=bool)
        for channelName in ChannelConfiguration.keys():
            ChannelSelection[PythonUtility.iterativeCompare(Data["ChannelNames"], channelName, "equal").flatten()] = ChannelConfiguration[channelName]["show"]

        return {
            "Data": Data["Data"][:,ChannelSelection].T,
            "ChannelNames": PythonUtility.listSelection(Data["ChannelNames"], ChannelSelection),
            "StartTime": Data["StartTime"],
            "SamplingRate": Data["SamplingRate"]
        } 
    else:
        if recording.recording_type == "BrainSenseStreamTimeDomain":
            Data = Database.loadSourceDataPointer(recording.recording_datapointer)
            ChannelSelection = np.ones(len(Data["ChannelNames"]), dtype=bool)
            for channelName in ChannelConfiguration.keys():
                ChannelSelection[PythonUtility.iterativeCompare(Data["ChannelNames"], channelName, "equal").flatten()] = ChannelConfiguration[channelName]["show"]

            return {
                "Data": Data["Data"][:,ChannelSelection].T,
                "ChannelNames": PythonUtility.listSelection(Data["ChannelNames"], ChannelSelection),
                "StartTime": Data["StartTime"],
                "SamplingRate": Data["SamplingRate"]
            } 
        elif recording.recording_type == "BrainSenseStreamPowerDomain":
            Data = Database.loadSourceDataPointer(recording.recording_datapointer)
            ChannelSelection = np.ones(len(Data["ChannelNames"]), dtype=bool)
            for channelName in ChannelConfiguration.keys():
                ChannelSelection[PythonUtility.iterativeCompare(Data["ChannelNames"], channelName, "equal").flatten()] = ChannelConfiguration[channelName]["show"]

            return {
                "Data": Data["Data"][:,ChannelSelection].T,
                "ChannelNames": PythonUtility.listSelection(Data["ChannelNames"], ChannelSelection),
                "StartTime": Data["StartTime"],
                "SamplingRate": Data["SamplingRate"]
            } 
        elif recording.recording_type == "IndefiniteStream":
            Data = Database.loadSourceDataPointer(recording.recording_datapointer)
            ChannelSelection = np.ones(len(Data["ChannelNames"]), dtype=bool)
            for channelName in ChannelConfiguration.keys():
                ChannelSelection[PythonUtility.iterativeCompare(Data["ChannelNames"], channelName, "equal").flatten()] = ChannelConfiguration[channelName]["show"]

            return {
                "Data": Data["Data"][:,ChannelSelection].T,
                "ChannelNames": PythonUtility.listSelection(Data["ChannelNames"], ChannelSelection),
                "StartTime": Data["StartTime"],
                "SamplingRate": Data["SamplingRate"]
            } 
    
    return None

def startAnalysis(user, patientId, analysisId, authority):
    if not authority["Permission"]:
        return "Permission Error"
    
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId, device_deidentified_id=patientId).first()
    if not analysis:
        return "Permission Error"
    
    if models.ProcessingQueue.objects.filter(type="ProcessAnalysis", state="InProgress", descriptor__analysisId=str(analysis.deidentified_id)).exists():
        #return "Queue Exists" 
        pass

    Descriptor = {
        "analysisId": str(analysis.deidentified_id)
    }

    processingqueue = models.ProcessingQueue(owner=user.unique_user_id, type="ProcessAnalysis", state="InProgress", descriptor=Descriptor)
    processingqueue.save()
    try:
        ws = websocket.WebSocket()
        ws.connect("ws://localhost:3001/socket/notification")
        ws.send(json.dumps({
            "NotificationType": "AnalysisProcessing",
            "TaskUser": str(user.unique_user_id),
            "TaskID": str(analysis.deidentified_id),
            "Authorization": os.environ["ENCRYPTION_KEY"],
            "State": "StartProcessing",
            "Message": "",
        }))
        ws.close()
    except Exception as e:
        print(e)

    return "Success"

def createResultMATFile(Data, patientId, recordingType, recordingDuration):
    recording = models.ExternalRecording(patient_deidentified_id=patientId, 
                                recording_type=recordingType, 
                                recording_date=datetime.now().astimezone(pytz.utc),
                                recording_duration=recordingDuration)

    filename = Database.saveResultMATFiles(Data, "AnalysisOutput", "Raw", recording.recording_id, recording.patient_deidentified_id)
    recording.recording_datapointer = filename
    recording.save()
    return recording

def createResultDataFile(Data, patientId, recordingType, recordingDuration):
    recording = models.ExternalRecording(patient_deidentified_id=patientId, 
                                recording_type=recordingType, 
                                recording_date=datetime.now().astimezone(pytz.utc),
                                recording_duration=recordingDuration)
    
    filename = Database.saveSourceFiles(Data, "AnalysisOutput", "Raw", recording.recording_id, recording.patient_deidentified_id)
    recording.recording_datapointer = filename
    recording.save()
    return recording

def removeResultDataFile(recordingId):
    recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
    if recording:
        try:
            os.remove(DATABASE_PATH + "recordings" + os.path.sep + recording.recording_datapointer)
        except:
            pass
        recording.delete()

def JSONEncode(item):
    if type(item) == dict:
        for i in item.keys():
            item[i] = JSONEncode(item[i])
        return item
    elif type(item) == list:
        for i in range(len(item)):
            item[i] = JSONEncode(item[i])
        return item
    elif type(item) == float:
        if np.isnan(item):
            return None
        elif np.isinf(item):
            return None
        else:
            return item
    else:
        return item

def queryResultData(user, patientId, analysisId, resultId, download, authority):
    analysis = models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=patientId, deidentified_id=analysisId).first()
    if not analysis:
        return None
    
    recording = models.ExternalRecording.objects.filter(patient_deidentified_id=patientId, recording_type="AnalysisOutput", recording_id=resultId).first()
    if not recording:
        return None
    
    ProcessedData = Database.loadSourceDataPointer(recording.recording_datapointer, bytes=download)
    if download:
        return ProcessedData, {}
    
    if type(ProcessedData) == dict:
        ProcessedData = [ProcessedData]

    GraphOptions = {}
    if ProcessedData[0]["ResultType"] == "TimeDomain":
        GraphOptions["RecommendedYLimit"] = []
        GraphOptions["ChannelNames"] = []
        for i in range(len(ProcessedData)):
            for j in range(len(ProcessedData[i]["ChannelNames"])):
                if not ProcessedData[i]["ChannelNames"][j] in GraphOptions["ChannelNames"]:
                    GraphOptions["ChannelNames"].append(ProcessedData[i]["ChannelNames"][j])
                    GraphOptions["RecommendedYLimit"].append([0,0])
                
                for index in range(len(GraphOptions["ChannelNames"])):
                    if GraphOptions["ChannelNames"][index] == ProcessedData[i]["ChannelNames"][j]:
                        break

                GraphOptions["RecommendedYLimit"][index] = [np.min([GraphOptions["RecommendedYLimit"][index][0], -np.std(ProcessedData[i]["Data"][:,j])*10]), np.max([GraphOptions["RecommendedYLimit"][index][1], np.std(ProcessedData[i]["Data"][:,j])*10])]
    
    return JSONEncode(ProcessedData), GraphOptions

def handleFilterProcessing(step, RecordingIds, Results, Configuration, analysis):
    print("Start Filter")
    targetSignal = step["config"]["targetRecording"]
    filterType = "Butterworth"

    if step["config"]["highpass"] == "":
        step["config"]["highpass"] = "0"
    elif step["config"]["lowpass"] == "":
        step["config"]["lowpass"] = "0"

    highpass = float(step["config"]["highpass"])
    lowpass = float(step["config"]["lowpass"])

    def processRawData(RawData):
        if highpass == 0:
            [b,a] = signal.butter(5, np.array([lowpass])*2/RawData["SamplingRate"], 'lp', output='ba')
        elif lowpass == 0:
            [b,a] = signal.butter(5, np.array([highpass])*2/RawData["SamplingRate"], 'hp', output='ba')
        else:
            [b,a] = signal.butter(5, np.array([highpass, lowpass])*2/RawData["SamplingRate"], 'bp', output='ba')

        RawData["Data"] = signal.filtfilt(b, a, RawData["Data"], axis=0)
        RawData["FilterState"] = [highpass if highpass > 0 else 0, lowpass if lowpass > 0 else RawData["SamplingRate"]/2]
        RawData["ResultType"] = "TimeDomain"
        return RawData

    ProcessedData = []
    for recordingId in RecordingIds:
        if Configuration["Descriptor"][recordingId]["Type"] == targetSignal:
            if models.ExternalRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            elif models.NeuralActivityRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.NeuralActivityRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)

            RawData = processRawData(RawData=RawData)
            ProcessedData.append(RawData)
    
    for result in Results:
        if result["ResultLabel"] == targetSignal:
            recording = models.ExternalRecording.objects.filter(recording_id=result["ProcessedData"]).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            
            for i in range(len(RawData)):
                RawData[i] = processRawData(RawData=RawData[i])
                ProcessedData.append(RawData[i])

    recording = createResultDataFile(ProcessedData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))

    return {
        "ResultLabel": step["config"]["output"],
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": "TimeDomain"
    }

def handleWienerFilterProcessing(step, RecordingIds, Results, Configuration, analysis):
    print("Start Wiener Filter")
    targetSignal = step["config"]["targetRecording"]

    def processRawData(RawData):
        Errors = signal.wiener(RawData["Data"], mysize=int(RawData["SamplingRate"]/2))
        RawData["Data"] = RawData["Data"] - Errors
        RawData["ResultType"] = "TimeDomain"
        return RawData

    ProcessedData = []
    for recordingId in RecordingIds:
        if Configuration["Descriptor"][recordingId]["Type"] == targetSignal:
            if models.ExternalRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            elif models.NeuralActivityRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.NeuralActivityRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)

            RawData = processRawData(RawData=RawData)
            ProcessedData.append(RawData)
    
    for result in Results:
        if result["ResultLabel"] == targetSignal:
            recording = models.ExternalRecording.objects.filter(recording_id=result["ProcessedData"]).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            
            for i in range(len(RawData)):
                RawData[i] = processRawData(RawData=RawData[i])
                ProcessedData.append(RawData[i])

    recording = createResultDataFile(ProcessedData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))

    return {
        "ResultLabel": step["config"]["output"],
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": "TimeDomain"
    }

def handleCardiacFilterProcessing(step, RecordingIds, Results, Configuration, analysis):
    print("Start Cardiac Filter")
    targetSignal = step["config"]["targetRecording"]
    filterMethod = step["config"]["cardiacFilterMethod"]

    def FixedPeakFilter(RawData):
        Signal = RawData["Data"]
        SamplingRate = RawData["SamplingRate"]

        for i in range(Signal.shape[1]):
            posPeaks,_ = signal.find_peaks(Signal[:,i], prominence=[10,200], distance=SamplingRate*0.5)
            PosCardiacVariability = np.std(np.diff(posPeaks))
            negPeaks,_ = signal.find_peaks(-Signal[:,i], prominence=[10,200], distance=SamplingRate*0.5)
            NegCardiacVariability = np.std(np.diff(negPeaks))

            if PosCardiacVariability < NegCardiacVariability:
                peaks = posPeaks
            else:
                peaks = negPeaks
            CardiacRate = int(np.mean(np.diff(peaks)))

            PrePeak = int(CardiacRate*0.25)
            PostPeak = int(CardiacRate*0.65)
            EKGMatrix = np.zeros((len(peaks)-2,PrePeak+PostPeak))
            for j in range(1,len(peaks)-1):
                if peaks[j]+PostPeak < len(Signal[:,i]) and peaks[j]-PrePeak > 0:
                    EKGMatrix[j-1,:] = Signal[peaks[j]-PrePeak:peaks[j]+PostPeak,i]

            EKGTemplate = np.mean(EKGMatrix,axis=0)
            EKGTemplate = EKGTemplate / (np.max(EKGTemplate)-np.min(EKGTemplate))

            def EKGTemplateFunc(xdata, amplitude, offset):
                return EKGTemplate * amplitude + offset

            for j in range(len(peaks)):
                if peaks[j]-PrePeak < 0:
                    pass
                elif peaks[j]+PostPeak >= len(Signal[:,i]) :
                    pass
                else:
                    sliceSelection = np.arange(peaks[j]-PrePeak,peaks[j]+PostPeak)
                    params, covmat = optimize.curve_fit(EKGTemplateFunc, sliceSelection, Signal[sliceSelection,i])
                    Signal[sliceSelection,i] = Signal[sliceSelection,i] - EKGTemplateFunc(sliceSelection, *params)

        RawData["Data"] = Signal
        return RawData

    def KurtosisFilterr(RawData):
        Signal = RawData["Data"]
        SamplingRate = RawData["SamplingRate"]

        Window = int(SamplingRate/2)
        KurtosisIndex = range(0, len(Signal)-Window)
        ExpectedKurtosis = np.zeros((len(KurtosisIndex)))
        for j in range(len(KurtosisIndex)):
            zScore = stats.zscore(Signal[KurtosisIndex[j]:KurtosisIndex[j]+Window])
            ExpectedKurtosis[j] = np.mean(np.power(zScore, 4))

        [b,a] = signal.butter(3, np.array([0.5, 2])*2/SamplingRate, "bandpass")
        ExpectedKurtosis = signal.filtfilt(b,a,ExpectedKurtosis)
        Peaks, _ = signal.find_peaks(ExpectedKurtosis, distance=Window)
        Peaks += int(Window/2)

        CardiacFiltered = copy.deepcopy(RawData["Data"])
        for i in range(Signal.shape[1]):
            CardiacEpochs = []
            SearchWindow = 100
            for j in range(len(Peaks)):
                if ExpectedKurtosis[Peaks[j]-int(Window/2)] < 1.2:
                    continue
                ShiftPeak = 0
                if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(Signal[:,i]):
                    continue 
                findPeak = np.argmax(Signal[Peaks[j]-SearchWindow:Peaks[j]+SearchWindow, i])
                ShiftPeak = SearchWindow-findPeak
                if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(Signal[:,i]):
                    continue 
                CardiacEpochs.append(Signal[Peaks[j]-SearchWindow-ShiftPeak:Peaks[j]+SearchWindow-ShiftPeak, i])

            if len(CardiacEpochs) == 0:
                continue
            
            EKGTemplate = np.mean(np.array(CardiacEpochs), axis=0)
            EKGTemplate = EKGTemplate / (np.max(EKGTemplate)-np.min(EKGTemplate))

            def EKGTemplateFunc(xdata, amplitude, offset):
                return EKGTemplate * amplitude + offset

            for j in range(len(Peaks)):
                ShiftPeak = 0
                if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(Signal[:,i]):
                    continue
                findPeak = np.argmax(Signal[Peaks[j]-SearchWindow:Peaks[j]+SearchWindow,i])
                ShiftPeak = SearchWindow-findPeak
                if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(Signal[:,i]):
                    continue
                sliceSelection = np.arange(Peaks[j]-SearchWindow-ShiftPeak, Peaks[j]+SearchWindow-ShiftPeak)
                Original = Signal[sliceSelection,i]
                params, covmat = optimize.curve_fit(EKGTemplateFunc, sliceSelection, Original)
                CardiacFiltered[sliceSelection,i] = Original - EKGTemplateFunc(sliceSelection, *params)
        
        RawData["Data"] = CardiacFiltered
        return RawData

    def LMSDecoupler(RawData):
        Signal = RawData["Data"]
        if not Signal.shape[1] == 2:
            return RawData
        
        SamplingRate = RawData["SamplingRate"]

        Window = int(SamplingRate/2)
        PaddedSignal = np.concatenate((Signal, Signal), axis=0)

        _, DecoupledSignal1, _ = SPU.filtLMS(PaddedSignal[:,0], PaddedSignal[:,1], order=Window, step_size=0.5)
        _, DecoupledSignal2, _ = SPU.filtLMS(PaddedSignal[:,1], PaddedSignal[:,0], order=Window, step_size=0.5)
        RawData["Data"][:,0] = DecoupledSignal2[len(Signal):]
        RawData["Data"][:,1] = DecoupledSignal1[len(Signal):]
        return RawData

    def processRawData(RawData):
        if filterMethod == "Kurtosis-peak Detection Template Matching":
            return KurtosisFilterr(RawData)
        elif filterMethod == "Fixed Height Peak Detection Template Matching":
            return FixedPeakFilter(RawData)
        elif filterMethod == "LMS Decoupler":
            return LMSDecoupler(RawData)
        return RawData

    ProcessedData = []
    for recordingId in RecordingIds:
        if Configuration["Descriptor"][recordingId]["Type"] == targetSignal:
            if models.ExternalRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            elif models.NeuralActivityRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.NeuralActivityRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            
            RawData = processRawData(RawData)
            RawData["ResultType"] = "TimeDomain"
            ProcessedData.append(RawData)
    
    for result in Results:
        if result["ResultLabel"] == targetSignal:
            recording = models.ExternalRecording.objects.filter(recording_id=result["ProcessedData"]).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            
            for i in range(len(RawData)):
                RawData[i] = processRawData(RawData[i])
                RawData[i]["ResultType"] = "TimeDomain"
                ProcessedData.append(RawData[i])

    recording = createResultDataFile(ProcessedData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))

    return {
        "ResultLabel": step["config"]["output"],
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": "TimeDomain"
    }

def handleExtractTimeFrequencyAnalysis(step, RecordingIds, Results, Configuration, analysis):
    print("Start Extract Time-Frequency Analysis")
    targetSignal = step["config"]["targetRecording"]
    psdMethod = step["config"]["psdMethod"]
    window = float(step["config"]["window"]) / 1000
    overlap = float(step["config"]["overlap"]) / 1000
    modelOrder = int(step["config"]["modelOrder"])
    frequencyResolution = float(step["config"]["frequencyResolution"])
    dropMissing = step["config"]["dropMissing"]

    def processRawData(RawData):
        RawData["ResultType"] = "RawSpectrogram"
        for i in range(len(RawData["ChannelNames"])):
            if RawData["ChannelNames"][i] in Configuration["Descriptor"][recordingId]["Channels"].keys():
                RawData["ChannelNames"][i] = Configuration["Descriptor"][recordingId]["Channels"][RawData["ChannelNames"][i]]["name"]
        RawData["Time"] = (np.arange(RawData["Data"].shape[0])/RawData["SamplingRate"]) + RawData["StartTime"] + (Configuration["Descriptor"][recordingId]["TimeShift"]/1000)
        
        RawData["Spectrogram"] = list()
        for i in range(len(RawData["ChannelNames"])):
            if psdMethod == "Short-time Fourier Transform":
                Spectrum = SPU.defaultSpectrogram(RawData["Data"][:,i], window=window, overlap=overlap, frequency_resolution=frequencyResolution if frequencyResolution < 1/window else 1/window, fs=RawData["SamplingRate"])
            elif psdMethod == "Welch's Periodogram":
                Spectrum = SPU.welchSpectrogram(RawData["Data"][:,i], window=window, overlap=overlap, frequency_resolution=frequencyResolution, fs=RawData["SamplingRate"])
            elif psdMethod == "Autoregressive (AR) Model":
                Spectrum = SPU.autoregressiveSpectrogram(RawData["Data"][:,i], window=window, overlap=overlap, frequency_resolution=1/window, fs=RawData["SamplingRate"], order=modelOrder)
            
            RawData["Spectrogram"].append(Spectrum)
            RawData["Spectrogram"][i]["Missing"] = SPU.calculateMissingLabel(RawData["Missing"][:,i], window=window, overlap=overlap, fs=RawData["SamplingRate"])
            RawData["Spectrogram"][i]["Type"] = "Spectrogram"
            RawData["Spectrogram"][i]["Time"] += RawData["StartTime"] # TODO Check later

            if dropMissing:
                TimeSelection = RawData["Spectrogram"][i]["Missing"] == 0
                RawData["Spectrogram"][i]["Missing"] = RawData["Spectrogram"][i]["Missing"][TimeSelection]
                RawData["Spectrogram"][i]["Time"] = RawData["Spectrogram"][i]["Time"][TimeSelection]
                RawData["Spectrogram"][i]["Power"] = RawData["Spectrogram"][i]["Power"][:, TimeSelection]
                RawData["Spectrogram"][i]["logPower"] = RawData["Spectrogram"][i]["logPower"][:, TimeSelection]
            RawData["Spectrogram"][i]["ColorRange"] = [-np.nanmax(np.abs(RawData["Spectrogram"][i]["logPower"][RawData["Spectrogram"][i]["Frequency"]<100,:])), np.nanmax(np.abs(RawData["Spectrogram"][i]["logPower"][RawData["Spectrogram"][i]["Frequency"]<100,:]))]

        del RawData["Data"], RawData["Time"], RawData["Missing"]
        return RawData

    ProcessedData = []
    for recordingId in RecordingIds:
        if Configuration["Descriptor"][recordingId]["Type"] == targetSignal:
            if models.ExternalRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            elif models.NeuralActivityRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.NeuralActivityRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)

            RawData = processRawData(RawData=RawData)
            ProcessedData.append(RawData)
    
    for result in Results:
        if result["ResultLabel"] == targetSignal:
            recording = models.ExternalRecording.objects.filter(recording_id=result["ProcessedData"]).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            for i in range(len(RawData)):
                RawData[i] = processRawData(RawData=RawData[i])
                ProcessedData.append(RawData[i])

    recording = createResultDataFile(ProcessedData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))

    return {
        "ResultLabel": step["config"]["output"],
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": "RawSpectrogram"
    }

def handleExtractAnnotationPSDs(step, RecordingIds, Results, Configuration, analysis):
    print("Start Extract Annotation")
    targetSignal = step["config"]["targetRecording"]

    def processRawData(RawData):
        RawData["ResultType"] = "RawPSDs"
        if not "Spectrogram" in RawData.keys():
            for i in range(len(RawData["ChannelNames"])):
                if RawData["ChannelNames"][i] in Configuration["Descriptor"][recordingId]["Channels"].keys():
                    RawData["ChannelNames"][i] = Configuration["Descriptor"][recordingId]["Channels"][RawData["ChannelNames"][i]]["name"]
            RawData["Time"] = (np.arange(RawData["Data"].shape[0])/RawData["SamplingRate"]) + RawData["StartTime"] + (Configuration["Descriptor"][recordingId]["TimeShift"]/1000)
            
            RawData["Spectrogram"] = list()
            for i in range(len(RawData["ChannelNames"])):
                RawData["Spectrogram"].append(SPU.defaultSpectrogram(RawData["Data"][:,i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=RawData["SamplingRate"]))
                RawData["Spectrogram"][i]["Type"] = "Spectrogram"
                RawData["Spectrogram"][i]["Time"] += RawData["StartTime"] # TODO Check later

            if models.DeidentifiedPatientID.objects.filter(deidentified_id=analysis.device_deidentified_id).exists():
                deidentifiedId = models.DeidentifiedPatientID.objects.filter(deidentified_id=analysis.device_deidentified_id).first()
                annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=deidentifiedId.authorized_patient_id, 
                                                                    event_time__gte=datetime.fromtimestamp(RawData["Time"][0], tz=pytz.utc), 
                                                                    event_time__lte=datetime.fromtimestamp(RawData["Time"][-1], tz=pytz.utc))
            else:
                annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=analysis.device_deidentified_id, 
                                                                    event_time__gte=datetime.fromtimestamp(RawData["Time"][0], tz=pytz.utc), 
                                                                    event_time__lte=datetime.fromtimestamp(RawData["Time"][-1], tz=pytz.utc))
            
        if models.DeidentifiedPatientID.objects.filter(deidentified_id=analysis.device_deidentified_id).exists():
            deidentifiedId = models.DeidentifiedPatientID.objects.filter(deidentified_id=analysis.device_deidentified_id).first()
            annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=deidentifiedId.authorized_patient_id, 
                                                                event_time__gte=datetime.fromtimestamp(RawData["Spectrogram"][0]["Time"][0], tz=pytz.utc), 
                                                                event_time__lte=datetime.fromtimestamp(RawData["Spectrogram"][0]["Time"][-1], tz=pytz.utc))
        else:
            annotations = models.CustomAnnotations.objects.filter(patient_deidentified_id=analysis.device_deidentified_id, 
                                                                event_time__gte=datetime.fromtimestamp(RawData["Spectrogram"][0]["Time"][0], tz=pytz.utc), 
                                                                event_time__lte=datetime.fromtimestamp(RawData["Spectrogram"][0]["Time"][-1], tz=pytz.utc))
        
        RawData["Annotations"] = [{
            "Name": item.event_name,
            "Time": item.event_time.timestamp(),
            "Duration": item.event_duration
        } for item in annotations]
        return RawData

    ProcessedData = []
    for recordingId in RecordingIds:
        if Configuration["Descriptor"][recordingId]["Type"] == targetSignal:
            if models.ExternalRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            elif models.NeuralActivityRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.NeuralActivityRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)

            RawData = processRawData(RawData=RawData)
            ProcessedData.append(RawData)
    
    for result in Results:
        if result["ResultLabel"] == targetSignal:
            recording = models.ExternalRecording.objects.filter(recording_id=result["ProcessedData"]).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            for i in range(len(RawData)):
                RawData[i] = processRawData(RawData=RawData[i])
                ProcessedData.append(RawData[i])

    ResultData = {"ResultType": "RawEventPSDs"}
    for i in range(len(ProcessedData)):
        if type(ProcessedData[i]["ChannelNames"]) == str:
            ProcessedData[i]["ChannelNames"] = [ProcessedData[i]["ChannelNames"]]

        if type(ProcessedData[i]["Spectrogram"]) == dict:
            ProcessedData[i]["Spectrogram"] = [ProcessedData[i]["Spectrogram"]]
            
        for j in range(len(ProcessedData[i]["Spectrogram"])):
            ProcessedData[i]["Spectrogram"][j]["Power"] = 10*np.log10(ProcessedData[i]["Spectrogram"][j]["Power"])
            ProcessedData[i]["ChannelNames"][j] = ProcessedData[i]["ChannelNames"][j].strip()
            
        if type(ProcessedData[i]["Annotations"]) == dict:
            ProcessedData[i]["Annotations"] = [ProcessedData[i]["Annotations"]]

        for annotation in ProcessedData[i]["Annotations"]:
            if annotation["Duration"] > 0:
                EventStartTime = annotation["Time"]
                for j in range(len(ProcessedData[i]["ChannelNames"])): 
                    if not ProcessedData[i]["ChannelNames"][j] in ResultData.keys():
                        ResultData[ProcessedData[i]["ChannelNames"][j]] = {}

                    if not annotation["Name"] in ResultData[ProcessedData[i]["ChannelNames"][j]].keys():
                        ResultData[ProcessedData[i]["ChannelNames"][j]][annotation["Name"]] = {"PSDs": []}
                    
                    TimeSelection = PythonUtility.rangeSelection(ProcessedData[i]["Spectrogram"][j]["Time"], [EventStartTime, EventStartTime+annotation["Duration"]])
                    PSDs = ProcessedData[i]["Spectrogram"][j]["Power"][:, TimeSelection]

                    if step["config"]["averaged"]:
                        ResultData[ProcessedData[i]["ChannelNames"][j]][annotation["Name"]]["PSDs"].append(np.nanmean(PSDs, axis=1))
                    else:
                        for k in range(PSDs.shape[1]):
                            ResultData[ProcessedData[i]["ChannelNames"][j]][annotation["Name"]]["PSDs"].append(PSDs[:,k])
                    ResultData[ProcessedData[i]["ChannelNames"][j]][annotation["Name"]]["Frequency"] = ProcessedData[i]["Spectrogram"][j]["Frequency"]

    recording = createResultDataFile(ResultData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))

    return {
        "ResultLabel": step["config"]["output"],
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": "RawEventPSDs"
    }

def handleNormalizeProcessing(step, RecordingIds, Results, Configuration, analysis):
    print("Start Normalization")
    targetSignal = step["config"]["targetRecording"]
    normalizeMethod = step["config"]["normalizeMethod"]

    if normalizeMethod == "Band Normalize":
        if step["config"]["highEdge"] == "":
            step["config"]["highEdge"] = "90"
        elif step["config"]["lowEdge"] == "":
            step["config"]["lowEdge"] = "70"

        highEdge = float(step["config"]["highEdge"])
        lowEdge = float(step["config"]["lowEdge"])

    ProcessedData = None
    ResultType = "RawPSDs"
    for result in Results:
        if result["ResultLabel"] == targetSignal:
            recording = models.ExternalRecording.objects.filter(recording_id=result["ProcessedData"]).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            ResultType = result["Type"]
            if result["Type"] == "RawSpectrogram":
                for k in range(len(RawData)):
                    for i in range(len(RawData[k]["Spectrogram"])):
                        meanPSDs = np.nanmean(np.array(RawData[k]["Spectrogram"][i]["Power"]), axis=1)
                        if len(meanPSDs) == 0:
                            continue

                        if normalizeMethod == "FOOOF":
                            if "FilterState" in RawData[k].keys():
                                WindowRange = RawData[k]["FilterState"]
                                if RawData[k]["FilterState"][0] == 0:
                                    WindowRange[0] = 1
                            else:
                                WindowRange = [1,RawData[k]["SamplingRate"]/2 if RawData[k]["SamplingRate"] < 200 else 100]

                            FrequencyWindow = PythonUtility.rangeSelection(RawData[k]["Spectrogram"][i]["Frequency"], WindowRange)
                            fm = SpectralModel(peak_width_limits=[1,24])
                            fm.fit(np.array(RawData[k]["Spectrogram"][i]["Frequency"])[FrequencyWindow], meanPSDs[FrequencyWindow], WindowRange)
                            oof = fm.get_model("aperiodic", "linear")
                            
                            for j in range(RawData[k]["Spectrogram"][i]["Power"].shape[1]):
                                RawData[k]["Spectrogram"][i]["Power"][FrequencyWindow,j] = np.array(RawData[k]["Spectrogram"][i]["Power"][FrequencyWindow,j]) / oof
                            RawData[k]["Spectrogram"][i]["Power"] = RawData[k]["Spectrogram"][i]["Power"][FrequencyWindow,:]
                            RawData[k]["Spectrogram"][i]["logPower"] = np.log10(RawData[k]["Spectrogram"][i]["Power"])
                            RawData[k]["Spectrogram"][i]["Frequency"] = np.array(RawData[k]["Spectrogram"][i]["Frequency"])[FrequencyWindow]
                            RawData[k]["Spectrogram"][i]["ColorRange"] = [-np.nanmax(np.abs(RawData[k]["Spectrogram"][i]["logPower"][RawData[k]["Spectrogram"][i]["Frequency"]<100,:])), np.nanmax(np.abs(RawData[k]["Spectrogram"][i]["logPower"][RawData[k]["Spectrogram"][i]["Frequency"]<100,:]))]
                            
                        elif normalizeMethod == "Band Normalize":
                            FrequencyWindow = PythonUtility.rangeSelection(RawData[k]["Spectrogram"][i]["Frequency"], [lowEdge,highEdge])
                            MeanRefPower = np.nanmean(meanPSDs[FrequencyWindow])
                            for j in range(RawData[k]["Spectrogram"][i]["Power"].shape[1]):
                                RawData[k]["Spectrogram"][i]["Power"][:,j] = np.array(RawData[k]["Spectrogram"][i]["Power"][:,j]) / MeanRefPower
                            RawData[k]["Spectrogram"][i]["logPower"] = np.log10(RawData[k]["Spectrogram"][i]["Power"])
                            RawData[k]["Spectrogram"][i]["ColorRange"] = [-np.nanmax(np.abs(RawData[k]["Spectrogram"][i]["logPower"][RawData[k]["Spectrogram"][i]["Frequency"]<100,:])), np.nanmax(np.abs(RawData[k]["Spectrogram"][i]["logPower"][RawData[k]["Spectrogram"][i]["Frequency"]<100,:]))]
                                
                ProcessedData = RawData

            elif RawData["ResultType"] == "RawPSDs":
                for channelName in RawData.keys():
                    if channelName == "ResultType":
                        continue

                    for event in RawData[channelName].keys():
                        meanPSDs = np.nanmean(np.array(RawData[channelName][event]["PSDs"]), axis=0)
                        if len(meanPSDs) == 0:
                            continue 
                        
                        if normalizeMethod == "FOOOF":
                            FrequencyWindow = PythonUtility.rangeSelection(RawData[channelName][event]["Frequency"], [2,100])
                            fm = SpectralModel(peak_width_limits=[1,24])
                            fm.fit(np.array(RawData[channelName][event]["Frequency"])[FrequencyWindow], np.power(10,meanPSDs)[FrequencyWindow], [0, 100])
                            oof = fm.get_model("aperiodic", "log")
                            for i in range(len(RawData[channelName][event]["PSDs"])):
                                RawData[channelName][event]["PSDs"][i] = np.array(RawData[channelName][event]["PSDs"][i])[FrequencyWindow] - oof
                            RawData[channelName][event]["Frequency"] = np.array(RawData[channelName][event]["Frequency"])[FrequencyWindow]

                        elif normalizeMethod == "Band Normalize":
                            FrequencyWindow = PythonUtility.rangeSelection(RawData[channelName][event]["Frequency"], [lowEdge,highEdge])
                            MeanRefPower = np.nanmean(meanPSDs[FrequencyWindow])
                            for i in range(len(RawData[channelName][event]["PSDs"])):
                                RawData[channelName][event]["PSDs"][i] = np.array(RawData[channelName][event]["PSDs"][i]) - MeanRefPower
                ProcessedData = RawData

    recording = createResultDataFile(ProcessedData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))

    return {
        "ResultLabel": step["config"]["output"],
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": ResultType
    }

def handleCalculateSpectralFeatures(step, RecordingIds, Results, Configuration, analysis):
    print("Start Calculating Spectral Features")
    targetSignal = step["config"]["targetRecording"]
    if not "bands" in step["config"].keys():
        bands = [
            ["Beta Band", 12, 30]
        ]
    elif len(step["config"]["bands"]) == 0:
        bands = [
            ["Beta Band", 12, 30]
        ]
    else:
        bands = step["config"]["bands"]

    ProcessedData = None
    for result in Results:
        if result["ResultLabel"] == targetSignal:
            recording = models.ExternalRecording.objects.filter(recording_id=result["ProcessedData"]).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)

            SpectralFeatures = []
            if result["Type"] == "RawEventPSDs":
                for channelName in RawData.keys():
                    if channelName == "ResultType":
                        continue
                    for event in RawData[channelName].keys():
                        Features = {"Channel": event + " | " + channelName}
                        Features["Time"] = np.arange(len(RawData[channelName][event]["PSDs"]))
                        for bandIndex in range(len(bands)):
                            FrequencySelection = PythonUtility.rangeSelection(RawData[channelName][event]["Frequency"], [float(bands[bandIndex][1]),float(bands[bandIndex][2])], "inclusive")
                            Features[bands[bandIndex][0] + "_Mean"] = np.zeros(len(RawData[channelName][event]["PSDs"]))
                            Features[bands[bandIndex][0] + "_Peak"] = np.zeros(len(RawData[channelName][event]["PSDs"]))
                            Features[bands[bandIndex][0] + "_PeakFreq"] = np.zeros(len(RawData[channelName][event]["PSDs"]))
                            
                            for t in range(len(Features["Time"])):
                                Power = RawData[channelName][event]["PSDs"][t][FrequencySelection]
                                Features[bands[bandIndex][0] + "_Mean"][t] = np.nanmean(Power)
                                Features[bands[bandIndex][0] + "_Peak"][t] = np.nanmax(Power)
                                Features[bands[bandIndex][0] + "_PeakFreq"][t] = RawData[channelName][event]["Frequency"][np.nanargmax(Power)] + float(bands[bandIndex][1])
                        SpectralFeatures.append(Features)

            else:
                for i in range(len(RawData)):
                    for j in range(len(RawData[i]["Spectrogram"])):
                        Features = {"Channel": RawData[i]["ChannelNames"][j]}
                        Features["Time"] = RawData[i]["Spectrogram"][j]["Time"]

                        for bandIndex in range(len(bands)):
                            FrequencySelection = PythonUtility.rangeSelection(RawData[i]["Spectrogram"][j]["Frequency"], [float(bands[bandIndex][1]),float(bands[bandIndex][2])], "inclusive")
                            Features[bands[bandIndex][0] + "_Mean"] = np.zeros(RawData[i]["Spectrogram"][j]["Time"].shape)
                            Features[bands[bandIndex][0] + "_Peak"] = np.zeros(RawData[i]["Spectrogram"][j]["Time"].shape)
                            Features[bands[bandIndex][0] + "_PeakFreq"] = np.zeros(RawData[i]["Spectrogram"][j]["Time"].shape)
                            
                            for t in range(RawData[i]["Spectrogram"][j]["Power"].shape[1]):
                                Power = RawData[i]["Spectrogram"][j]["Power"][FrequencySelection, t]
                                Features[bands[bandIndex][0] + "_Mean"][t] = np.nanmean(Power)
                                Features[bands[bandIndex][0] + "_Peak"][t] = np.nanmax(Power)
                                Features[bands[bandIndex][0] + "_PeakFreq"][t] = RawData[i]["Spectrogram"][j]["Frequency"][np.nanargmax(Power)] + float(bands[bandIndex][1])
                        SpectralFeatures.append(Features)
            ProcessedData = {"ResultType": "SpectralFeatures", "Features": SpectralFeatures}

    recording = createResultDataFile(ProcessedData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))

    return {
        "ResultLabel": step["config"]["output"],
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": "SpectralFeatures"
    }

def handleExtractNarrowBandFeature(step, RecordingIds, Results, Configuration, analysis):
    targetSignal = step["config"]["targetRecording"]
    labelSignal = step["config"]["labelRecording"]

    step["config"]["frequencyRangeStart"] = float(step["config"]["frequencyRangeStart"])
    step["config"]["frequencyRangeEnd"] = float(step["config"]["frequencyRangeEnd"])
    step["config"]["averageDuration"] = float(step["config"]["averageDuration"])
    
    def processRawData(RawData):
        return RawData

    ProcessedData = []
    LabeledData = []
    for recordingId in RecordingIds:
        if Configuration["Descriptor"][recordingId]["Type"] == targetSignal:
            if models.ExternalRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            elif models.NeuralActivityRecording.objects.filter(recording_id=recordingId).exists():
                recording = models.NeuralActivityRecording.objects.filter(recording_id=recordingId).first()
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)

            RawData = processRawData(RawData=RawData)
            ProcessedData.append(RawData)
        
    for result in Results:
        if result["ResultLabel"] == targetSignal:
            recording = models.ExternalRecording.objects.filter(recording_id=result["ProcessedData"]).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            for i in range(len(RawData)):
                RawData[i] = processRawData(RawData=RawData[i])
                ProcessedData.append(RawData[i])
            
    ResultData = {"ResultType": "NarrowBandFeatures", "Time": [], "Channel": [], "NarrowBandPower": [], "NarrowBandFrequency": []}
    for i in range(len(ProcessedData)):
        if type(ProcessedData[i]["ChannelNames"]) == str:
            ProcessedData[i]["ChannelNames"] = [ProcessedData[i]["ChannelNames"]]

        if type(ProcessedData[i]["Spectrogram"]) == dict:
            ProcessedData[i]["Spectrogram"] = [ProcessedData[i]["Spectrogram"]]
            
        for j in range(len(ProcessedData[i]["Spectrogram"])):
            Spectrogram = np.array(ProcessedData[i]["Spectrogram"][j]["logPower"])
            Frequency = np.array(ProcessedData[i]["Spectrogram"][j]["Frequency"])
            FrequencyBand = PythonUtility.rangeSelection(Frequency, [step["config"]["frequencyRangeStart"],step["config"]["frequencyRangeEnd"]])
            
            Timestamp = ProcessedData[i]["Spectrogram"][j]["Time"]
            PeakPower = np.zeros(len(ProcessedData[i]["Spectrogram"][j]["Time"]))
            PeakFrequency = np.zeros(len(ProcessedData[i]["Spectrogram"][j]["Time"]))
            
            for t in range(len(ProcessedData[i]["Spectrogram"][j]["Time"])):
                maxIndex = np.argmax(Spectrogram[FrequencyBand,t])
                PeakFreq = Frequency[FrequencyBand][maxIndex]
                NarrowBand = [PeakFreq-5, PeakFreq+5]
                if NarrowBand[1] > step["config"]["frequencyRangeEnd"]:
                    NarrowBand[1] = step["config"]["frequencyRangeEnd"]
                NarrowBandSelection = PythonUtility.rangeSelection(Frequency, NarrowBand)
                #coe = np.polyfit(Frequency[NarrowBandSelection], Spectrogram[NarrowBandSelection, t], 1)
                #fit = np.poly1d(coe)
                #GammaSelection = Spectrogram[NarrowBandSelection, t] - fit(Frequency[NarrowBandSelection])

                GammaSelection = Spectrogram[NarrowBandSelection, t]
                index = np.argmax(GammaSelection)
                PeakWindow = PythonUtility.rangeSelection(np.arange(len(GammaSelection)), [index-3,index+3])
                PeakHeight = np.mean(GammaSelection[PeakWindow]) - np.mean(GammaSelection[~PeakWindow])
                
                PeakPower[t] = PeakHeight 
                PeakFrequency[t] = PeakFreq
                
            ProcessedData[i]["Spectrogram"][j]["Power"] = 10*np.log10(ProcessedData[i]["Spectrogram"][j]["Power"])
            if ProcessedData[i]["ChannelNames"][j].strip() in ResultData["Channel"]:
                for i in range(len(ResultData["Channel"])):
                    if ResultData["Channel"][i] == ProcessedData[i]["ChannelNames"][j].strip():
                        ResultData["Time"][i].extend(Timestamp.tolist())
                        ResultData["NarrowBandPower"][i].extend(PeakPower.tolist())
                        ResultData["NarrowBandFrequency"][i].extend(PeakFrequency.tolist())
            else:
                ResultData["Channel"].append(ProcessedData[i]["ChannelNames"][j].strip())
                ResultData["Time"].append(Timestamp.tolist())
                ResultData["NarrowBandPower"].append(PeakPower.tolist())
                ResultData["NarrowBandFrequency"].append(PeakFrequency.tolist())
    

    recording = createResultDataFile(ResultData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))

    return {
        "ResultLabel": step["config"]["output"],
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": "NarrowBandFeatures"
    }

def handleExportStructure(step, RecordingIds, Configuration, analysis):
    ProcessedData = []
    for recordingId in RecordingIds:
        if models.ExternalRecording.objects.filter(recording_id=recordingId).exists():
            recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
        elif models.NeuralActivityRecording.objects.filter(recording_id=recordingId).exists():
            recording = models.NeuralActivityRecording.objects.filter(recording_id=recordingId).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
        
        RawData["ResultType"] = "AlignedData"
        RawData["DataType"] = Configuration["Descriptor"][recordingId]["Type"]
        for i in range(len(RawData["ChannelNames"])):
            if RawData["ChannelNames"][i] in Configuration["Descriptor"][recordingId]["Channels"].keys():
                RawData["ChannelNames"][i] = Configuration["Descriptor"][recordingId]["Channels"][RawData["ChannelNames"][i]]["name"]
        RawData["Time"] = (np.arange(RawData["Data"].shape[0])/RawData["SamplingRate"]) + RawData["StartTime"] + (Configuration["Descriptor"][recordingId]["TimeShift"]/1000)
        ProcessedData.append(RawData)

    recording = createResultMATFile({"ProcessedData": ProcessedData}, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))
    return {
        "ResultLabel": step["config"]["output"] + ".mat",
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": "AlignedData"
    }

def handleViewRecordings(step, RecordingIds, Results, Configuration, analysis):
    targetSignal = step["config"]["targetRecording"]
    ProcessedData = []
    for result in Results:
        if result["ResultLabel"] == targetSignal:
            recording = models.ExternalRecording.objects.filter(recording_id=result["ProcessedData"]).first()
            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
            if result["Type"] == "RawPSDs":
                for channelName in RawData.keys():
                    if channelName == "ResultType":
                        continue
                    for event in RawData[channelName].keys():
                        RawData[channelName][event]["MeanPower"] = np.nanmean(np.array(RawData[channelName][event]["PSDs"]), axis=0)
                        RawData[channelName][event]["StdPower"] = SPU.stderr(np.array(RawData[channelName][event]["PSDs"]), axis=0)
                RawData["ResultType"] = "PSDs"
            ProcessedData.append(RawData)
            
    recording = createResultDataFile(ProcessedData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
    analysis.recording_type.append(recording.recording_type)
    analysis.recording_list.append(str(recording.recording_id))
    return {
        "ResultLabel": step["config"]["output"],
        "Id": step["id"],
        "ProcessedData": str(recording.recording_id),
        "Type": "VisualizationData"
    }

def processAnalysis(user, analysisId):
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId).first()
    if not analysis:
        return "Permission Error"
    
    Configuration = loadAnalysisConfiguration(user, str(analysis.device_deidentified_id), analysisId)
    RecordingIds = Configuration["Descriptor"].keys()

    if "Results" in Configuration.keys():
        for k in range(len(Configuration["Results"])):
            if "ProcessedData" in Configuration["Results"][k].keys():
                removeResultDataFile(Configuration["Results"][k]["ProcessedData"])
                index = [i for i in range(len(analysis.recording_list)) if analysis.recording_list[i] == Configuration["Results"][k]["ProcessedData"]]
                if len(index) > 0:
                    del(analysis.recording_type[index[0]])
                    del(analysis.recording_list[index[0]])
                analysis.save()

    Results = []
    for i in range(len(Configuration["AnalysisSteps"])):
        step = Configuration["AnalysisSteps"][i]
        try:
            if step["type"]["value"] == "filter":
                Result = handleFilterProcessing(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
            elif step["type"]["value"] == "cardiacFilter":
                Result = handleCardiacFilterProcessing(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
            elif step["type"]["value"] == "wienerFilter":
                Result = handleWienerFilterProcessing(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
            elif step["type"]["value"] == "export":
                Result = handleExportStructure(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
            elif step["type"]["value"] == "extractTimeFrequencyAnalysis":
                Result = handleExtractTimeFrequencyAnalysis(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
            elif step["type"]["value"] == "extractAnnotations":
                Result = handleExtractAnnotationPSDs(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
            elif step["type"]["value"] == "calculateSpectralFeatures":
                Result = handleCalculateSpectralFeatures(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
            elif step["type"]["value"] == "extractNarrowBandFeature":
                Result = handleExtractNarrowBandFeature(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
            elif step["type"]["value"] == "normalize":
                Result = handleNormalizeProcessing(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
            elif step["type"]["value"] == "view":
                Result = handleViewRecordings(step, RecordingIds, Results, Configuration, analysis)
                Results.append(Result)
                
        except Exception as e:
            print(e)
            Results.append({
                "ResultLabel": step["config"]["output"],
                "Id": step["id"],
                "ErrorMessage": str(e)
            })

    Configuration["Results"] = Results
    saveAnalysisConfiguration(Configuration, user, str(analysis.device_deidentified_id), analysis.deidentified_id)
    analysis.analysis_date = datetime.now().astimezone(pytz.utc)
    analysis.save()

    return Results