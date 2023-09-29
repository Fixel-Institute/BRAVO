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
Chronic BrainSense Processing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from calendar import c
import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(os.environ.get("PYTHON_UTILITY"))

import json
import uuid
import numpy as np
import copy
from shutil import copyfile, rmtree
from datetime import datetime, date, timedelta
import dateutil, pytz
import pickle, joblib
import pandas as pd

from scipy import signal, stats, optimize, interpolate

from decoder import Percept
from utility import SignalProcessingUtility as SPU
from utility.PythonUtility import *

from Backend import models
from modules import Database

key = os.environ.get('ENCRYPTION_KEY')

def saveChronicLogs(deviceID, ChronicLogs, sourceFile):
    """ Save Chronic BrainSense Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      ChronicLFPs: Chronic BrainSense (Power-band) structures extracted from Medtronic JSON file.
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """
    ChronicLogTimestamp = []
    ChronicLogState = []
    for log in ChronicLogs:
        if log["Payload"]["ID"] == "AdaptiveTherapyStateChange":
            ChronicLogTimestamp.append(log["Timestamp"])
            ChronicLogState.append(log["Payload"]["AdaptiveTherapy"]["NewState"])
    ChronicLogTimestamp = np.array(ChronicLogTimestamp)
    ChronicLogState = np.array(ChronicLogState)
    
    NewRecordingFound = False
    recording_info = {"Hemisphere": "AllHemisphere"}
    if not models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="SummitChronicLogs", recording_info__Hemisphere=recording_info["Hemisphere"]).exists():
        sortedIndex = np.argsort(ChronicLogTimestamp,axis=0).flatten()
        ChronicLogTimestamp = ChronicLogTimestamp[sortedIndex]
        ChronicLogState = ChronicLogState[sortedIndex]
        
        recording = models.BrainSenseRecording(device_deidentified_id=deviceID, recording_type="SummitChronicLogs", recording_info=recording_info)
        filename = Database.saveSourceFiles({
            "ChronicLogs": {
                "DateTime": ChronicLogTimestamp,
                "State": ChronicLogState,
            }
        }, "SummitChronicLogs", "SummitRCS", recording.recording_id, recording.device_deidentified_id)
        recording.recording_datapointer = filename
        recording.save()
        NewRecordingFound = True
    else:
        recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="SummitChronicLogs", recording_info__Hemisphere=recording_info["Hemisphere"]).first()
        ChronicData = Database.loadSourceDataPointer(recording.recording_datapointer)

        Common = set(ChronicLogTimestamp) & set(ChronicData["ChronicLogs"]["DateTime"])

        toInclude = np.zeros(len(ChronicLogTimestamp), dtype=bool)
        IndexToInclude = list()
        for i in range(len(ChronicLogTimestamp)):
            if not ChronicLogTimestamp[i] in Common:
                toInclude[i] = True

        if np.any(toInclude):
            ChronicData["ChronicLogs"]["DateTime"] = np.concatenate((ChronicData["ChronicLogs"]["DateTime"], ChronicLogTimestamp[toInclude]),axis=0)
            ChronicData["ChronicLogs"]["State"] = np.concatenate((ChronicData["ChronicLogs"]["State"], ChronicLogState[toInclude]),axis=0)
            
            sortedIndex = np.argsort(ChronicData["ChronicLogs"]["DateTime"],axis=0).flatten()
            ChronicData["ChronicLogs"]["DateTime"] = ChronicData["ChronicLogs"]["DateTime"][sortedIndex]
            ChronicData["ChronicLogs"]["State"] = ChronicData["ChronicLogs"]["State"][sortedIndex]
            filename = Database.saveSourceFiles({
                "ChronicLogs": ChronicData["ChronicLogs"]
            }, "SummitChronicLogs", "SummitRCS", recording.recording_id, recording.device_deidentified_id)
            
            NewRecordingFound = True

    return NewRecordingFound

