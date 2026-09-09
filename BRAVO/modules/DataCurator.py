""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under Open Source GPL-3.0 License

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Data Curators 
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, pathlib
import uuid
import shutil
import datetime
import json
from cryptography.fernet import Fernet
import hmac, hashlib
import base64
import pickle
import numpy as np
import pandas as pd
from io import BytesIO
import blosc2
from filelock import Timeout, FileLock

from Server import models
from modules.NeuroPace.PersystDecoder import parsePersystRecording
from modules.MedtronicPercept.Session import decodeMedtronicJSON
from modules.ExternalDevices.DelsysTrigno import decodeMDATData, decodeHPFCSVData
from modules.ExternalDevices.BRAVOfflineWinUI import decodeMDATv2, decodeMDATv3
from modules.ExternalDevices.MATLAB import decodeMATLABFile
from modules.ExternalDevices.BRAVORecordingStructure import decodebdata
from modules.AlphaOmega.MPX import extractAlphaOmegaRecordings
from modules import Database, Therapy, Event

import time

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')
key = os.environ.get('DATASERVER_ENCRYPTION')
secureEncoder = Fernet(key)

def loadCacheFile(source_file):
    rawBytes = Database.loadSourceFile(source_file.pointer, source_file.hashed, bytes=True)
    rawBytes = secureEncoder.decrypt(rawBytes)
    return rawBytes

def saveCacheFile(filename, metadata, raw_bytes):
    source_file = models.SourceFile.create(type=metadata["UploadType"], metadata=metadata)
    source_file.name = filename
    source_file.pointer = DATABASE_PATH + "cache" + os.path.sep + source_file.uid + "_" + filename
    hashed = Database.saveSourceFile(secureEncoder.encrypt(raw_bytes), source_file.pointer, bytes=True)
    source_file.hashed = hashed
    source_file.save()
    return source_file

def NeuroPacePersystDatDecoder(source_file, person=None):
    rawBytes = loadCacheFile(source_file)

    # Process Patient/Device/Electrode Information for Storage and Query
    PatientInformation = source_file.metadata["layout"]["PatientInformation"]

    lock = FileLock(DATABASE_PATH + "ParticipantInfoLookup.lock")
    with lock.acquire(timeout=180):
        if not person:
            person, person_created = models.Participant.find_or_create(PatientInformation["Initials"], PatientInformation["Identifier"], source_file.metadata["Institute"])
            if person_created:
                person.date_of_birth = PatientInformation["Timestamp"] if "Timestamp" in PatientInformation.keys() else 0
                person.sex = PatientInformation["Gender"] if "Gender" in PatientInformation.keys() else "Unknown"
                person.diagnosis = PatientInformation["Diagnosis"] if "Diagnosis" in PatientInformation.keys() else "Unknown"
                person.institute_id = source_file.metadata["Institute"]
                person.save()
        
        
        device = models.DBSDevice.find(owner=person, type="NeuroPace " + PatientInformation["DeviceType"], serial_number=PatientInformation["DeviceIdentifier"] if "DeviceIdentifier" in PatientInformation.keys() else "")
        if not device:
            device = models.DBSDevice(serial_number=PatientInformation["DeviceIdentifier"] if "DeviceIdentifier" in PatientInformation.keys() else "", type="NeuroPace " + PatientInformation["DeviceType"])
            device.owner = person
            device.name = ""
            device.device_bloodline = ""
            device.save()
        
        # Electrode Information not available for RNS.
        
    Recordings = parsePersystRecording(rawBytes, source_file.metadata["layout"])
    for stream in Recordings:
        recording = models.Recording(**{key: stream[key] for key in stream.keys() if key in ["name", "type", "date", "metadata"]}, source=source_file)
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__owner=person, source__metadata__Uploader=source_file.metadata["Uploader"]):
            recording.delete()
            continue
        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(stream["recording"], filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue 
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + person.uid, exist_ok=True)
    shutil.move(source_file.pointer, DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".persystdat")
    source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".persystdat"
    source_file.metadata["Timezone"] = ""
    source_file.metadata["Device"] = device.uid
    source_file.owner = person
    source_file.save()

    person.last_update = models.current_time()
    person.save()
    return True

