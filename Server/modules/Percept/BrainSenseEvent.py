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
Event Markings Processing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(os.environ.get("PYTHON_UTILITY"))

import numpy as np
from datetime import datetime
import pytz
import pandas as pd

from decoder import Percept
from utility import SignalProcessingUtility as SPU
from utility.PythonUtility import *

from Backend import models
from modules import Database, Therapy

key = os.environ.get('ENCRYPTION_KEY')

def saveBrainSenseEvents(deviceID, LfpFrequencySnapshotEvents, sourceFile):
    """ Save BrainSense Events Data in MySQL Database.

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      LfpFrequencySnapshotEvents: Event-snapshot Power Spectrum data extracted from Medtronic JSON file.
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """

    NewRecordingFound = False
    batchStorage = list()
    for event in LfpFrequencySnapshotEvents:
        EventTime = datetime.fromtimestamp(Percept.getTimestamp(event["DateTime"]),tz=pytz.utc)
        SensingExist = False
        if "LfpFrequencySnapshotEvents" in event.keys():
            SensingExist = True
            EventData = event["LfpFrequencySnapshotEvents"]

        if not models.PatientCustomEvents.objects.filter(device_deidentified_id=deviceID, event_name=event["EventName"], event_time=EventTime, sensing_exist=SensingExist).exists():
            customEvent = models.PatientCustomEvents(device_deidentified_id=deviceID, event_name=event["EventName"], event_time=EventTime, sensing_exist=SensingExist, source_file=sourceFile)
            if SensingExist:
                customEvent.neural_psd = EventData
            batchStorage.append(customEvent)
        else:
            if SensingExist:
                customEvent = models.PatientCustomEvents.objects.filter(device_deidentified_id=deviceID, event_name=event["EventName"], event_time=EventTime, sensing_exist=SensingExist).first()
                if len(customEvent.neural_psd.keys()) == 0:
                    customEvent.neural_psd = EventData
                    customEvent.save()

    if len(batchStorage) > 0:
        NewRecordingFound = True
        models.PatientCustomEvents.objects.bulk_create(batchStorage,ignore_conflicts=True)

    return NewRecordingFound

def queryPatientEventPSDsByTime(user, patientUniqueID, timeRange, authority):
    PatientEventPSDs = list()
    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)

    for device in availableDevices:
        EventPSDs = models.PatientCustomEvents.objects.filter(device_deidentified_id=device.deidentified_id, sensing_exist=True, event_time__gt=timeRange[0], event_time__lt=timeRange[1]).all()
        if len(EventPSDs) > 0:
            leads = device.device_lead_configurations
            for hemisphere in ["HemisphereLocationDef.Left","HemisphereLocationDef.Right"]:
                if device.device_name == "":
                    PatientEventPSDs.append({"Device": str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key), "DeviceLocation": device.device_location, "PSDs": list(), "EventName": list(), "EventTime": list(), "Therapy": list()})
                else:
                    PatientEventPSDs.append({"Device": device.device_name, "DeviceLocation": device.device_location, "PSDs": list(), "EventName": list(), "EventTime": list(), "Therapy": list()})

                for lead in leads:
                    if lead["TargetLocation"].startswith(hemisphere.replace("HemisphereLocationDef.","")):
                        PatientEventPSDs[-1]["Hemisphere"] = lead["TargetLocation"]

                TherapyKey = hemisphere.replace("HemisphereLocationDef.","") + "Hemisphere"
                for eventPSD in EventPSDs:
                    if hemisphere in eventPSD.neural_psd.keys():
                        EventTimestamp = Percept.getTimestamp(eventPSD.neural_psd[hemisphere]["DateTime"])
                        if EventTimestamp > authority["Permission"][0]:
                            if authority["Permission"][1] > 0 and EventTimestamp < authority["Permission"][1]:
                                PatientEventPSDs[-1]["Therapy"].append("Generic")
                                PatientEventPSDs[-1]["PSDs"].append(eventPSD.neural_psd[hemisphere]["FFTBinData"])
                                PatientEventPSDs[-1]["EventName"].append(eventPSD.event_name)
                                PatientEventPSDs[-1]["EventTime"].append(EventTimestamp)
                                break
                            elif authority["Permission"][1] == 0:
                                PatientEventPSDs[-1]["Therapy"].append("Generic")
                                PatientEventPSDs[-1]["PSDs"].append(eventPSD.neural_psd[hemisphere]["FFTBinData"])
                                PatientEventPSDs[-1]["EventName"].append(eventPSD.event_name)
                                PatientEventPSDs[-1]["EventTime"].append(EventTimestamp)
                                break

    i = 0
    while i < len(PatientEventPSDs):
        if not "Hemisphere" in PatientEventPSDs[i]:
            del(PatientEventPSDs[i])
        else:
            i += 1

    return PatientEventPSDs