def processPowerBand(device, ChronicLFPs):
    recordings = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type="SummitStreamingPower")
    PowerStreams = {}
    for recording in recordings:
        PowerStream = Database.loadSourceDataPointer(recording.recording_datapointer)
        if not "LfpConfig" in PowerStream["Descriptor"].keys():
            continue
        
        PowerStream["Time"] = np.arange(PowerStream["Data"].shape[0])/PowerStream["SamplingRate"] + PowerStream["StartTime"]
        for i in range(len(PowerStream["Descriptor"]["PowerBands"])):
            FrequencyResolution = PowerStream["Descriptor"]["LfpConfig"][int(i/2)]["SamplingRate"] / PowerStream["Descriptor"]["NFFT"]
            if i < 4:
                ChannelNames = "Left " + PowerStream["Descriptor"]["LfpConfig"][int(i/2)]["Channels"][0] + "-" + PowerStream["Descriptor"]["LfpConfig"][int(i/2)]["Channels"][1]
            else:
                ChannelNames = "Right " + PowerStream["Descriptor"]["LfpConfig"][int(i/2)]["Channels"][0] + "-" + PowerStream["Descriptor"]["LfpConfig"][int(i/2)]["Channels"][1]
            #ChannelNames += f" {PowerStream['ChannelNames'][i]}"
            ChannelNames += f" {PowerStream['Descriptor']['PowerBands'][i][0]*FrequencyResolution:.2f}-{PowerStream['Descriptor']['PowerBands'][i][1]*FrequencyResolution:.2f} Hz"
            
            if not ChannelNames in PowerStreams.keys():
                if i < 4:
                    PowerStreams[ChannelNames] = {"Hemisphere": "Left", "PowerBand": PowerStream['ChannelNames'][i], "Power": np.array((0,1)), "Time": np.array((0,1))}
                else:
                    PowerStreams[ChannelNames] = {"Hemisphere": "Right", "PowerBand": PowerStream['ChannelNames'][i], "Power": np.array((0,1)), "Time": np.array((0,1))}
            PowerStreams[ChannelNames]["Power"] = np.concatenate((PowerStreams[ChannelNames]["Power"], PowerStream["Data"][:,i]))
            PowerStreams[ChannelNames]["Time"] = np.concatenate((PowerStreams[ChannelNames]["Time"], PowerStream["Time"]))
    
    for key in PowerStreams.keys():
        SortIndex = np.argsort(PowerStreams[key]["Time"])
        PowerStreams[key]["Time"] = PowerStreams[key]["Time"][SortIndex]
        PowerStreams[key]["Power"] = PowerStreams[key]["Power"][SortIndex]

        NewTimestamp = []
        SmoothPower = []
        i = 0
        while i < len(PowerStreams[key]["Time"]):
            TimeSelection = rangeSelection(PowerStreams[key]["Time"], [PowerStreams[key]["Time"][i]-60, PowerStreams[key]["Time"][i]+60], "inclusive")
            SmoothPower.append(np.mean(PowerStreams[key]["Power"][TimeSelection]))
            NewTimestamp.append(PowerStreams[key]["Time"][SortIndex[i]])
            i = np.where(TimeSelection)[0][-1]+1

        PowerStreams[key]["Power"] = np.array(SmoothPower)
        PowerStreams[key]["Time"] = np.array(NewTimestamp)

    ChronicLFPs["PowerBand"] = PowerStreams
    return ChronicLFPs

