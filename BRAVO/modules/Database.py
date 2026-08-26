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
Database Interaction 
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
import pickle, blosc2
import zlib
import hashlib, hmac
import shutil
from filelock import Timeout, FileLock
import numpy as np
import datetime

import zarr

from Server import models
from modules.MedtronicPercept import BrainSenseStream

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')
FALLBACK_COMPRESSION_MAGIC = b"BRAVO_ZLIB_v1\0"

def retrieveProcessingSettings(config=dict()):
    options = {
        "TimeSeriesRecording": {
            "StandardFilter": {
                "name": "Standard Bandpass Filter",
                "description": "",
                "options": ["No Filter","Butterworth 1-100Hz"],
                "value": "Butterworth 1-100Hz"
            },
            "NotchFilter": {
                "name": "Powerline Noise Notch Filter",
                "description": "",
                "options": ["No Filter","Notch 55-65Hz","Notch 45-55Hz"],
                "value": "No Filter"
            },
            "WienerFilter": {
                "name": "Wiener Filter for Artifact Removals",
                "description": "",
                "options": ["No Filter","Use Wiener Filter"],
                "value": "No Filter"
            },
            "CardiacFilter": {
                "name": "Cardiac Filter for EKG Removals",
                "description": "",
                "options": ["No Filter","Use Adaptive Template Matching"],
                "value": "No Filter"
            },
            "SpectrogramMethod": {
                "name": "Time-Frequency Analysis Algorithm",
                "description": "",
                "options": ["Welch's Periodogram","Short-time Fourier Transform","Medtronic Percept PSD","Wavelet","Autoregressive Model (Yule-Walker)"],
                "value": "Welch's Periodogram"
            },
            "BaselineCorrection": {
                "name": "Baseline Correlation for Time-Frequency Analysis",
                "description": "",
                "options": ["No Correction"],
                "value": "No Correction"
            },
            "Normalization": {
                "name": "Normalization for Time-Frequency Analysis",
                "description": "",
                "options": ["No Normalization", "1/f PSD Trend Removal"],
                "value": "No Normalization"
            },
        },
        "PowerSpectralDensity": {
            "PSDMethod": {
                "name": "Power Spectrum Estimation Algorithm",
                "description": "",
                "options": ["Estimated Medtronic PSD","Welch's Periodogram","Autoregressive Model (Yule-Walker)","Short-time Fourier Transform"],
                "value": "Welch's Periodogram"
            },
            "MonopolarEstimation": {
                "name": "Monopolar Estimation Algorithm",
                "description": "",
                "options": ["No Estimation", "DETEC Algorithm (Strelow et. al., 2022)"],
                "value": "No Estimation"
            },
        }
    }

    if not "ProcessingConfiguration" in config.keys():
        return options, True
    
    if not type(config["ProcessingConfiguration"]) == dict:
        return options, True

    for key in config["ProcessingConfiguration"].keys():
        if type(config["ProcessingConfiguration"][key]) == dict:
            for subkey in config["ProcessingConfiguration"][key].keys():
                if type(config["ProcessingConfiguration"][key][subkey]) == dict and subkey in options[key].keys():
                    if not "name" in config["ProcessingConfiguration"][key][subkey].keys():
                        options[key][subkey]["value"] = config["ProcessingConfiguration"][key][subkey]["value"]

                    elif config["ProcessingConfiguration"][key][subkey]["name"] == options[key][subkey]["name"] and config["ProcessingConfiguration"][key][subkey]["description"] == options[key][subkey]["description"] and config["ProcessingConfiguration"][key][subkey]["options"] == options[key][subkey]["options"]:
                        options[key][subkey]["value"] = config["ProcessingConfiguration"][key][subkey]["value"]
    
    return options, not (options==config["ProcessingConfiguration"])

def checkConfiguration(metadata, config):
    if not type(metadata) == dict:
        return False 
    
    for key in config:
        if not key in metadata.keys():
            return False
        if not metadata[key] == config[key]:
            return False
    
    return True

def checkAccessPermission(user, participant_uid, study_uid=None, recording_uid=None):
    Permission = {
        "Deidentified": True,
    }

    Participant = models.Participant.find(uid=participant_uid)
    if not Participant:
        return False 
    
    if Participant.institute.has_permission(user):
        Permission["Deidentified"] = False
        return Permission
    
    if not study_uid:
        return False 
    
    study = models.Study.find(uid=study_uid)
    rel = models.StudyDataRel.find(study=study, participant=Participant)
    if rel:
        if "PHIAllowed" in rel.permission.keys():
            Permission["Deidentified"] = False
            return Permission
        else:
            Permission["Deidentified"] = True
            return Permission
    
    return False

