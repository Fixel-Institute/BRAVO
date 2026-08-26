""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Medtronic Percept BrainSense Event Logs Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os
from datetime import datetime
import copy
import numpy as np
import pandas as pd

from modules import Therapy, Database
from modules.utility.PythonUtility import rangeSelection

key = os.environ.get('DATASERVER_ENCRYPTION')

def saveChronicBrainSense(ChronicLFPs):
    """ Save Chronic BrainSense Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      ChronicLFPs: Chronic BrainSense (Power-band) structures extracted from Medtronic JSON file.
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """

    NewRecordings = []
    for key in ChronicLFPs.keys():
        if key == "HemisphereLocationDef.Right": 
            hemisphere = "RightHemisphere"
        else:
            hemisphere = "LeftHemisphere"

        Time = np.array([t.timestamp() for t in ChronicLFPs[key]["DateTime"]])
        Amplitude = ChronicLFPs[key]["Amplitude"]
        LFP = ChronicLFPs[key]["LFP"]

        Recording = dict()
        Recording["SamplingRate"] = -1 # Variable Frequency
        Recording["Time"] = Time
        Recording["Data"] = np.zeros((len(Recording["Time"]),2))
        Recording["Data"][:,0] = LFP
        Recording["Data"][:,1] = Amplitude
        Recording["ChannelNames"] = [hemisphere + " LFP", hemisphere + " Amplitude"]
        Recording["StartTime"] = Recording["Time"][0]
        Recording["Duration"] = Recording["Time"][-1] - Recording["Time"][0]
        NewRecordings.append(Recording)

    return NewRecordings

def extractTherapyString(note):
    try:
        TherapyString = str(int(note["Stimulation"]["Frequency"])) + "Hz " + str(int(note["Stimulation"]["Pulsewidth"])) + "" + note["Stimulation"]["PulsewidthUnit"]

        if note["Stimulation"]["ReturnContact"] == ["CAN"]:
            TherapyString += " [" + "|".join(note["Stimulation"]["Contact"]) + "]"
        else:
            TherapyString += " [" + " ".join(note["Stimulation"]["Contact"]) + " => " + " ".join(note["Stimulation"]["ReturnContact"]) + "]"
        return TherapyString
    except Exception as e:
        return "Unknown"
    
def extractSensingString(note):
    try:
        if "Bypass" in note["Adaptive"]["StimulationConfiguration"]["Config"].keys():
            return str(note["Adaptive"]["RecordingConfiguration"]["Config"]["SensingSetup"]["FrequencyInHertz"]) + "Hz Bypassed"
        else:
            return str(note["Adaptive"]["RecordingConfiguration"]["Config"]["SensingSetup"]["FrequencyInHertz"]) + "Hz"
    except Exception as e:
        return "Unknown"

def checkExistingSegments(segments, params):
    for i in range(len(segments)):
        if segments[i]["TherapyWindow"] == params["TherapyWindow"]:
            if segments[i]["TherapyNote"] == params["TherapyNote"]:
                if segments[i]["RecordingString"] == params["RecordingString"]:
                    if segments[i]["Device"] == params["Device"]:
                        if segments[i]["ChannelNames"] == params["ChannelNames"]:
                            return i
    return -1