def queryChronicLFPs(user, patientUniqueID, TherapyHistory, authority):
    """ Query Chronic LFPs based on Therapy History.

    This function will query Chronic BrainSense Power Band data and Event PSDs based on therapy change logs.
    This design is made because a change in therapy group may lead to different therapy effect or BrainSense configurations.

    Args:
      user: BRAVO Platform User object. 
      patientUniqueID: Deidentified patient ID as referenced in SQL Database. 
      TherapyHistory: List of therapy change logs ordered by time extracted from ``Therapy.queryTherapyHistory``. 
      authority: User permission structure indicating the type of access the user has.

    Returns:
      Returns a list of LFPTrends, where each LFPTrends are continuous BrainSense Power with the same therapy configurations. 
    """

    LFPTrends = list()
    if not authority["Permission"]:
        return LFPTrends
    
    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    PowerBandIndex = []

    for device in availableDevices:
        leads = device.device_lead_configurations
        recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type="SummitChronicLogs", recording_info__Hemisphere="AllHemisphere").first()
        if not recording == None:
            ChronicLFPs = Database.loadSourceDataPointer(recording.recording_datapointer)

            if not "PowerBand" in ChronicLFPs.keys():
                ChronicLFPs = processPowerBand(device, ChronicLFPs)
                Database.saveSourceFiles(ChronicLFPs, "SummitChronicLogs", "SummitRCS", recording.recording_id, recording.device_deidentified_id)

            ChronicLFPChannels = ChronicLFPs["PowerBand"].keys()
            for Channel in ChronicLFPChannels:
                if not (str(device.deidentified_id) + ChronicLFPs["PowerBand"][Channel]["PowerBand"]) in PowerBandIndex:
                    PowerBandIndex.append(str(device.deidentified_id) + ChronicLFPs["PowerBand"][Channel]["PowerBand"])
                    if device.device_name == "":
                        LFPTrends.append({"Device": str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key), "DeviceLocation": device.device_location})
                    else:
                        LFPTrends.append({"Device": device.device_name, "DeviceLocation": device.device_location})
                    index = len(PowerBandIndex)-1
                    
                    LFPTrends[index]["Timestamp"] = list()
                    LFPTrends[index]["Power"] = list()
                    LFPTrends[index]["AdaptiveTimestamp"] = list()
                    LFPTrends[index]["Amplitude"] = list()
                    LFPTrends[index]["Therapy"] = list()
                    LFPTrends[index]["EventName"] = list()
                    LFPTrends[index]["EventTime"] = list()
                    LFPTrends[index]["EventPower"] = list()
                else:
                    index = PowerBandIndex.index(str(device.deidentified_id) + ChronicLFPs["PowerBand"][Channel]["PowerBand"])
                
                for lead in leads:
                    if lead["TargetLocation"].startswith(ChronicLFPs["PowerBand"][Channel]["Hemisphere"]):
                        LFPTrends[index]["Hemisphere"] = lead["TargetLocation"]
                        LFPTrends[index]["CustomName"] = lead["CustomName"] + " " + ChronicLFPs["PowerBand"][Channel]["PowerBand"]
                
                Hemisphere = LFPTrends[index]["Hemisphere"].split(" ")[0]
                LFPTimestamps = ChronicLFPs["PowerBand"][Channel]["Time"]
                LFPPowers = ChronicLFPs["PowerBand"][Channel]["Power"]
                StimulationTimestamps = ChronicLFPs["ChronicLogs"]["DateTime"]
                StimulationAmplitude = ChronicLFPs["ChronicLogs"]["State"]

                LFPTimestamps = np.array(LFPTimestamps)
                LFPPowers = np.array(LFPPowers)
                StimulationTimestamps = np.array(StimulationTimestamps)
                StimulationAmplitude = np.array(StimulationAmplitude, dtype=int)

                # Remove Outliers
                LFPSelection = np.abs(LFPPowers) <= (np.median(LFPPowers) + np.std(LFPPowers)*6)
                LFPTimestamps = LFPTimestamps[LFPSelection]
                LFPPowers = LFPPowers[LFPSelection]

                LFPTrends[index]["PowerRange"] = [0,0]

                for therapy in TherapyHistory:
                    if therapy["device"] == str(device.deidentified_id):
                        for i in range(len(therapy["date_of_change"])-1):
                            rangeSelected = rangeSelection(LFPTimestamps, [therapy["date_of_change"][i]/1000000000, therapy["date_of_change"][i+1]/1000000000])
                            if np.any(rangeSelected):
                                LFPTrends[index]["Timestamp"].append(LFPTimestamps[rangeSelected])
                                LFPTrends[index]["AdaptiveTimestamp"].append([])
                                FiltPower = np.array(LFPPowers[rangeSelected])
                                LFPTrends[index]["Power"].append(FiltPower.tolist())
                                LFPTrends[index]["Amplitude"].append([])
                                LFPTrends[index]["Therapy"].append(copy.deepcopy(therapy["therapy"][i]))
                                
                                LFPTrends[index]["Therapy"][-1]["TherapyOverview"] = Channel
                                    
                                if np.percentile(FiltPower,5) < LFPTrends[index]["PowerRange"][0]:
                                    LFPTrends[index]["PowerRange"][0] = np.percentile(FiltPower,5)
                                if np.percentile(FiltPower,95) > LFPTrends[index]["PowerRange"][1]:
                                    LFPTrends[index]["PowerRange"][1] = np.percentile(FiltPower,95)

                                LFPTrends[index]["EventName"].append([])
                                LFPTrends[index]["EventTime"].append([])
                                LFPTrends[index]["EventPower"].append([])
                                
                            rangeSelected = rangeSelection(StimulationTimestamps, [therapy["date_of_change"][i]/1000000000, therapy["date_of_change"][i+1]/1000000000])
                            if np.any(rangeSelected):
                                LFPTrends[index]["Timestamp"].append([])
                                LFPTrends[index]["Power"].append([])

                                StateDictionary = np.zeros(9)
                                if "Adaptive" in therapy["therapy"][i]["Therapy"].keys():
                                    if "Adaptive" in therapy["therapy"][i]["Therapy"]["Adaptive"].keys():
                                        if "State" in therapy["therapy"][i]["Therapy"]["Adaptive"]["Adaptive"].keys():
                                            if therapy["therapy"][i]["Therapy"]["Adaptive"]["Adaptive"]["Status"] == "EmbeddedActive":
                                                StateDictionary = []
                                                for j in range(9):
                                                    TherapyAmplitudes = np.array([therapy["therapy"][i]["Therapy"]["Adaptive"]["Adaptive"]["State"][j]["prog0AmpInMilliamps"], 
                                                                     therapy["therapy"][i]["Therapy"]["Adaptive"]["Adaptive"]["State"][j]["prog1AmpInMilliamps"],
                                                                     therapy["therapy"][i]["Therapy"]["Adaptive"]["Adaptive"]["State"][j]["prog2AmpInMilliamps"],
                                                                     therapy["therapy"][i]["Therapy"]["Adaptive"]["Adaptive"]["State"][j]["prog3AmpInMilliamps"]])
                                                    TherapyAmplitudes[TherapyAmplitudes > 25] = 0
                                                    StateDictionary.append(np.sum(TherapyAmplitudes))
                                                StateDictionary = np.array(StateDictionary)

                                TimestampRaw = StimulationTimestamps[rangeSelected]
                                AmplitudeRaw = StateDictionary[StimulationAmplitude[rangeSelected]]

                                SmoothWindow = 1800
                                NewTimestamp = np.arange(TimestampRaw[0], TimestampRaw[-1], SmoothWindow)
                                SmoothAmplitude = np.zeros(NewTimestamp.shape)
                                for j in range(len(NewTimestamp)):
                                    StartAmplitude = np.where(TimestampRaw <= NewTimestamp[j])[0][-1]
                                    EndAmplitude = np.where(TimestampRaw <= NewTimestamp[j]+SmoothWindow)[0][-1]
                                    AmplitudeAdjustmentSelection = rangeSelection(TimestampRaw, [NewTimestamp[j], NewTimestamp[j]+SmoothWindow])
                                    AmplitudeAdjustment = TimestampRaw[AmplitudeAdjustmentSelection]
                                    SelectedAmplitude = AmplitudeRaw[AmplitudeAdjustmentSelection]
                                    
                                    if len(AmplitudeAdjustment) == 0:
                                        SmoothAmplitude[j] = AmplitudeRaw[StartAmplitude]
                                    elif len(AmplitudeAdjustment) == 1:
                                        SmoothAmplitude[j] = AmplitudeRaw[StartAmplitude] * (AmplitudeAdjustment[0]-NewTimestamp[j]) + AmplitudeRaw[EndAmplitude] * (SmoothWindow-AmplitudeAdjustment[0]+NewTimestamp[j])
                                        SmoothAmplitude[j] /= SmoothWindow
                                    else:
                                        SmoothAmplitude[j] += AmplitudeRaw[StartAmplitude] * (AmplitudeAdjustment[0]-NewTimestamp[j])
                                        for k in range(1, len(AmplitudeAdjustment)):
                                            SmoothAmplitude[j] += SelectedAmplitude[k-1] * (AmplitudeAdjustment[k]-AmplitudeAdjustment[k-1])
                                        SmoothAmplitude[j] += AmplitudeRaw[EndAmplitude] * (SmoothWindow-AmplitudeAdjustment[-1]+NewTimestamp[j])
                                        SmoothAmplitude[j] /= SmoothWindow
                                        
                                LFPTrends[index]["AdaptiveTimestamp"].append(NewTimestamp+SmoothWindow/2)
                                LFPTrends[index]["Amplitude"].append(SmoothAmplitude)
                                LFPTrends[index]["Therapy"].append(copy.deepcopy(therapy["therapy"][i]))
                                if Hemisphere+'Hemisphere' in LFPTrends[index]['Therapy'][-1]['Therapy'].keys():
                                    LFPTrends[index]["Therapy"][-1]["TherapyOverview"] = f"{LFPTrends[index]['Therapy'][-1]['Therapy'][Hemisphere+'Hemisphere']['Frequency']}Hz {LFPTrends[index]['Therapy'][-1]['Therapy'][Hemisphere+'Hemisphere']['PulseWidth']}μSec @ {LFPTrends[index]['Therapy'][-1]['Therapy']['Programs'][0]['Electrode']}"
                                else:
                                    LFPTrends[index]["Therapy"][-1]["TherapyOverview"] = "Therapy Unavailable"

                                LFPTrends[index]["EventName"].append([])
                                LFPTrends[index]["EventTime"].append([])
                                LFPTrends[index]["EventPower"].append([])

                ChronicLFPs["ChronicLogs"]["DateTime"] = np.array([])
                ChronicLFPs["ChronicLogs"]["State"] = np.array([])
                
    return LFPTrends