def checkManagePermission(user, participant_uid, type="View"):
    Participant = models.Participant.find(uid=participant_uid)
    if not Participant:
        return False
    return Participant.institute.has_permission(user, type)

def extractParticipantInformation(participant_uid, deidentified=False):
    Participant = models.Participant.find(uid=participant_uid)
    ParticipantInfo = Participant.get_info()
    ParticipantInfo["DBSDevices"] = [i.get_info() for i in models.DBSDevice.find_all(owner=Participant)]
    if deidentified:
        ParticipantInfo["Name"] = ParticipantInfo["Id"]
        ParticipantInfo["MRN"] = ""
        ParticipantInfo["DOB"] = 0

    return ParticipantInfo

def extractParticipantContext(participant_uid, check_files=[], deidentified=False):
    Participant = models.Participant.find(uid=participant_uid)
    ParticipantContext = list()

    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    for device in DBSDevices:
        SourceFiles = models.SourceFile.find_all(owner=Participant, type="MedtronicJSON", metadata__Device=device.uid)
        SourceFiles = sorted(SourceFiles, key=lambda x: -x.date)

        TherapyModificationList = list()
        TherapyModifications = models.TherapyModification.find_all(source__in=SourceFiles)
        for modification in TherapyModifications:
            TherapyModificationList.append({
                "Name": "",
                "Timestamp": modification.date*1000,
                "PreviousState": modification.previous_state,
                "NewState": modification.new_state,
                "Type": modification.type
            })

        for n in range(len(SourceFiles)):
            source = SourceFiles[n]
            if source.metadata["hashed_id"] in check_files:
                Context = {
                    "Id": source.uid, "OnlineFile": True, "HashedId": source.metadata["hashed_id"],
                }
                ParticipantContext.append(Context)
                continue
                
            Context = {"Id": source.uid, "HashedId": source.metadata["hashed_id"] if "hashed_id" in source.metadata.keys() else "", "PatientInfo": {
                "SessionTimestamp": source.date*1000,
                "SessionTimezone": source.metadata["Timezone"] if "Timezone" in source.metadata.keys() else "",
                "Name": Participant.name,
                "MRN": Participant.mrn,
                "Diagnosis": Participant.diagnosis,
                "Sex": Participant.sex,
                "DOB": Participant.date_of_birth*1000,
                "Device": {}
            }, "TherapyInformation": [], "TherapyModification": TherapyModificationList, "ChronicBrainSense": [], "Recordings": [], "TherapyRecordings": []}

            Context["PatientInfo"]["Device"]["Id"] = device.uid
            Context["PatientInfo"]["Device"]["Type"] = device.type
            Context["PatientInfo"]["Device"]["Name"] = device.name
            Context["PatientInfo"]["Device"]["SerialNumber"] = device.serial_number
            Context["PatientInfo"]["Device"]["BatteryPercent"] = 0
            Context["PatientInfo"]["Device"]["EOL"] = 0
            Context["PatientInfo"]["Device"]["Location"] = device.implanted_location
            Context["PatientInfo"]["Device"]["ImplantDate"] = int(device.implanted_date*1000) if device.implanted_date else 0
            Context["PatientInfo"]["Device"]["ConnectedLeads"] = list()
            for lead in device.electrodes.all():
                LeadInfo = {
                    "Id": lead.uid,
                    "Target": lead.target.split(" ")[1],
                    "Hemisphere": lead.target.split(" ")[0],
                    "CustomName": lead.custom_name,
                    "ChannelCount": lead.channel_count,
                    "LeadType": lead.type,
                }
                Context["PatientInfo"]["Device"]["ConnectedLeads"].append(LeadInfo)

            Therapies = models.ElectricalTherapy.find_all(therapy__source=source, therapy__type__in=["Pre-visit Therapy", "Post-visit Therapy"])
            TherapyDates = np.unique([therapy.therapy.date for therapy in Therapies])
            for date in TherapyDates:
                DateTherapies = [therapy for therapy in Therapies if therapy.therapy.date == date]
                TherapyGroups = np.unique([therapy.group_id for therapy in DateTherapies])
                for therapyType in ["Pre-visit Therapy", "Post-visit Therapy"]:
                    for group in TherapyGroups:
                        GroupTherapies = [therapy for therapy in DateTherapies if therapy.group_id == group and therapy.therapy.type == therapyType]
                        if len(GroupTherapies) == 0:
                            continue

                        therapy = GroupTherapies[0]
                        TherapyInformation = {
                            "Active": therapy.group_type == "Active",
                            "SourceId": therapy.therapy.source.uid,
                            "GroupId": therapy.group_id,
                            "GroupName": therapy.group_name,
                            "ProgramName": therapy.therapy.type,
                            "Timestamp": therapy.therapy.date*1000,
                            "StimulationConfigurations": []
                        }

                        for therapy in GroupTherapies:
                            AdaptiveSettings = therapy.adaptive_settings.all()
                            StimulationSettings = therapy.stimulation_settings.all()
                            for i in range(len(StimulationSettings)):
                                setting = StimulationSettings[i]
                                StimulationConfiguration = {
                                    "Mode": therapy.stimulation_type,
                                    "ActiveContacts": [],
                                    "ReturnContacts": [],
                                    "Amplitude": setting.amplitude,
                                    "PulseWidth": setting.pulsewidth,
                                    "Frequency": setting.frequency,
                                    "CyclingEnabled": setting.cycling < 0,
                                    "CyclingOnDuration": setting.cycling * setting.cycling_period,
                                    "CyclingOffDuration": setting.cycling_period * (1-setting.cycling),
                                    "SensingConfiguration": {}, "AdaptiveConfiguration": {}
                                }

                                KnownContacts = []
                                for contact in setting.contact:
                                    for electrode in Context["PatientInfo"]["Device"]["ConnectedLeads"]:
                                        if electrode["Id"] == setting.electrode.uid:
                                            StimulationConfiguration["ActiveContacts"].append({
                                                "Electrode": electrode,
                                                "ContactName": setting.electrode.channel_names[contact] if contact < len(setting.electrode.channel_names) else f"Contact {contact}",
                                                "ContactIndex": contact,
                                                "Amplitude": 0
                                            })
                                            if "02" in StimulationConfiguration["ActiveContacts"][-1]["ContactName"]:
                                                KnownContacts.append(2)
                                            elif "01" in StimulationConfiguration["ActiveContacts"][-1]["ContactName"]:
                                                KnownContacts.append(1)
                                            elif "00" in StimulationConfiguration["ActiveContacts"][-1]["ContactName"]:
                                                KnownContacts.append(0)
                                            elif "03" in StimulationConfiguration["ActiveContacts"][-1]["ContactName"]:
                                                KnownContacts.append(3)
                                KnownContacts = np.unique(KnownContacts)

                                for contact in setting.return_contact:
                                    for electrode in Context["PatientInfo"]["Device"]["ConnectedLeads"]:
                                        if electrode["Id"] == setting.electrode.uid:
                                            if contact < 0:
                                                StimulationConfiguration["ReturnContacts"].append({
                                                    "Electrode": electrode,
                                                    "ContactName": "CAN",
                                                    "ContactIndex": contact,
                                                    "Amplitude": 0
                                                })
                                            else:
                                                StimulationConfiguration["ReturnContacts"].append({
                                                    "Electrode": electrode,
                                                    "ContactName": setting.electrode.channel_names[contact] if contact < len(setting.electrode.channel_names) else f"Contact {contact}",
                                                    "ContactIndex": contact,
                                                    "Amplitude": 0
                                                })

                                if "SensingSetup" in AdaptiveSettings[i].sensing.keys():
                                    StimulationConfiguration["SensingConfiguration"]["SensingFrequency"] = AdaptiveSettings[i].sensing["SensingSetup"]["FrequencyInHertz"]
                                    StimulationConfiguration["SensingConfiguration"]["AveragingDuration"] = AdaptiveSettings[i].sensing["SensingSetup"]["AveragingDurationInMilliSeconds"]
                                    if 2 in KnownContacts and 1 in KnownContacts:
                                        StimulationConfiguration["SensingConfiguration"]["SensingChannel"] = "ZERO_AND_THREE"
                                    elif 2 in KnownContacts:
                                        StimulationConfiguration["SensingConfiguration"]["SensingChannel"] = "ONE_AND_THREE"
                                    elif 1 in KnownContacts:
                                        StimulationConfiguration["SensingConfiguration"]["SensingChannel"] = "ZERO_AND_TWO"
                                    else:
                                        StimulationConfiguration["SensingConfiguration"]["SensingChannel"] = ""
                                    StimulationConfiguration["SensingConfiguration"]["Status"] = "ENABLED"
                                
                                if "Mode" in AdaptiveSettings[i].adaptive.keys():
                                    StimulationConfiguration["AdaptiveConfiguration"]["Configured"] = True
                                    StimulationConfiguration["AdaptiveConfiguration"]["Status"] = AdaptiveSettings[i].adaptive["Status"].split(".")[1]
                                    StimulationConfiguration["AdaptiveConfiguration"]["Mode"] = AdaptiveSettings[i].adaptive["Mode"].split(".")[1]
                                    StimulationConfiguration["AdaptiveConfiguration"]["RampUpDuration"] = AdaptiveSettings[i].adaptive["RampUpTime"]
                                    StimulationConfiguration["AdaptiveConfiguration"]["RampDownDuration"] = AdaptiveSettings[i].adaptive["RampDownTime"]
                                    StimulationConfiguration["AdaptiveConfiguration"]["OnsetDuration"] = AdaptiveSettings[i].adaptive["UpperThresholdOnsetInMilliSeconds"]
                                    StimulationConfiguration["AdaptiveConfiguration"]["TerminationDuration"] = AdaptiveSettings[i].adaptive["LowerThresholdOnsetInMilliSeconds"]
                                    StimulationConfiguration["AdaptiveConfiguration"]["DetectionBlankingDuration"] = AdaptiveSettings[i].adaptive["DetectionBlankingDurationInMilliSeconds"]
                                    StimulationConfiguration["AdaptiveConfiguration"]["AdaptiveStartupDelay"] = AdaptiveSettings[i].adaptive["AdaptiveStartupDelayInMilliSeconds"]

                                if "Thresholds" in AdaptiveSettings[i].sensing.keys():
                                    StimulationConfiguration["AdaptiveConfiguration"]["AdaptiveThresholds"] = AdaptiveSettings[i].sensing["Thresholds"]["LFPThresholds"]
                                    StimulationConfiguration["AdaptiveConfiguration"]["DefaultThresholds"] = AdaptiveSettings[i].sensing["Thresholds"]["MeasuredLFP"]
                                    StimulationConfiguration["AdaptiveConfiguration"]["AdaptiveAmplitudes"] = AdaptiveSettings[i].sensing["Thresholds"]["AmplitudeThreshold"]
                                    StimulationConfiguration["AdaptiveConfiguration"]["CaptureAmplitudes"] = AdaptiveSettings[i].sensing["Thresholds"]["CaptureAmplitudes"]
                                    
                                TherapyInformation["StimulationConfigurations"].append(StimulationConfiguration)
                        Context["TherapyInformation"].append(TherapyInformation)
            
            Recordings = models.Recording.find_all(source=source, type__in=["MedtronicChronicBrainSense"])
            for recording in Recordings:
                Data = loadSourceFile(recording.pointer, recording.hashed)
                Context["ChronicBrainSense"].append({
                    "Id": recording.uid,
                    "Name": recording.name,
                    "Timestamp": recording.date*1000,
                    "Data": Data["Data"], 
                    "Time": Data["Time"],
                    "ChannelNames": Data["ChannelNames"],
                })

            Recordings = models.Recording.find_all(source=source, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages"])
            for recording in Recordings:
                Data = loadSourceFile(recording.pointer, recording.hashed)
                Context["Recordings"].append({
                    "Id": recording.uid,
                    "Name": recording.name,
                    "Type": recording.type,
                    "Timestamp": recording.date*1000,
                    "Duration": recording.metadata["Duration"]*1000,
                    "DataURL": "getRawData?CacheType=queryTimeSeriesData&ParticipantId=" + participant_uid + "&RecordingId=" + recording.uid,
                    "SamplingRate": Data["SamplingRate"],
                    "ChannelNames": Data["ChannelNames"],
                })

            Recordings = models.Recording.find_all(source=source, type__in=["MedtronicBrainSenseTimeDomain"])
            for recording in Recordings:
                Data = loadSourceFile(recording.pointer, recording.hashed)
                Context["Recordings"].append({
                    "Id": recording.uid,
                    "Name": recording.name,
                    "Type": recording.type,
                    "Timestamp": recording.date*1000,
                    "Duration": recording.metadata["Duration"]*1000,
                    "DataURL": "getRawData?CacheType=queryTimeSeriesData&ParticipantId=" + participant_uid + "&RecordingId=" + recording.uid,
                    "SamplingRate": Data["SamplingRate"],
                    "ChannelNames": Data["ChannelNames"],
                })
            
            Recordings = models.Recording.find_all(source=source, type__in=["MedtronicBrainSensePowerDomain"])
            for recording in Recordings:
                Data = loadSourceFile(recording.pointer, recording.hashed)
                device = models.DBSDevice.find(uid=recording.source.metadata["Device"])
                ChannelNames = []
                for name in Data["ChannelNames"]:
                    Channel = name.split(" ")[0]
                    if not Channel in ChannelNames:
                        ChannelNames.append(Channel)
                
                for name in ChannelNames:
                    Context["Recordings"].append({
                        "Id": recording.uid + "|" + name,
                        "Name": recording.name,
                        "Type": recording.type,
                        "Timestamp": recording.date*1000,
                        "Duration": recording.metadata["Duration"]*1000,
                        "SamplingRate": Data["SamplingRate"],
                        "ChannelName": name,
                        "TherapySnapshot": Data["Descriptor"]["Therapy"],
                    })

                """
                Context["TherapyRecordings"].append({
                    "Id": recording.uid,
                    "Name": recording.name,
                    "Type": recording.type,
                    "Timestamp": recording.date*1000,
                    "Duration": recording.metadata["Duration"]*1000,
                    "DataURL": "getRawData?CacheType=queryTimeSeriesData&ParticipantId=" + participant_uid + "&RecordingId=" + recording.uid,
                    "SamplingRate": Data["SamplingRate"],
                    "ChannelName": Data["ChannelName"],
                })
                """

            ParticipantContext.append(Context)
    return ParticipantContext

def extractParticipantDevices(participant):
    return [i.get_info() for i in models.DBSDevice.find_all(owner=participant)]

# Database.assignSourceFile("","")
def assignSourceFile(old_device_uid, new_device_uid):
    old_device = models.DBSDevice.find(uid=old_device_uid)
    new_device = models.DBSDevice.find(uid=new_device_uid)

    for electrode in old_device.electrodes.all():
        if not new_device.electrodes.filter(uid=electrode.uid).exists():
            new_device.electrodes.add(electrode)

    source_files = models.SourceFile.objects.filter(metadata__Device=old_device.uid).all()
    for file in source_files:
        file.metadata["Device"] = new_device.uid
        file.save()

    old_device.delete()

def mergeParticipants(source, target):
    for entry in models.DBSDevice.find_all(owner=source):
        entry.owner = target
        entry.save()
    
    for entry in models.MERDevice.find_all(owner=source):
        entry.owner = target
        entry.save()
    
    for entry in models.FitbitDevice.find_all(owner=source):
        entry.owner = target
        entry.save()
    
    for entry in models.Electrode.find_all(owner=source):
        entry.owner = target
        entry.save()

    for entry in models.TherapyModification.find_all(owner=source):
        entry.owner = target
        entry.save()

    for entry in models.Annotation.find_all(owner=source):
        entry.owner = target
        entry.save()

    for entry in models.ParticipantLinkRel.find_all(participant=source):
        entry.participant = target
        entry.save()

    for entry in models.ScaleRecord.find_all(participant=source):
        entry.participant = target
        entry.save()

    for entry in models.Participant.find_all(original=source):
        entry.original = target
        entry.save()

    for entry in models.SourceFile.find_all(owner=source):
        entry.owner = target
        entry.save()
    
    source.delete()

def listRecordings(participant_uid):
    Participant = models.Participant.find(uid=participant_uid)
    SourceFiles = models.SourceFile.find_all(owner=Participant)
    DBSDevices = [device.get_info() for device in models.DBSDevice.find_all(owner=Participant)]
    Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicBrainSenseTimeDomain", "MedtronicBrainSensePowerDomain", "MedtronicIndefiniteStream", "DelsysMDAT", "HPFCSV", "AOMPX"])
    
    AllRecordings = []
    for recording in Recordings:
        Description = recording.get_info()
        if recording.type == "MedtronicBrainSenseTimeDomain" or recording.type == "MedtronicIndefiniteStream":
            for device in DBSDevices:
                if device["Id"] == recording.source.metadata["Device"]:
                    Description["Device"] = device
                    for i in range(len(Description["Metadata"]["ChannelNames"])):
                        Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"])

        elif recording.type == "MedtronicBrainSensePowerDomain":
            for device in DBSDevices:
                if device["Id"] == recording.source.metadata["Device"]:
                    Description["Therapy"] = [{
                        "Hemisphere": side,
                        "Frequency": recording.metadata["Therapy"][side]["RateInHertz"],
                        "Pulsewidth": recording.metadata["Therapy"][side]["PulseWidthInMicroSecond"],
                        "Contact": BrainSenseStream.reformatStimulationChannel(recording.metadata["Therapy"][side]["SensingChannel"].replace("SensingChannelDef.",""), device["Electrodes"]),
                        "Segment": ""
                    } for side in ["Left", "Right"] if side in recording.metadata["Therapy"].keys()]
                    Description["Device"] = device
                    for i in range(len(Description["Metadata"]["ChannelNames"])):
                        if Description["Metadata"]["ChannelNames"][i].endswith("Stimulation"):
                            Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"]) + " Stimulation"
                        else:
                            Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"]) + " Recording"

        elif recording.type == "DelsysMDAT":
            pass

        elif recording.type == "HPFCSV":
            Description["Name"] = recording.metadata["SensorType"]

        AllRecordings.append(Description)
        
    return AllRecordings

def listSourceFiles(participant_uid, file_type=None):
    Participant = models.Participant.find(uid=participant_uid)
    if not file_type:
        source_files = models.SourceFile.find_all(owner=Participant)
    else:
        source_files = models.SourceFile.find_all(owner=Participant, type=file_type)

    SourceFiles = []
    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    for source in source_files:
        if source.type == "MedtronicJSON" or source.type == "DefaultType":
            SourceFile = {
                "Id": source.uid,
                "Name": source.name,
                "Type": "Medtronic JSON Sessions",
                "DateOfUpload": source.date,
                "Timezone": source.metadata["Timezone"] if "Timezone" in source.metadata.keys() else ""
            }

            if "Device" in source.metadata.keys():
                for device in DBSDevices:
                    if device.uid == source.metadata["Device"]:
                        SourceFile["Device"] = device.get_info()

            AllRecordings = models.Recording.find_all(source=source, type__in=["MedtronicBrainSenseTimeDomain", "MedtronicBrainSensePowerDomain", "MedtronicIndefiniteStream"])
            SourceFile["RecordingCount"] = len(AllRecordings)
            if SourceFile["RecordingCount"] > 0:
                SourceFile["DateOfRecording"] = np.mean([i.date for i in AllRecordings])
            else:
                SourceFile["DateOfRecording"] = source.date
            SourceFile["TherapyEventCount"] = len(models.TherapyModification.find_all(source=source))
            SourceFile["TherapyEventCount"] = len(models.TherapyModification.find_all(source=source))
            SourceFile["TherapyCount"] = len(models.Therapy.find_all(source=source))
            SourceFile["DBSEventCount"] = len(models.DBSEvent.find_all(source=source).exclude(type="MedtronicDeviceImpedance"))

            SourceFiles.append(SourceFile)
        
        elif source.type == "NeuroImage":
            SourceFile = {
                "Id": source.uid,
                "Name": source.name,
                "Type": "NeuroImaging Data",
                "DateOfUpload": source.date,
                "DateOfRecording": source.date,
                "Timezone": source.metadata["Timezone"] if "Timezone" in source.metadata.keys() else "",
                "DataType": source.metadata["FileType"],
                "Color": source.metadata["Color"] if "Color" in source.metadata.keys() else None,
            }
            try:
                SourceFile["DataSize"] = os.path.getsize(source.pointer)
            except:
                SourceFile["DataSize"] = 0

            SourceFiles.append(SourceFile)

        elif source.type == "HPFCSV":
            SourceFile = {
                "Id": source.uid,
                "Name": source.name,
                "Type": "HDF CSV Format",
                "DateOfUpload": source.date,
                "DateOfRecording": source.date,
                "Timezone": "",
                "DataSize": os.path.getsize(source.pointer)
            }

            AllRecordings = models.Recording.find_all(source=source)
            
            SourceFile["RecordingCount"] = 0
            for i in range(len(AllRecordings)):
                if "ChannelNames" in AllRecordings[i].metadata.keys():
                    SourceFile["RecordingCount"] += len(AllRecordings[i].metadata["ChannelNames"])

            SourceFiles.append(SourceFile)

        elif source.type == "AlphaOmegaMPX":
            SourceFile = {
                "Id": source.uid,
                "Name": source.name,
                "Type": "AlphaOmega MPX Format",
                "DateOfUpload": source.date,
                "DateOfRecording": source.date,
                "Timezone": "",
                "DataSize": os.path.getsize(source.pointer)
            }

            AllRecordings = models.Recording.find_all(source=source)
            
            SourceFile["RecordingCount"] = 0
            for i in range(len(AllRecordings)):
                if "ChannelNames" in AllRecordings[i].metadata.keys():
                    SourceFile["RecordingCount"] += len(AllRecordings[i].metadata["ChannelNames"])

            SourceFiles.append(SourceFile)

        elif source.type == "BRAVORecordingStructure":
            SourceFile = {
                "Id": source.uid,
                "Name": source.name,
                "Type": "BRAVO Recording Structure (Binary)",
                "DateOfUpload": source.date,
                "DateOfRecording": source.date,
                "Timezone": source.metadata["Timezone"] if "Timezone" in source.metadata.keys() else ""
            }

            AllRecordings = models.Recording.find_all(source=source)
            
            SourceFile["SensorType"] = []
            SourceFile["RecordingCount"] = []
            for i in range(len(AllRecordings)):
                if "ChannelNames" in AllRecordings[i].metadata.keys():
                    SourceFile["RecordingCount"].append(len(AllRecordings[i].metadata["ChannelNames"]))
                    SourceFile["SensorType"].append(AllRecordings[i].type)
            SourceFiles.append(SourceFile)

        elif source.type == "UFMDATv2":
            SourceFile = {
                "Id": source.uid,
                "Name": source.name,
                "Type": "Synchronized External Device Data",
                "DateOfUpload": source.date,
                "DateOfRecording": source.date,
                "Timezone": source.metadata["Timezone"] if "Timezone" in source.metadata.keys() else ""
            }

            AllRecordings = models.Recording.find_all(source=source)
            
            SourceFile["SensorType"] = []
            SourceFile["RecordingCount"] = []
            for i in range(len(AllRecordings)):
                if "ChannelNames" in AllRecordings[i].metadata.keys():
                    SourceFile["RecordingCount"].append(len(AllRecordings[i].metadata["ChannelNames"]))
                    SourceFile["SensorType"].append(AllRecordings[i].metadata["SensorType"])
            SourceFiles.append(SourceFile)

        else:
            SourceFile = {
                "Id": source.uid,
                "Name": source.name,
                "Type": source.type,
                "DateOfUpload": source.date,
                "DateOfRecording": source.date,
                "Timezone": source.metadata["Timezone"] if "Timezone" in source.metadata.keys() else ""
            }

            SourceFiles.append(SourceFile)

    SourceFiles.sort(key=lambda x: x["DateOfRecording"])
    return SourceFiles

def deleteSourceFile(pointer):
    if not pointer.startswith(DATABASE_PATH) or ".." in pointer:
        raise Exception("Malicious Attempt at Accessing Other Data in the Computer.")
    
    lock = FileLock(pointer + ".lock")
    try:
        with lock.acquire(timeout=30):
            pathlib.Path.unlink(pathlib.Path(pointer))
        return True
    except Timeout:
        print("Lockfile Not Acquired before Timeout")
        return False

def saveSourceFile(datastruct, pointer, bytes=False):
    pointer = pointer.replace("\\", os.path.sep).replace("/", os.path.sep)
    
    if not pointer.startswith(DATABASE_PATH) or ".." in pointer:
        raise Exception("Malicious Attempt at Accessing Other Data in the Computer.")
    
    if not bytes:
        pData = pickle.dumps(datastruct, protocol=pickle.HIGHEST_PROTOCOL)
    else:
        pData = datastruct

    # Convert common binary-like inputs to bytes to ensure stable compression behavior.
    if isinstance(pData, memoryview):
        pData = pData.tobytes()
    elif isinstance(pData, bytearray):
        pData = bytes(pData)

    lock = FileLock(pointer + ".lock")
    try:
        with lock.acquire(timeout=30):
            with open(pointer + ".tmp", "wb+") as file:
                try:
                    #rawBytes = blosc2.compress2(pData, typesize=1)
                    pDataTensor = np.frombuffer(pData, dtype=np.uint8)
                    rawBytes = blosc2.pack_tensor(pDataTensor)
                except ValueError as e:
                    # blosc2 may throw "negative count" on very large payloads; fallback keeps data path alive.
                    if "negative count" in str(e):
                        rawBytes = FALLBACK_COMPRESSION_MAGIC + zlib.compress(pData)
                    else:
                        raise
                hashed = hmac.new(HASH_KEY.encode("utf8"), rawBytes, hashlib.sha256).hexdigest()
                file.write(rawBytes)
            shutil.move(pointer + ".tmp", pointer)
            return hashed
    except Timeout:
        print("Lockfile Not Acquired before Timeout")
        return False

def loadSourceFile(pointer, verifiedHash, bytes=False):
    pointer = pointer.replace("\\", os.path.sep).replace("/", os.path.sep)

    if not pointer.startswith(DATABASE_PATH) or ".." in pointer:
        raise Exception("Malicious Attempt at Accessing Other Data in the Computer.")
    
    with open(pointer, "rb") as file:
        rawBytes = file.read()
    hashed = hmac.new(HASH_KEY.encode("utf8"), rawBytes, hashlib.sha256).hexdigest()
    if not hashed == verifiedHash:
        raise Exception(f"DANGER: Unauthorized Modification of Data {pointer}, risk of Pickle Arbitrary Code Execution.")

    if rawBytes.startswith(FALLBACK_COMPRESSION_MAGIC):
        decompressed = zlib.decompress(rawBytes[len(FALLBACK_COMPRESSION_MAGIC):])
    elif b"b2frame" in rawBytes[:16]:
        decompressed = blosc2.unpack_tensor(rawBytes).tobytes()
    else:
        decompressed = blosc2.decompress2(rawBytes)

    # If Request Raw Byte Data
    if bytes:
        return decompressed
    
    # Else just pickle load it
    datastruct = pickle.loads(decompressed)
    return datastruct

def saveProcessedCollection(pointer, key, data, metadata):
    if not os.path.exists(pointer.replace(".bdat", ".zarr")):
        root = zarr.create_group(pointer.replace(".bdat", ".zarr"))
    else:
        root = zarr.open(pointer.replace(".bdat", ".zarr"), mode="r+")

    # Reset the array if it already exists to avoid appending to old data in case of re-processing the same file.
    if key in root.array_keys():
        del root[key]

    z = root.create_array(
        name=key,
        data=data,
        chunks=(data.shape[0] if data.shape[0] < 400000 else 400000, 1),
        compressors=zarr.codecs.BloscCodec(cname='zstd', clevel=5, shuffle=zarr.codecs.BloscShuffle.shuffle, typesize=1)
    )
    for metaKey in metadata.keys():
        if type(metadata[metaKey]) == np.ndarray:
            if len(metadata[metaKey]) == 1:
                z.attrs[metaKey] = metadata[metaKey][0]
            else:
                z.attrs[metaKey] = metadata[metaKey].tolist()
        else:
            z.attrs[metaKey] = metadata[metaKey]

def delete_directory(path):
    for root, dirs, files in os.walk(path, topdown=False):
        for file in files:
            os.remove(os.path.join(root, file))
        for dir in dirs:
            os.rmdir(os.path.join(root, dir))
    os.rmdir(path)

def loadProcessedCollection(pointer, key):
    if not os.path.exists(pointer.replace(".bdat", ".zarr")):
        raise Exception(f"Collection not found")
    
    root = zarr.open(pointer.replace(".bdat", ".zarr"), mode="r")
    print(list(root.array_keys()))
    if key not in root.array_keys():
        raise Exception(f"Key {key} not found in processed collection at {pointer}.")
    metadata = dict(root[key].attrs)
    return root[key], metadata

def loadSourceBinary(pointer):
    pointer = pointer.replace("\\", os.path.sep).replace("/", os.path.sep)

    if not pointer.startswith(DATABASE_PATH) or ".." in pointer:
        raise Exception("Malicious Attempt at Accessing Other Data in the Computer.")
    
    with open(pointer, "rb") as file:
        rawBytes = file.read()
        
    return rawBytes

def saveSourceBinary(pointer, rawBytes):
    pointer = pointer.replace("\\", os.path.sep).replace("/", os.path.sep)

    if not pointer.startswith(DATABASE_PATH) or ".." in pointer:
        raise Exception("Malicious Attempt at Accessing Other Data in the Computer.")
    
    os.makedirs(os.path.dirname(pointer), exist_ok=True)
    with open(pointer, "wb") as file:
        file.write(rawBytes)

def getCachedResult(url, participant_uid, config):
    models.SourceFile.purge(type="CachedResult", date__lt=models.current_time() - 3600)
    metadata = {**config, **{"URL": url, "Participant": participant_uid}}
    result = models.SourceFile.find(type="CachedResult", metadata=metadata)
    if result:
        return loadSourceFile(result.pointer, result.hashed)
    
def saveCachedResult(data, url, participant_uid, config):
    metadata = {**config, **{"URL": url, "Participant": participant_uid}}
    result = models.SourceFile.create(type="CachedResult", metadata=metadata)
    result.pointer = DATABASE_PATH + "visualization" + os.path.sep + participant_uid + os.path.sep + result.uid + ".bdat"
    result.hashed = saveSourceFile(data, DATABASE_PATH + "visualization" + os.path.sep + participant_uid + os.path.sep + result.uid + ".bdat")
    result.save()

def deleteCachedResult(participant_uid=None, url=None):
    if participant_uid and url:
        models.SourceFile.purge(type="CachedResult", metadata__Participant=participant_uid, metadata__URL=url)
    elif participant_uid:
        models.SourceFile.purge(type="CachedResult", metadata__Participant=participant_uid)
    elif url:
        models.SourceFile.purge(type="CachedResult", metadata__URL=url)
    else:
        models.SourceFile.purge(type="CachedResult")
        