def MedtronicPerceptJSONDecoder(source_file, device=None, person=None):
    rawBytes = loadCacheFile(source_file)
    JSON = json.loads(rawBytes)
    if source_file.metadata["automatic_concatenation"]:
        JSON["AutomaticStreamingFix"] = True
    else:
        JSON["AutomaticStreamingFix"] = False
    
    DatabaseEntries = decodeMedtronicJSON(JSON)
    
    if source_file.metadata["automatic_deidentification"]:
        DatabaseEntries["SessionOverview"]["Name"] = hmac.new(HASH_KEY.encode("utf8"), DatabaseEntries["SessionOverview"]["Name"].encode("utf-8"), hashlib.sha256).hexdigest()
        DatabaseEntries["SessionOverview"]["DOB"] = DatabaseEntries["SessionOverview"]["DOB"] + int.from_bytes(base64.b64encode(DatabaseEntries["SessionOverview"]["Name"].encode("utf-8"))[8:13], "little") / 1000
        DatabaseEntries["SessionOverview"]["MRN"] = hmac.new(HASH_KEY.encode("utf8"), DatabaseEntries["SessionOverview"]["MRN"].encode("utf-8"), hashlib.sha256).hexdigest()
        DatabaseEntries["SessionOverview"]["Device"]["SerialNumber"] = hmac.new(HASH_KEY.encode("utf8"), DatabaseEntries["SessionOverview"]["Device"]["SerialNumber"].encode("utf-8"), hashlib.sha256).hexdigest()

    # Process Patient/Device/Electrode Information for Storage and Query
    lock = FileLock(DATABASE_PATH + "ParticipantInfoLookup.lock")
    with lock.acquire(timeout=180):
        if not device:
            device, device_created = models.DBSDevice.find_or_create(DatabaseEntries["SessionOverview"]["Device"]["SerialNumber"], 
                                                                     DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"], 
                                                                     DatabaseEntries["SessionOverview"]["Device"]["Type"], source_file.metadata["Institute"])
            if not device_created and device.owner.institute_id == source_file.metadata["Institute"]:
                if not person:
                    person = device.owner
                else:
                    if not person.uid == device.owner.uid:
                        raise Exception("Attempting to upload data of another Participant. Please merge record before attempt so")
            else:
                if not person:
                    person, person_created = models.Participant.find_or_create(DatabaseEntries["SessionOverview"]["Name"], DatabaseEntries["SessionOverview"]["MRN"], source_file.metadata["Institute"])
                    if person_created:
                        person.date_of_birth = DatabaseEntries["SessionOverview"]["DOB"]
                        person.sex = DatabaseEntries["SessionOverview"]["Sex"]
                        person.diagnosis = DatabaseEntries["SessionOverview"]["Diagnosis"]
                        person.institute_id = source_file.metadata["Institute"]
                        person.save()
                
                device.owner = person
                device.name = DatabaseEntries["SessionOverview"]["Device"]["Name"]
                device.implanted_date = DatabaseEntries["SessionOverview"]["Device"]["ImplantDate"]
                device.implanted_location = DatabaseEntries["SessionOverview"]["Device"]["Location"]
                device.estimated_eol = DatabaseEntries["SessionOverview"]["Device"]["EOL"]
                device.device_bloodline = DatabaseEntries["SessionOverview"]["Device"]["Location"]
                device.save()
        
        elif not person:
            person = device.owner

        # This method is designed in a way that Electroe remain the same even with new DBS device. 
        for lead in DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"]:
            electrode, electrode_created = models.Electrode.find_or_create(person, lead["type"], lead["name"])
            if electrode_created:
                electrode.type = lead["type"]
                electrode.custom_name = lead["custom_name"]
                electrode.channel_count = lead["channel_count"]
                electrode.channel_names = lead["channel_names"]
                electrode.save()
            
            if not device.electrodes.filter(uid=electrode.uid).exists():
                device.electrodes.add(electrode)
            
            if DatabaseEntries["SessionOverview"]["SessionTimestamp"] < electrode.implanted_date:
                electrode.implanted_date = DatabaseEntries["SessionOverview"]["SessionTimestamp"]
                electrode.save()
        
        source_file.owner = person
        source_file.save()

    
    electrodes = device.electrodes.all()
    for k in range(len(DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"])):
        for elec in electrodes:
            if DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"][k]["name"] == elec.target:
                if elec.channel_count == DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"][k]["channel_count"]:
                    if elec.type == DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"][k]["type"]:
                        DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"][k]["model"] = elec 

    # Therapy History Storage
    for therapy in DatabaseEntries["Therapies"]:
        electrode = None
        for k in range(len(DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"])):
            if DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"][k]["name"].startswith(therapy["hemisphere"]):
                electrode = DatabaseEntries["SessionOverview"]["Device"]["ConnectedLeads"][k].get("model", None)

        if Therapy.checkDuplicate(device, electrode, therapy):
            continue 
        
        therapy_object = models.Therapy(**{key: therapy[key] for key in therapy.keys() if key in ["name", "type", "date"]}, source=source_file)
        therapy_object.save()

        stimulation_therapy = models.ElectricalTherapy(**{key: therapy[key] for key in therapy.keys() if key in ["group_type", "group_name", "group_id", "stimulation_type"]}, therapy=therapy_object)
        stimulation_therapy.save()

        for i in range(len(therapy["stimulation_settings"])):
            setting = therapy["stimulation_settings"][i]

            if not electrode:
                electrode = device.electrodes.filter(target__startswith=therapy["hemisphere"]).first()
                
            detail_setting = models.ElectricalStimulation(**{key: setting[key] for key in setting.keys() if key in ["contact", "return_contact", "amplitude", "amplitude_fraction", "amplitude_unit", "pulsewidth", "pulsewidth_unit", "frequency", "cycling", "cycling_period"]}, group=stimulation_therapy)
            detail_setting.electrode = electrode
            detail_setting.save()
            stimulation_therapy.stimulation_settings.add(detail_setting)
    
            detail_setting = models.AdaptiveTherapy(group=stimulation_therapy)
            if therapy["sensing_settings"][i]:
                detail_setting.sensing_type = therapy["sensing_settings"][i]["type"]
                detail_setting.sensing = therapy["sensing_settings"][i]["sensing"]
                
            if therapy["adaptive_settings"][i]:
                detail_setting.adaptive_type = therapy["adaptive_settings"][i]["type"]
                detail_setting.adaptive = therapy["adaptive_settings"][i]["adaptive"]
            detail_setting.save()
            stimulation_therapy.adaptive_settings.add(detail_setting)
    
    AllEntries = []
    for log in DatabaseEntries["TherapyChangeHistory"]:
        if models.TherapyModification.include(date=log["date"], type=log["type"], source__metadata__Device=device.uid, owner=person):
            continue
        AllEntries.append(models.TherapyModification(**log, source=source_file, owner=person))
    models.TherapyModification.objects.bulk_create(AllEntries)
    
    for survey in DatabaseEntries["SurveyRecordings"]:
        recording = models.Recording(**{key: survey[key] for key in survey.keys() if key in ["name", "type", "date", "metadata"]}, source=source_file)
        content_hashed = hmac.new(HASH_KEY.encode("utf8"), pickle.dumps(survey["recording"]), hashlib.sha256).hexdigest()
        recording.metadata["ContentHash"] = content_hashed
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__owner=person):
            recording.delete()
            continue
        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(survey["recording"], filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue 
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

    for stream in DatabaseEntries["StreamingRecordings"]:
        recording = models.Recording(**{key: stream[key] for key in stream.keys() if key in ["name", "type", "date", "metadata"]}, source=source_file)
        content_hashed = hmac.new(HASH_KEY.encode("utf8"), pickle.dumps(stream["recording"]), hashlib.sha256).hexdigest()
        recording.metadata["ContentHash"] = content_hashed
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__owner=person):
            recording.delete()
            continue
        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(stream["recording"], filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue 
        
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

    for stream in DatabaseEntries["ChronicRecordings"]:
        recording = models.Recording(**{key: stream[key] for key in stream.keys() if key in ["name", "type", "date", "metadata"]}, source=source_file)
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__owner=person):
            recording.delete()
            continue

        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(stream["recording"], filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

        full_recording = models.Recording.find(type="MedtronicChronicNeuralActivity", source__owner=person)
        if full_recording:
            full_recording.delete()

    for event in DatabaseEntries["EventRecordings"]:
        if models.DBSEvent.include(date=event["date"], type=event["type"], name=event["name"], source__owner=person):
            continue
        event_log = models.DBSEvent(**{key: event[key] for key in event.keys() if key in ["name", "type", "date"]}, source=source_file)
        event_log.save()
        if "data" in event.keys():
            recording = models.Recording(**{key: event[key] for key in event.keys() if key in ["name", "type", "date", "metadata"]}, source=source_file)
            recording.metadata = {**recording.metadata, **event["data"]}
            recording.save()
            event_log.data.add(recording)
    
    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + person.uid, exist_ok=True)
    shutil.move(source_file.pointer, DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".json")
    source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".json"
    source_file.metadata["Timezone"] = DatabaseEntries["SessionOverview"]["SessionTimezone"]
    source_file.metadata["Device"] = device.uid
    source_file.metadata["SessionEndTimestamp"] = DatabaseEntries["SessionOverview"]["SessionEndTimestamp"]
    source_file.owner = person
    source_file.date = DatabaseEntries["SessionOverview"]["SessionTimestamp"]
    source_file.save()

    person.last_update = models.current_time()
    person.save()
    return True

def NeuroImageStorage(source_file, person):
    os.makedirs(DATABASE_PATH + "imaging" + os.path.sep + person.uid, exist_ok=True)
    if source_file.pointer.endswith(".nii") or source_file.pointer.endswith(".nii.gz"):
        source_file.metadata["FileType"] = "NifTi"
    elif source_file.pointer.endswith(".stl"):
        source_file.metadata["FileType"] = "STL"
    elif source_file.pointer.endswith(".glb"):
        source_file.metadata["FileType"] = "Blender Scene"
    else:
        source_file.metadata["FileType"] = "Unknown"

    shutil.move(source_file.pointer, DATABASE_PATH + "imaging" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".image")
    source_file.pointer = DATABASE_PATH + "imaging" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".image"
    source_file.metadata["Timezone"] = ""
    source_file.metadata["Device"] = ""
    source_file.owner = person
    source_file.save()

def EventCSVDecoder(source_file, person):
    rawBytes = loadCacheFile(source_file)
    CSV = pd.read_csv(BytesIO(rawBytes), skiprows=0)

    if not "Time" in CSV.keys() or not "Annotation" in CSV.keys() or not "Type" in CSV.keys() or not "Duration" in CSV.keys():
        raise Exception("CSV Format Error")
    
    for i in CSV.index:
        Timestamp = 0
        try:
            Timestamp = datetime.datetime.fromisoformat(CSV["Time"][i]).timestamp()
        except:
            Timestamp = float(CSV["Time"][i])
        Event.addAnnotation(person.uid, CSV["Type"][i], CSV["Annotation"][i], Timestamp, CSV["Duration"][i])

def MATFileDecoder(source_file, person, startTime=None):
    rawBytes = loadCacheFile(source_file)
    DataType, MATFile = decodeMATLABFile(rawBytes)

    def CommonName(nameList):
        commonNames = []
        allSubString = nameList[0].split(" ")
        for i in range(len(allSubString)):
            Found = True
            for j in range(len(nameList)):
                if not allSubString[i] in nameList[j].split(" "):
                    Found = False
            if Found:
                commonNames.append(allSubString[i])
        return commonNames
    
    if DataType == "ExternalSensorStreaming":
        for ProcessedData in MATFile:
            if startTime and ProcessedData["StartTime"] == 0:
                ProcessedData["StartTime"] = startTime

            recording = models.Recording(**{
                "name": "", "type": "MATFile", "date": ProcessedData["StartTime"], "metadata": {
                    "SensorType": ("_".join(CommonName(ProcessedData["ChannelNames"]))),
                    "Duration": ProcessedData["Duration"],
                    "ChannelNames": ProcessedData["ChannelNames"]
                }
            }, source=source_file)
            if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__owner=person):
                recording.delete()
                continue

            filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
            hashed = Database.saveSourceFile(ProcessedData, filename)
            # TODO: Error handling
            if not hashed:
                print("Hashing Failed for Data Storage")
                print(recording.__dict__)
                continue 
            if models.Recording.include(hashed=hashed, source__owner=person):
                recording.delete()
            else:
                recording.pointer = filename
                recording.hashed = hashed
                recording.save()

    elif DataType == "CustomizedTimelineData":
        for ProcessedData in MATFile:
            recording = models.Recording(**{
                "name": "", "type": "CustomizedTimelineData", "date": ProcessedData["StartTime"], "metadata": {
                    "ChannelNames": ProcessedData["ChannelNames"]
                }
            }, source=source_file)
            if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__owner=person):
                recording.delete()
                continue

            filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
            hashed = Database.saveSourceFile(ProcessedData, filename)
            # TODO: Error handling
            if not hashed:
                print("Hashing Failed for Data Storage")
                print(recording.__dict__)
                continue 
            if models.Recording.include(hashed=hashed, source__owner=person):
                recording.delete()
            else:
                recording.pointer = filename
                recording.hashed = hashed
                recording.save()

    elif DataType == "CustomizedStreamingData":
        for ProcessedData in MATFile:
            if "RecordingName" in ProcessedData["Descriptor"].keys():
                name = ProcessedData["Descriptor"]["RecordingName"]
            else:
                name = ""
            recording = models.Recording(**{
                "name": name, "type": "CustomizedStreamingData", "date": ProcessedData["StartTime"], "metadata": {**{
                    "ChannelNames": ProcessedData["ChannelNames"],
                    "Duration": ProcessedData["Duration"]
                }, **ProcessedData["Descriptor"]}
            }, source=source_file)
            if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__owner=person):
                recording.delete()
                continue

            filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
            hashed = Database.saveSourceFile(ProcessedData, filename)
            # TODO: Error handling
            if not hashed:
                print("Hashing Failed for Data Storage")
                print(recording.__dict__)
                continue 
            if models.Recording.include(hashed=hashed, source__owner=person):
                recording.delete()
            else:
                recording.pointer = filename
                recording.hashed = hashed
                recording.save()
            
    else:
        raise Exception("MAT File DataType Incorrect")

    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + person.uid, exist_ok=True)
    shutil.move(source_file.pointer, DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat")
    source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat"
    source_file.metadata["Timezone"] = ""
    if not "Device" in source_file.metadata.keys():
        source_file.metadata["Device"] = ""
    source_file.owner = person
    source_file.save()

    person.last_update = models.current_time()
    person.save()
    
    models.SourceFile.purge(type="CachedResult", date__lt=person.last_update, metadata__Participant=person.uid)
    return True

def HPFCSVDecoder(source_file, person, startTime=None):
    rawBytes = loadCacheFile(source_file)
    TrignoData = decodeHPFCSVData(rawBytes)

    def CommonName(nameList):
        commonNames = []
        allSubString = nameList[0].split(" ")
        for i in range(len(allSubString)):
            Found = True
            for j in range(len(nameList)):
                if not allSubString[i] in nameList[j].split(" "):
                    Found = False 
            if Found:
                commonNames.append(allSubString[i])
        return commonNames

    for ProcessedData in TrignoData:
        if startTime and ProcessedData["StartTime"] == 0:
            ProcessedData["StartTime"] = startTime

        recording = models.Recording(**{
            "name": "", "type": "HPFCSV", "date": ProcessedData["StartTime"], "metadata": {
                "SensorType": ("_".join(CommonName(ProcessedData["ChannelNames"]))),
                "Duration": ProcessedData["Duration"],
                "ChannelNames": ProcessedData["ChannelNames"]
            }
        }, source=source_file)
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__owner=person):
            recording.delete()
            continue

        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(ProcessedData, filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue 
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + person.uid, exist_ok=True)
    shutil.move(source_file.pointer, DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat")
    source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat"
    source_file.metadata["Timezone"] = ""
    source_file.metadata["Device"] = ""
    source_file.owner = person
    source_file.save()

    person.last_update = models.current_time()
    person.save()
    
    models.SourceFile.purge(type="CachedResult", date__lt=person.last_update, metadata__Participant=person.uid)
    return True

def AlphaOmegaMPXDecoder(source_file, person, name=""):
    rawBytes = loadCacheFile(source_file)
    MPXData = extractAlphaOmegaRecordings(rawBytes)
    
    def CommonName(nameList):
        commonNames = []
        allSubString = nameList[0].split(" ")
        for i in range(len(allSubString)):
            Found = True
            for j in range(len(nameList)):
                if not allSubString[i] in nameList[j].split(" "):
                    Found = False 
            if Found:
                commonNames.append(allSubString[i])
        return commonNames

    for ProcessedData in MPXData:
        recording = models.Recording(**{
            "name": name, "type": "AOMPX", "date": ProcessedData["StartTime"], "metadata": {
                "SensorType": ("_".join(CommonName(ProcessedData["ChannelNames"]))),
                "Duration": ProcessedData["Duration"],
                "ChannelNames": ProcessedData["ChannelNames"]
            }
        }, source=source_file)
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__metadata__Uploader=source_file.metadata["Uploader"]):
            recording.delete()
            continue

        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(ProcessedData, filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue 
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + person.uid, exist_ok=True)
    shutil.move(source_file.pointer, DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat")
    source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat"
    source_file.metadata["Timezone"] = ""
    source_file.metadata["Device"] = ""
    source_file.owner = person
    source_file.save()

    person.last_update = models.current_time()
    person.save()
    
    models.SourceFile.purge(type="CachedResult", date__lt=person.last_update, metadata__Participant=person.uid)
    return True

def UFMDATDecoder(source_file, person):
    rawBytes = loadCacheFile(source_file)
    TrignoData = decodeMDATData(rawBytes)

    for ProcessedData in TrignoData:
        recording = models.Recording(**{
            "name": "", "type": "DelsysMDAT", "date": ProcessedData["StartTime"], "metadata": {
                "SensorType": ProcessedData["ChannelNames"][0].split(".")[0],
                "Duration": ProcessedData["Duration"],
                "ChannelNames": ProcessedData["ChannelNames"]
            }
        }, source=source_file)
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__metadata__Uploader=source_file.metadata["Uploader"]):
            recording.delete()
            continue

        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(ProcessedData, filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue 
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + person.uid, exist_ok=True)
    shutil.move(source_file.pointer, DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat")
    source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat"
    source_file.metadata["Timezone"] = ""
    source_file.metadata["Device"] = ""
    source_file.owner = person
    source_file.save()

    person.last_update = models.current_time()
    person.save()
    
    models.SourceFile.purge(type="CachedResult", date__lt=person.last_update, metadata__Participant=person.uid)
    return True

def UFMDATv2Decoder(source_file, person):
    rawBytes = loadCacheFile(source_file)
    TrignoData = decodeMDATv2(rawBytes)

    def CommonName(nameList):
        commonNames = []
        allSubString = nameList[0].split(" ")
        for i in range(len(allSubString)):
            Found = True
            for j in range(len(nameList)):
                if not allSubString[i] in nameList[j].split(" "):
                    Found = False
            if Found:
                commonNames.append(allSubString[i])
        return commonNames
    
    try:
        SourceFilename = source_file.name.replace(source_file.name[source_file.name.index("["):source_file.name.index("]")+1], "").replace(".mdat","")
    except Exception as e:
        SourceFilename = ""

    for ProcessedData in TrignoData:
        recording = models.Recording(**{
            "name": SourceFilename, "type": "SynchronizedMDAT", "date": ProcessedData["StartTime"], "metadata": {
                "SensorType": ("_".join(CommonName(ProcessedData["ChannelNames"]))),
                "Duration": ProcessedData["Duration"],
                "ChannelNames": ProcessedData["ChannelNames"]
            }
        }, source=source_file)
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__metadata__Uploader=source_file.metadata["Uploader"]):
            recording.delete()
            continue

        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(ProcessedData, filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue 
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + person.uid, exist_ok=True)
    shutil.move(source_file.pointer, DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat")
    source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat"
    source_file.metadata["Timezone"] = ""
    source_file.metadata["Device"] = ""
    source_file.owner = person
    source_file.save()

    person.last_update = models.current_time()
    person.save()
    
    models.SourceFile.purge(type="CachedResult", date__lt=person.last_update, metadata__Participant=person.uid)
    return True

def UFMDATv3Decoder(source_file, person):
    rawBytes = loadCacheFile(source_file)
    TrignoData = decodeMDATv3(rawBytes)

    def CommonName(nameList):
        commonNames = []
        allSubString = nameList[0].split(" ")
        for i in range(len(allSubString)):
            Found = True
            for j in range(len(nameList)):
                if not allSubString[i] in nameList[j].split(" "):
                    Found = False
            if Found:
                commonNames.append(allSubString[i])
        return commonNames
    
    try:
        SourceFilename = source_file.name.replace(source_file.name[source_file.name.index("["):source_file.name.index("]")+1], "").replace(".mdat","")
    except Exception as e:
        SourceFilename = ""

    for ProcessedData in TrignoData:
        recording = models.Recording(**{
            "name": SourceFilename, "type": "SynchronizedMDAT", "date": ProcessedData["StartTime"], "metadata": {
                "SensorType": ("_".join(CommonName(ProcessedData["ChannelNames"]))),
                "Duration": ProcessedData["Duration"],
                "ChannelNames": ProcessedData["ChannelNames"]
            }
        }, source=source_file)
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__metadata__Uploader=source_file.metadata["Uploader"]):
            recording.delete()
            continue

        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(ProcessedData, filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue 
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + person.uid, exist_ok=True)
    shutil.move(source_file.pointer, DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat")
    source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat"
    source_file.metadata["Timezone"] = ""
    source_file.metadata["Device"] = ""
    source_file.owner = person
    source_file.save()

    person.last_update = models.current_time()
    person.save()
    
    models.SourceFile.purge(type="CachedResult", date__lt=person.last_update, metadata__Participant=person.uid)
    return True

def BRAVORecordingBinaryDecoder(source_file, person):
    rawBytes = loadCacheFile(source_file)
    rawBytes = blosc2.decompress(rawBytes)
    Recordings = decodebdata(rawBytes)

    try:
        SourceFilename = source_file.name.replace(source_file.name[source_file.name.index("["):source_file.name.index("]")+1], "").replace(".bdata","")
    except Exception as e:
        SourceFilename = ""

    RecordingTypes = []
    for i in range(len(Recordings)):
        if "RecordingType" in Recordings[i]["Metadata"].keys():
            if not Recordings[i]["Metadata"]["RecordingType"] in RecordingTypes:
                RecordingTypes.append(Recordings[i]["Metadata"]["RecordingType"])
    
    for i in range(len(RecordingTypes)):
        ProcessedData = [Recording for Recording in Recordings if Recording["Metadata"]["RecordingType"] == RecordingTypes[i]]
        StartTime = ProcessedData[0]["StartTime"]
        ChannelNames = []
        for j in range(len(ProcessedData)):
            if ProcessedData[j]["StartTime"] < StartTime:
                StartTime = ProcessedData[j]["StartTime"]

            for k in range(len(ProcessedData[j]["ChannelNames"])):
                if not ProcessedData[j]["ChannelNames"][k] in ChannelNames:
                    ChannelNames.append(ProcessedData[j]["ChannelNames"][k])

        recording = models.Recording(**{
            "name": SourceFilename, "type": RecordingTypes[i], "date": StartTime, "metadata": {
                "ChannelNames": ChannelNames
            }
        }, source=source_file)
        if models.Recording.include(date=recording.date, type=recording.type, metadata=recording.metadata, source__metadata__Uploader=source_file.metadata["Uploader"]):
            recording.delete()
            continue

        filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
        hashed = Database.saveSourceFile(ProcessedData, filename)
        # TODO: Error handling
        if not hashed:
            print("Hashing Failed for Data Storage")
            print(recording.__dict__)
            continue 
        if models.Recording.include(hashed=hashed, source__owner=person):
            recording.delete()
        else:
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

    os.makedirs(DATABASE_PATH + "raws" + os.path.sep + person.uid, exist_ok=True)
    shutil.move(source_file.pointer, DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat")
    source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + person.uid + os.path.sep + source_file.uid + ".mdat"
    source_file.metadata["Timezone"] = ""
    source_file.metadata["Device"] = ""
    source_file.owner = person
    source_file.save()

    person.last_update = models.current_time()
    person.save()
    
    models.SourceFile.purge(type="CachedResult", date__lt=person.last_update, metadata__Participant=person.uid)
    return True

def ImportBRAVOExport(source_file):
    rawBytes = loadCacheFile(source_file)
    if not rawBytes[:12].decode("utf-8") == "BRAVO EXPORT":
        raise Exception("Incorrect File Format")

    FernetEncoder = Fernet(source_file.metadata["Password"])

    HeaderSize = int.from_bytes(rawBytes[12:16], "little")
    Header = json.loads(FernetEncoder.decrypt(rawBytes[16:16+HeaderSize].decode("utf-8")))
    
    if source_file.metadata["automatic_deidentification"]:
        Header["Name"] = hmac.new(HASH_KEY.encode("utf8"), Header["Name"].encode("utf-8"), hashlib.sha256).hexdigest()
        Header["DOB"] = Header["DOB"] + int.from_bytes(base64.b64encode(Header["Name"].encode("utf-8"))[8:13], "little") / 1000
        Header["MRN"] = hmac.new(HASH_KEY.encode("utf8"), Header["MRN"].encode("utf-8"), hashlib.sha256).hexdigest()
        for i in range(len(Header["Devices"])):
            Header["Devices"][i]["SerialNumber"] = hmac.new(HASH_KEY.encode("utf8"), Header["Devices"][i]["SerialNumber"].encode("utf-8"), hashlib.sha256).hexdigest()

    # Process Patient/Device/Electrode Information for Storage and Query
    person = models.Participant.find(uid=uuid.UUID(Header["Id"]).hex)
    if person:
        raise Exception("Participant with the same UID Existed")
    for i in range(len(Header["Devices"])):
        device = models.DBSDevice.find(serial_number=Header["Devices"][i]["SerialNumber"])
        if device:
            print(device.__dict__)
            raise Exception("Device ID Existed")
    
    person = models.Participant(uid=uuid.UUID(Header["Id"]).hex, name=Header["Name"], sex=Header["Gender"], date_of_birth=Header["DOB"],
                        diagnosis=Header["Diagnosis"], mrn=Header["MRN"], institute_id=source_file.metadata["Institute"])
    
    person.save()
    
    currentIndex = 16+HeaderSize
    while currentIndex < len(rawBytes):
        PacketType = rawBytes[currentIndex:currentIndex+7].decode("utf-8")
        if PacketType == "NVMSEDA":
            PacketSize = int.from_bytes(rawBytes[currentIndex+7:currentIndex+11], "little")
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+11:currentIndex+11+PacketSize])
            metadata = {**source_file.metadata, **{
                "UploadType": "MedtronicJSON",
                "UniqueHashed": hmac.new(HASH_KEY.encode("utf8"), PacketContent, hashlib.sha256).hexdigest()
            }}

            json_file = saveCacheFile(person.uid + "_" + uuid.uuid4().hex + ".json", metadata, PacketContent)
            #lockFile = json_file.pointer + ".lock"
            if models.SourceFile.objects.exclude(pk=json_file.pk).filter(metadata__Institute=metadata["Institute"], metadata__UniqueHashed=metadata["UniqueHashed"]).exists():
                json_file.delete()
            else:
                try:
                    MedtronicPerceptJSONDecoder(json_file, person=person)
                except Exception as e:
                    json_file.delete()
                    person.delete()
                    raise Exception("Processing Error: " + str(e))
            currentIndex += 11+PacketSize

        elif PacketType == "EVSDADA":
            PacketSize = int.from_bytes(rawBytes[currentIndex+7:currentIndex+11], "little")
            PacketContent = json.loads(FernetEncoder.decrypt(rawBytes[currentIndex+11:currentIndex+11+PacketSize]).decode("utf-8"))
            models.Annotation(name=PacketContent["Name"], type=PacketContent["Type"], date=PacketContent["Date"], duration=PacketContent["Duration"], owner=person).save()
            currentIndex += 11+PacketSize

        elif PacketType == "AVSDADA":
            PacketSize = int.from_bytes(rawBytes[currentIndex+7:currentIndex+11], "little")
            PacketHeader = json.loads(FernetEncoder.decrypt(rawBytes[currentIndex+11:currentIndex+11+PacketSize]).decode("utf-8"))
            PacketContentSize = int.from_bytes(rawBytes[currentIndex+11+PacketSize:currentIndex+15+PacketSize], "little")
            PacketContent = rawBytes[currentIndex+15+PacketSize:currentIndex+15+PacketSize+PacketContentSize]
            
            metadata = {
                "UploadType": "ImportedSource",
                "Institute": source_file.metadata["Institute"],
                "Uploader": source_file.metadata["Uploader"],
                "UniqueHashed": source_file.uid
            }

            bin_file = models.SourceFile.find(type="ImportedSource", name=source_file.uid, owner=person)
            if not bin_file:
                bin_file = models.SourceFile(type="ImportedSource", name=source_file.uid, owner=person)
                bin_file.save()
            
            recording = models.Recording(name="ExternalRecording", type=PacketHeader["Type"], date=PacketHeader["Date"], metadata=PacketHeader, source=bin_file)
            filename = DATABASE_PATH + "recordings" + os.path.sep + person.uid + os.path.sep + recording.uid + ".bdat"
            hashed = Database.saveSourceFile(pickle.loads(PacketContent), filename)
            # TODO: Error handling
            if not hashed:
                print("Hashing Failed for Data Storage")
                print(recording.__dict__)
            else:
                recording.pointer = filename
                recording.hashed = hashed
                recording.save()
            
            currentIndex += 15+PacketSize+PacketContentSize