def processChronicLFPs(LFPTrends, timezoneOffset=0):
    """ Process Chronic LFPs based on Therapy History.

    This pipeline will take the Chronic BrainSense data extracted from ``queryChronicLFPs`` and further processed 
    to calculate Event-Locked Power, Therapy Amplitudes, and Circadian Rhythms. 

    **Event-Locked Power**:

    Take all BrainSense power within the same therapy configurations and calculate power trend 3 hours before and after an event marking
    to identify changes in brain power related to pathology or events. 

    **Therapy Amplitudes**:

    When BrainSense is enabled, the therapy amplitude is logged. User can simply correlate brain power at different therapy amplitude
    to track pathological brain signals with adjustable therapy amplitude.
    
    **Circadian Rhythms**:

    Brain signal changes with sleep, and circadian rhythm analysis takes the timezoneOffset that the patient has 
    and overlay all Chronic BrainSense on a 24-hour scale in a 30 minutes window. 
    
    Args:
      LFPTrends: List of Chronic BrainSense Power data extracted from ``queryChronicLFPs``. 
      timezoneOffset: user timezone offset from UTC, used to perform 24-hours circadian rhythm analysis.

    Returns:
      Returns a list of LFPTrends, where each LFPTrends are continuous BrainSense Power with the same therapy configurations. 
    """

    for i in range(len(LFPTrends)):
        DeviceName = LFPTrends[i]["Device"]

        TherapyList = list()
        for j in range(len(LFPTrends[i]["Therapy"])):
            if LFPTrends[i]["Therapy"][j]["TherapyOverview"].startswith("Left") or LFPTrends[i]["Therapy"][j]["TherapyOverview"].startswith("Right"):
                TherapyList.append(DeviceName + " " + LFPTrends[i]["Therapy"][j]["TherapyOverview"])
        UniqueTherapyList = uniqueList(TherapyList)
        
        LFPTrends[i]["EventLockedPower"] = list()
        LFPTrends[i]["TherapyAmplitudes"] = list()
        LFPTrends[i]["CircadianPowers"] = list()
        for therapy in UniqueTherapyList:
            LFPTrends[i]["EventLockedPower"].append({"EventName": list(), "Timestamp": list(), "Therapy": therapy.replace(DeviceName + " ","")})
            LFPTrends[i]["CircadianPowers"].append({"Power": list(), "Timestamp": list(), "Therapy": therapy.replace(DeviceName + " ","")})
            LFPTrends[i]["TherapyAmplitudes"].append({"Power": list(), "Amplitude": list(), "Therapy": therapy.replace(DeviceName + " ","")})

            for j in range(len(LFPTrends[i]["Therapy"])):
                TherapyOverview = DeviceName + " " + LFPTrends[i]["Therapy"][j]["TherapyOverview"]
                if TherapyOverview == therapy and len(LFPTrends[i]["Power"][j]) > 0:
                    LFPTrends[i]["CircadianPowers"][-1]["Power"].extend(LFPTrends[i]["Power"][j])
                    LFPTrends[i]["CircadianPowers"][-1]["Timestamp"].extend(LFPTrends[i]["Timestamp"][j])

                    LFPTrends[i]["TherapyAmplitudes"][-1]["Power"].extend(LFPTrends[i]["Power"][j])
                    LFPTrends[i]["TherapyAmplitudes"][-1]["Amplitude"].extend(LFPTrends[i]["Amplitude"][j])

                    LFPTrends[i]["EventLockedPower"][-1]["EventName"].extend(LFPTrends[i]["EventName"][j])
                    LFPTrends[i]["EventLockedPower"][-1]["Timestamp"].extend(LFPTrends[i]["EventTime"][j])

            LFPTrends[i]["CircadianPowers"][-1]["Power"] = np.array(LFPTrends[i]["CircadianPowers"][-1]["Power"])
            LFPTrends[i]["CircadianPowers"][-1]["Timestamp"] = np.array(LFPTrends[i]["CircadianPowers"][-1]["Timestamp"])

            # Event Locked Power
            EventToInclude = list()
            LFPTrends[i]["EventLockedPower"][-1]["TimeArray"] = np.arange(37)*600 - 180*60
            EventLockedPower = np.zeros((len(LFPTrends[i]["EventLockedPower"][-1]["EventName"]),len(LFPTrends[i]["EventLockedPower"][-1]["TimeArray"])))
            for iEvent in range(len(LFPTrends[i]["EventLockedPower"][-1]["EventName"])):
                dataSelected = rangeSelection(LFPTrends[i]["CircadianPowers"][-1]["Timestamp"], [LFPTrends[i]["EventLockedPower"][-1]["Timestamp"][iEvent]+LFPTrends[i]["EventLockedPower"][-1]["TimeArray"][0], LFPTrends[i]["EventLockedPower"][-1]["Timestamp"][iEvent]+LFPTrends[i]["EventLockedPower"][-1]["TimeArray"][-1]])
                PowerTrend = LFPTrends[i]["CircadianPowers"][-1]["Power"][dataSelected]
                Timestamp = LFPTrends[i]["CircadianPowers"][-1]["Timestamp"][dataSelected]
                if len(Timestamp) > 35:
                    index = np.argsort(Timestamp)
                    EventLockedPower[iEvent,:] = np.interp(LFPTrends[i]["EventLockedPower"][-1]["TimeArray"]+LFPTrends[i]["EventLockedPower"][-1]["Timestamp"][iEvent], Timestamp[index], PowerTrend[index])
                    EventToInclude.append(iEvent)
            EventToInclude = np.array(EventToInclude)

            if not len(EventToInclude) == 0:
                LFPTrends[i]["EventLockedPower"][-1]["PowerChart"] = list()
                LFPTrends[i]["EventLockedPower"][-1]["EventName"] = np.array(LFPTrends[i]["EventLockedPower"][-1]["EventName"])[EventToInclude]
                EventLockedPower = EventLockedPower[EventToInclude,:]
                for name in np.unique(LFPTrends[i]["EventLockedPower"][-1]["EventName"]):
                    SelectedEvent = LFPTrends[i]["EventLockedPower"][-1]["EventName"] == name
                    LFPTrends[i]["EventLockedPower"][-1]["PowerChart"].append({"EventName": name + f" (n={np.sum(SelectedEvent)})",
                                                    "Line": np.mean(EventLockedPower[SelectedEvent,:], axis=0),
                                                    "Shade": SPU.stderr(EventLockedPower[SelectedEvent,:],axis=0)})

                LFPTrends[i]["EventLockedPower"][-1]["PowerRange"] = [np.percentile(EventLockedPower.flatten(),1),np.percentile(EventLockedPower.flatten(),99)]
                del(LFPTrends[i]["EventLockedPower"][-1]["EventName"])
                del(LFPTrends[i]["EventLockedPower"][-1]["Timestamp"])
                LFPTrends[i]["EventLockedPower"][-1]["TimeArray"] = LFPTrends[i]["EventLockedPower"][-1]["TimeArray"] / 60

            LFPTrends[i]["CircadianPowers"][-1]["Timestamp"] = (np.array(LFPTrends[i]["CircadianPowers"][-1]["Timestamp"])-timezoneOffset) % (24*60*60)

            # Calculate Average Power/Std Power
            LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"] = np.arange(24*12)*300
            LFPTrends[i]["CircadianPowers"][-1]["AveragePower"] = np.zeros(LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"].shape)
            LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"] = np.zeros(LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"].shape)
            for t in range(len(LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"])):
                timeSelection = rangeSelection(LFPTrends[i]["CircadianPowers"][-1]["Timestamp"],[LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"][t]-20*60, LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"][t]+20*60])
                PowerList = LFPTrends[i]["CircadianPowers"][-1]["Power"][timeSelection]
                while True:
                    PowerList = PowerList[np.abs(stats.zscore(PowerList)) < 3]
                    if np.sum(np.abs(stats.zscore(PowerList)) < 3) == len(PowerList):
                        break

                if len(PowerList) > 0:
                    LFPTrends[i]["CircadianPowers"][-1]["AveragePower"][t] = np.median(PowerList)
                    LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"][t] = SPU.stderr(PowerList)*2
                else:
                    LFPTrends[i]["CircadianPowers"][-1]["AveragePower"][t] = 0
                    LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"][t] = 0

            LFPTrends[i]["CircadianPowers"][-1]["Power"] = LFPTrends[i]["CircadianPowers"][-1]["Power"][::1].tolist()
            LFPTrends[i]["CircadianPowers"][-1]["Timestamp"] = (LFPTrends[i]["CircadianPowers"][-1]["Timestamp"] + timezoneOffset).tolist()
            LFPTrends[i]["CircadianPowers"][-1]["AveragePower"] = LFPTrends[i]["CircadianPowers"][-1]["AveragePower"].tolist()
            LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"] = LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"].tolist()
            LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"] = (LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"] + timezoneOffset).tolist()
            
            if len(LFPTrends[i]["CircadianPowers"][-1]["Power"]) > 0:
                LFPTrends[i]["CircadianPowers"][-1]["PowerRange"] = [np.percentile(LFPTrends[i]["CircadianPowers"][-1]["Power"],5),np.percentile(LFPTrends[i]["CircadianPowers"][-1]["Power"],95)]
            else:
                LFPTrends[i]["CircadianPowers"][-1]["PowerRange"] = [0,0]

    return LFPTrends

