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
import websocket
from scipy import signal

from Backend import models
from modules import Database
from modules.Percept import BrainSenseStream

from utility import PythonUtility

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

        recordings = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id).all()
        for recording in recordings:
            if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
                continue
            
            # Currently does not support BrainSense Survey unless new analysis is designed around it
            if recording.recording_type == "BrainSenseSurvey":
                continue
            
            if not "Channel" in recording.recording_info.keys() and not recording.recording_type == "ChronicLFPs":
                RecordingData = Database.loadSourceDataPointer(recording.recording_datapointer)
                recording.recording_info = {
                    "Channel": RecordingData["ChannelNames"]
                }
                recording.save()
            
            AvailableRecordings.append({
                "RecordingId": recording.recording_id,
                "RecordingType": recording.recording_type,
                "RecordingChannels": recording.recording_info["Hemisphere"].replace("HemisphereLocationDef.","") if recording.recording_type == "ChronicLFPs" else recording.recording_info["Channel"],
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
    if models.BrainSenseRecording.objects.filter(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)}).exists():
        recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)}).first()
        filename = Database.saveSourceFiles(Data, "AnalysisConfiguration", "Raw", recording.recording_id, recording.device_deidentified_id)
    else:
        recording = models.BrainSenseRecording(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)})
        filename = Database.saveSourceFiles(Data, "AnalysisConfiguration", "Raw", recording.recording_id, recording.device_deidentified_id)
        recording.recording_datapointer = filename
        recording.save()
    return recording

def loadAnalysisConfiguration(user, patientId, analysisId):
    analysisConfig = models.BrainSenseRecording.objects.filter(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)}).first()
    Data = Database.loadSourceDataPointer(analysisConfig.recording_datapointer)
    return Data

def deleteAnalysisConfiguration(user, patientId, analysisId):
    analysisConfig = models.BrainSenseRecording.objects.filter(device_deidentified_id=patientId, recording_type="AnalysisConfiguration", recording_info={"Creator": str(user.unique_user_id), "Analysis": str(analysisId)}).first()
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

def addRecordingToAnalysis(user, patientId, analysisId, recordingId, authority):
    if not authority["Permission"]:
        return None
    
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId, device_deidentified_id=patientId).first()
    if not analysis:
        return None
    
    if recordingId in analysis.recording_list:
        return None

    isExternalRecording = False
    recording = models.BrainSenseRecording.objects.filter(recording_id=recordingId).first()
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
            "Type": "Signal",
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
                    "Type": "Signal",
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

def getRawRecordingData(user, patientId, analysisId, recordingId, authority):
    if not authority["Permission"]:
        return None
    
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=analysisId, device_deidentified_id=patientId).first()
    if not analysis:
        return None
    
    if not recordingId in analysis.recording_list:
        return None

    isExternalRecording = False
    recording = models.BrainSenseRecording.objects.filter(recording_id=recordingId).first()
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

def queryResultData(user, patientId, analysisId, resultId, authority):
    analysis = models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=patientId, deidentified_id=analysisId).first()
    if not analysis:
        return None
    
    recording = models.ExternalRecording.objects.filter(patient_deidentified_id=patientId,  recording_type="AnalysisOutput",  recording_id=resultId).first()
    if not recording:
        return None
    
    ProcessedData = Database.loadSourceDataPointer(recording.recording_datapointer)
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

    return ProcessedData, GraphOptions
    
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
    for step in Configuration["AnalysisSteps"]:
        try:
            if step["type"]["value"] == "filter":
                targetSignal = step["config"]["targetRecording"]
                filterType = "Butterworth"

                if step["config"]["highpass"] == "":
                    step["config"]["highpass"] = "0"
                elif step["config"]["lowpass"] == "":
                    step["config"]["lowpass"] = "0"

                highpass = float(step["config"]["highpass"])
                lowpass = float(step["config"]["lowpass"])

                ProcessedData = []
                for recordingId in RecordingIds:
                    if Configuration["Descriptor"][recordingId]["Type"] == targetSignal:
                        if models.ExternalRecording.objects.filter(recording_id=recordingId).exists():
                            recording = models.ExternalRecording.objects.filter(recording_id=recordingId).first()
                            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
                        elif models.BrainSenseRecording.objects.filter(recording_id=recordingId).exists():
                            recording = models.BrainSenseRecording.objects.filter(recording_id=recordingId).first()
                            RawData = Database.loadSourceDataPointer(recording.recording_datapointer)

                        if highpass == 0:
                            [b,a] = signal.butter(5, np.array([lowpass])*2/RawData["SamplingRate"], 'lp', output='ba')
                        elif lowpass == 0:
                            [b,a] = signal.butter(5, np.array([highpass])*2/RawData["SamplingRate"], 'hp', output='ba')
                        else:
                            [b,a] = signal.butter(5, np.array([highpass, lowpass])*2/RawData["SamplingRate"], 'bp', output='ba')

                        RawData["Data"] = signal.filtfilt(b, a, RawData["Data"], axis=0)
                        RawData["ResultType"] = "TimeDomain"
                        ProcessedData.append(RawData)

                recording = createResultDataFile(ProcessedData, str(analysis.device_deidentified_id), "AnalysisOutput", 0)
                analysis.recording_type.append(recording.recording_type)
                analysis.recording_list.append(str(recording.recording_id))

                Results.append({
                    "ResultLabel": step["config"]["output"],
                    "Id": step["id"],
                    "ProcessedData": str(recording.recording_id),
                    "Type": "TimeDomain"
                })
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