def queryPatientEventPSDs(user, patientUniqueID, TherapyHistory, authority):
    PatientEventPSDs = list()
    if not authority["Permission"]:
        return PatientEventPSDs

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    TherapyConfigurations = Therapy.queryTherapyConfigurations(user, patientUniqueID, authority, therapyType="Past Therapy")
    for device in availableDevices:
        EventPSDs = models.PatientCustomEvents.objects.filter(device_deidentified_id=device.deidentified_id, sensing_exist=True).all()
        if len(EventPSDs) > 0:
            leads = device.device_lead_configurations
            for hemisphere in ["HemisphereLocationDef.Left","HemisphereLocationDef.Right"]:
                if device.device_name == "":
                    PatientEventPSDs.append({"Device": str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key), "DeviceLocation": device.device_location, "PSDs": list(), "EventName": list(), "Therapy": list()})
                else:
                    PatientEventPSDs.append({"Device": device.device_name, "DeviceLocation": device.device_location, "PSDs": list(), "EventName": list(), "Therapy": list()})

                for lead in leads:
                    if lead["TargetLocation"].startswith(hemisphere.replace("HemisphereLocationDef.","")):
                        PatientEventPSDs[-1]["Hemisphere"] = lead["TargetLocation"]

                TherapyKey = hemisphere.replace("HemisphereLocationDef.","") + "Hemisphere"
                for eventPSD in EventPSDs:
                    if hemisphere in eventPSD.neural_psd.keys():
                        EventTimestamp = Percept.getTimestamp(eventPSD.neural_psd[hemisphere]["DateTime"])
                        if EventTimestamp > authority["Permission"][0]:
                            if authority["Permission"][1] > 0 and EventTimestamp < authority["Permission"][1]:
                                for therapy in TherapyConfigurations:
                                    if therapy["DeviceID"] == str(device.deidentified_id) and therapy["TherapyGroup"] == eventPSD.neural_psd[hemisphere]["GroupId"] and therapy["TherapyDate"] > EventTimestamp and TherapyKey in therapy["Therapy"].keys():
                                        PatientEventPSDs[-1]["Therapy"].append(therapy["Therapy"][TherapyKey])
                                        if len(eventPSD.neural_psd[hemisphere]["FFTBinData"]) < 100: 
                                            eventPSD.neural_psd[hemisphere]["FFTBinData"].extend([0 for i in range(100-len(eventPSD.neural_psd[hemisphere]["FFTBinData"]))])
                                        PatientEventPSDs[-1]["PSDs"].append(eventPSD.neural_psd[hemisphere]["FFTBinData"])
                                        PatientEventPSDs[-1]["EventName"].append(eventPSD.event_name)
                                        break
                            elif authority["Permission"][1] == 0:
                                for therapy in TherapyConfigurations:
                                    if therapy["DeviceID"] == str(device.deidentified_id) and therapy["TherapyGroup"] == eventPSD.neural_psd[hemisphere]["GroupId"] and therapy["TherapyDate"] > EventTimestamp and TherapyKey in therapy["Therapy"].keys():
                                        PatientEventPSDs[-1]["Therapy"].append(therapy["Therapy"][TherapyKey])
                                        if len(eventPSD.neural_psd[hemisphere]["FFTBinData"]) < 100: 
                                            eventPSD.neural_psd[hemisphere]["FFTBinData"].extend([0 for i in range(100-len(eventPSD.neural_psd[hemisphere]["FFTBinData"]))])
                                        PatientEventPSDs[-1]["PSDs"].append(eventPSD.neural_psd[hemisphere]["FFTBinData"])
                                        PatientEventPSDs[-1]["EventName"].append(eventPSD.event_name)
                                        break

    i = 0
    while i < len(PatientEventPSDs):
        if not "Hemisphere" in PatientEventPSDs[i]:
            del(PatientEventPSDs[i])
        else:
            i += 1

    return PatientEventPSDs