def createExportContent(message, encoder=None):
    if encoder:
        encryptedMessage = encoder.encrypt(message.encode("utf-8"))
        return encryptedMessage
    return message.encode("utf-8")

def ImportBRAVOStructure(source_file):
    rawBytes = loadCacheFile(source_file)
    raise Exception("Not Implemented Yet")
    if not rawBytes[:12].decode("utf-8") == "BRAVO Export":
        raise Exception("Incorrect File Format")

    if source_file.metadata["Password"] == "":
        hashed_key = hashlib.sha256(b"BRAVOExportv2").digest()
    else:
        hashed_key = hashlib.sha256(source_file.metadata["Password"].encode("utf-8")).digest()
    export_key = base64.urlsafe_b64encode(hashed_key)
    FernetEncoder = Fernet(export_key)

    UIDMapper = {}

    currentIndex = 12
    while currentIndex < len(rawBytes):
        HeaderBytes = rawBytes[currentIndex:currentIndex+8]
        ContentSize = int.from_bytes(rawBytes[currentIndex+8:currentIndex+12], "little")

        if HeaderBytes == b"XXXXPART":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            participant = models.Participant(
                name=Content["name"], date_of_birth=Content["date_of_birth"], 
                sex=Content["sex"], mrn=Content["mrn"],
                diagnosis=Content["diagnosis"], disease_start_time=Content["disease_start_time"],
            )
            participant.save()
            UIDMapper[Content["uid"]] = participant

            for tag in Content["tags"]:
                tagObj = models.Tag.find(name=tag)
                if not tagObj:
                    tagObj = models.Tag(name=tag)
                    tagObj.save()
                participant.tags.add(tagObj)
            currentIndex += 12 + ContentSize
        
        elif HeaderBytes == b"XXXXDBSD":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            device = models.DBSDevice(
                owner=participant,
                name=Content["name"],
                type=Content["type"],
                serial_number=Content["serial_number"],
                implanted_location=Content["implanted_location"],
                implanted_date=Content["implanted_date"],
                estimated_eol=Content["estimated_eol"],
                device_bloodline=Content["device_bloodline"],
            )
            device.save()
            UIDMapper[Content["uid"]] = device
            currentIndex += 12 + ContentSize

        elif HeaderBytes == b"XXXXMERD":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            device = models.MERDevice(
                owner=participant,
                name=Content["name"],
                type=Content["type"],
            )
            device.save()
            UIDMapper[Content["uid"]] = device
            currentIndex += 12 + ContentSize

        elif HeaderBytes == b"XXXXELEC":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            electrode = models.Electrode(
                owner=participant,
                type=Content["type"],
                name=Content["name"],
                hemisphere=Content["hemisphere"],
                target=Content["target"],
                custom_name=Content["custom_name"],
                channel_count=Content["channel_count"],
                channel_names=Content["channel_names"],
                channel_mapping=Content["channel_mapping"],
                channel_coordinates=Content["channel_coordinates"],
                implanted_date=Content["implanted_date"],
            )
            electrode.save()
            UIDMapper[Content["uid"]] = electrode

            device = UIDMapper[Content["device"]]
            device.electrodes.add(electrode)
            currentIndex += 12 + ContentSize
        
        elif HeaderBytes == b"XXXXFITB":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            device = models.FitbitDevice(
                owner=participant,
                name=Content["name"],
                type=Content["type"],
                pkce=Content["pkce"],
                auth=Content["auth"],
                date_periods=Content["date_periods"],
            )
            device.save()
            UIDMapper[Content["uid"]] = device
            currentIndex += 12 + ContentSize
        
        elif HeaderBytes == b"XXXXOURA":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            device = models.OuraRingDevice(
                owner=participant,
                name=Content["name"],
                type=Content["type"],
                pkce=Content["pkce"],
                auth=Content["auth"],
                date_periods=Content["date_periods"],
            )
            device.save()
            UIDMapper[Content["uid"]] = device
            currentIndex += 12 + ContentSize
        
        elif HeaderBytes == b"XXXXSOUR":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            source_file = models.SourceFile(
                owner=participant,
                name=Content["name"],
                type=Content["type"],
                date=Content["date"],
                metadata=Content["metadata"],
            )
            source_file.save()
            UIDMapper[Content["uid"]] = source_file

            if Content["type"] == "MedtronicJSON":
                hashed = Database.saveSourceFile({}, DATABASE_PATH + "raws" + os.path.sep + participant.uid + os.path.sep + source_file.uid + ".json")
                source_file.pointer = DATABASE_PATH + "raws" + os.path.sep + participant.uid + os.path.sep + source_file.uid + ".json"
                source_file.hashed = hashed
                source_file.save()

            currentIndex += 12 + ContentSize
        
        elif HeaderBytes == b"XXXXTMOD":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            event = models.TherapyModification(
                owner=participant,
                name=Content["name"],
                type=Content["type"],
                date=Content["date"],
                previous_state=Content["previous_state"],
                new_state=Content["new_state"],
            )

            if not Content["source"] == "":
                event.source = UIDMapper[Content["source"]]
            event.save()

            currentIndex += 12 + ContentSize
        
        elif HeaderBytes == b"XXXXANNO":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            event = models.Annotation(
                owner=participant,
                name=Content["name"],
                type=Content["type"],
                date=Content["date"],
                duration=Content["duration"],
            )

            if not Content["source"] == "":
                event.source = UIDMapper[Content["source"]]
            event.save()

            currentIndex += 12 + ContentSize
        
        elif HeaderBytes == b"XXXXDBSE":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            event = models.DBSEvent(
                name=Content["name"],
                type=Content["type"],
                date=Content["date"],
            )
            
            if not Content["source"] == "":
                event.source = UIDMapper[Content["source"]]
            event.save()

            currentIndex += 12 + ContentSize
            
        elif HeaderBytes == b"XXXXRECD":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            recording = models.Recording(
                name=Content["name"],
                type=Content["type"],
                date=Content["date"],
                adjusted_alignment=Content["adjusted_alignment"],
                hashed=Content["hashed"],
                metadata=Content["metadata"],
                source=UIDMapper[Content["source"]]
            )
            recording.save()
            UIDMapper[Content["uid"]] = recording
            currentIndex += 12 + ContentSize
            
            HeaderBytes = rawBytes[currentIndex:currentIndex+8]
            ContentSize = int.from_bytes(rawBytes[currentIndex+8:currentIndex+12], "little")
            if HeaderBytes == b"XXXXRAWD":
                recording.pointer = DATABASE_PATH + "recordings" + os.path.sep + participant.uid + os.path.sep + recording.uid + ".bdat"
                Content = rawBytes[currentIndex+12:currentIndex+12+ContentSize]
                Database.saveSourceBinary(recording.pointer, Content)
                recording.save()
                currentIndex += 12 + ContentSize
        
        elif HeaderBytes == b"XXXXTHER":
            PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
            Content = json.loads(PacketContent)

            therapy = models.Therapy(
                name=Content["name"],
                type=Content["type"],
                date=Content["date"],
                source=UIDMapper[Content["source"]]
            )
            therapy.save()
            UIDMapper[Content["uid"]] = therapy
            currentIndex += 12 + ContentSize

            HeaderBytes = rawBytes[currentIndex:currentIndex+8]
            ContentSize = int.from_bytes(rawBytes[currentIndex+8:currentIndex+12], "little")
            if HeaderBytes == b"XXXXETHE":
                PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
                Content = json.loads(PacketContent)

                eTherapy = models.ElectricalTherapy(
                    therapy=therapy,
                    group_type=Content["group_type"],
                    group_name=Content["group_name"],
                    stimulation_type=Content["stimulation_type"],
                    label=Content["label"],
                )
                eTherapy.save()
                currentIndex += 12 + ContentSize

                while True:
                    HeaderBytes = rawBytes[currentIndex:currentIndex+8]
                    ContentSize = int.from_bytes(rawBytes[currentIndex+8:currentIndex+12], "little")

                    if HeaderBytes == b"XXXXESTM":
                        PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
                        Content = json.loads(PacketContent)

                        setting = models.ElectricalStimulation(
                            group=eTherapy,
                            electrode=UIDMapper[Content["electrode"]],
                            contact=Content["contact"],
                            return_contact=Content["return_contact"],
                            amplitude=Content["amplitude"],
                            amplitude_fraction=Content["amplitude_fraction"],
                            amplitude_unit=Content["amplitude_unit"],
                            pulsewidth=Content["pulsewidth"],
                            pulsewidth_unit=Content["pulsewidth_unit"],
                            frequency=Content["frequency"],
                            cycling=Content["cycling"],
                            cycling_period=Content["cycling_period"],
                        )
                        setting.save()
                        currentIndex += 12 + ContentSize
                        
                    elif HeaderBytes == b"XXXXEADT":
                        PacketContent = FernetEncoder.decrypt(rawBytes[currentIndex+12:currentIndex+12+ContentSize]).decode("utf-8")
                        Content = json.loads(PacketContent)

                        setting = models.AdaptiveTherapy(
                            group=eTherapy,
                            sensing_type=Content["sensing_type"],
                            sensing=Content["sensing"],
                            adaptive_type=Content["adaptive_type"],
                            adaptive=Content["adaptive"],
                        )
                        setting.save()
                        currentIndex += 12 + ContentSize
                        
                    else:
                        break
        
        else:
            raise Exception("Unknown Packet Type: " + str(HeaderBytes))
    
    return participant