def extractChronicNeuralActivity(participant, devices, recordings, config):
    DBSDeviceDict = {}
    for i in range(len(devices)):
        if not devices[i].serial_number in DBSDeviceDict.keys():
            DBSDeviceDict[devices[i].serial_number] = []
        DBSDeviceDict[devices[i].serial_number].append(devices[i])

    TherapyHistory = Therapy.queryTherapyHistory(participant)
    TherapyTimeline = Therapy.createTherapyTimeline(TherapyHistory)

    Sources = []
    for i in range(len(recordings)):
        if not recordings[i].source in Sources:
            Sources.append(recordings[i].source)

    ChronicNeuralActivity = []
    for key in DBSDeviceDict.keys():
        LeadCount = 0
        DBSDeviceIds = []
        for i in range(len(DBSDeviceDict[key])):
            DeviceInfoTemp = DBSDeviceDict[key][i].get_info()
            DBSDeviceIds.append(DeviceInfoTemp["Id"])
            if len(DeviceInfoTemp["Electrodes"]) > LeadCount:
                LeadCount = len(DeviceInfoTemp["Electrodes"])
                DBSDevice = {**DeviceInfoTemp}
        
        for i in range(len(TherapyHistory["TherapyModification"])):
            if TherapyHistory["TherapyModification"][i]["Device"]["Id"] in DBSDeviceIds:
                TherapyHistory["TherapyModification"][i]["History"] = [x for x in TherapyHistory["TherapyModification"][i]["History"] if x["Type"] == "TherapyChangeGroup"]
                TherapyHistory["TherapyModification"][i]["History"].sort(key=lambda x: x["Date"])
                Timestamps = [event["Date"] for event in TherapyHistory["TherapyModification"][i]["History"]]
                GroupIds = [event["New"] for event in TherapyHistory["TherapyModification"][i]["History"]]
                TimelineTherapy = [event["Therapy"] if "Therapy" in event.keys() else None for event in TherapyHistory["TherapyModification"][i]["History"]]
        
        TimelineSegments = []
        for recording in recordings:
            if not recording.source.metadata["Device"] in DBSDeviceIds:
                continue
            
            Data = Database.loadSourceFile(recording.pointer, recording.hashed)
            for i in range(len(Timestamps)):
                DataSelected = (Data["Time"] > Timestamps[i])
                if i < len(Timestamps) - 1:
                    DataSelected = DataSelected & (Data["Time"] < Timestamps[i+1] + 3)
                    
                if np.any(DataSelected):
                    TherapyNote = TimelineTherapy[i]
                    BrainSenseSegment = {
                        "RecordingId": recording.uid,
                        "Device": recording.source.metadata["Device"],
                        "ChannelNames": Data["ChannelNames"],
                        "Data": Data["Data"][DataSelected,:],
                        "Time": Data["Time"][DataSelected],
                        "TherapyStartTime": Timestamps[i],
                        "GroupId": GroupIds[i],
                        "TherapyNote": TherapyNote
                    }
                    TimelineSegments.append(BrainSenseSegment)
        
        TimelineSegments = sorted(TimelineSegments, key=lambda x: x["TherapyStartTime"])
        for i in range(len(Timestamps)):
            AvailableData = [TimelineSegments[j] for j in range(len(TimelineSegments)) if TimelineSegments[j]["TherapyStartTime"] == Timestamps[i]]
            if len(AvailableData) > 0:
                TimelineDataframe = pd.DataFrame({"Time": []})
                for j in range(len(AvailableData)):
                    AvailableData[j]["StartTime"] = AvailableData[j]["Time"][0]
                    RecordingDF = {"Time": AvailableData[j]["Time"]}
                    for k in range(len(AvailableData[j]["ChannelNames"])):
                        if not AvailableData[j]["ChannelNames"][k] in TimelineDataframe.columns:
                            TimelineDataframe[AvailableData[j]["ChannelNames"][k]] = np.nan
                        RecordingDF[AvailableData[j]["ChannelNames"][k]] = AvailableData[j]["Data"][:,k]
                    RecordingDF = pd.DataFrame(RecordingDF)
                    TimelineDataframe = pd.concat([TimelineDataframe, pd.DataFrame(RecordingDF)], ignore_index=True)
                    
                TimelineDataframe.drop_duplicates(inplace=True)
                TimelineDataframe = TimelineDataframe.groupby("Time", as_index=False).first()
                TimelineDataframe.sort_values(by="Time", inplace=True)
                TimelineDataframe.reset_index(inplace=True, drop=True)
                ChannelNames = list(TimelineDataframe.columns)
                ChannelNames.remove("Time")

                TherapyList = []
                for j in range(len(ChannelNames)):
                    TherapyNote = TimelineTherapy[i]
                    TherapyList.append(TherapyNote)
                
                for j in range(len(TherapyList)):
                    if TherapyList[j] is None:
                        TherapyList[j] = {"Stimulation": {}, "Adaptive": {}}
                    else:
                        leadId = -1
                        for k in range(len(TherapyList[j]["Electrodes"])):
                            indexToInclude = []
                            for l in range(len(TherapyList[j]["Stimulation"][k])):
                                if TherapyList[j]["Stimulation"][k][l]["Electrode"]["Target"] == TherapyList[j]["Electrodes"][k]["Target"]:
                                    indexToInclude.append(l)
                            TherapyList[j]["Stimulation"][k] = [TherapyList[j]["Stimulation"][k][m] for m in indexToInclude]
                            TherapyList[j]["Adaptive"][k] = [TherapyList[j]["Adaptive"][k][m] for m in indexToInclude]

                            if ChannelNames[j].startswith("LeftHemisphere") and TherapyList[j]["Electrodes"][k]["Target"].startswith("Left"):
                                leadId = k
                            elif ChannelNames[j].startswith("RightHemisphere") and TherapyList[j]["Electrodes"][k]["Target"].startswith("Right"):
                                leadId = k
                        
                        if leadId >= 0 and len(TherapyList[j]["Stimulation"][leadId]) > 0:
                            TherapyList[j] = {
                                "Stimulation": TherapyList[j]["Stimulation"][leadId],
                                "Adaptive": TherapyList[j]["Adaptive"][leadId][0]
                            }
                        else:
                            TherapyList[j] = {"Stimulation": {}, "Adaptive": {}}

                Activity = {
                    "Device": AvailableData[0]["Device"],
                    "TherapyStartTime": Timestamps[i],
                    "Description": [],
                    "TherapyNote": TherapyList,
                    "TherapyString": [extractTherapyString(therapy) if len(therapy.keys()) > 0 else "Unknown" for therapy in TherapyList ],
                    "RecordingString": [extractSensingString(therapy) if len(therapy.keys()) > 0 else "Unknown" for therapy in TherapyList ],
                    "Time": TimelineDataframe["Time"].tolist(),
                    "ChannelNames": copy.deepcopy(ChannelNames),
                    "ChannelNamesFix": copy.deepcopy(ChannelNames),
                    "ChannelUnits": ["" if x.endswith("LFP") else "mA" for x in ChannelNames],
                    "Data": TimelineDataframe[ChannelNames].to_numpy(copy=True).T
                }

                for k in range(len(Activity["ChannelNames"])):
                    mean = np.nanmean(Activity["Data"][k,:])
                    std = np.nanstd(Activity["Data"][k,:])
                    
                    counter = 0
                    while True:
                        counter += 1
                        outlier_idx = np.where(Activity["Data"][k,:] > mean + 6*std)[0]
                        if len(outlier_idx) == 0 or counter > 10:
                            break
                        
                        for idx in outlier_idx:
                            if 0 < idx < len(Activity["Data"][k,:]) - 1:
                                Activity["Data"][k,idx] = np.nanmean([Activity["Data"][k,idx-1], Activity["Data"][k,idx+1]])
                            elif idx == 0:
                                Activity["Data"][k,idx] = Activity["Data"][k,idx+1]
                            else:
                                Activity["Data"][k,idx] = Activity["Data"][k,idx-1]

                for lead in DBSDevice["Electrodes"]:
                    for k in range(len(Activity["ChannelNames"])):
                        if Activity["ChannelNames"][k].startswith("LeftHemisphere") and lead["Target"].startswith("Left"):
                            Activity["ChannelNamesFix"][k] = Activity["ChannelNames"][k].replace("LeftHemisphere", lead["CustomName"])
                        elif Activity["ChannelNames"][k].startswith("RightHemisphere") and lead["Target"].startswith("Right"):
                            Activity["ChannelNamesFix"][k] = Activity["ChannelNames"][k].replace("RightHemisphere", lead["CustomName"])

                for k in range(len(Activity["ChannelNames"])):
                    Description = {}
                    Description["Stimulation"] = Activity["TherapyString"][k]
                    if "Adaptive" in TherapyList[k].keys():
                        if "RecordingConfiguration" in TherapyList[k]["Adaptive"].keys():
                            if "SensingSetup" in TherapyList[k]["Adaptive"]["RecordingConfiguration"]["Config"].keys():
                                if "FrequencyInHertz" in TherapyList[k]["Adaptive"]["RecordingConfiguration"]["Config"]["SensingSetup"].keys():
                                    Description["Bypass"] = False
                                    Description["SensingFrequency"] = str(TherapyList[k]["Adaptive"]["RecordingConfiguration"]["Config"]["SensingSetup"]["FrequencyInHertz"]) + " Hz"
                                    if "Bypass" in TherapyList[k]["Adaptive"]["StimulationConfiguration"]["Config"].keys():
                                        Description["Bypass"] = True

                    Activity["Description"].append(Description)

                ChronicNeuralActivity.append(Activity)

    return ChronicNeuralActivity

def revertChronicActivityFormat(data):
    Recording = dict()
    Recording["SamplingRate"] = -1 # Variable Frequency
    Recording["Time"] = data["Time"]
    Recording["Data"] = data["Data"].T
    Recording["ChannelNames"] = data["ChannelNamesFix"]
    Recording["StartTime"] = Recording["Time"][0]
    Recording["Duration"] = Recording["Time"][-1] - Recording["Time"][0]
    return Recording