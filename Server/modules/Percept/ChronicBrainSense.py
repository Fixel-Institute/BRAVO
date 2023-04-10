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

def saveChronicLFP(deviceID, ChronicLFPs, sourceFile):
    """ Save Chronic BrainSense Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      ChronicLFPs: Chronic BrainSense (Power-band) structures extracted from Medtronic JSON file.
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """

    NewRecordingFound = False
    for key in ChronicLFPs.keys():
        recording_info = {"Hemisphere": key}
        if not models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="ChronicLFPs", recording_info__Hemisphere=recording_info["Hemisphere"]).exists():
            recording = models.BrainSenseRecording(device_deidentified_id=deviceID, recording_type="ChronicLFPs", recording_info=recording_info)
            filename = Database.saveSourceFiles(ChronicLFPs[key], "ChronicLFPs", key.replace("HemisphereLocationDef.",""), recording.recording_id, recording.device_deidentified_id)
            recording.recording_datapointer = filename
            recording.save()
            NewRecordingFound = True
        else:
            recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="ChronicLFPs", recording_info__Hemisphere=recording_info["Hemisphere"]).first()
            pastChronicLFPs = Database.loadSourceDataPointer(recording.recording_datapointer)

            Common = set(ChronicLFPs[key]["DateTime"]) & set(pastChronicLFPs["DateTime"])

            toInclude = np.zeros(len(ChronicLFPs[key]["DateTime"]), dtype=bool)
            IndexToInclude = list()
            for i in range(len(ChronicLFPs[key]["DateTime"])):
                if not ChronicLFPs[key]["DateTime"][i] in Common:
                    toInclude[i] = True

            if np.any(toInclude):
                pastChronicLFPs["DateTime"] = np.concatenate((pastChronicLFPs["DateTime"], ChronicLFPs[key]["DateTime"][toInclude]),axis=0)
                pastChronicLFPs["Amplitude"] = np.concatenate((pastChronicLFPs["Amplitude"], ChronicLFPs[key]["Amplitude"][toInclude]),axis=0)
                pastChronicLFPs["LFP"] = np.concatenate((pastChronicLFPs["LFP"], ChronicLFPs[key]["LFP"][toInclude]),axis=0)

                sortedIndex = np.argsort(pastChronicLFPs["DateTime"],axis=0).flatten()
                pastChronicLFPs["DateTime"] = pastChronicLFPs["DateTime"][sortedIndex]
                pastChronicLFPs["Amplitude"] = pastChronicLFPs["Amplitude"][sortedIndex]
                pastChronicLFPs["LFP"] = pastChronicLFPs["LFP"][sortedIndex]
                filename = Database.saveSourceFiles(pastChronicLFPs, "ChronicLFPs", key.replace("HemisphereLocationDef.",""), recording.recording_id, recording.device_deidentified_id)
                NewRecordingFound = True

    return NewRecordingFound