def ExportBRAVOStructure(participant, deidentified=False, password="BRAVOExportv2"):
    rawBytes = b"BRAVO Export"
    hashed_key = hashlib.sha256(password.encode("utf-8")).digest()
    export_key = base64.urlsafe_b64encode(hashed_key)
    FernetEncoder = Fernet(export_key)

    os.makedirs(DATABASE_PATH + "exports", exist_ok=True)
    filePath = DATABASE_PATH + "exports" + os.path.sep + participant.uid + (".Deidentified" if deidentified else "") + ".bravoexp"
    fid = open(filePath, "wb")
    fid.write(rawBytes)

    ParticipantInfo = {
        "uid": participant.uid,
        "name": participant.name if not deidentified else participant.uid,
        "date_of_birth": participant.date_of_birth if not deidentified else 0,
        "sex": participant.sex,
        "mrn": participant.mrn if not deidentified else "",
        "diagnosis": participant.diagnosis,
        "disease_start_time": participant.disease_start_time,
        "tags": [tag.name for tag in participant.tags.all()],
    }
    headerContent = b"XXXXPART"
    exportContent = createExportContent(json.dumps(ParticipantInfo), FernetEncoder)
    headerContent += len(exportContent).to_bytes(4, "little")
    fid.write(headerContent)
    fid.write(exportContent)

    devices = models.DBSDevice.find_all(owner=participant)
    for device in devices:
        DeviceInfo = {
            "uid": device.uid,
            "name": device.name,
            "type": device.type,
            "serial_number": device.serial_number,
            "implanted_location": device.implanted_location,
            "implanted_date": device.implanted_date,
            "estimated_eol": device.estimated_eol,
            "device_bloodline": device.device_bloodline,
        }

        headerContent = b"XXXXDBSD"
        exportContent = createExportContent(json.dumps(DeviceInfo), FernetEncoder)
        headerContent += len(exportContent).to_bytes(4, "little")
        fid.write(headerContent)
        fid.write(exportContent)

        for electrode in device.electrodes.all():
            ElectrodeInfo = {
                "uid": electrode.uid,
                "type": electrode.type,
                "name": electrode.name,
                "hemisphere": electrode.hemisphere,
                "target": electrode.target,
                "custom_name": electrode.custom_name,
                "device": device.uid,
                "channel_count": electrode.channel_count,
                "channel_names": electrode.channel_names,
                "channel_mapping": electrode.channel_mapping,
                "channel_coordinates": electrode.channel_coordinates,
                "implanted_date": electrode.implanted_date,
            }
            
            headerContent = b"XXXXELEC"
            exportContent = createExportContent(json.dumps(ElectrodeInfo), FernetEncoder)
            headerContent += len(exportContent).to_bytes(4, "little")
            fid.write(headerContent)
            fid.write(exportContent)
        
    devices = models.MERDevice.find_all(owner=participant)
    for device in devices:
        DeviceInfo = {
            "uid": device.uid,
            "name": device.name,
            "type": device.type,
        }

        headerContent = b"XXXXMERD"
        exportContent = createExportContent(json.dumps(DeviceInfo), FernetEncoder)
        headerContent += len(exportContent).to_bytes(4, "little")
        fid.write(headerContent)
        fid.write(exportContent)

        for electrode in device.electrodes.all():
            ElectrodeInfo = {
                "uid": electrode.uid,
                "type": electrode.type,
                "name": electrode.name,
                "hemisphere": electrode.hemisphere,
                "target": electrode.target,
                "custom_name": electrode.custom_name,
                "device": device.uid,
                "channel_count": electrode.channel_count,
                "channel_names": electrode.channel_names,
                "channel_mapping": electrode.channel_mapping,
                "channel_coordinates": electrode.channel_coordinates,
                "implanted_date": electrode.implanted_date,
            }
            
            headerContent = b"XXXXELEC"
            exportContent = createExportContent(json.dumps(ElectrodeInfo), FernetEncoder)
            headerContent += len(exportContent).to_bytes(4, "little")
            fid.write(headerContent)
            fid.write(exportContent)
        
    devices = models.FitbitDevice.find_all(owner=participant)
    for device in devices:
        DeviceInfo = {
            "uid": device.uid,
            "name": device.name,
            "type": device.type,
            "pkce": device.pkce,
            "auth": device.auth,
            "date_periods": device.date_periods,
        }

        headerContent = b"XXXXFITB"
        exportContent = createExportContent(json.dumps(DeviceInfo), FernetEncoder)
        headerContent += len(exportContent).to_bytes(4, "little")
        fid.write(headerContent)
        fid.write(exportContent)

    devices = models.OuraRingDevice.find_all(owner=participant)
    for device in devices:
        DeviceInfo = {
            "uid": device.uid,
            "name": device.name,
            "type": device.type,
            "pkce": device.pkce,
            "auth": device.auth,
            "date_periods": device.date_periods,
        }

        headerContent = b"XXXXOURA"
        exportContent = createExportContent(json.dumps(DeviceInfo), FernetEncoder)
        headerContent += len(exportContent).to_bytes(4, "little")
        fid.write(headerContent)
        fid.write(exportContent)

    sources = models.SourceFile.find_all(owner=participant)
    for source in sources:
        SourceInfo = {
            "uid": source.uid,
            "name": source.name,
            "type": source.type,
            "date": source.date,
            "metadata": source.metadata,
        }

        headerContent = b"XXXXSOUR"
        exportContent = createExportContent(json.dumps(SourceInfo), FernetEncoder)
        headerContent += len(exportContent).to_bytes(4, "little")
        fid.write(headerContent)
        fid.write(exportContent)

    events = models.TherapyModification.find_all(owner=participant)
    for event in events:
        EventInfo = {
            "uid": event.uid,
            "name": event.name,
            "type": event.type,
            "date": event.date,
            "previous_state": event.previous_state,
            "new_state": event.new_state,
            "source": event.source.uid if event.source else "",
        }

        headerContent = b"XXXXTMOD"
        exportContent = createExportContent(json.dumps(EventInfo), FernetEncoder)
        headerContent += len(exportContent).to_bytes(4, "little")
        fid.write(headerContent)
        fid.write(exportContent)

    events = models.Annotation.find_all(owner=participant)
    for event in events:
        EventInfo = {
            "uid": event.uid,
            "name": event.name,
            "type": event.type,
            "date": event.date,
            "duration": event.duration,
            "source": event.source.uid if event.source else "",
        }

        headerContent = b"XXXXANNO"
        exportContent = createExportContent(json.dumps(EventInfo), FernetEncoder)
        headerContent += len(exportContent).to_bytes(4, "little")
        fid.write(headerContent)
        fid.write(exportContent)

    for source in sources:
        events = models.DBSEvent.find_all(source=source)
        for event in events:
            EventInfo = {
                "uid": event.uid,
                "name": event.name,
                "type": event.type,
                "date": event.date,
                "source": event.source.uid if event.source else "",
            }

            headerContent = b"XXXXDBSE"
            exportContent = createExportContent(json.dumps(EventInfo), FernetEncoder)
            headerContent += len(exportContent).to_bytes(4, "little")
            fid.write(headerContent)
            fid.write(exportContent)

        recordings = models.Recording.find_all(source=source)
        for recording in recordings:
            RecordingInfo = {
                "uid": recording.uid,
                "name": recording.name,
                "type": recording.type,
                "date": recording.date,
                "adjusted_alignment": recording.adjusted_alignment,
                "hashed": recording.hashed,
                "metadata": recording.metadata,
                "source": source.uid,
            }
            
            headerContent = b"XXXXRECD"
            exportContent = createExportContent(json.dumps(RecordingInfo), FernetEncoder)
            headerContent += len(exportContent).to_bytes(4, "little")
            fid.write(headerContent)
            fid.write(exportContent)

            if recording.pointer == "":
                continue
            data = Database.loadSourceBinary(recording.pointer)
            headerContent = b"XXXXRAWD"
            headerContent += len(data).to_bytes(4, "little")
            fid.write(headerContent)
            fid.write(data)

        therapies = models.Therapy.find_all(source=source)
        for therapy in therapies:
            TherapyInfo = {
                "uid": therapy.uid,
                "name": therapy.name,
                "type": therapy.type,
                "date": therapy.date,
                "source": source.uid,
            }

            headerContent = b"XXXXTHER"
            exportContent = createExportContent(json.dumps(TherapyInfo), FernetEncoder)
            headerContent += len(exportContent).to_bytes(4, "little")
            fid.write(headerContent)
            fid.write(exportContent)

            eTherapy = models.ElectricalTherapy.find(therapy=therapy)
            ElecTherapyInfo = {
                "therapy": therapy.uid,
                "group_type": eTherapy.group_type,
                "group_name": eTherapy.group_name,
                "group_id": eTherapy.group_id,
                "stimulation_type": eTherapy.stimulation_type,
                "label": eTherapy.label
            }

            headerContent = b"XXXXETHE"
            exportContent = createExportContent(json.dumps(ElecTherapyInfo), FernetEncoder)
            headerContent += len(exportContent).to_bytes(4, "little")
            fid.write(headerContent)
            fid.write(exportContent)

            for setting in eTherapy.stimulation_settings.all():
                SettingInfo = {
                    "therapy": therapy.uid,
                    "electrode": setting.electrode.uid,
                    "contact": setting.contact,
                    "return_contact": setting.return_contact,
                    "amplitude": setting.amplitude,
                    "amplitude_fraction": setting.amplitude_fraction,
                    "amplitude_unit": setting.amplitude_unit,
                    "pulsewidth": setting.pulsewidth,
                    "pulsewidth_unit": setting.pulsewidth_unit,
                    "frequency": setting.frequency,
                    "cycling": setting.cycling,
                    "cycling_period": setting.cycling_period,
                }

                headerContent = b"XXXXESTM"
                exportContent = createExportContent(json.dumps(SettingInfo), FernetEncoder)
                headerContent += len(exportContent).to_bytes(4, "little")
                fid.write(headerContent)
                fid.write(exportContent)

            for setting in eTherapy.adaptive_settings.all():
                SettingInfo = {
                    "therapy": therapy.uid,
                    "sensing_type": setting.sensing_type,
                    "sensing": setting.sensing,
                    "adaptive_type": setting.adaptive_type,
                    "adaptive": setting.adaptive
                }

                headerContent = b"XXXXEADT"
                exportContent = createExportContent(json.dumps(SettingInfo), FernetEncoder)
                headerContent += len(exportContent).to_bytes(4, "little")
                fid.write(headerContent)
                fid.write(exportContent)

    fid.close()
    return filePath