def processCircadianPower(LFPTrends, therapyInfo, timezoneOffset=0):
    CircadianPowers = {"Power": list(), "Timestamp": list()}
        
    for i in range(len(LFPTrends)):
        if LFPTrends[i]["Hemisphere"].startswith("Left"):
            Hemisphere = "LeftHemisphere"
        else:
            Hemisphere = "RightHemisphere"
        
        if not Hemisphere == therapyInfo["Hemisphere"]:
            continue

        for j in range(len(LFPTrends[i]["Therapy"])):
            if not Hemisphere in LFPTrends[i]["Therapy"][j].keys():
                continue
            Therapy = LFPTrends[i]["Therapy"][j][Hemisphere]

            if "SensingSetup" in Therapy.keys():
                if Therapy['Frequency'] == therapyInfo["Frequency"] and Therapy['SensingSetup']['FrequencyInHertz'] == therapyInfo["FrequencyInHertz"] and f"E{therapyInfo['Channel']}" in Therapy["Channel"]:
                    CircadianPowers["Power"].extend(LFPTrends[i]["Power"][j])
                    CircadianPowers["Timestamp"].extend(LFPTrends[i]["Timestamp"][j])
            
        if len(CircadianPowers["Power"]) > 0:
            CircadianPowers["Suggestion"] = list()
            Timestamp = (np.array(CircadianPowers["Timestamp"])-timezoneOffset) % (24*60*60)
            Power = np.array(CircadianPowers["Power"])
            for threshold in range(30, 70, 1):
                HighPower = Timestamp[Power >= np.percentile(Power,threshold)]
                LowPower = Timestamp[Power < np.percentile(Power,threshold)]
                if len(HighPower) > 20 and len(LowPower) > 20:
                    [t, p] = stats.ranksums(HighPower, LowPower)
                    CircadianPowers["Suggestion"].append({"threshold": np.percentile(Power,threshold), "separation": t})

        """
            LFPTrends[i]["CircadianPowers"][-1]["Power"] = np.array(LFPTrends[i]["CircadianPowers"][-1]["Power"])
            LFPTrends[i]["CircadianPowers"][-1]["Timestamp"] = np.array(LFPTrends[i]["CircadianPowers"][-1]["Timestamp"])

            LFPTrends[i]["CircadianPowers"][-1]["Timestamp"] = (np.array(LFPTrends[i]["CircadianPowers"][-1]["Timestamp"])-timezoneOffset) % (24*60*60)

            # Calculate Average Power/Std Power
            LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"] = np.arange(24*12)*300
            LFPTrends[i]["CircadianPowers"][-1]["AveragePower"] = np.zeros(LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"].shape)
            LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"] = np.zeros(LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"].shape)
            for t in range(len(LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"])):
                timeSelection = rangeSelection(LFPTrends[i]["CircadianPowers"][-1]["Timestamp"],[LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"][t]-20*60, LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"][t]+20*60])
                if np.any(timeSelection):
                    LFPTrends[i]["CircadianPowers"][-1]["AveragePower"][t] = np.median(LFPTrends[i]["CircadianPowers"][-1]["Power"][timeSelection])
                    LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"][t] = SPU.stderr(LFPTrends[i]["CircadianPowers"][-1]["Power"][timeSelection])*2
                else:
                    LFPTrends[i]["CircadianPowers"][-1]["AveragePower"][t] = 0
                    LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"][t] = 0

            LFPTrends[i]["CircadianPowers"][-1]["Power"] = LFPTrends[i]["CircadianPowers"][-1]["Power"][::1].tolist()
            LFPTrends[i]["CircadianPowers"][-1]["Timestamp"] = (LFPTrends[i]["CircadianPowers"][-1]["Timestamp"] + timezoneOffset).tolist()
            LFPTrends[i]["CircadianPowers"][-1]["AveragePower"] = LFPTrends[i]["CircadianPowers"][-1]["AveragePower"].tolist()
            LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"] = LFPTrends[i]["CircadianPowers"][-1]["StdErrPower"].tolist()
            LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"] = (LFPTrends[i]["CircadianPowers"][-1]["AverageTimestamp"] + timezoneOffset).tolist()

            LFPTrends[i]["CircadianPowers"][-1]["PowerRange"] = [np.percentile(LFPTrends[i]["CircadianPowers"][-1]["Power"],5),np.percentile(LFPTrends[i]["CircadianPowers"][-1]["Power"],95)]
        """
    return CircadianPowers