def processEventPSDs(PatientEventPSDs):
    def formatTherapyString(Therapy):
        return f"Stimulation {Percept.reformatStimulationChannel(Therapy['Channel'])} {Therapy['Frequency']}Hz {Therapy['PulseWidth']}uS"

    for i in range(len(PatientEventPSDs)):
        PatientEventPSDs[i]["Render"] = list()
        PatientEventPSDs[i]["PSDs"] = np.array(PatientEventPSDs[i]["PSDs"])
        StimulationConfigurations = [PatientEventPSDs[i]["Therapy"][j] if PatientEventPSDs[i]["Therapy"][j] == "Generic" else formatTherapyString(PatientEventPSDs[i]["Therapy"][j]) for j in range(len(PatientEventPSDs[i]["Therapy"]))]
        uniqueConfiguration = uniqueList(StimulationConfigurations)
        for config in uniqueConfiguration:
            PatientEventPSDs[i]["Render"].append({"Therapy": config, "Hemisphere": PatientEventPSDs[i]["Device"] + " " + PatientEventPSDs[i]["Hemisphere"], "Events": list()})

            selectedPSDs = iterativeCompare(StimulationConfigurations, config, "equal").flatten()
            Events = listSelection(PatientEventPSDs[i]["EventName"], selectedPSDs)
            for eventName in uniqueList(Events):
                eventSelection = iterativeCompare(PatientEventPSDs[i]["EventName"], eventName, "equal").flatten()
                PatientEventPSDs[i]["Render"][-1]["Events"].append({
                    "EventName": eventName,
                    "Count": f"(n={np.sum(np.bitwise_and(selectedPSDs, eventSelection))})",
                    "MeanPSD": np.mean(PatientEventPSDs[i]["PSDs"][np.bitwise_and(selectedPSDs, eventSelection),:],axis=0).flatten(),
                    "StdPSD": SPU.stderr(PatientEventPSDs[i]["PSDs"][np.bitwise_and(selectedPSDs, eventSelection),:],axis=0).flatten()
                })

    return PatientEventPSDs

def processEventMarkers(LFPTrends, EventNames):
    EventMarker = list()
    for i in range(len(LFPTrends)):
        EventMarker.append({"EventPower": list(), "EventTime": list(), "EventName": list(), "EventColor": list()})
        for cIndex in range(len(EventNames)):
            EventMarker[i]["EventName"].append(EventNames[cIndex])
            EventMarker[i]["EventPower"].append(list())
            EventMarker[i]["EventTime"].append(list())
            for j in range(len(LFPTrends[i]["EventTime"])):
                for k in range(len(LFPTrends[i]["EventTime"][j])):
                    if LFPTrends[i]["EventName"][j][k] == EventNames[cIndex]:
                        index = np.argmin(np.abs(LFPTrends[i]["EventTime"][j][k] - LFPTrends[i]["Timestamp"][j]))
                        EventMarker[i]["EventPower"][cIndex].append(LFPTrends[i]["Power"][j][index])
                        EventMarker[i]["EventTime"][cIndex].append(LFPTrends[i]["EventTime"][j][k]*1000)
    return EventMarker

def getAllPatientEvents(user, patientUniqueID, authority):
    PatientEventPSDs = list()
    if not authority["Permission"]:
        return PatientEventPSDs

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        EventPSDs = models.PatientCustomEvents.objects.filter(device_deidentified_id=device.deidentified_id).all()
        if len(EventPSDs) > 0:
            if device.device_name == "":
                PatientEventPSDs.append({"Device": str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key), "DeviceLocation": device.device_location, "PSDs": list(), "EventName": list(), "EventTime": list()})
            else:
                PatientEventPSDs.append({"Device": device.device_name, "DeviceLocation": device.device_location, "PSDs": list(), "EventName": list(), "EventTime": list()})

            for hemisphere in ["HemisphereLocationDef.Left","HemisphereLocationDef.Right"]:
                PatientEventPSDs[-1][hemisphere] = list()

            EventPSDsDF = pd.DataFrame.from_records(EventPSDs.values("neural_psd", "event_name", "event_time"))
            EventPSDsDF.drop_duplicates(subset=['event_name', 'event_time'], inplace=True)

            for i in EventPSDsDF.index:
                EventTimestamp = EventPSDsDF["event_time"][i].timestamp()
                if EventTimestamp > authority["Permission"][0]:
                    if authority["Permission"][1] > 0 and EventTimestamp < authority["Permission"][1]:
                        for hemisphere in ["HemisphereLocationDef.Left","HemisphereLocationDef.Right"]:
                            if hemisphere in EventPSDsDF["neural_psd"][i]:
                                PatientEventPSDs[-1][hemisphere].append(EventPSDsDF["neural_psd"][i][hemisphere]["FFTBinData"])
                            else:
                                PatientEventPSDs[-1][hemisphere].append(None)
                        PatientEventPSDs[-1]["EventName"].append(EventPSDsDF["event_name"][i])
                        PatientEventPSDs[-1]["EventTime"].append(EventTimestamp)
                        
                    elif authority["Permission"][1] == 0:
                        for hemisphere in ["HemisphereLocationDef.Left","HemisphereLocationDef.Right"]:
                            if hemisphere in EventPSDsDF["neural_psd"][i]:
                                PatientEventPSDs[-1][hemisphere].append(EventPSDsDF["neural_psd"][i][hemisphere]["FFTBinData"])
                            else:
                                PatientEventPSDs[-1][hemisphere].append(None)
                        PatientEventPSDs[-1]["EventName"].append(EventPSDsDF["event_name"][i])
                        PatientEventPSDs[-1]["EventTime"].append(EventTimestamp)

    return PatientEventPSDs