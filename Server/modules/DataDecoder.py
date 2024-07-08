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
Data Decoder Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())

from datetime import datetime, date, timedelta
import pickle, blosc
import dateutil, pytz
import numpy as np
import pandas as pd
from cryptography.fernet import Fernet
import hashlib
import scipy.io as sio
import json

from Backend import models
from Backend.models.HelperFunctions import decryptMessage, encryptMessage
from modules.Percept import Therapy as PerceptTherapy, BrainSenseStream, BrainSenseSurvey, BrainSenseEvent, IndefiniteStream, ChronicBrainSense
from decoder import Percept

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

def decodeMedtronicJSON(cache_file):
    metadata = cache_file.metadata
    participant = cache_file.participant[0]

    JSON = Percept.decodeEncryptedJSON(cache_file.file_pointer, os.environ.get('ENCRYPTION_KEY'))
    try:
        Data = Percept.extractPerceptJSON(JSON)
    except:
        return {"error": "Percept JSON Decoding Error"}
    
    if "ProcessFailure" in Data.keys():
        print(Data["ProcessFailure"])
        return {"error": "Percept JSON Process Error", "content": Data["ProcessFailure"]}
    
    SessionTimestamp = Percept.estimateSessionDateTime(JSON)
    DeviceInformation = JSON["DeviceInformation"]["Final"]

    device = None
    for existingDevice in participant.devices:
        if existingDevice.getDeviceName() == DeviceInformation["NeurostimulatorSerialNumber"]:
            device = existingDevice
            break
        
    if not device:
        device = models.DBSDevice(type=DeviceInformation["Neurostimulator"])
        device.setDeviceName(DeviceInformation["NeurostimulatorSerialNumber"])

    if metadata["infer_from_device"]:
        PatientInformation = JSON["PatientInformation"]["Final"]
        if PatientInformation["Diagnosis"] == "DiagnosisTypeDef.ParkinsonsDisease":
            participant.diagnosis = "Parkinson's Disease"
        elif PatientInformation["Diagnosis"] == "DiagnosisTypeDef.ParkinsonsDisease":
            participant.diagnosis = "Essential Tremor"
        if PatientInformation["PatientGender"] == "PatientGenderDef.MALE":
            participant.sex = "Male"
        elif PatientInformation["PatientGender"] == "PatientGenderDef.FEMALE":
            participant.sex = "Female"
        else:
            participant.sex = "Other"
        # Patient Date of Birth does not exist for non-Percept Device
        if "PatientDateOfBirth" in PatientInformation.keys():
            participant.date_of_birth = Percept.getTimestamp(PatientInformation["PatientDateOfBirth"])
        participant.save()
        
        if DeviceInformation["NeurostimulatorLocation"] == "InsLocation.CHEST_RIGHT":
            device.implanted_location = "Right IPG"
        elif DeviceInformation["NeurostimulatorLocation"] == "InsLocation.CHEST_LEFT":
            device.implanted_location = "Left IPG"
        else:
            device.implanted_location = DeviceInformation["NeurostimulatorLocation"].replace("InsLocation.", "")
        device.implanted_date = Percept.getTimestamp(DeviceInformation["ImplantDate"])
    else:
        if not device.implanted_location and not metadata.device_location == "":
            device.implanted_location = metadata.device_location

    device.save()
    if not device.uid in [i.uid for i in participant.devices]:
        participant.devices.connect(device)

    LeadInformation = JSON["LeadConfiguration"]["Final"]
    for lead in LeadInformation:
        TargetLocation = lead["Hemisphere"].replace("HemisphereLocationDef.","") + " "
        if lead["LeadLocation"] == "LeadLocationDef.Vim":
            TargetLocation += "VIM"
        elif lead["LeadLocation"] == "LeadLocationDef.Stn":
            TargetLocation += "STN"
        elif lead["LeadLocation"] == "LeadLocationDef.Gpi":
            TargetLocation += "GPi"
        else:
            TargetLocation += lead["LeadLocation"].replace("LeadLocationDef.","")

        ElectrodeFound = False
        for electrode in device.electrodes:
            if electrode.name == TargetLocation:
                ElectrodeFound = True
        if ElectrodeFound:
            continue

        electrode = models.DBSElectrode(name=TargetLocation, custom_name=TargetLocation)
        if lead["ElectrodeNumber"] == "InsPort.ZERO_THREE" or lead["ElectrodeNumber"] == "InsPort.EIGHT_ELEVEN":
            electrode.channel_count = 4
        elif lead["ElectrodeNumber"] == "InsPort.ZERO_SEVEN" or lead["ElectrodeNumber"] == "InsPort.EIGHT_FIFTEEN":
            electrode.channel_count = 8
        
        if lead["Model"] == "LeadModelDef.LEAD_B33015":
            electrode.type = "SenSight B33015"
            electrode.channel_names = ["E00","E01-A","E01-B","E01-C","E02-A","E02-B","E02-C","E03"]
        elif lead["Model"] == "LeadModelDef.LEAD_B33005":
            electrode.type = "SenSight B33005"
            electrode.channel_names = ["E00","E01-A","E01-B","E01-C","E02-A","E02-B","E02-C","E03"]
        elif lead["Model"] == "LeadModelDef.LEAD_3387":
            electrode.type = "Medtronic 3387"
            electrode.channel_names = ["E00","E01","E02","E03"]
        elif lead["Model"] == "LeadModelDef.LEAD_3389":
            electrode.type = "Medtronic 3389"
            electrode.channel_names = ["E00","E01","E02","E03"]
        elif lead["Model"] == "LeadModelDef.LEAD_OTHER":
            electrode.type = "Other"
        else:
            electrode.type = lead["Model"]
        electrode.save()
        device.electrodes.connect(electrode)

    # Handle Therapy History
    if "StimulationGroups" in Data.keys():
        NewTherapies = PerceptTherapy.saveTherapySettings(participant, device, Data["StimulationGroups"], SessionTimestamp, "Post-visit Therapy")
        [cache_file.therapies.connect(item) for item in NewTherapies]
    
    if "PreviousGroups" in Data.keys():
        NewTherapies = PerceptTherapy.saveTherapySettings(participant, device, Data["PreviousGroups"], SessionTimestamp, "Pre-visit Therapy")
        [cache_file.therapies.connect(item) for item in NewTherapies]
    
    if "TherapyHistory" in Data.keys():
        for i in range(len(Data["TherapyHistory"])):
            HistorySessionDate = Percept.getTimestamp(Data["TherapyHistory"][i]["DateTime"])
            NewTherapies = PerceptTherapy.saveTherapySettings(participant, device, Data["TherapyHistory"][i]["Therapy"], HistorySessionDate, "Past Therapy")
            [cache_file.therapies.connect(item) for item in NewTherapies]
    
    # Handle Therapy Change History
    if "TherapyChangeHistory" in Data.keys():
        NewTherapies = PerceptTherapy.saveTherapyEvents(participant, device, Data["TherapyChangeHistory"])
        [cache_file.events.connect(item) for item in NewTherapies]

    # Handle Recording Data
    visit = models.Visit.nodes.get_or_none(name="Generic Percept Session")
    if not visit:
        visit = models.Visit(name="Generic Percept Session").save()

    # Process BrainSense Survey
    if "MontagesTD" in Data.keys():
        NewRecordings = BrainSenseSurvey.saveBrainSenseSurvey(participant, device, Data["MontagesTD"])
        for item in NewRecordings:
            cache_file.recordings.connect(item)
            visit.recordings.connect(item)

    if "BaselineTD" in Data.keys():
        NewRecordings = BrainSenseSurvey.saveBrainSenseSurvey(participant, device, Data["BaselineTD"])
        for item in NewRecordings:
            cache_file.recordings.connect(item)
            visit.recordings.connect(item)
    
    # Process Montage Streams
    if "IndefiniteStream" in Data.keys():
        NewRecordings = IndefiniteStream.saveIndefiniteStreams(participant, device, Data["IndefiniteStream"])
        for item in NewRecordings:
            cache_file.recordings.connect(item)
            visit.recordings.connect(item)

    # Process Realtime Streams
    if "StreamingTD" in Data.keys() and "StreamingPower" in Data.keys():
        NewRecordings = BrainSenseStream.saveBrainSenseStreams(participant, device, Data["StreamingTD"], Data["StreamingPower"])
        for item in NewRecordings:
            cache_file.recordings.connect(item)
            visit.recordings.connect(item)

    # Stiore Chronic LFPs
    if "LFPTrends" in Data.keys():
        NewRecordings = ChronicBrainSense.saveChronicBrainSense(participant, device, Data["LFPTrends"], Data["PreviousGroups"], SessionTimestamp)
        for item in NewRecordings:
            cache_file.recordings.connect(item)
            visit.recordings.connect(item)

    if "PatientEventLogs" in Data.keys():
        NewEvents = BrainSenseEvent.saveBrainSenseEvents(participant, device, Data["PatientEventLogs"])
        [cache_file.events.connect(item) for item in NewEvents]

    if "Impedance" in Data.keys():
        if len(device.recordings.filter(type="ImpedanceMeasurement", date=SessionTimestamp)) == 0:
            for impedanceData in Data["Impedance"]:
                recording = models.InMemoryRecording(type="ImpedanceMeasurement", date=SessionTimestamp, in_memory_storage=impedanceData).save()
                recording.devices.connect(device)
                device.recordings.connect(recording)
                cache_file.recordings.connect(recording)
                visit.recordings.connect(recording)

    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + participant.uid, exist_ok=True)
    os.rename(cache_file.file_pointer, DATABASE_PATH + "raws" + os.path.sep + participant.uid + os.path.sep + cache_file.uid + ".json")
    cache_file.file_pointer = DATABASE_PATH + "raws" + os.path.sep + participant.uid + os.path.sep + cache_file.uid + ".json"
    cache_file.save()
    device.source_files.connect(cache_file)
    return None

def saveCacheFile(rawBytes, filename, data_type, metadata, event=None):
    sourceFile = models.SourceFile(name=filename, metadata=metadata)
    extension = filename.replace(filename.split(".")[0],"")
    sourceFile.file_pointer = DATABASE_PATH + "cache" + os.path.sep + sourceFile.uid + extension
    with open(sourceFile.file_pointer, "wb+") as file:
        file.write(rawBytes)

    sourceFile.save()
    queue = models.ProcessingQueue(status="created", job_type=data_type).save()
    queue.cache_file.connect(sourceFile)
    if event:
        sourceFile.events.connect(event)
    return sourceFile, queue