def queryChronicLFPsByTime(user, patientUniqueID, timeRange, authority):
    LFPTrends = list()
    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        leads = device.device_lead_configurations
        for hemisphere in ["HemisphereLocationDef.Left","HemisphereLocationDef.Right"]:
            recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type="ChronicLFPs", recording_info__Hemisphere=hemisphere).first()
            if not recording == None:
                ChronicLFPs = Database.loadSourceDataPointer(recording.recording_datapointer)
                if device.device_name == "":
                    LFPTrends.append({"Device": device.getDeviceSerialNumber(key), "DeviceLocation": device.device_location})
                else:
                    LFPTrends.append({"Device": device.device_name, "DeviceLocation": device.device_location})

                for lead in leads:
                    if lead["TargetLocation"].startswith(hemisphere.replace("HemisphereLocationDef.","")):
                        LFPTrends[-1]["Hemisphere"] = lead["TargetLocation"]

                LFPTimestamps = ChronicLFPs["DateTime"]
                LFPPowers = ChronicLFPs["LFP"]
                StimulationAmplitude = ChronicLFPs["Amplitude"]
                LFPTimestamps = np.array([time.timestamp() for time in LFPTimestamps])
                LFPTrends[-1]["Timestamp"] = list()
                LFPTrends[-1]["Power"] = list()
                LFPTrends[-1]["Amplitude"] = list()
                LFPTrends[-1]["EventName"] = list()
                LFPTrends[-1]["EventTime"] = list()

                # Remove Outliers
                LFPSelection = LFPPowers < np.median(LFPPowers) + np.std(LFPPowers)*6
                LFPTimestamps = LFPTimestamps[LFPSelection]
                LFPPowers = LFPPowers[LFPSelection]
                StimulationAmplitude = StimulationAmplitude[LFPSelection]

                LFPTrends[-1]["PowerRange"] = [0,0]
                LFPTrends[-1]["Timestamp"].append(LFPTimestamps)
                FiltPower = np.array(LFPPowers).tolist()
                LFPTrends[-1]["Power"].append(FiltPower)
                LFPTrends[-1]["Amplitude"].append(np.array(StimulationAmplitude).tolist())
                if np.percentile(FiltPower,5) < LFPTrends[-1]["PowerRange"][0]:
                    LFPTrends[-1]["PowerRange"][0] = np.percentile(FiltPower,5)
                if np.percentile(FiltPower,95) > LFPTrends[-1]["PowerRange"][1]:
                    LFPTrends[-1]["PowerRange"][1] = np.percentile(FiltPower,95)

                ChronicEvents = models.PatientCustomEvents.objects.filter(device_deidentified_id=device.deidentified_id,
                                    event_time__gt=timeRange[0], event_time__lt=timeRange[1]).all()
                ChronicEvents = pd.DataFrame.from_records(ChronicEvents.values("event_name", "event_time"))
                if "event_name" in ChronicEvents.keys():
                    LFPTrends[-1]["EventName"] = ChronicEvents["event_name"]
                    LFPTrends[-1]["EventTime"] = [time.timestamp() for time in ChronicEvents["event_time"]]
                else:
                    LFPTrends[-1]["EventName"] = []
                    LFPTrends[-1]["EventTime"] = []

                LFPTrends[-1]["Power"] = np.array(LFPTrends[-1]["Power"])
                LFPTrends[-1]["Timestamp"] = np.array(LFPTrends[-1]["Timestamp"])

    for i in range(len(LFPTrends)):
        # Event Locked Power
        EventToInclude = list()
        LFPTrends[i]["EventLockedPower"] = dict()
        LFPTrends[i]["EventLockedPower"]["TimeArray"] = np.arange(37)*600 - 180*60
        EventLockedPower = np.zeros((len(LFPTrends[i]["EventName"]),len(LFPTrends[i]["EventLockedPower"]["TimeArray"])))
        for iEvent in range(len(LFPTrends[i]["EventName"])):
            dataSelected = rangeSelection(LFPTrends[i]["Timestamp"], [LFPTrends[i]["EventTime"][iEvent]+LFPTrends[i]["EventLockedPower"]["TimeArray"][0], LFPTrends[i]["EventTime"][iEvent]+LFPTrends[i]["EventLockedPower"]["TimeArray"][-1]])
            PowerTrend = LFPTrends[i]["Power"][dataSelected]
            Timestamp = LFPTrends[i]["Timestamp"][dataSelected]
            if len(Timestamp) > 35:
                index = np.argsort(Timestamp)
                EventLockedPower[iEvent,:] = np.interp(LFPTrends[i]["EventLockedPower"]["TimeArray"]+LFPTrends[i]["EventTime"][iEvent], Timestamp[index], PowerTrend[index])
                EventToInclude.append(iEvent)
        EventToInclude = np.array(EventToInclude)

        if not len(EventToInclude) == 0:
            LFPTrends[i]["EventLockedPower"]["PowerChart"] = list()
            LFPTrends[i]["EventLockedPower"]["EventName"] = np.array(LFPTrends[i]["EventName"])[EventToInclude]
            EventLockedPower = EventLockedPower[EventToInclude,:]
            for name in np.unique(LFPTrends[i]["EventLockedPower"]["EventName"]):
                SelectedEvent = LFPTrends[i]["EventLockedPower"]["EventName"] == name
                LFPTrends[i]["EventLockedPower"]["PowerChart"].append({"EventName": name + f" (n={np.sum(SelectedEvent)})",
                                                "Line": np.mean(EventLockedPower[SelectedEvent,:], axis=0),
                                                "Shade": SPU.stderr(EventLockedPower[SelectedEvent,:],axis=0)})

            LFPTrends[i]["EventLockedPower"]["PowerRange"] = [np.percentile(EventLockedPower.flatten(),1),np.percentile(EventLockedPower.flatten(),99)]
            LFPTrends[i]["EventLockedPower"]["TimeArray"] = LFPTrends[i]["EventLockedPower"]["TimeArray"] / 60

    return LFPTrends

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
    for device in availableDevices:
        leads = device.device_lead_configurations
        for hemisphere in ["HemisphereLocationDef.Left","HemisphereLocationDef.Right"]:
            recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type="ChronicLFPs", recording_info__Hemisphere=hemisphere).first()
            if not recording == None:
                ChronicLFPs = Database.loadSourceDataPointer(recording.recording_datapointer)
                if device.device_name == "":
                    LFPTrends.append({"Device": device.getDeviceSerialNumber(key), "DeviceLocation": device.device_location})
                else:
                    LFPTrends.append({"Device": device.device_name, "DeviceLocation": device.device_location})

                for lead in leads:
                    if lead["TargetLocation"].startswith(hemisphere.replace("HemisphereLocationDef.","")):
                        LFPTrends[-1]["Hemisphere"] = lead["TargetLocation"]
                        LFPTrends[-1]["CustomName"] = lead["CustomName"]

                LFPTimestamps = ChronicLFPs["DateTime"]
                LFPPowers = ChronicLFPs["LFP"]
                StimulationAmplitude = ChronicLFPs["Amplitude"]
                LFPTimestamps = np.array([time.timestamp() for time in LFPTimestamps])
                LFPTrends[-1]["Timestamp"] = list()
                LFPTrends[-1]["Power"] = list()
                LFPTrends[-1]["Amplitude"] = list()
                LFPTrends[-1]["Therapy"] = list()
                LFPTrends[-1]["EventName"] = list()
                LFPTrends[-1]["EventTime"] = list()
                LFPTrends[-1]["EventPower"] = list()

                # Remove Outliers
                LFPSelection = LFPPowers < (np.median(LFPPowers) + np.std(LFPPowers)*6)
                LFPTimestamps = LFPTimestamps[LFPSelection]
                LFPPowers = LFPPowers[LFPSelection]
                StimulationAmplitude = StimulationAmplitude[LFPSelection]

                LFPTrends[-1]["PowerRange"] = [0,0]

                #[b,a] = signal.butter(5, 0.00003*2*600, 'high', output='ba')
                for therapy in TherapyHistory:
                    if therapy["device"] == device.deidentified_id:
                        for i in range(len(therapy["date_of_change"])-1):
                            rangeSelected = rangeSelection(LFPTimestamps,[therapy["date_of_change"][i]/1000000000,therapy["date_of_change"][i+1]/1000000000])
                            if np.any(rangeSelected):
                                LFPTrends[-1]["Timestamp"].append(LFPTimestamps[rangeSelected])
                                #FiltPower = signal.filtfilt(b,a,LFPPowers[rangeSelected])
                                FiltPower = np.array(LFPPowers[rangeSelected])
                                LFPTrends[-1]["Power"].append(FiltPower.tolist())
                                LFPTrends[-1]["Amplitude"].append(np.array(StimulationAmplitude[rangeSelected]).tolist())
                                LFPTrends[-1]["Therapy"].append(copy.deepcopy(therapy["therapy"][i]))

                                TherapyDetails = LFPTrends[-1]["Therapy"][-1][hemisphere.replace("HemisphereLocationDef.","")+"Hemisphere"]
                                if "AdaptiveSetup" in TherapyDetails.keys():
                                    if "Bypass" in TherapyDetails["AdaptiveSetup"].keys():
                                        #LFPTrends[-1]["Power"][-1] = []
                                        pass
                                
                                if np.percentile(FiltPower,5) < LFPTrends[-1]["PowerRange"][0]:
                                    LFPTrends[-1]["PowerRange"][0] = np.percentile(FiltPower,5)
                                if np.percentile(FiltPower,95) > LFPTrends[-1]["PowerRange"][1]:
                                    LFPTrends[-1]["PowerRange"][1] = np.percentile(FiltPower,95)

                                ChronicEvents = models.PatientCustomEvents.objects.filter(device_deidentified_id=device.deidentified_id,
                                                    event_time__gt=datetime.fromtimestamp(therapy["date_of_change"][i]/1000000000,tz=pytz.utc), event_time__lt=datetime.fromtimestamp(therapy["date_of_change"][i+1]/1000000000,tz=pytz.utc)).all()
                                ChronicEvents = pd.DataFrame.from_records(ChronicEvents.values("event_name", "event_time"))
                                if "event_name" in ChronicEvents.keys():
                                    LFPTrends[-1]["EventName"].append(ChronicEvents["event_name"])
                                    LFPTrends[-1]["EventTime"].append([time.timestamp() for time in ChronicEvents["event_time"]])
                                    LFPTrends[-1]["EventPower"].append([LFPTrends[-1]["Power"][-1][findClosest(LFPTrends[-1]["Timestamp"][-1], time)[1]] for time in LFPTrends[-1]["EventTime"][-1]])
                                else:
                                    LFPTrends[-1]["EventName"].append([])
                                    LFPTrends[-1]["EventTime"].append([])
                                    LFPTrends[-1]["EventPower"].append([])

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
        if LFPTrends[i]["Hemisphere"].startswith("Left"):
            Hemisphere = "LeftHemisphere"
        else:
            Hemisphere = "RightHemisphere"

        TherapyList = list()
        for j in range(len(LFPTrends[i]["Therapy"])):
            if not Hemisphere in LFPTrends[i]["Therapy"][j].keys():
                continue
            Therapy = LFPTrends[i]["Therapy"][j][Hemisphere]
            if "SensingSetup" in Therapy.keys():
                TherapyOverview = f"{Therapy['Frequency']}Hz {Therapy['PulseWidth']}uS {Therapy['Channel']} @ {Therapy['SensingSetup']['FrequencyInHertz']}Hz"
            else:
                TherapyOverview = f"{Therapy['Frequency']}Hz {Therapy['PulseWidth']}uS {Therapy['Channel']} @ {0}Hz"
            LFPTrends[i]["Therapy"][j]["TherapyOverview"] = TherapyOverview

            TherapyList.append(TherapyOverview)
        UniqueTherapyList = uniqueList(TherapyList)

        LFPTrends[i]["EventLockedPower"] = list()
        LFPTrends[i]["TherapyAmplitudes"] = list()
        LFPTrends[i]["CircadianPowers"] = list()
        for therapy in UniqueTherapyList:
            LFPTrends[i]["EventLockedPower"].append({"EventName": list(), "Timestamp": list(), "Therapy": therapy})
            LFPTrends[i]["CircadianPowers"].append({"Power": list(), "Timestamp": list(), "Therapy": therapy})
            LFPTrends[i]["TherapyAmplitudes"].append({"Power": list(), "Amplitude": list(), "Therapy": therapy})

            for j in range(len(LFPTrends[i]["Therapy"])):
                if not Hemisphere in LFPTrends[i]["Therapy"][j].keys():
                    continue
                Therapy = LFPTrends[i]["Therapy"][j][Hemisphere]
                if "SensingSetup" in Therapy.keys():
                    TherapyOverview = f"{Therapy['Frequency']}Hz {Therapy['PulseWidth']}uS {Therapy['Channel']} @ {Therapy['SensingSetup']['FrequencyInHertz']}Hz"
                else:
                    TherapyOverview = f"{Therapy['Frequency']}Hz {Therapy['PulseWidth']}uS {Therapy['Channel']} @ {0}Hz"

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