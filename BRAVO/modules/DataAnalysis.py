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
Data Analysis Pipelines
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
import hashlib, hmac
import shutil
import json
import copy
import pandas as pd
from filelock import Timeout, FileLock
import datetime

import numpy as np
from scipy import signal, stats, optimize
import pywt
from specparam import SpectralModel

from Server import models
import modules.utility.SignalProcessingUtility as SPU
from modules.utility.PythonUtility import rangeSelection, uniqueList, uniqueListOfDicts
from modules import Database, Therapy, Event
from modules.MedtronicPercept import BrainSenseStream, ChronicBrainSense, BrainSenseEvent, Percept
from modules.Resources.ProcessingTemplates import ProcessingNodes
from modules.Fitbit import DataManager as FitbitDataManager
from modules.OURA import DataManager as OuraDataManager
from modules.Empatica import DataManager as EmpaticaDataManager
from modules.AnalysisPipelineScripts import ExtractSpectralFeaturesDuringStimulation
from modules.SurveyForms import RedcapForm
#from modules.AIModels.ContactSelection.ContactSelection import ContactPredictor
#from modules.AIModels.ContactSelection_VerWong2026.ContactSelection import ContactPredictor as ContactPredictor_VerWong2026

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')

def queryProcessingNodes(type=None):
    if not type:
        return ProcessingNodes
    
    for i in range(len(ProcessingNodes)):
        if type == ProcessingNodes[i]["Type"]:
            return ProcessingNodes[i]

def deleteProcessedData(recording, type=None):
    if not type:
        models.Recording.find_all(original__in=recording).delete()
    else:
        models.Recording.find_all(original__in=recording, type=type).delete()

def saveAnalysisProcessedData(Data, type, metadata, recording):
    ProcessedData = models.Recording.create(recording, type)
    ProcessedData.pointer = DATABASE_PATH + "recordings" + os.path.sep + recording.source.owner.uid + os.path.sep + ProcessedData.uid + ".bdat"
    ProcessedData.hashed = Database.saveSourceFile(Data, ProcessedData.pointer)
    ProcessedData.metadata = metadata
    ProcessedData.save()
    return ProcessedData

def queryAllRecordings(participant_uid, request_type=None):
    Overview = {"Recordings": [], "Surveys": []}
    Participant = models.Participant.find(uid=participant_uid)
    if request_type == "Timeseries":
        SourceFiles = models.SourceFile.find_all(owner=Participant)
        DBSDevices = [device.get_info() for device in models.DBSDevice.find_all(owner=Participant)]
        Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicChronicBrainSense", "MedtronicBrainSenseSurvey", "MedtronicBaselineMontages", "MedtronicBrainSenseTimeDomain", "MedtronicBrainSensePowerDomain", "MedtronicIndefiniteStream", "DelsysMDAT", "HPFCSV", "AOMPX", "MATFile", "SynchronizedMDAT"])
        
        Overview["Recordings"] = []
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
                            "SegmentMode": recording.metadata["Therapy"][side]["SegmentMode"] if "SegmentMode" in recording.metadata["Therapy"][side].keys() else "Ring"
                        } for side in ["Left", "Right"] if side in recording.metadata["Therapy"].keys()]
                        Description["Device"] = device
                        for i in range(len(Description["Metadata"]["ChannelNames"])):
                            if Description["Metadata"]["ChannelNames"][i].endswith("Stimulation"):
                                Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"]) + " Stimulation"
                            else:
                                Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"]) + " Recording"

            elif recording.type == "MedtronicBaselineMontages" or recording.type == "MedtronicBrainSenseSurvey":
                for device in DBSDevices:
                    if device["Id"] == recording.source.metadata["Device"]:
                        Description["Device"] = device
                        for i in range(len(Description["Metadata"]["ChannelNames"])):
                            Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"])

                Description["Type"] = "DBS Snapshots"

            elif recording.type == "DelsysMDAT":
                Description["Type"] = "Delsys MDT"

            elif recording.type == "SynchronizedMDAT":
                Description["Type"] = "Synchronized External Data"

            elif recording.type == "HPFCSV":
                Description["Name"] = recording.metadata["SensorType"]
                Description["Type"] = "Delsys CSV Format"
            
            elif recording.type == "AOMPX":
                Description["Type"] = "Alpha Omega MPX"
            
            elif recording.type == "MATFile":
                Description["Type"] = "MATLAB File"
            
            elif recording.type == "MedtronicChronicBrainSense":
                Description["Type"] = "Timeline"
                for device in DBSDevices:
                    if device["Id"] == recording.source.metadata["Device"]:
                        for i in range(len(Description["Metadata"]["ChannelNames"])):
                            for k in range(len(device["Electrodes"])):
                                if Description["Metadata"]["ChannelNames"][i].startswith(device["Electrodes"][k]["Target"].split(" ")[0]):
                                    Description["Metadata"]["ChannelNames"][i] = device["Electrodes"][k]["CustomName"] + " " + Description["Metadata"]["ChannelNames"][i].split(" ")[-1]

            Description["RawType"] = recording.type
            Overview["Recordings"].append(Description)

    elif request_type == "Surveys":
        AllRecords = models.ScaleRecord.find_all(participant=Participant)
        for record in AllRecords:
            Description = {
                "Id": record.uid,
                "Date": record.date,
                "FormId": record.source.uid,
                "FormName": record.source.name,
            }
            Overview["Surveys"].append(Description)

    elif request_type == "ChronicTimeline":
        AllRecords = models.ScaleRecord.find_all(participant=Participant)
        for record in AllRecords:
            Description = {
                "Id": record.uid,
                "Date": record.date,
                "FormId": record.source.uid,
                "FormName": record.source.name,
            }
            Overview["Surveys"].append(Description)

    elif not request_type:
        Overview["Recordings"].extend(queryAllRecordings(participant_uid, "Timeseries")["Recordings"])
        Overview["Surveys"].extend(queryAllRecordings(participant_uid, "Surveys")["Surveys"])

    return Overview

def queryAvailableAnalyses(participant_uid, request_type):
    Overview = {"Analyses": [], "Recordings": []}
    Participant = models.Participant.find(uid=participant_uid)
    if request_type == "TherapeuticAnalysis":
        SourceFiles = models.SourceFile.find_all(owner=Participant)
        DBSDevices = [device.get_info() for device in models.DBSDevice.find_all(owner=Participant)]
        Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicBrainSenseTimeDomain", "MedtronicBrainSensePowerDomain", "MedtronicIndefiniteStream"])
        
        Overview["Recordings"] = []
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
                        Description["Therapy"] = []
                        for side in ["Left", "Right"]: 
                            if side in recording.metadata["Therapy"].keys():
                                TherapyDescription = {
                                    "Hemisphere": side,
                                    "Frequency": recording.metadata["Therapy"][side]["RateInHertz"],
                                    "Pulsewidth": recording.metadata["Therapy"][side]["PulseWidthInMicroSecond"],
                                    "Contact": BrainSenseStream.reformatStimulationChannel(recording.metadata["Therapy"][side]["SensingChannel"].replace("SensingChannelDef.",""), device["Electrodes"]),
                                    "SegmentMode": recording.metadata["Therapy"][side]["SegmentMode"] if "SegmentMode" in recording.metadata["Therapy"][side].keys() else "Ring"
                                }

                                if "ElectrodeState" in recording.metadata["Therapy"][side].keys():
                                    TherapyDescription["Contact"] = ""
                                    TherapyDescription["SegmentMode"] = ""
                                    
                                    for lead in device["Electrodes"]:
                                        if lead["Target"].startswith(side):
                                            TherapyDescription["Contact"] = lead["CustomName"] + " "
                                    for contact in recording.metadata["Therapy"][side]["ElectrodeState"]:
                                        if contact["ElectrodeStateResult"] != "ElectrodeStateDef.None":
                                            electrodeName, _ = Percept.reformatElectrodeDef(contact["Electrode"])
                                            if not electrodeName == "CAN":
                                                TherapyDescription["Contact"] += electrodeName + "-"
                                    
                                    TherapyDescription["Contact"] = TherapyDescription["Contact"][:-1]
                                
                                Description["Therapy"].append(TherapyDescription)

                        Description["Device"] = device
                        for i in range(len(Description["Metadata"]["ChannelNames"])):
                            if Description["Metadata"]["ChannelNames"][i].endswith("Stimulation"):
                                Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"]) + " Stimulation"
                            else:
                                Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"]) + " Recording"

            Overview["Recordings"].append(Description)
        
        AnalysisList = BrainSenseStream.createDefaultAnalysis([recording for recording in Overview["Recordings"] if recording["Type"] == "MedtronicBrainSenseTimeDomain"],
                                                              [recording for recording in Overview["Recordings"] if recording["Type"] == "MedtronicBrainSensePowerDomain"])
        
        for analysis in AnalysisList:
            Analysis = models.Analysis.find(type=analysis["Type"], metadata__DataId=analysis["Metadata"]["DataId"])
            if not Analysis:
                Analysis = models.Analysis.create(type=analysis["Type"], name=analysis["Name"], date=analysis["Date"], metadata=analysis["Metadata"])
                for recordingId in analysis["Metadata"]["DataId"]:
                    recording = Recordings.filter(uid=recordingId).first() # NOTE: SQL-Specific QuerySet
                    Analysis.add_recording(recording)
            
            Overview["Analyses"].append(Analysis.get_info())
    
        AnalysisList = models.Analysis.find_all(type=request_type, metadata__ParticipantId=participant_uid)
        for analysis in AnalysisList:
            AnalysisOverview = analysis.get_info()
            if AnalysisOverview:
                Overview["Analyses"].append(AnalysisOverview)
        
    elif request_type == "TimeSeriesAnalysis":
        SourceFiles = models.SourceFile.find_all(owner=Participant)
        DBSDevices = [device.get_info() for device in models.DBSDevice.find_all(owner=Participant)]
        Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["CustomizedStreamingData", 
                                                                                 "MedtronicElectrodeIdentifier", 
                                                                                 "MedtronicBrainSenseSurvey", 
                                                                                 "MedtronicBaselineMontages", 
                                                                                 "MedtronicBrainSenseTimeDomain", 
                                                                                 "MedtronicBrainSensePowerDomain", 
                                                                                 "MedtronicIndefiniteStream", 
                                                                                 "DelsysMDAT", "SynchronizedMDAT", "HPFCSV", "AOMPX", "MATFile"])
        
        Overview["Recordings"] = []
        for recording in Recordings:
            Description = recording.get_info()
            if recording.type == "MedtronicBrainSenseTimeDomain" or recording.type == "MedtronicIndefiniteStream":
                for device in DBSDevices:
                    if device["Id"] == recording.source.metadata["Device"]:
                        Description["Device"] = device
                        for i in range(len(Description["Metadata"]["ChannelNames"])):
                            Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"])

                for i in range(len(Recordings)):
                    if Recordings[i].type == "MedtronicBrainSensePowerDomain" and Recordings[i].source.metadata["Device"] == recording.source.metadata["Device"]:
                        
                        Overlap = BrainSenseStream.calculateOverlap(recording, Recordings[i]) 
                        if (Overlap > 0.7 and Overlap < 1.3):
                            Therapy = Database.loadSourceFile(Recordings[i].pointer, Recordings[i].hashed)
                            Description["Therapy"] = [{
                                "Id": Recordings[i].uid,
                                "Hemisphere": side,
                                "Amplitudes": [0,0],
                                "Frequency": Recordings[i].metadata["Therapy"][side]["RateInHertz"],
                                "Pulsewidth": Recordings[i].metadata["Therapy"][side]["PulseWidthInMicroSecond"],
                                "Contact": BrainSenseStream.reformatStimulationChannel(Recordings[i].metadata["Therapy"][side]["SensingChannel"].replace("SensingChannelDef.",""), Description["Device"]["Electrodes"]),
                                "SegmentMode": Recordings[i].metadata["Therapy"][side]["SegmentMode"] if "SegmentMode" in Recordings[i].metadata["Therapy"][side].keys() else "Ring"
                            } for side in ["Left", "Right"] if side in Recordings[i].metadata["Therapy"].keys()]

                            for j in range(len(Therapy["ChannelNames"])):
                                for k in range(len(Description["Therapy"])):
                                    if Therapy["ChannelNames"][j].endswith("Stimulation"):
                                        if Therapy["ChannelNames"][j].replace(" Stimulation", "").endswith(Description["Therapy"][k]["Hemisphere"].upper()):
                                            Description["Therapy"][k]["Amplitudes"] = [np.min(Therapy["Data"][:,j]), np.max(Therapy["Data"][:,j])]
                                            Description["Therapy"][k]["UniqueAmplitudes"] = []

                                            for z in np.unique(Therapy["Data"][:,j]):
                                                if np.sum(Therapy["Data"][:,j] == z) > 20:
                                                    Description["Therapy"][k]["UniqueAmplitudes"].append(z)

                            break
                        
                Description["Type"] = "DBS TimeDomain Recordings"

            elif recording.type == "MedtronicBrainSensePowerDomain":
                continue

            elif recording.type == "MedtronicBaselineMontages" or recording.type == "MedtronicBrainSenseSurvey" or recording.type == "MedtronicElectrodeIdentifier":
                for device in DBSDevices:
                    if device["Id"] == recording.source.metadata["Device"]:
                        Description["Device"] = device
                        for i in range(len(Description["Metadata"]["ChannelNames"])):
                            Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"])

                Description["Type"] = "DBS Snapshots"

            elif recording.type == "DelsysMDAT":
                Description["Type"] = "Delsys MDT"

            elif recording.type == "SynchronizedMDAT":
                Description["Type"] = "Synchronized External Data"

            elif recording.type == "HPFCSV":
                Description["Name"] = recording.metadata["SensorType"]
                Description["Type"] = "Delsys CSV Format"
            
            elif recording.type == "AOMPX":
                Description["Type"] = "Alpha Omega MPX"
            
            elif recording.type == "MATFile":
                Description["Type"] = "MATLAB File"
            
            elif recording.type == "CustomizedStreamingData":
                Description["Type"] = recording.metadata["DataType"]
            
            Overview["Recordings"].append(Description)

    return Overview

def createAnalysis(participant_uid, type, recording_ids):
    Recordings = models.Recording.find_all(uid__in=recording_ids)
    if len(Recordings) == 0:
        return None

    for recording in Recordings:
        if not recording.source.owner.uid == participant_uid:
            return None

    Analysis = models.Analysis.find(type=type, metadata__DataId=recording_ids)
    if Analysis:
        return Analysis

    Analysis = models.Analysis.create(type=type, name="")
    Analysis.metadata = {"DataId": [], "Timezone": "", "ParticipantId": participant_uid}
    Analysis.save()
    for recording in Recordings:
        if recording.date < Analysis.date:
            Analysis.date = recording.date
            Analysis.metadata["Timezone"] = recording.get_info()["Timezone"]
        Analysis.metadata["DataId"].append(recording.uid)
        Analysis.add_recording(recording)
    Analysis.save()
    return Analysis

def deleteAnalysis(participant_uid, analysis_uid):
    Analysis = models.Analysis.find(uid=analysis_uid)
    if Analysis:
        for recording in Analysis.recordings.all():
            if not recording.source.owner.uid == participant_uid:
                return None

        Analysis.delete()
        return True
    
def queryCustomizedAnalysis(participant_uid, analysis):
    Overview = {"Analysis": analysis.get_info(), "Configurations": {}, "Recordings": []}
    Participant = models.Participant.find(uid=participant_uid)
    
    SourceFiles = models.SourceFile.find_all(owner=Participant)
    DBSDevices = [device.get_info() for device in models.DBSDevice.find_all(owner=Participant)]
    Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicChronicNeuralActivity", "MedtronicBrainSenseTimeDomain", "MedtronicBrainSensePowerDomain", "MedtronicIndefiniteStream", "DelsysMDAT", "HPFCSV", "AOMPX", "MATFile"])
    
    Overview["Recordings"] = []
    for recording in Recordings:
        Description = recording.get_info()
        if recording.type == "MedtronicBrainSenseTimeDomain" or recording.type == "MedtronicIndefiniteStream":
            for device in DBSDevices:
                if device["Id"] == recording.source.metadata["Device"]:
                    Description["Device"] = device
                    for i in range(len(Description["Metadata"]["ChannelNames"])):
                        Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"])
            Description["Type"] = "DBS TimeDomain Recording"
        elif recording.type == "MedtronicBrainSensePowerDomain":
            for device in DBSDevices:
                if device["Id"] == recording.source.metadata["Device"]:
                    Description["Therapy"] = [{
                        "Hemisphere": side,
                        "Frequency": recording.metadata["Therapy"][side]["RateInHertz"],
                        "Pulsewidth": recording.metadata["Therapy"][side]["PulseWidthInMicroSecond"],
                        "Contact": BrainSenseStream.reformatStimulationChannel(recording.metadata["Therapy"][side]["SensingChannel"].replace("SensingChannelDef.",""), device["Electrodes"]),
                        "SegmentMode": recording.metadata["Therapy"][side]["SegmentMode"] if "SegmentMode" in recording.metadata["Therapy"][side].keys() else "Ring"
                    } for side in ["Left", "Right"] if side in recording.metadata["Therapy"].keys()]
                    Description["Device"] = device
                    for i in range(len(Description["Metadata"]["ChannelNames"])):
                        if Description["Metadata"]["ChannelNames"][i].endswith("Stimulation"):
                            Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"]) + " Stimulation"
                        else:
                            Description["Metadata"]["ChannelNames"][i] = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], Description["Device"]["Electrodes"]) + " Recording"

            Description["Type"] = "DBS Therapy Labels"

        elif recording.type == "MedtronicChronicNeuralActivity":
            Description["Type"] = "Medtronic Chronic Timeline"

        elif recording.type == "DelsysMDAT":
            pass

        elif recording.type == "HPFCSV":
            Description["Name"] = recording.metadata["SensorType"]

        Overview["Recordings"].append(Description)
        
    Overview["Configurations"] = analysis.metadata
    return Overview

def processCustomizedPipeline(analysis):
    Participant = models.Participant.find(uid=analysis.metadata["ParticipantId"])
    if not Participant:
        raise Exception("Participant Not Found")

    source = models.SourceFile.find(name=analysis.uid, type="CustomizedPipelineSource", owner=Participant)
    if not source:
        source = models.SourceFile(name=analysis.uid, type="CustomizedPipelineSource", owner=Participant)
        source.save()
    
    for i in range(len(analysis.metadata["Nodes"])):
        Input = analysis.metadata["Nodes"][i][0]
        recording = models.Recording.find(type="CustomAnalysis_"+Input["type"], metadata={ "RecordingList": [input["Id"] for input in Input["data"]], }, source=source)
        if not recording:
            ProcessedData = []
            recordings = models.Recording.find_all(uid__in=[input["Id"] for input in Input["data"]])
            for recording in recordings:
                Data = Database.loadSourceFile(recording.pointer, recording.hashed)
                if recording.type == "MedtronicChronicNeuralActivity":
                    for j in range(len(Data)):
                        StructuredData = ChronicBrainSense.revertChronicActivityFormat(Data[j])
                        for input in Input["data"]:
                            if input["Id"] == recording.uid:
                                StructuredData["StartTime"] += input["Alignment"]
                        ProcessedData.append(StructuredData)
                else:
                    for input in Input["data"]:
                        if input["Id"] == recording.uid:
                            Data["StartTime"] += input["Alignment"]
                    ProcessedData.append(Data)
            
            recording = models.Recording(name=Input["name"], type="CustomAnalysis_"+Input["type"], metadata={
                "RecordingList": [input["Id"] for input in Input["data"]],
            }, source=source)
            filename = DATABASE_PATH + "recordings" + os.path.sep + source.owner.uid + os.path.sep + recording.uid + ".bdat"
            hashed = Database.saveSourceFile({
                "DataType": "Original",
                "Data": ProcessedData,
            }, filename)

            # TODO: Error handling
            recording.pointer = filename
            recording.hashed = hashed
            recording.save()

        PreviousOutput = recording.uid
        for j in range(1, len(analysis.metadata["Nodes"][i])):
            analysis.metadata["Nodes"][i][j] = handleProcessingNode(analysis.metadata["Nodes"][i][j], analysis.metadata["ParticipantId"], PreviousOutput)
            PreviousOutput = analysis.metadata["Nodes"][i][j]["result"]

    analysis.save()


    """
    for edge in analysis.metadata["Edges"]:
        edge["Input"] = [node for node in analysis.metadata["Nodes"] if node["id"] == edge["source"]][0]
        edge["Output"] = [node for node in analysis.metadata["Nodes"] if node["id"] == edge["target"]][0]
    
    def checkProcessingState():
        for node in analysis.metadata["Nodes"]:
            if not "Result" in node["data"].keys():
                return True
        return False

    Counter = 0
    while checkProcessingState() and Counter < 1000:
        Counter += 1

        for node in analysis.metadata["Nodes"]:
            if "Result" in node["data"].keys():
                continue

            InputReady = True
            InputNodes = []
            for edge in analysis.metadata["Edges"]:
                if edge["target"] == node["id"]:
                    if not "Result" in edge["Input"]["data"].keys():
                        InputReady = False
                    InputNodes.append(edge["Input"])
            
            if InputReady:
                if node["type"] == "RecordingNode":
                    node["data"]["Result"] = True
                
                elif node["type"] == "RecordingGroupNode":
                    recording = models.Recording.find(type=node["type"], metadata={ "RecordingList": node["data"]["List"], }, source=source)
                    if recording:
                        node["data"]["Result"] = recording.uid
                        continue

                    ProcessedData = []
                    recordings = models.Recording.find_all(uid__in=[input["data"]["Id"] for input in InputNodes])
                    for recording in recordings:
                        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
                        ProcessedData.append(Data)
                    
                    recording = models.Recording(name=node["data"]["Name"], type=node["type"], metadata={
                        "RecordingList": node["data"]["List"],
                    }, source=source)
                    filename = DATABASE_PATH + "recordings" + os.path.sep + source.owner.uid + os.path.sep + recording.uid + ".bdat"
                    hashed = Database.saveSourceFile({
                        "DataType": "Original",
                        "Data": ProcessedData,
                    }, filename)
                    # TODO: Error handling
                    recording.pointer = filename
                    recording.hashed = hashed
                    recording.save()

                    node["data"]["Result"] = recording.uid
                
                elif node["type"] == "SingleInputProcessingNode":
                    if len(InputNodes) == 0:
                        raise Exception("No Input provided for processing node.")
                    node = handleProcessingNode(node, InputNodes[0])
    """

def handleProcessingNode(node, participant_uid, input_uid):
    recording = models.Recording.find(uid=input_uid)
    if not recording:
        raise Exception("Input not found")

    DefaultConfig = queryProcessingNodes(node["data"]["Type"])
    for i in range(len(DefaultConfig["Configurations"])):
        if not "Value" in node["data"]["Configurations"][i]:
            node["data"]["Configurations"][i]["Value"] = node["data"]["Configurations"][i]["Default"]
    
    metadata = {
        "Input": input_uid,
        "ParticipantId": participant_uid,
        "Configurations": node["data"]["Configurations"],
        "ProcessMode": "CustomizedAnalysis",
    }
    
    processed = models.Recording.find(metadata=metadata, original=recording)
    if not processed:
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        if node["data"]["Type"] == "Butterworth Digital Filter":
            Data = handleButterworthFilter(Data, node["data"])
            Data["DataType"] = "TimeDomain"
            
        elif node["data"]["Type"] == "Wiener Filter":
            Data = handleWienerFilter(Data, node["data"])
            Data["DataType"] = "TimeDomain"
        
        elif node["data"]["Type"] == "Welch's Periodogram":
            Data = handleWelchPeriodogram(Data, node["data"])
            Data["DataType"] = "PSD"
            
        elif node["data"]["Type"] == "Epoch by Annotations":
            Data = handleAnnotationSegmentation(Data, metadata)
            Data["DataType"] = ""
            
        elif node["data"]["Type"] == "Epoch by Timestamps":
            Data = handleTimestampSegmentation(Data, node["data"])
            Data["DataType"] = ""
            
        elif node["data"]["Type"] == "Compute Distribution":
            Data = handleDistributionComputation(Data, metadata)
            Data["DataType"] = "Distribution"

        elif node["data"]["Type"] == "Compute Power Spectral Separation":
            Data = handlePowerSpectralSeparationTest(Data, metadata)
            Data["DataType"] = "Power Spectral Separation"

        elif node["data"]["Type"] == "Compute Circadian Rhythm from Timeline":
            Data = handleCircadianRhythmComputation(Data, metadata)
            Data["DataType"] = "Circadian Rhythm"
            
        elif node["data"]["Type"] == "Time Frequency Analysis":
            Data = handleCustomTimeFrequencyAnalysis(Data, metadata)
            Data["DataType"] = "Time Frequency Analysis"

        elif node["data"]["Type"] == "Aperiodic Component Extraction":
            Data = handleAperiodicComponentExtraction(Data, metadata)
            Data["DataType"] = "Aperiodic Component"

        elif node["data"]["Type"] == "Narrow-band Power Extraction":
            Data = handleNarrowBandPowerExtraction(Data, metadata)
            Data["DataType"] = "Narrow-band Power Extraction"
            
        processed = saveAnalysisProcessedData(Data, "CustomAnalysis_"+node["data"]["Type"], metadata, recording)
        
    node["result"] = processed.uid
    return node

def extractAnalysisOutput(node):
    result =  models.Recording.find(uid=node["result"])
    Data = Database.loadSourceFile(result.pointer, result.hashed)

    def CleanupSignalSeries(a):
        a["Data"] = a["Data"].T
        a["MissingIndex"] = []
        for j in range(a["Missing"].shape[1]):
            a["MissingIndex"].append(np.where(a["Missing"][:,j])[0])
        del a["Missing"]
        return a

    AnalysisStruct = {"Signal": [], "Spectrum": [], "TimeFrequencyAnalysis": [], "Annotations": []}
    if Data["DataType"] == "TimeDomain":
        for i in range(len(Data["Data"])):
            Data["Data"][i] = CleanupSignalSeries(Data["Data"][i])

            AnalysisStruct["Signal"].append({
                "Type": "Signal",
                "RecordingId": result.uid,
                "SignalSeries": Data["Data"][i],
                "Alignment": 0
            })
        AnalysisStruct["Type"] = "TimeSeries"

    elif Data["DataType"] == "PSD":
        for i in range(len(Data["Data"])):
            AnalysisStruct["Spectrum"].append({
                "Type": "Spectrum",
                "RecordingId": result.uid,
                "PSDSeries": Data["Data"][i]
            })
        AnalysisStruct["Type"] = "Spectrum"

    elif Data["DataType"] == "Power Spectral Separation":
        for channel in Data["Condition"].keys():
            if "TStatistics" in Data["Condition"][channel].keys():
                AnalysisStruct["Spectrum"].append({
                    "Type": "Statistics",
                    "TestType": "Welch's T-Statistics",
                    "Channel": channel,
                    "Frequency": Data["Condition"][channel]["Frequency"],
                    "Range": None,
                    "Results": [Data["Condition"][channel]["TStatistics"],
                                Data["Condition"][channel]["TStatisticsPValues"]*len(Data["Condition"][channel]["TStatisticsPValues"])]
                })
                AnalysisStruct["Spectrum"].append({
                    "Type": "Statistics",
                    "TestType": "Spearman's R",
                    "Channel": channel,
                    "Frequency": Data["Condition"][channel]["Frequency"],
                    "Range": [-1,1],
                    "Results": [Data["Condition"][channel]["RStatistics"],
                                Data["Condition"][channel]["RStatisticsPValues"]*len(Data["Condition"][channel]["RStatisticsPValues"])]
                })
        AnalysisStruct["Type"] = "PSDStatistics"

    elif Data["DataType"] == "Aperiodic Component":
        for i in range(len(Data["Data"])):
            AnalysisStruct["Spectrum"].append({
                "Type": "Spectrum",
                "RecordingId": result.uid,
                "PSDSeries": Data["Data"][i]
            })
        AnalysisStruct["Type"] = "Aperiodic Component"

    elif Data["DataType"] == "Distribution":

        for i in range(len(Data["Data"])):
            if "Epochs" in Data["Data"][i].keys():
                for j in range(len(Data["Data"][i]["Epochs"])):
                    Data["Data"][i]["Epochs"][j] = CleanupSignalSeries(Data["Data"][i]["Epochs"][j])
            else:
                Data["Data"][i] = CleanupSignalSeries(Data["Data"][i])
            
            AnalysisStruct["Signal"].append({
                "Type": "Signal",
                "RecordingId": result.uid,
                "SignalSeries": Data["Data"][i],
                "Alignment": 0
            })
        AnalysisStruct["Type"] = "Distribution"

    elif Data["DataType"] == "Circadian Rhythm":
        for i in range(len(Data["Data"])):
            if "Epochs" in Data["Data"][i].keys():
                for j in range(len(Data["Data"][i]["Epochs"])):
                    Data["Data"][i]["Epochs"][j] = CleanupSignalSeries(Data["Data"][i]["Epochs"][j])
            else:
                Data["Data"][i] = CleanupSignalSeries(Data["Data"][i])
            
            AnalysisStruct["Signal"].append({
                "Type": "Signal",
                "RecordingId": result.uid,
                "SignalSeries": Data["Data"][i],
                "Alignment": 0
            })
        AnalysisStruct["Type"] = "Circadian Rhythm"

    elif Data["DataType"] == "Time Frequency Analysis":
        for i in range(len(Data["Data"])):
            for j in range(len(Data["Data"][i]["Spectrum"])):
                AnalysisStruct["Spectrum"].append({
                    "Type": "Time Frequency Analysis",
                    "RecordingId": result.uid,
                    "Spectrum": Data["Data"][i]["Spectrum"][j],
                    "Alignment": 0
                })

        AnalysisStruct["Type"] = "Time Frequency Analysis"

    elif Data["DataType"] == "Narrow-band Power Extraction":
        for i in range(len(Data["Data"])):
            Data["Data"][i] = CleanupSignalSeries(Data["Data"][i])
            AnalysisStruct["Signal"].append({
                "Type": "Signal",
                "RecordingId": result.uid,
                "SignalSeries": Data["Data"][i],
                "Alignment": 0
            })

        AnalysisStruct["Type"] = "TimeSeries"

    return AnalysisStruct

# %% Processing Node Configuration: Butterworth Filter
ProcessingNodes.append({
    "Group": "Digital Filters",
    "Type": "Butterworth Digital Filter",
    "Description": "Default 5th-order Butterworth IIR Digital Filter with zero-phase Filtering.",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "FilterType",
            "Condition": True,
            "Label": "Filter Type",
            "Type": "SelectSingle",
            "Options": ["Bandpass Filter", "Bandstop Filter"],
            "Default": "Bandpass Filter",
        },
        {
            "Id": "FilterRangeLow",
            "Condition": True,
            "Label": "Filter Range (Lower, Leave Empty to Disable)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "1",
        },
        {
            "Id": "FilterRangeHigh",
            "Condition": True,
            "Label": "Filter Range (Upper, Leave Empty to Disable)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "100",
        }
    ]
})
def handleButterworthFilter(Data, config):
    if config["Configurations"][1]["Value"] == "" and config["Configurations"][2]["Value"] == "":
        return Data

    for data in Data["Data"]:
        if config["Configurations"][0]["Value"] == "Bandpass Filter":
            if config["Configurations"][1]["Value"] == "":
                sos = signal.butter(5, np.array([float(config["Configurations"][2]["Value"])])*2/data["SamplingRate"], 'lowpass', output='sos')
            elif config["Configurations"][2]["Value"] == "":
                sos = signal.butter(5, np.array([float(config["Configurations"][1]["Value"])])*2/data["SamplingRate"], 'highpass', output='sos')
            else:
                sos = signal.butter(5, np.array([float(config["Configurations"][1]["Value"]), float(config["Configurations"][2]["Value"])])*2/data["SamplingRate"], 'bp', output='sos')
        elif config["Configurations"][0]["Value"] == "Bandstop Filter":
            if config["Configurations"][1]["Value"] == "":
                sos = signal.butter(5, np.array([float(config["Configurations"][2]["Value"])])*2/data["SamplingRate"], 'highpass', output='sos')
            elif config["Configurations"][2]["Value"] == "":
                sos = signal.butter(5, np.array([float(config["Configurations"][1]["Value"])])*2/data["SamplingRate"], 'lowpass', output='sos')
            else:
                sos = signal.butter(5, np.array([float(config["Configurations"][1]["Value"]), float(config["Configurations"][2]["Value"])])*2/data["SamplingRate"], 'bandstop', output='sos')

        data["Data"] = signal.sosfiltfilt(sos, data["Data"], axis=0)
    return Data

# %% Processing Node Configuration: Wiener Filter
ProcessingNodes.append({
    "Group": "Digital Filters",
    "Type": "Wiener Filter",
    "Description": "",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "FilterSize",
            "Condition": True,
            "Label": "Wiener Filter Window Size (Samples)",
            "Type": "Input",
            "Verify": "Int",
            "Default": "250",
        }
    ]
})
def handleWienerFilter(Data, config):
    size = int(config["Configurations"][0]["Value"])
    for data in Data["Data"]:
        for i in range(data["Data"].shape[1]):
            Errors = signal.wiener(data["Data"][:,i], mysize=size)
            data["Data"][:,i] = Errors
    return Data

# %% Processing Node Configuration: Epoch by Annotations
ProcessingNodes.append({
    "Group": "Segmentation",
    "Type": "Epoch by Annotations",
    "Description": "",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "EpochMethod",
            "Condition": True,
            "Label": "Window Size (in seconds)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "1",
        }
    ]
})
def handleAnnotationSegmentation(Data, config):
    for data in Data["Data"]:
        Annotations = Event.queryAnnotations(config["ParticipantId"], "RecordingCustomEvent", start_time=data["StartTime"], duration=data["Duration"])
        data["Time"] = np.arange(data["Data"].shape[0]) / data["SamplingRate"] + data["StartTime"]
        data["Epochs"] = []
        for annotation in Annotations:
            TimeSelection = rangeSelection(data["Time"], [annotation["Date"], annotation["Date"]+annotation["Duration"]], "inclusive")
            if np.any(TimeSelection):
                data["Epochs"].append({
                    "Data": data["Data"][TimeSelection,:],
                    "TimeRange": [annotation["Date"], annotation["Date"]+annotation["Duration"]],
                    "Missing": data["Missing"][TimeSelection,:],
                    "Label": annotation["Name"]
                })
        del data["Data"]
        del data["Missing"]
    return Data

# %% Processing Node Configuration: Epoch by Timestamps
ProcessingNodes.append({
    "Group": "Segmentation",
    "Type": "Epoch by Timestamps",
    "Description": "",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "StartTime",
            "Condition": True,
            "Label": "Beginning Timestamp",
            "Type": "Date",
            "Verify": "Timestamp",
            "Default": "0",
        },{
            "Id": "EndTime",
            "Condition": True,
            "Label": "Ending Timestamp",
            "Type": "Date",
            "Verify": "Timestamp",
            "Default": "0",
        }
    ]
})
def handleTimestampSegmentation(Data, config):
    StartTime = int(config["Configurations"][0]["Value"])/1000
    EndTime = int(config["Configurations"][1]["Value"])/1000
    for data in Data["Data"]:
        if not "Time" in data.keys():
            data["Time"] = np.arange(data["Data"].shape[0]) / data["SamplingRate"] + data["StartTime"]
        
        if not "Missing" in data.keys():
            data["Missing"] = np.zeros(data["Data"].shape)

        data["Epochs"] = []
        TimeSelection = rangeSelection(data["Time"], [StartTime, EndTime], "inclusive")
        if np.any(TimeSelection):
            Epoch = {
                "Data": data["Data"][TimeSelection,:],
                "TimeRange": [StartTime, EndTime],
                "Missing": data["Missing"][TimeSelection,:],
                "Label": "Segmentation"
            }
            
            if data["SamplingRate"] < 0:
                Epoch["Time"] = data["Time"][TimeSelection]
            else:
                Epoch["Time"] = data["Time"][TimeSelection]
            data["Epochs"].append(Epoch)
    
    Data["Data"] = [data for data in Data["Data"] if len(data["Epochs"]) > 0]
    for data in Data["Data"]:
        del data["Data"]
    
    return Data

# %% Processing Node Configuration: Compute Statistical Comparison of PSDs
ProcessingNodes.append({
    "Group": "Statistics",
    "Type": "Compute Power Spectral Separation",
    "Description": "",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "Label1Name",
            "Condition": True,
            "Label": "Baseline Label (Annotation for Reference)",
            "Type": "Input",
            "Verify": "String",
            "Default": "",
        },
        {
            "Id": "Label2Name",
            "Condition": True,
            "Label": "Condition Label (Annotation for Testing)",
            "Type": "Input",
            "Verify": "String",
            "Default": "",
        },
        {
            "Id": "Bandwidth",
            "Condition": True,
            "Label": "Feature Bandwidth",
            "Type": "Input",
            "Verify": "Float",
            "Default": "2.5",
        }
    ]
})
def handlePowerSpectralSeparationTest(Data, config):
    Label1Name = config["Configurations"][0]["Value"]
    Label2Name = config["Configurations"][1]["Value"]
    Bandwidth = float(config["Configurations"][2]["Value"])

    PSDs = {"Baseline": {}, "Condition": {}}
    AllChannels = []
    for data in Data["Data"]:
        for spectrum in data["Spectrum"]:
            if not spectrum["Channel"] in AllChannels:
                AllChannels.append(spectrum["Channel"])

            if spectrum["Label"] == Label1Name:
                if spectrum["Channel"] not in PSDs["Baseline"].keys():
                    PSDs["Baseline"][spectrum["Channel"]] = {"Frequency": spectrum["Frequency"], "Power": np.zeros((spectrum["Frequency"].shape[0], 0))}
                PSDs["Baseline"][spectrum["Channel"]]["Power"] = np.concatenate((PSDs["Baseline"][spectrum["Channel"]]["Power"], spectrum["Power"]), axis=1)
            elif spectrum["Label"] == Label2Name:
                if spectrum["Channel"] not in PSDs["Condition"].keys():
                    PSDs["Condition"][spectrum["Channel"]] = {"Frequency": spectrum["Frequency"], "Power": np.zeros((spectrum["Frequency"].shape[0], 0))}
                PSDs["Condition"][spectrum["Channel"]]["Power"] = np.concatenate((PSDs["Condition"][spectrum["Channel"]]["Power"], spectrum["Power"]), axis=1)

    for channel in PSDs["Baseline"].keys():
        PSDs["Baseline"][channel]["Power"] = np.array(PSDs["Baseline"][channel]["Power"])
    for channel in PSDs["Condition"].keys():
        PSDs["Condition"][channel]["Power"] = np.array(PSDs["Condition"][channel]["Power"])

    for channel in AllChannels:
        if channel in PSDs["Baseline"].keys() and channel in PSDs["Condition"].keys():
            # Compute the power spectral separation
            BaselinePower = PSDs["Baseline"][channel]["Power"]
            ConditionPower = PSDs["Condition"][channel]["Power"]
            # Perform statistical comparison (e.g., t-test)
            if len(PSDs["Baseline"][channel]["Frequency"]) == len(PSDs["Condition"][channel]["Frequency"]):
                PSDs["Condition"][channel]["TStatistics"] = []
                PSDs["Condition"][channel]["TStatisticsPValues"] = []
                PSDs["Condition"][channel]["RStatistics"] = []
                PSDs["Condition"][channel]["RStatisticsPValues"] = []
                for f in range(len(PSDs["Baseline"][channel]["Frequency"])):
                    # Compute the t-test
                    Selection = (PSDs["Baseline"][channel]["Frequency"] >= (PSDs["Baseline"][channel]["Frequency"][f] - Bandwidth)) & (PSDs["Baseline"][channel]["Frequency"] <= (PSDs["Baseline"][channel]["Frequency"][f] + Bandwidth))
                    BaseFeature = np.mean(BaselinePower[Selection,:],axis=0)
                    CondFeature = np.mean(ConditionPower[Selection,:],axis=0)
                    t_stat, p_value = stats.ttest_ind(BaseFeature, CondFeature, equal_var=False)
                    PSDs["Condition"][channel]["TStatistics"].append(t_stat)
                    PSDs["Condition"][channel]["TStatisticsPValues"].append(p_value)

                    # Compute the Spearman correlation coefficient
                    label = np.concatenate((np.zeros(BaselinePower.shape[1]), np.ones(ConditionPower.shape[1])))
                    r_stat, p_value = stats.spearmanr(np.concatenate((BaseFeature, CondFeature)), label)
                    PSDs["Condition"][channel]["RStatistics"].append(r_stat)
                    PSDs["Condition"][channel]["RStatisticsPValues"].append(p_value)

    return PSDs

# %% Processing Node Configuration: Compute Value Distribution
ProcessingNodes.append({
    "Group": "Statistics",
    "Type": "Compute Distribution",
    "Description": "",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "FrequencyIndex",
            "Condition": True,
            "Label": "(If Spectral Feature) Center Frequency (in Hertz)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "22.0",
        },
        {
            "Id": "FrequencyWindow",
            "Condition": True,
            "Label": "(If Spectral Feature) Bandwidth (in Hz)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "2.5",
        }
    ]
})
def handleDistributionComputation(Data, config):
    for data in Data["Data"]:
        if "Epochs" in data.keys():
            for i in range(len(data["Epochs"])):
                if "Spectrum" in data["Epochs"][i].keys():
                    pass 
    
    return Data

# %% Processing Node Configuration: Compute Circadian Rhythm from Timeline
ProcessingNodes.append({
    "Group": "Statistics",
    "Type": "Compute Circadian Rhythm from Timeline",
    "Description": "",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": []
})
def handleCircadianRhythmComputation(Data, config):
    for data in Data["Data"]:
        if "Epochs" in data.keys():
            for i in range(len(data["Epochs"])):
                pass
    
    return Data

# %% Processing Node Configuration: Time Frequency Analysis
ProcessingNodes.append({
    "Group": "Power Spectral Estimation",
    "Type": "Time Frequency Analysis",
    "Description": "Time Frequency Analysis",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "FilterType",
            "Condition": True,
            "Label": "Filter Type",
            "Type": "SelectSingle",
            "Options": ["Welch's Periodogram", "Autoregressive Model"],
            "Default": "Welch's Periodogram",
        },
        {
            "Id": "PSDWindowSize",
            "Condition": True,
            "Label": "Window Size (in seconds)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "1",
        },
        {
            "Id": "PSDOverlapSize",
            "Condition": True,
            "Label": "Overlap Size (in seconds)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "0.5",
        },
        {
            "Id": "FrequencyResolution",
            "Condition": True,
            "Label": "Frequency Resolution (Hz)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "0.5",
        }
    ]
})
def handleCustomTimeFrequencyAnalysis(Data, config):
    windowSec = float(config["Configurations"][1]["Value"])
    overlapSec = float(config["Configurations"][2]["Value"])
    frequencyResolution = float(config["Configurations"][3]["Value"])

    for data in Data["Data"]:
        data["Spectrum"] = []
        for Channel in range(len(data["ChannelNames"])):
            if "Data" in data.keys():
                if config["Configurations"][0]["Value"] == "Welch's Periodogram":
                    Spectrum = SPU.welchSpectrogram(data["Data"][:,Channel], window=windowSec, overlap=overlapSec, fs=data["SamplingRate"], frequency_resolution=frequencyResolution)
                    Spectrum["Missing"] = SPU.calculateMissingLabel(data["Missing"][:,Channel], window=windowSec, overlap=overlapSec, fs=data["SamplingRate"])
                elif config["Configurations"][0]["Value"] == "Autoregressive Model":
                    Spectrum = SPU.autoRegressiveSpectrogram(data["Data"][:,Channel], window=windowSec, overlap=overlapSec, frequency_resolution=frequencyResolution, fs=data["SamplingRate"], order=int(data["SamplingRate"]/10))
                    Spectrum["Missing"] = SPU.calculateMissingLabel(data["Missing"][:,Channel], window=windowSec, overlap=overlapSec, fs=data["SamplingRate"])
                data["Spectrum"].append({**Spectrum, **{"Method": config["Configurations"][0]["Value"], 
                                                        "Channel": data["ChannelNames"][Channel], 
                                                        "StartTime": data["StartTime"],
                                                        "Label": ""}})

            elif "Epochs" in data.keys():
                for i in range(len(data["Epochs"])):
                    if config["Configurations"][0]["Value"] == "Welch's Periodogram":
                        Spectrum = SPU.welchSpectrogram(data["Epochs"][i]["Data"][:,Channel], window=windowSec, overlap=overlapSec, fs=data["SamplingRate"])
                        Spectrum["Missing"] = SPU.calculateMissingLabel(data["Epochs"][i]["Missing"][:,Channel], window=windowSec, overlap=overlapSec, fs=data["SamplingRate"])
                        
                    elif config["Configurations"][0]["Value"] == "Autoregressive Model":
                        Spectrum = SPU.autoRegressiveSpectrogram(data["Epochs"][i]["Data"][:,Channel], window=windowSec, overlap=overlapSec, frequency_resolution=0.5, fs=data["SamplingRate"], order=int(data["SamplingRate"]/10))
                        Spectrum["Missing"] = SPU.calculateMissingLabel(data["Epochs"][i]["Missing"][:,Channel], window=windowSec, overlap=overlapSec, fs=data["SamplingRate"])
                    data["Spectrum"].append({**Spectrum,  **{"Method": config["Configurations"][0]["Value"], 
                                                             "Channel": data["ChannelNames"][Channel], 
                                                             "StartTime": data["Epochs"][i]["TimeRange"][0],
                                                             "Label": data["Epochs"][i]["Label"]}})

        if "Data" in data.keys():
            del data["Data"]
            del data["Missing"]
        elif "Epochs" in data.keys():
            del data["Epochs"]

    return Data

# %% Processing Node Configuration: Time Frequency Analysis
ProcessingNodes.append({
    "Group": "Power Spectral Estimation",
    "Type": "Aperiodic Component Extraction",
    "Description": "Extract Aperiodic Component from PSDs",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "EstimationType",
            "Condition": True,
            "Label": "Estimation Type",
            "Type": "SelectSingle",
            "Options": ["Log-Log Linear Fit", "Spectral Parameterization"],
            "Default": "Log-Log Linear Fit",
        },
        {
            "Id": "FrequencyRange",
            "Condition": True,
            "Label": "Frequency Range in a Comma-Separated List (i.e.: 4-12,40,60-90)",
            "Type": "Input",
            "Verify": "String",
            "Default": "4-12,40,60-90",
        }
    ]
})
def handleAperiodicComponentExtraction(Data, config):
    frequencyRanges = config["Configurations"][1]["Value"].split(",")
    
    for data in Data["Data"]:
        for i in range(len(data["Spectrum"])):
            frequencySelection = np.zeros(data["Spectrum"][i]["Frequency"].shape, dtype=bool)
            for j in range(len(frequencyRanges)):
                if "-" in frequencyRanges[j]:
                    frequencySelection = np.bitwise_or(frequencySelection, rangeSelection(data["Spectrum"][i]["Frequency"], [float(k) for k in frequencyRanges[j].split("-")], "inclusive"))
                else:
                    frequencySelection = np.bitwise_or(frequencySelection, data["Spectrum"][i]["Frequency"] == float(frequencyRanges[j]))

            YData = np.log10(data["Spectrum"][i]["Power"][frequencySelection])
            XData = np.log10(data["Spectrum"][i]["Frequency"][frequencySelection])
            coe = np.polyfit(XData, YData, 2)
            data["Spectrum"][i]["AperiodicBaseline"] = np.polyval(coe, np.log10(data["Spectrum"][i]["Frequency"]))
            for j in range(len(data["Spectrum"][i]["AperiodicBaseline"])):
                if np.isnan(data["Spectrum"][i]["AperiodicBaseline"][-j-1]):
                    data["Spectrum"][i]["AperiodicBaseline"][-j-1] = data["Spectrum"][i]["AperiodicBaseline"][-j]
            data["Spectrum"][i]["AperiodicBaseline"] = np.power(10,data["Spectrum"][i]["AperiodicBaseline"])
            
    return Data

# %% Processing Node Configuration: Narrow-Band Power Extraction
ProcessingNodes.append({
    "Group": "Feature Extraction",
    "Type": "Narrow-band Power Extraction",
    "Description": "Extract narrow band spectral feature from Spectrogram and visualize across time",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "CenterFrequency",
            "Condition": True,
            "Label": "Spectral Feature Center Frequency (Hz)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "20",
        },
        {
            "Id": "FrequencyWindow",
            "Condition": True,
            "Label": "Spectral Feature Bandwidth [Fc-Fw, Fc+Fw] (Hz)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "2.5",
        },
    ]
})
def handleNarrowBandPowerExtraction(Data, config):
    centerFreq = float(config["Configurations"][0]["Value"])
    freqWidth = float(config["Configurations"][1]["Value"])

    Features = []
    for data in Data["Data"]:
        for i in range(len(data["Spectrum"])):
            if "Spectrum" in data.keys():
                FrequencySelection = rangeSelection(data["Spectrum"][i]["Frequency"], [centerFreq-freqWidth, centerFreq+freqWidth], "inclusive")
                NarrowbandPower = np.mean(data["Spectrum"][i]["Power"][FrequencySelection, :], axis=0)
                Features.append({
                    "Unit": "uV/Hz",
                    "Data": NarrowbandPower.reshape(1,-1).T,
                    "Missing": data["Spectrum"][i]["Missing"].reshape(1,-1).T,
                    "Time": data["Spectrum"][i]["Time"],
                    "StartTime": data["Spectrum"][i]["StartTime"],
                    "ChannelNames": [data["Spectrum"][i]["Channel"]]
                })

    Data["Data"] = Features
    return Data

# %% Processing Node Configuration: Welch's Periodogram
ProcessingNodes.append({
    "Group": "Power Spectral Estimation",
    "Type": "Welch's Periodogram",
    "Description": "Welch's Periodogram",
    "NodeType": "SingleInputProcessingNode",
    "Configurations": [
        {
            "Id": "PSDWindowSize",
            "Condition": True,
            "Label": "Window Size (in seconds)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "1",
        },
        {
            "Id": "PSDOverlapSize",
            "Condition": True,
            "Label": "Overlap Size (in seconds)",
            "Type": "Input",
            "Verify": "Float",
            "Default": "0.5",
        }
    ]
})
def handleWelchPeriodogram(Data, config):
    windowSec = float(config["Configurations"][0]["Value"])
    overlapSec = float(config["Configurations"][1]["Value"])
    if windowSec > 2:
        nfftSize = windowSec
    else:
        nfftSize = 2

    for data in Data["Data"]:
        data["Spectrum"] = []
        for Channel in range(len(data["ChannelNames"])):
            if "Data" in data.keys():
                Fxx, Pxx = signal.welch(data["Data"][data["Missing"][:,Channel] == 0,Channel], fs=data["SamplingRate"], nperseg=data["SamplingRate"]*windowSec, noverlap=data["SamplingRate"]*overlapSec, nfft=data["SamplingRate"]*nfftSize)
                data["Spectrum"].append({
                    "Frequency": Fxx, 
                    "Power": Pxx,
                    "Time": [0],
                    "Method": "Welch",
                    "Channel": data["ChannelNames"][Channel],
                    "Label": ""
                })
            elif "Epochs" in data.keys():
                for i in range(len(data["Epochs"])):
                    Fxx, Pxx = signal.welch(data["Epochs"][i]["Data"][data["Epochs"][i]["Missing"][:,Channel] == 0,Channel], fs=data["SamplingRate"], nperseg=data["SamplingRate"]*windowSec, noverlap=data["SamplingRate"]*overlapSec, nfft=data["SamplingRate"]*nfftSize)
                    data["Spectrum"].append({
                        "Frequency": Fxx, 
                        "Power": Pxx,
                        "Time": [0],
                        "Method": "Welch",
                        "Channel": data["ChannelNames"][Channel],
                        "Label": data["Epochs"][i]["Label"]
                    })

        if "Data" in data.keys():
            del data["Data"]
            del data["Missing"]
        elif "Epochs" in data.keys():
            del data["Epochs"]

    return Data

def processTimeseriesAnalysisRaw(data, config):
    AnalysisStruct = {"Signal": [], "Annotations": []}
    Data = processTimeDomainStreaming(None, data, config)

    Data["Data"] = Data["Data"].T
    Data["MissingIndex"] = []
    for i in range(Data["Missing"].shape[1]):
        Data["MissingIndex"].append(np.where(Data["Missing"][:,i])[0])
    del Data["Missing"]

    AnalysisStruct["Signal"].append({
        "Type": "Signal",
        "RecordingId": "",
        "SignalSeries": Data,
        "Alignment": 0
    })

    AnalysisStruct["Annotations"] = uniqueList(AnalysisStruct["Annotations"])
    return AnalysisStruct

def computeTherapeuticEffects(AnalysisStruct):
    AllTherapyLabels = []
    for i in range(len(AnalysisStruct["Therapy"])):
        for j in range(len(AnalysisStruct["Therapy"][i]["TherapySeries"])):
            for key in AnalysisStruct["Therapy"][i]["TherapySeries"][j]["TherapyOverview"].keys():
                if not key in AllTherapyLabels:
                    AllTherapyLabels.append(key)
    
    parameters = ["Amplitude", "Frequency", "Pulsewidth"]
    
    StimulationPSDs = {}
    for label in AllTherapyLabels:
        StimulationPSDs[label] = {}
        TherapyChanges = getTherapyChanges(AnalysisStruct, label)
        for i in range(len(AnalysisStruct["Signal"])):
            for j in range(len(AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"])):
                if not AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j] in StimulationPSDs[label].keys():
                    StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]] = {}
                if not "Spectrum" in AnalysisStruct["Signal"][i]["SignalSeries"].keys():
                    continue
                Time = AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Time"] + AnalysisStruct["Signal"][i]["SignalSeries"]["StartTime"] + AnalysisStruct["Signal"][i]["Alignment"]

                for parameter in parameters:
                    UniqueStates = []
                    for stage in range(len(TherapyChanges[parameter])):
                        if not TherapyChanges[parameter][stage]["State"] in UniqueStates:
                            UniqueStates.append(TherapyChanges[parameter][stage]["State"])
                    UniqueStates = sorted(UniqueStates)
                    if not parameter in StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]].keys():
                        StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]][parameter] = []

                    if len(UniqueStates) > 1:
                        for state in UniqueStates:
                            TimeSelection = np.zeros(Time.shape, dtype=bool)
                            for stage in range(len(TherapyChanges[parameter])-1):
                                if TherapyChanges[parameter][stage]["State"] == state:
                                    TimeSelection |= (
                                        (Time > TherapyChanges[parameter][stage]["Time"]+2) & 
                                        (Time < TherapyChanges[parameter][stage+1]["Time"]-2)
                                    )
                                
                            if TherapyChanges[parameter][-1]["State"] == state:
                                TimeSelection |= (
                                    (Time > TherapyChanges[parameter][-1]["Time"]+2)
                                )

                            if np.sum(TimeSelection) > 0:
                                StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]][parameter].append({
                                    "Frequency": AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Frequency"],
                                    "MeanPower": np.mean(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"][:, TimeSelection],axis=1),
                                    "StdErrPower": np.std(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"][:, TimeSelection],axis=1)/np.sqrt(np.sum(TimeSelection)),
                                    "State": state
                                })
                                
                    elif len(UniqueStates) == 1:
                        StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]][parameter].append({
                            "Frequency": AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Frequency"],
                            "MeanPower": np.mean(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"],axis=1),
                            "StdErrPower": np.std(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"],axis=1)/np.sqrt(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"].shape[1]),
                            "State": UniqueStates[0]
                        })
                        
    AnalysisStruct["TherapeuticEffects"] = StimulationPSDs
    return AnalysisStruct

def processTimeseriesAnalysis(participant_uid, recording_uid, config):
    recording = models.Recording.find(uid=recording_uid)
    AnalysisStruct = {"Signal": [], "Annotations": []}

    if not recording.source.owner.pk == participant_uid:
        raise Exception("Permission Denied. Accessing Denied Recordings")

    if recording.type in ["MedtronicElectrodeIdentifier", "MedtronicBrainSenseSurvey", "MedtronicBaselineMontages", "MedtronicBrainSenseTimeDomain", "MedtronicIndefiniteStream"]:
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        Data = processTimeDomainStreaming(recording, Data, config)

        Data["Data"] = Data["Data"].T
        Data["MissingIndex"] = []
        for i in range(Data["Missing"].shape[1]):
            Data["MissingIndex"].append(np.where(Data["Missing"][:,i])[0])
        del Data["Missing"]
        
        DBSDevice = models.DBSDevice.find(uid=recording.source.metadata["Device"]).get_info()
        for i in range(len(Data["ChannelNames"])):
            Data["ChannelNames"][i] = DBSDevice["GenericName"] + ": " + BrainSenseStream.reformatChannelName(Data["ChannelNames"][i], DBSDevice["Electrodes"])

        TimeShift = recording.adjusted_alignment
        AnalysisStruct["Signal"].append({
            "Type": "Signal",
            "RecordingId": recording.uid,
            "SignalSeries": Data,
            "Alignment": TimeShift
        })

        Annotations = Event.queryAnnotations(participant_uid, "RecordingCustomEvent", start_time=Data["StartTime"]+TimeShift, duration=Data["Duration"])
        AnalysisStruct["Annotations"].extend(Annotations)

    elif recording.type in ["MedtronicBrainSensePowerDomain"]:
        AnalysisStruct["Therapy"] = []
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        DBSDevice = models.DBSDevice.find(uid=recording.source.metadata["Device"]).get_info()
        if config["APIAccess"]:
            TherapeuticLabel, TherapyGraphs = BrainSenseStream.processTherapyInformation(Data, DBSDevice)
            AnalysisStruct["Therapy"].append({
                "Type": "Therapy",
                "Data": Data,
                "DBSDevice": DBSDevice,
                "RecordingId": recording.uid,
                "TherapySeries": TherapeuticLabel,
                "TherapyGraphs": TherapyGraphs,
                "FullTherapy": Data["Descriptor"]["Therapy"],
                "Alignment": recording.adjusted_alignment
            })
        else:
            TherapeuticLabel, TherapyGraphs = BrainSenseStream.processTherapyInformation(Data, DBSDevice)
            AnalysisStruct["Therapy"].append({
                "Type": "Therapy",
                "RecordingId": recording.uid,
                "TherapySeries": TherapeuticLabel,
                "TherapyGraphs": TherapyGraphs,
                "FullTherapy": Data["Descriptor"]["Therapy"],
                "Alignment": recording.adjusted_alignment
            })

    elif recording.type in ["CustomizedStreamingData"]:
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        Data = processTimeDomainStreaming(recording, Data, config)
        Data["Data"] = Data["Data"].T
        Data["MissingIndex"] = []
        for i in range(Data["Missing"].shape[1]):
            Data["MissingIndex"].append(np.where(Data["Missing"][:,i])[0])
        del Data["Missing"]
        
        #DBSDevice = models.DBSDevice.find(uid=recording.source.metadata["Device"]).get_info()

        TimeShift = recording.adjusted_alignment
        AnalysisStruct["Signal"].append({
            "Type": "Signal",
            "RecordingId": recording.uid,
            "SignalSeries": Data,
            "Alignment": TimeShift
        })

        Annotations = Event.queryAnnotations(participant_uid, "RecordingCustomEvent", start_time=Data["StartTime"]+TimeShift, duration=Data["Duration"])
        AnalysisStruct["Annotations"].extend(Annotations)

    elif recording.type in ["AOMPX"]:
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        if not config["APIAccess"]:
            Data = downsampleTimeDomainStreaming(Data)
        Data = processTimeDomainStreaming(recording, Data, config)
        Data["Data"] = Data["Data"].T
        Data["MissingIndex"] = []
        for i in range(Data["Missing"].shape[1]):
            Data["MissingIndex"].append(np.where(Data["Missing"][:,i])[0])
        del Data["Missing"]
        
        TimeShift = recording.adjusted_alignment
        AnalysisStruct["Signal"].append({
            "Type": "Signal",
            "RecordingId": recording.uid,
            "SignalSeries": Data,
            "Alignment": TimeShift
        })

        Annotations = Event.queryAnnotations(participant_uid, "RecordingCustomEvent", start_time=Data["StartTime"]+TimeShift, duration=Data["Duration"])
        AnalysisStruct["Annotations"].extend(Annotations)

    elif recording.type in ["HPFCSV", "MATFile", "SynchronizedMDAT"]:
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        if not config["APIAccess"]:
            Data = downsampleTimeDomainStreaming(Data)
            config["TimeSeriesRecording"]["CardiacFilter"]["value"] = "Skipped for Non-APIAccess"
        
        Data = processTimeDomainStreaming(recording, Data, config)
        Data["Data"] = Data["Data"].T
        Data["MissingIndex"] = []
        for i in range(Data["Missing"].shape[1]):
            Data["MissingIndex"].append(np.where(Data["Missing"][:,i])[0])
        del Data["Missing"]
        
        TimeShift = recording.adjusted_alignment
        AnalysisStruct["Signal"].append({
            "Type": "Signal",
            "RecordingId": recording.uid,
            "SignalSeries": Data,
            "Alignment": TimeShift
        })

        Annotations = Event.queryAnnotations(participant_uid, "RecordingCustomEvent", start_time=Data["StartTime"]+TimeShift, duration=Data["Duration"])
        AnalysisStruct["Annotations"].extend(Annotations)

    else:
        print(recording.type)

    AnalysisStruct["Annotations"] = uniqueList(AnalysisStruct["Annotations"])
    return AnalysisStruct

def downloadNeuralActivitySnapshot(participant_uid, config):
    AllSnapshots = []
    Participant = models.Participant.find(uid=participant_uid)
    SourceFiles = models.SourceFile.find_all(owner=Participant)
    DBSDevices = [device.get_info() for device in models.DBSDevice.find_all(owner=Participant)]
    DBSDeviceDictionary = {}
    for i in range(len(DBSDevices)):
        DBSDeviceDictionary[DBSDevices[i]["Id"]] = DBSDevices[i]

    Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages"])
    for recording in Recordings:
        Description = recording.get_info()
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        Data = processNeuralActivitySnapshot(recording, Data, config)
        
        if recording.source.metadata["Device"] in DBSDeviceDictionary.keys():
            DBSDevice = DBSDeviceDictionary[recording.source.metadata["Device"]]
        else:
            raise Exception("Neural Activity Snapshot Query found a recording whose DeviceId does not belongs to the Participant")

        MedtronicPSDs = []
        if "MedtronicPSD" in Data["Descriptor"].keys():
            for channel in Data["ChannelNames"]:
                found = False
                for psd in Data["Descriptor"]["MedtronicPSD"]:
                    if psd and psd["Hemisphere"].split(".")[1]:
                        if channel.startswith(psd["SensingElectrodes"].split(".")[1]):
                            MedtronicPSDs.append(psd)
                            found = True
                            break

                if not found:
                    MedtronicPSDs.append(None)

        for i in range(len(Data["ChannelNames"])):
            ElectrodeIdentifier = BrainSenseStream.reformatChannelName(Data["ChannelNames"][i], DBSDevice["Electrodes"])
            if ElectrodeIdentifier.startswith("Left"):
                Description["Date"] += 1

            Data["ChannelNames"][i] = DBSDevice["Heritage"] + ": " + ElectrodeIdentifier
            Data["ChannelNames"][i] = Data["ChannelNames"][i].replace(".1","A").replace(".2","B").replace(".3","C")
        
        AllSnapshots.append({**Description, **{
            "Type": recording.type,
            "MedtronicPSDs": MedtronicPSDs if "MedtronicPSD" in Data["Descriptor"].keys() else None,
            "RecordingId": recording.uid,
            "Channels": Data["ChannelNames"],
            "PSDs": Data["PSD"],
            "Data": Data["Data"]
        }})
    
    return AllSnapshots
        
def downloadRawRecordings(participant_uid, recording_uid, channel, config):
    recording = models.Recording.find(uid=recording_uid)
    if not recording.source.owner.pk == participant_uid:
        raise Exception("Permission Denied. Accessing Denied Recordings")
    
    Data = Database.loadSourceFile(recording.pointer, recording.hashed)
    if recording.type in ["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages", "MedtronicBrainSenseTimeDomain", "MedtronicIndefiniteStream"]:
        Data = processTimeDomainStreaming(recording, Data, config)
        Data["Data"] = Data["Data"].T
        for i in range(Data["Data"].shape[0]):
            if (Data["ChannelNames"][i] == channel):
                return Data["Data"][i,:].astype(np.float64).tobytes()
    
    elif recording.type in ["MedtronicBrainSensePowerDomain"]:
        BrainSenseLfp = [{"Time": (i / Data["SamplingRate"] + Data["StartTime"]) * 1000, "LFP": 0, "Amplitude": 0} for i in range(len(Data["Data"]))]
        for j in range(len(Data["Data"])):
            for i in range(len(Data["ChannelNames"])):
                if Data["ChannelNames"][i].startswith(channel):
                    if Data["ChannelNames"][i].endswith("Stimulation"):
                        BrainSenseLfp[j]["Amplitude"] = Data["Data"][j][i]
                    elif Data["ChannelNames"][i].endswith("Power"):
                        BrainSenseLfp[j]["LFP"] = Data["Data"][j][i]

        rawBytes = bytearray()
        for i in range(len(BrainSenseLfp)):
            rawBytes.extend(np.array([BrainSenseLfp[i]["Time"], BrainSenseLfp[i]["LFP"], BrainSenseLfp[i]["Amplitude"]], dtype=np.float64).tobytes())
        return rawBytes

    return bytearray()

def downloadTimeseriesAnalysis(participant_uid, recording_uid, config):
    Analysis = processTimeseriesAnalysis(participant_uid, recording_uid, config)
    
    Data = {}
    for i in range(len(Analysis["Signal"])):
        for j in range(len(Analysis["Signal"][i]["SignalSeries"]["ChannelNames"])):
            Data["Time"] = np.arange(len(Analysis["Signal"][i]["SignalSeries"]["Data"][j,:])) / Analysis["Signal"][i]["SignalSeries"]["SamplingRate"]
            Data[Analysis["Signal"][i]["SignalSeries"]["ChannelNames"][j]] = Analysis["Signal"][i]["SignalSeries"]["Data"][j,:]

    Data["Time"] += Analysis["Signal"][i]["SignalSeries"]["StartTime"] + Analysis["Signal"][i]["Alignment"]

    df = pd.DataFrame(Data)
    df["Time"] = df["Time"].astype(np.float64)
    return df

def downloadChronicNeuralActivity(participant_uid, config):
    Analysis = queryChronicNeuralActivity(participant_uid, config)
    
    Data = {"Time": [], "Power": [], "Amplitude": [], "ChannelName": [], "TherapyConfig": [], "RecordingConfig": []}
    for i in range(len(Analysis["ChronicNeuralActivity"])):
        Data["Time"].extend(Analysis["ChronicNeuralActivity"][i]["Time"])
        ChannelName = Analysis["ChronicNeuralActivity"][i]["Device"]["Heritage"] + ": " + Analysis["ChronicNeuralActivity"][i]["ChannelNames"][0]
        for j in range(len(Analysis["ChronicNeuralActivity"][i]["ChannelNames"])):
            if Analysis["ChronicNeuralActivity"][i]["ChannelNames"][j].endswith("Amplitude"):
                Data["Amplitude"].extend(Analysis["ChronicNeuralActivity"][i]["Data"][j])
            else:
                Data["Power"].extend(Analysis["ChronicNeuralActivity"][i]["Data"][j])
        Data["ChannelName"].extend([ChannelName for k in range(len(Analysis["ChronicNeuralActivity"][i]["Data"][j]))])
        Data["TherapyConfig"].extend([Analysis["ChronicNeuralActivity"][i]["TherapyString"] for k in range(len(Analysis["ChronicNeuralActivity"][i]["Data"][j]))])
        Data["RecordingConfig"].extend([Analysis["ChronicNeuralActivity"][i]["RecordingString"] for k in range(len(Analysis["ChronicNeuralActivity"][i]["Data"][j]))])

    df = pd.DataFrame(Data)
    if "Time" in df.columns:
        df["Time"] = df["Time"].astype(np.float64)
    return df

def getTherapyChanges(Analysis, key):
    TherapySeries = {}
    PreviousState = {}
    parameters = ["Amplitude", "Frequency", "Pulsewidth"]
    for i in range(len(Analysis["Therapy"])):
        for j in range(len(Analysis["Therapy"][i]["TherapySeries"])):
            if key in Analysis["Therapy"][i]["TherapySeries"][j]["TherapyOverview"].keys():
                if Analysis["Therapy"][i]["TherapySeries"][j]["TherapyOverview"][key]["Type"] == "StandardIPGStimulation":
                    for parameter in parameters:
                        if not parameter in PreviousState.keys():
                            TherapySeries[parameter] = [{"Time": Analysis["Therapy"][i]["TherapySeries"][j]["Time"], 
                                                         "State": Analysis["Therapy"][i]["TherapySeries"][j]["TherapyOverview"][key][parameter]}]
                        else:
                            if not PreviousState[parameter] == Analysis["Therapy"][i]["TherapySeries"][j]["TherapyOverview"][key][parameter]:
                                TherapySeries[parameter].append({"Time": Analysis["Therapy"][i]["TherapySeries"][j]["Time"], 
                                                                 "State": Analysis["Therapy"][i]["TherapySeries"][j]["TherapyOverview"][key][parameter]})

                        PreviousState[parameter] = Analysis["Therapy"][i]["TherapySeries"][j]["TherapyOverview"][key][parameter]

    if len(TherapySeries.keys()) == 0:
        for parameter in parameters:
            TherapySeries[parameter] = [{"Time": 0, "State": -1}]
    
    return TherapySeries
    
def processTherapeuticAnalysis(participant_uid, analysis_uid, config):
    Analysis = models.Analysis.find(uid=analysis_uid)
    AnalysisStruct = {"Signal": [], "Therapy": [], "Annotations": []}
    for recording in Analysis.recordings.all():
        if not recording.source.owner.pk == participant_uid:
            raise Exception("Permission Denied. Accessing Denied Recordings")
        
        if recording.type in ["MedtronicBrainSenseTimeDomain"]:
            rel = models.RecordingRel.find(analysis=Analysis, recording=recording)
            Data = Database.loadSourceFile(recording.pointer, recording.hashed)
            Data = processTimeDomainStreaming(recording, Data, config)
            Data["Data"] = Data["Data"].T
            Data["MissingIndex"] = []
            for i in range(Data["Missing"].shape[1]):
                Data["MissingIndex"].append(np.where(Data["Missing"][:,i])[0])
            del Data["Missing"]

            DBSDevice = models.DBSDevice.find(uid=recording.source.metadata["Device"]).get_info()
            for i in range(len(Data["ChannelNames"])):
                Data["ChannelNames"][i] = DBSDevice["GenericName"] + ": " + BrainSenseStream.reformatChannelName(Data["ChannelNames"][i], DBSDevice["Electrodes"])

            TimeShift = (rel.time_shift if rel else 0) + recording.adjusted_alignment
            AnalysisStruct["Signal"].append({
                "Type": "Signal",
                "RecordingId": recording.uid,
                "SignalSeries": Data,
                "Alignment": TimeShift
            })

            Annotations = Event.queryAnnotations(participant_uid, "RecordingCustomEvent", start_time=Data["StartTime"]+TimeShift, duration=Data["Duration"])
            AnalysisStruct["Annotations"].extend(Annotations)

        elif recording.type in ["MedtronicBrainSensePowerDomain"]:
            rel = models.RecordingRel.find(analysis=Analysis, recording=recording)
            Data = Database.loadSourceFile(recording.pointer, recording.hashed)
            DBSDevice = models.DBSDevice.find(uid=recording.source.metadata["Device"]).get_info()
            if config["APIAccess"]:
                TherapeuticLabel, TherapyGraphs = BrainSenseStream.processTherapyInformation(Data, DBSDevice)
                AnalysisStruct["Therapy"].append({
                    "Type": "Therapy",
                    "Data": Data,
                    "DBSDevice": DBSDevice,
                    "RecordingId": recording.uid,
                    "TherapySeries": TherapeuticLabel,
                    "TherapyGraphs": TherapyGraphs,
                    "FullTherapy": Data["Descriptor"]["Therapy"],
                    "Alignment": (rel.time_shift if rel else 0) + recording.adjusted_alignment
                })
            else:
                TherapeuticLabel, TherapyGraphs = BrainSenseStream.processTherapyInformation(Data, DBSDevice)
                AnalysisStruct["Therapy"].append({
                    "Type": "Therapy",
                    "RecordingId": recording.uid,
                    "TherapySeries": TherapeuticLabel,
                    "TherapyGraphs": TherapyGraphs,
                    "FullTherapy": Data["Descriptor"]["Therapy"],
                    "Alignment": (rel.time_shift if rel else 0) + recording.adjusted_alignment
                })


    AnalysisStruct["Annotations"] = uniqueList(AnalysisStruct["Annotations"])

    if config["APIAccess"]:
        return AnalysisStruct

    AllTherapyLabels = []
    for i in range(len(AnalysisStruct["Therapy"])):
        for j in range(len(AnalysisStruct["Therapy"][i]["TherapySeries"])):
            for key in AnalysisStruct["Therapy"][i]["TherapySeries"][j]["TherapyOverview"].keys():
                if not key in AllTherapyLabels:
                    AllTherapyLabels.append(key)
    
    parameters = ["Amplitude", "Frequency", "Pulsewidth"]
    
    StimulationPSDs = {}
    for label in AllTherapyLabels:
        StimulationPSDs[label] = {}
        TherapyChanges = getTherapyChanges(AnalysisStruct, label)
        for i in range(len(AnalysisStruct["Signal"])):
            for j in range(len(AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"])):
                if not AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j] in StimulationPSDs[label].keys():
                    StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]] = {}
                Time = AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Time"] + AnalysisStruct["Signal"][i]["SignalSeries"]["StartTime"] + AnalysisStruct["Signal"][i]["Alignment"]

                for parameter in parameters:
                    UniqueStates = []
                    for stage in range(len(TherapyChanges[parameter])):
                        if not TherapyChanges[parameter][stage]["State"] in UniqueStates:
                            UniqueStates.append(TherapyChanges[parameter][stage]["State"])
                    UniqueStates = sorted(UniqueStates)
                    if not parameter in StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]].keys():
                        StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]][parameter] = []

                    if len(UniqueStates) > 1:
                        for state in UniqueStates:
                            TimeSelection = np.zeros(Time.shape, dtype=bool)
                            for stage in range(len(TherapyChanges[parameter])-1):
                                if TherapyChanges[parameter][stage]["State"] == state:
                                    TimeSelection |= (
                                        (Time > TherapyChanges[parameter][stage]["Time"]+2) & 
                                        (Time < TherapyChanges[parameter][stage+1]["Time"]-2)
                                    )
                                
                            if TherapyChanges[parameter][-1]["State"] == state:
                                TimeSelection |= (
                                    (Time > TherapyChanges[parameter][-1]["Time"]+2)
                                )

                            if np.sum(TimeSelection) > 0:
                                StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]][parameter].append({
                                    "Frequency": AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Frequency"],
                                    "MeanPower": np.mean(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"][:, TimeSelection],axis=1),
                                    "StdErrPower": np.std(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"][:, TimeSelection],axis=1)/np.sqrt(np.sum(TimeSelection)),
                                    "State": state
                                })
                                
                    elif len(UniqueStates) == 1:
                        StimulationPSDs[label][AnalysisStruct["Signal"][i]["SignalSeries"]["ChannelNames"][j]][parameter].append({
                            "Frequency": AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Frequency"],
                            "MeanPower": np.mean(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"],axis=1),
                            "StdErrPower": np.std(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"],axis=1)/np.sqrt(AnalysisStruct["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"].shape[1]),
                            "State": UniqueStates[0]
                        })
                        
    AnalysisStruct["TherapeuticEffects"] = StimulationPSDs
    
    return AnalysisStruct

def downloadTherapeuticAnalysis(participant_uid, analysis_uid, config):
    Analysis = processTherapeuticAnalysis(participant_uid, analysis_uid, config)
    
    Data = {}
    for i in range(len(Analysis["Signal"])):
        for j in range(len(Analysis["Signal"][i]["SignalSeries"]["ChannelNames"])):
            Data["Time"] = np.arange(len(Analysis["Signal"][i]["SignalSeries"]["Data"][j,:])) / Analysis["Signal"][i]["SignalSeries"]["SamplingRate"]
            Data[Analysis["Signal"][i]["SignalSeries"]["ChannelNames"][j]] = Analysis["Signal"][i]["SignalSeries"]["Data"][j,:]

    Data["Time"] += Analysis["Signal"][i]["SignalSeries"]["StartTime"] + Analysis["Signal"][i]["Alignment"]
    df = pd.DataFrame(Data)
    if "Time" in df.columns:
        df["Time"] = df["Time"].astype(np.float64)
    return df

def downsampleTimeDomainStreaming(data):
    if data["SamplingRate"] > 300:
        sos = signal.butter(5, np.array([1,150])*2/data["SamplingRate"], 'bp', output='sos')
        data["Data"] = signal.sosfiltfilt(sos, data["Data"], axis=0)
        
        skipIndexes = int(np.floor(data["SamplingRate"] / 300))
        data["Data"] = data["Data"][::skipIndexes, :]
        data["Time"] = data["Time"][::skipIndexes]
        data["Missing"] = data["Missing"][::skipIndexes, :]
        data["SamplingRate"] /= skipIndexes
    return data

def processTimeDomainStreaming(recording, data, config):
    if len(data["Data"].shape) == 1:
        data["Data"] = data["Data"].reshape(-1,1)

    if config["TimeSeriesRecording"]["StandardFilter"]["value"] == "Butterworth 1-100Hz":
        if data["SamplingRate"] > 200:
            sos = signal.butter(5, np.array([1,100])*2/data["SamplingRate"], 'bp', output='sos')
            data["Data"] = signal.sosfiltfilt(sos, data["Data"], axis=0)
        else:
            sos = signal.butter(5, 1*2/data["SamplingRate"], 'highpass', output='sos')
            data["Data"] = signal.sosfiltfilt(sos, data["Data"], axis=0)

    if config["TimeSeriesRecording"]["NotchFilter"]["value"] == "Notch 55-65Hz":
        sos = signal.butter(5, np.array([55,65])*2/data["SamplingRate"], 'bandstop', output='sos')
        data["Data"] = signal.sosfiltfilt(sos, data["Data"], axis=0)
    elif config["TimeSeriesRecording"]["NotchFilter"]["value"] == "Notch 45-55Hz":
        sos = signal.butter(5, np.array([45,55])*2/data["SamplingRate"], 'bandstop', output='sos')
        data["Data"] = signal.sosfiltfilt(sos, data["Data"], axis=0)

    for i in range(len(data["ChannelNames"])):
        if config["TimeSeriesRecording"]["WienerFilter"]["value"] == "Use Wiener Filter":
            data["Data"][:,i] -= signal.wiener(data["Data"][:,i], mysize=int(data["SamplingRate"] / 2))

    if config["TimeSeriesRecording"]["CardiacFilter"]["value"] == "Use Adaptive Template Matching":
        data = handleCardiacFilter(data, {
            "StandardFilter": config["TimeSeriesRecording"]["StandardFilter"]["value"],
            "NotchFilter": config["TimeSeriesRecording"]["NotchFilter"]["value"],
            "WienerFilter": config["TimeSeriesRecording"]["WienerFilter"]["value"],
            "CardiacFilter": config["TimeSeriesRecording"]["CardiacFilter"]["value"]
        }, recording=recording)
    
    if not config["TimeSeriesRecording"]["SpectrogramMethod"]["value"] == "No Spectrogram":
        data = handleTimeFrequencyAnalysis(data, {
            "StandardFilter": config["TimeSeriesRecording"]["StandardFilter"]["value"],
            "NotchFilter": config["TimeSeriesRecording"]["NotchFilter"]["value"],
            "WienerFilter": config["TimeSeriesRecording"]["WienerFilter"]["value"],
            "CardiacFilter": config["TimeSeriesRecording"]["CardiacFilter"]["value"],
            "SpectrogramMethod": config["TimeSeriesRecording"]["SpectrogramMethod"]["value"],
            "BaselineCorrection": config["TimeSeriesRecording"]["BaselineCorrection"]["value"],
            "Normalization": config["TimeSeriesRecording"]["Normalization"]["value"]
        }, recording=recording)

    return data

def handleCardiacFilter(data, config, recording=None):
    if recording:
        ProcessedData = models.Recording.find(original=recording, type="CardiacFiltered", metadata=config)
        if ProcessedData:
            return Database.loadSourceFile(ProcessedData.pointer, ProcessedData.hashed)

    Window = int(data["SamplingRate"] / 2)
    for i in range(len(data["ChannelNames"])):
        KurtosisIndex = range(0, len(data["Data"][:,i])-Window)
        ExpectedKurtosis = np.zeros((len(KurtosisIndex)))
        for j in range(len(KurtosisIndex)):
            zScore = stats.zscore(data["Data"][:,i][KurtosisIndex[j]:KurtosisIndex[j]+Window])
            ExpectedKurtosis[j] = np.mean(np.power(zScore, 4))

        sos = signal.butter(3, np.array([0.5, 2])*2/data["SamplingRate"], "bandpass", output="sos")
        ExpectedKurtosis = signal.sosfiltfilt(sos,ExpectedKurtosis)
        Peaks, _ = signal.find_peaks(ExpectedKurtosis, distance=125)
        Peaks += int(Window/2)

        CardiacEpochs = []
        SearchWindow = int(data["SamplingRate"] * 0.4)
        for j in range(len(Peaks)):
            if ExpectedKurtosis[Peaks[j]-int(Window/2)] < 1.2:
                continue

            ShiftPeak = 0
            if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(data["Data"][:,i]):
                continue 
            findPeak = np.argmax(data["Data"][:,i][Peaks[j]-SearchWindow:Peaks[j]+SearchWindow])
            ShiftPeak = SearchWindow-findPeak
            if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(data["Data"][:,i]):
                continue 
            CardiacEpochs.append(data["Data"][:,i][Peaks[j]-SearchWindow-ShiftPeak:Peaks[j]+SearchWindow-ShiftPeak])

        EKGTemplate = np.mean(np.array(CardiacEpochs), axis=0)
        EKGTemplate = EKGTemplate / (np.max(EKGTemplate)-np.min(EKGTemplate))

        def EKGTemplateFunc(xdata, amplitude, offset):
            return EKGTemplate * amplitude + offset

        CardiacFiltered = copy.deepcopy(data["Data"][:,i])
        for j in range(len(Peaks)):
            ShiftPeak = 0
            if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(data["Data"][:,i]):
                continue 

            findPeak = np.argmax(data["Data"][:,i][Peaks[j]-SearchWindow:Peaks[j]+SearchWindow])
            ShiftPeak = SearchWindow-findPeak
            if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(data["Data"][:,i]):
                continue
            
            sliceSelection = np.arange(Peaks[j]-SearchWindow-ShiftPeak, Peaks[j]+SearchWindow-ShiftPeak)
            Original = data["Data"][:,i][sliceSelection]
            params, covmat = optimize.curve_fit(EKGTemplateFunc, sliceSelection, Original)
            CardiacFiltered[sliceSelection] = Original - EKGTemplateFunc(sliceSelection, *params)
        data["Data"][:,i] = CardiacFiltered
    
    if recording:
        ProcessedData = models.Recording.create(recording, "CardiacFlitered")
        ProcessedData.pointer = DATABASE_PATH + "recordings" + os.path.sep + recording.source.owner.uid + os.path.sep + ProcessedData.uid + ".bdat"
        ProcessedData.hashed = Database.saveSourceFile(data, ProcessedData.pointer)
        ProcessedData.metadata = config
        ProcessedData.save()
    return data

def handleTimeFrequencyAnalysis(data, config, recording=None):
    if recording:
        ProcessedData = models.Recording.find(original=recording, type="TimeFrequencyAnalysis", metadata=config)
        if ProcessedData:
            return Database.loadSourceFile(ProcessedData.pointer, ProcessedData.hashed)
    
    data["Spectrum"] = []
    if len(data["ChannelNames"]) == 1:
        data["Data"] = data["Data"].reshape(-1,1)
        data["Missing"] = data["Missing"].reshape(-1,1)

    for i in range(len(data["ChannelNames"])):
        if config["SpectrogramMethod"] == "Welch's Periodogram":
            Spectrum = SPU.welchSpectrogram(data["Data"][:,i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=data["SamplingRate"])
        
        elif config["SpectrogramMethod"] == "Medtronic Percept PSD":
            Spectrum = SPU.MedtronicPSD(data["Data"][:,i], packets=[5], fs=data["SamplingRate"])

        elif config["SpectrogramMethod"] == "Short-time Fourier Transform":
            Spectrum = SPU.defaultSpectrogram(data["Data"][:,i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=data["SamplingRate"])

        elif config["SpectrogramMethod"] == "Wavelet":
            Spectrum = SPU.waveletTimeFrequency(data["Data"][:,i], freq=np.arange(0.5,data["SamplingRate"]/2,0.5), ma=int(data["SamplingRate"]/2), fs=data["SamplingRate"])
            Spectrum["Missing"] = data["Missing"][:,i][::int(data["SamplingRate"]/2)]
            Spectrum["Power"] = Spectrum["Power"][:,::int(data["SamplingRate"]/2)]
            Spectrum["Time"] = Spectrum["Time"][::int(data["SamplingRate"]/2)] + 0.5

        elif config["SpectrogramMethod"] == "Autoregressive Model (Yule-Walker)":
            Spectrum = SPU.autoRegressiveSpectrogram(data["Data"][:,i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=data["SamplingRate"], order=0)

        else: # Default Welch's Periodogram
            Spectrum = SPU.welchSpectrogram(data["Data"][:,i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=data["SamplingRate"])

        Spectrum["Missing"] = SPU.calculateMissingLabel(data["Missing"][:,i], window=1.0, overlap=0.5, fs=data["SamplingRate"])
        #Spectrum["Time"] += data["StartTime"] + (Configuration["Descriptor"][recordingId]["TimeShift"]/1000)# TODO Check later
        del Spectrum["logPower"]

        dropMissing = False
        if dropMissing:
            TimeSelection = Spectrum["Missing"] == 0
            Spectrum["Missing"] = Spectrum["Missing"][TimeSelection]
            Spectrum["Time"] = Spectrum["Time"][TimeSelection]
            Spectrum["Power"] = Spectrum["Power"][:, TimeSelection]
            Spectrum["logPower"] = Spectrum["logPower"][:, TimeSelection]
        
        if config["Normalization"] == "1/f PSD Trend Removal":
            meanPSDs = np.nanmedian(np.array(Spectrum["Power"]), axis=1)
            WindowRange = [1,data["SamplingRate"]/2 if data["SamplingRate"] < 200 else 100]

            FrequencyWindow = rangeSelection(Spectrum["Frequency"], WindowRange)
            fm = SpectralModel(peak_width_limits=[1,24])
            fm.fit(np.array(Spectrum["Frequency"])[FrequencyWindow], meanPSDs[FrequencyWindow], WindowRange)
            oof = fm.get_model("aperiodic", "linear")
            
            for j in range(Spectrum["Power"].shape[1]):
                Spectrum["Power"][FrequencyWindow,j] = np.array(Spectrum["Power"][FrequencyWindow,j]) / oof

            Spectrum["Power"] = Spectrum["Power"][FrequencyWindow,:]
            Spectrum["Frequency"] = np.array(Spectrum["Frequency"])[FrequencyWindow]
            
        elif config["Normalization"] == "Gamma Band Normalize":
            meanPSDs = np.nanmean(np.array(Spectrum["Power"]), axis=1)
            FrequencyWindow = rangeSelection(Spectrum["Frequency"], [70,90])
            MeanRefPower = np.nanmean(meanPSDs[FrequencyWindow])
            for j in range(Spectrum["Power"].shape[1]):
                Spectrum["Power"][:,j] = np.array(Spectrum["Power"][:,j]) / MeanRefPower
        
        Spectrum["Config"] = {**Spectrum["Config"], **config}
        data["Spectrum"].append(Spectrum)
    
    if recording:
        ProcessedData = models.Recording.create(recording, "TimeFrequencyAnalysis")
        ProcessedData.pointer = DATABASE_PATH + "recordings" + os.path.sep + recording.source.owner.uid + os.path.sep + ProcessedData.uid + ".bdat"
        ProcessedData.hashed = Database.saveSourceFile(data, ProcessedData.pointer)
        ProcessedData.metadata = config
        ProcessedData.save()

    return data

def processBurstAnalysis(participant_uid, recording_uid, config, centerFreq=22):
    recording = models.Recording.find(uid=recording_uid)
    AnalysisStruct = {"Signal": [], "Annotations": []}

    if not recording.source.owner.pk == participant_uid:
        raise Exception("Permission Denied. Accessing Denied Recordings")

    if recording.type in ["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages", "MedtronicBrainSenseTimeDomain", "MedtronicIndefiniteStream"]:
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        Data = processTimeDomainStreaming(recording, Data, config)
        Data = handleBurstActivityPreprocessing(recording, Data, config)
        
        for i in range(len(Data["BurstEnvelop"])):
            WaveletIndex = np.argmin(np.abs(Data["BurstEnvelop"][i]["Frequency"] - centerFreq))
            Data["BurstEnvelop"][i]["Wavelet"] = Data["BurstEnvelop"][i]["Wavelet"][WaveletIndex,:]
        
        Data["MissingIndex"] = []
        for i in range(Data["Missing"].shape[1]):
            Data["MissingIndex"].append(np.where(Data["Missing"][:,i])[0])
        del Data["Missing"]
        del Data["Data"]
        del Data["Spectrum"]
        
        DBSDevice = models.DBSDevice.find(uid=recording.source.metadata["Device"]).get_info()
        for i in range(len(Data["ChannelNames"])):
            Data["ChannelNames"][i] = DBSDevice["GenericName"] + ": " + BrainSenseStream.reformatChannelName(Data["ChannelNames"][i], DBSDevice["Electrodes"])

        TimeShift = recording.adjusted_alignment
        AnalysisStruct["Signal"].append({
            "Type": "Signal",
            "RecordingId": recording.uid,
            "SignalSeries": Data,
            "Alignment": TimeShift
        })
        
    elif recording.type in ["CustomizedStreamingData"]:
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        Data = processTimeDomainStreaming(recording, Data, config)
        Data = handleBurstActivityPreprocessing(recording, Data, config)
        
        for i in range(len(Data["BurstEnvelop"])):
            WaveletIndex = np.argmin(np.abs(Data["BurstEnvelop"][i]["Frequency"] - centerFreq))
            Data["BurstEnvelop"][i]["Wavelet"] = Data["BurstEnvelop"][i]["Wavelet"][WaveletIndex,:]
        
        Data["MissingIndex"] = []
        for i in range(Data["Missing"].shape[1]):
            Data["MissingIndex"].append(np.where(Data["Missing"][:,i])[0])
        del Data["Missing"]
        del Data["Data"]
        del Data["Spectrum"]
        
        TimeShift = recording.adjusted_alignment
        AnalysisStruct["Signal"].append({
            "Type": "Signal",
            "RecordingId": recording.uid,
            "SignalSeries": Data,
            "Alignment": TimeShift
        })

    return AnalysisStruct

def handleBurstActivityPreprocessing(recording, data, config, centerFreq=22):
    ProcessedData = models.Recording.find(original=recording, type="BurstActivityPreprocessing", metadata=config)
    if ProcessedData:
        return Database.loadSourceFile(ProcessedData.pointer, ProcessedData.hashed)
    
    data["BurstEnvelop"] = []
    if len(data["ChannelNames"]) == 1:
        data["Data"] = data["Data"].reshape(-1,1)
        data["Missing"] = data["Missing"].reshape(-1,1)

    for i in range(len(data["ChannelNames"])):
        coefs, freqs = pywt.cwt(data["Data"][:,i], np.geomspace(1, data["SamplingRate"], num=100), "morl", sampling_period=1/data["SamplingRate"])

        averaging = int(data["SamplingRate"] * 0.2)
        for j in range(coefs.shape[0]):
            coefs[j,:] = np.abs(signal.hilbert(coefs[j,:]))
            coefs[j,:] = SPU.smooth(coefs[j,:], averaging)

        BurstEnvelop = {
            "Wavelet": coefs,
            "Frequency": freqs, 
            "Method": "Morlet",
        }

        dropMissing = False
        if dropMissing:
            TimeSelection = data["Missing"][:,i] == 0
            BurstEnvelop["Wavelet"] = BurstEnvelop["Wavelet"][:, TimeSelection]
        
        BurstEnvelop["Config"] = config
        data["BurstEnvelop"].append(BurstEnvelop)
    
    ProcessedData = models.Recording.create(recording, "BurstActivityPreprocessing")
    ProcessedData.pointer = DATABASE_PATH + "recordings" + os.path.sep + recording.source.owner.uid + os.path.sep + ProcessedData.uid + ".bdat"
    ProcessedData.hashed = Database.saveSourceFile(data, ProcessedData.pointer)
    ProcessedData.metadata = config
    ProcessedData.save()
    return data

def calculateBurstParameters(envelop, fs):
    threshold = np.percentile(envelop, 75)
    above_threshold = np.int16(envelop > threshold)
    onset = np.where(np.diff(above_threshold) == 1)[0]  # Find where the signal goes above the threshold
    offset = np.where(np.diff(above_threshold) == -1)[0]
    if onset[0] > offset[0]:
        onset = np.insert(onset, 0, 0)
    if len(offset) > 0 and offset[-1] < onset[-1]:  
        offset = np.append(offset, len(envelop) - 1)
    
    burst_durations = np.array(offset - onset) / fs
    burst_amplitudes = np.array([np.max(envelop[onset[i]:offset[i]]) for i in range(len(onset))])
    burst_amplitudes = burst_amplitudes[burst_durations > 0.1]
    burst_durations = burst_durations[burst_durations > 0.1]

    return {
        "Threshold": threshold,
        "Duration": burst_durations,
        "Amplitude": burst_amplitudes,
    }

def handlePowerSpectralEstimation(recording, data, config):
    Spectrum = handleTimeFrequencyAnalysis(data, config, recording=recording)

    data["PSD"] = []
    for i in range(len(Spectrum["Spectrum"])):
        PowerSpectralEstimation = {}
        PowerSpectralEstimation["Frequency"] = Spectrum["Spectrum"][i]["Frequency"]
        PowerSpectralEstimation["Power"] = np.mean(Spectrum["Spectrum"][i]["Power"],axis=1)
        PowerSpectralEstimation["stdPower"] = np.std(Spectrum["Spectrum"][i]["Power"],axis=1)
        PowerSpectralEstimation["nObservation"] = Spectrum["Spectrum"][i]["Power"].shape[1]
        PowerSpectralEstimation["Config"] = {**Spectrum["Spectrum"][i]["Config"], **config}
        data["PSD"].append(PowerSpectralEstimation)
    
    return data

def selectRecordingChannel(analysis, channel_names=[]):
    AllChannels = []
    ActiveChannels = []

    FilteredAnalysis = {"Signal": [], "Spectrum": [],  "Annotations": analysis["Annotations"]}
    for key in analysis.keys():
        if not key in FilteredAnalysis.keys():
            FilteredAnalysis[key] = analysis[key]
            
    if "Signal" in analysis.keys():
        def SelectChannelSeries(a):
            if "Data" in a.keys():
                a["Data"] = a["Data"][i,:]
            if "Spectrum" in a.keys():
                a["Spectrum"] = a["Spectrum"][i]
            if "BurstEnvelop" in a.keys():
                a["BurstEnvelop"] = a["BurstEnvelop"][i]
            return a
                    
        for trial in range(len(analysis["Signal"])):
            if len(ActiveChannels) == 0:
                if len(channel_names) == 0:
                    if len(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"]) > 6:
                        ActiveChannels.append(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][0])
                        ActiveChannels.append(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][1])
                        ActiveChannels.append(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][2])
                        ActiveChannels.append(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][2])
                        ActiveChannels.append(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][3])
                        ActiveChannels.append(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][4])
                        ActiveChannels.append(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][5])
                    else:
                        ActiveChannels.extend(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"])
                else:
                    ActiveChannels = channel_names

            for i in range(len(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"])):
                if not analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][i] in AllChannels:
                    AllChannels.append(analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][i])

                if analysis["Signal"][trial]["SignalSeries"]["ChannelNames"][i] in ActiveChannels:
                    SelectedRecording = copy.deepcopy(analysis["Signal"][trial])
                    SelectedRecording["SignalSeries"]["ChannelNames"] = SelectedRecording["SignalSeries"]["ChannelNames"][i]
                    SelectedRecording["SignalSeries"] = SelectChannelSeries(SelectedRecording["SignalSeries"])
                    if "Epochs" in SelectedRecording["SignalSeries"].keys():
                        for j in range(len(SelectedRecording["SignalSeries"]["Epochs"])):
                            SelectedRecording["SignalSeries"]["Epochs"][j] = SelectChannelSeries(SelectedRecording["SignalSeries"]["Epochs"][j])
                    FilteredAnalysis["Signal"].append(SelectedRecording)

    if "Spectrum" in analysis.keys():
        for trial in range(len(analysis["Spectrum"])):
            if "PSDSeries" in analysis["Spectrum"][trial].keys():
                for i in range(len(analysis["Spectrum"][trial]["PSDSeries"]["ChannelNames"])):
                    if not analysis["Spectrum"][trial]["PSDSeries"]["ChannelNames"][i] in AllChannels:
                        AllChannels.append(analysis["Spectrum"][trial]["PSDSeries"]["ChannelNames"][i])
                        ActiveChannels.append(analysis["Spectrum"][trial]["PSDSeries"]["ChannelNames"][i])

            elif "Spectrum" in analysis["Spectrum"][trial].keys():
                if not analysis["Spectrum"][trial]["Spectrum"]["Channel"] in AllChannels:
                    AllChannels.append(analysis["Spectrum"][trial]["Spectrum"]["Channel"])
                    ActiveChannels.append(analysis["Spectrum"][trial]["Spectrum"]["Channel"])

            elif "Channel" in analysis["Spectrum"][trial].keys():
                if not analysis["Spectrum"][trial]["Channel"] in AllChannels:
                    AllChannels.append(analysis["Spectrum"][trial]["Channel"])
                    ActiveChannels.append(analysis["Spectrum"][trial]["Channel"])

            FilteredAnalysis["Spectrum"].append(analysis["Spectrum"][trial])

    FilteredAnalysis["AllChannels"] = AllChannels
    FilteredAnalysis["ActiveChannel"] = ActiveChannels
    return FilteredAnalysis

def queryNeuralActivitySnapshot(participant_uid, config):
    NeuralActivitySnapshot = {"AnalysisType": "NeuralActivitySnapshot", "Recordings": []}

    Participant = models.Participant.find(uid=participant_uid)
    SourceFiles = models.SourceFile.find_all(owner=Participant)
    Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages", "MedtronicElectrodeIdentifier"])

    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    DBSDeviceDictionary = {}
    for i in range(len(DBSDevices)):
        DBSDeviceDictionary[DBSDevices[i].uid] = DBSDevices[i].get_info()

    for recording in Recordings:
        Description = recording.get_info()
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        Data = processNeuralActivitySnapshot(recording, Data, config)
        
        if recording.source.metadata["Device"] in DBSDeviceDictionary.keys():
            DBSDevice = DBSDeviceDictionary[recording.source.metadata["Device"]]
        else:
            raise Exception("Neural Activity Snapshot Query found a recording whose DeviceId does not belongs to the Participant")

        MedtronicPSDs = []
        if "MedtronicPSD" in Data["Descriptor"].keys():
            for channel in Data["ChannelNames"]:
                found = False
                #for psd in Data["Descriptor"]["MedtronicPSD"]:
                #    if psd and psd["Hemisphere"].split(".")[1]:
                #        if channel.startswith(psd["SensingElectrodes"].split(".")[1]):
                #            MedtronicPSDs.append(psd)
                #            found = True
                #            break

                if not found:
                    MedtronicPSDs.append(None)

        for i in range(len(Data["ChannelNames"])):
            ElectrodeIdentifier = BrainSenseStream.reformatChannelName(Data["ChannelNames"][i], DBSDevice["Electrodes"])
            if ElectrodeIdentifier.startswith("Left"):
                Description["Date"] += 1

            Data["ChannelNames"][i] = DBSDevice["Heritage"] + ": " + ElectrodeIdentifier
            Data["ChannelNames"][i] = Data["ChannelNames"][i].replace(".1","A").replace(".2","B").replace(".3","C")
        
        NeuralActivitySnapshot["Recordings"].append({**Description, **{
            "Type": recording.type,
            "MedtronicPSDs": MedtronicPSDs if "MedtronicPSD" in Data["Descriptor"].keys() else None,
            "RecordingId": recording.uid,
            "Channels": Data["ChannelNames"],
            "PSDs": Data["PSD"],
        }})
    
    Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["CustomizedStreamingData"], metadata__DataType="Scheduled Streams").order_by("date")
    for i in range(len(Recordings)):
        recording = Recordings[i]
        Description = recording.get_info()
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        Data = processNeuralActivitySnapshot(recording, Data, config)

        NeuralActivitySnapshot["Recordings"].append({**Description, **{
            "Type": recording.type,
            "RecordingId": recording.uid,
            "Channels": Data["ChannelNames"],
            "PSDs": Data["PSD"],
        }})

    return NeuralActivitySnapshot

def processNeuralActivitySnapshot(recording, data, config):
    ProcessedData = models.Recording.find(original=recording, type="NeuralActivitySnapshot", metadata=config)
    if ProcessedData:
        return Database.loadSourceFile(ProcessedData.pointer, ProcessedData.hashed)
    
    if len(data["Data"].shape) == 1:
        data["Data"] = data["Data"].reshape(-1,1)

    if config["TimeSeriesRecording"]["StandardFilter"]["value"] == "Butterworth 1-100Hz":
        sos = signal.butter(5, np.array([1,100])*2/data["SamplingRate"], 'bp', output='sos')
        data["Data"] = signal.sosfiltfilt(sos, data["Data"], axis=0)

    if config["TimeSeriesRecording"]["NotchFilter"]["value"] == "Notch 55-65Hz":
        sos = signal.butter(5, np.array([55,65])*2/data["SamplingRate"], 'bandstop', output='sos')
        data["Data"] = signal.sosfiltfilt(sos, data["Data"], axis=0)
    elif config["TimeSeriesRecording"]["NotchFilter"]["value"] == "Notch 45-55Hz":
        sos = signal.butter(5, np.array([45,55])*2/data["SamplingRate"], 'bandstop', output='sos')
        data["Data"] = signal.sosfiltfilt(sos, data["Data"], axis=0)

    for i in range(len(data["ChannelNames"])):
        if config["TimeSeriesRecording"]["WienerFilter"]["value"] == "Use Wiener Filter":
            data["Data"][:,i] -= signal.wiener(data["Data"][:,i], mysize=int(data["SamplingRate"] / 2))

    data = handlePowerSpectralEstimation(recording, data, {
        "StandardFilter": config["TimeSeriesRecording"]["StandardFilter"]["value"],
        "NotchFilter": config["TimeSeriesRecording"]["NotchFilter"]["value"],
        "WienerFilter": config["TimeSeriesRecording"]["WienerFilter"]["value"],
        "CardiacFilter": config["TimeSeriesRecording"]["CardiacFilter"]["value"],
        "SpectrogramMethod": config["TimeSeriesRecording"]["SpectrogramMethod"]["value"],
        "BaselineCorrection": config["TimeSeriesRecording"]["BaselineCorrection"]["value"],
        "Normalization": config["TimeSeriesRecording"]["Normalization"]["value"]
    })

    ProcessedData = models.Recording.create(recording, "NeuralActivitySnapshot")
    ProcessedData.pointer = DATABASE_PATH + "recordings" + os.path.sep + recording.source.owner.uid + os.path.sep + ProcessedData.uid + ".bdat"
    ProcessedData.hashed = Database.saveSourceFile(data, ProcessedData.pointer)
    ProcessedData.metadata = config
    ProcessedData.save()

    return data

def queryChronicTimeline(participant_uid, config):
    Participant = models.Participant.find(uid=participant_uid)
    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    SourceFiles = models.SourceFile.find_all(owner=Participant)

    ChronicTimeline = []
    TimelineAnnotation = []

    Annotations = Event.queryDBSEvents(participant_uid, "PatientControllerEvent", source_files=SourceFiles, data=True)
    Annotations = uniqueListOfDicts(Annotations, ["Name", "Type", "Date"])
    TimelineAnnotation.extend(Annotations)

    Annotations = Event.queryAnnotations(participant_uid, "ChronicCustomEvent")
    Annotations = uniqueListOfDicts(Annotations, ["Name", "Type", "Date"])
    TimelineAnnotation.extend(Annotations)
    
    if models.Recording.include(source__in=SourceFiles, type__in=["CustomizedTimelineData"]):
        Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["CustomizedTimelineData"])
        for recording in Recordings:
            RecordingInfo = recording.get_info()
            Data = Database.loadSourceFile(recording.pointer, recording.hashed)
            Activity = {
                "AnalysisType": "CustomizedTimelineData",
                "Time": Data["Time"],
                "Duration": Data["Duration"],
                "ChannelNames": Data["ChannelNames"],
                "ChannelUnits": ["" for name in Data["ChannelNames"]],
                "Data": Data["Data"],
            }
            ChronicTimeline.append(Activity)

    if models.Recording.include(source__in=SourceFiles, type__in=["MedtronicChronicBrainSense"]):
        Recording = models.Recording.find(type="MedtronicChronicNeuralActivity", source__owner=Participant)
        if not Recording:
            Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicChronicBrainSense"])
            Activity = ChronicBrainSense.extractChronicNeuralActivity(Participant, DBSDevices, Recordings, config)
            Activity = uniqueListOfDicts(Activity, ["Device", "TherapyStartTime", "ChannelNames", "Time"])
            source = models.SourceFile(name="ChronicNeuralActivitySource", type="ChronicNeuralActivitySource", owner=Participant)
            source.save()
            Recording = models.Recording(name="ChronicNeuralActivity", type="MedtronicChronicNeuralActivity", source=source)
            Recording.pointer = DATABASE_PATH + "recordings" + os.path.sep + Recording.source.owner.uid + os.path.sep + Recording.uid + ".bdat"
            Recording.hashed = Database.saveSourceFile(Activity, Recording.pointer)
            Recording.save()
        
        if Recording:
            ChronicNeuralActivity = Database.loadSourceFile(Recording.pointer, Recording.hashed)

            # Rename Channels
            for i in range(len(ChronicNeuralActivity)):
                ChronicNeuralActivity[i]["AnalysisType"] = "MedtronicChronicBrainSense"
                ChronicNeuralActivity[i]["Device"] = DBSDevices.filter(uid=ChronicNeuralActivity[i]["Device"]).first().get_info()
                for j in range(len(ChronicNeuralActivity[i]["ChannelNames"])):
                    for k in range(len(ChronicNeuralActivity[i]["Device"]["Electrodes"])):
                        if ChronicNeuralActivity[i]["ChannelNames"][j].startswith(ChronicNeuralActivity[i]["Device"]["Electrodes"][k]["Target"].split(" ")[0]):
                            ChronicNeuralActivity[i]["ChannelNames"][j] = ChronicNeuralActivity[i]["Device"]["Electrodes"][k]["CustomName"] + " " + ChronicNeuralActivity[i]["ChannelNames"][j].split(" ")[-1]
                            break
            
                Activity = {
                    "AnalysisType": "CustomizedTimelineData",
                    "Time": ChronicNeuralActivity[i]["Time"],
                    "Duration": np.diff(ChronicNeuralActivity[i]["Time"]),
                    "ChannelNames": ChronicNeuralActivity[i]["ChannelNames"],
                    "ChannelUnits": ["" for name in ChronicNeuralActivity[i]["ChannelNames"]],
                    "Data": ChronicNeuralActivity[i]["Data"],
                }

                ChronicTimeline.append(Activity)
    
    if models.Recording.include(source__in=SourceFiles, type__in=["AppleWatchData"]):
        Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["AppleWatchData"])
        for recording in Recordings:
            RecordingInfo = recording.get_info()
            Data = Database.loadSourceFile(recording.pointer, recording.hashed)
            for i in range(len(Data)):
                if Data[i]["ChannelNames"][0].startswith("accel"):
                    continue

                Activity = {
                    "AnalysisType": "CustomizedTimelineData",
                    "Time": Data[i]["Time"] + Data[i]["StartTime"],
                    "Duration": Data[i]["Duration"],
                    "ChannelNames": Data[i]["ChannelNames"],
                    "ChannelUnits": ["" for name in Data[i]["ChannelNames"]],
                    "Data": Data[i]["Data"].T,
                }
                ChronicTimeline.append(Activity)

    if models.SourceFile.include(owner=Participant, type="FitbitWebAPISource"):
        Data = FitbitDataManager.loadFitbitData(Participant)
        for key in Data.keys():
            SingleTimePoint = False
            for i in range(len(Data[key])):
                if len(Data[key][i]["Data"]) > 0:
                    if Data[key][i]["Data"].shape[0] == 1:
                        SingleTimePoint = True
                    else:
                        SingleTimePoint = False
                        break

            if SingleTimePoint:
                Activity = {
                    "AnalysisType": "CustomizedTimelineData",
                    "Time": [],
                    "Duration": [],
                    "ChannelNames": [],
                    "ChannelUnits": [],
                    "Data": [],
                }
                
                for i in range(len(Data[key])):
                    if len(Data[key][i]["Data"]) > 0:
                        Activity["ChannelNames"] = ["[Fitbit] " + key + " " + name for name in Data[key][i]["ChannelNames"]]
                        Activity["ChannelUnits"] = ["" for name in Data[key][i]["ChannelNames"]]
                        break

                for i in range(len(Data[key])):
                    if len(Data[key][i]["Data"]) > 0:
                        Activity["Time"].append(Data[key][i]["StartTime"])
                        Activity["Duration"].append(3600*24)

                Activity["Data"] = np.zeros((len(Activity["ChannelNames"]), len(Activity["Time"])))
                Count = 0
                for i in range(len(Data[key])):
                    if len(Data[key][i]["Data"]) > 0:
                        for j in range(len(Data[key][i]["ChannelNames"])):
                            try:
                                chanIndex = Activity["ChannelNames"].index("[Fitbit] " + key + " " + Data[key][i]["ChannelNames"][j])
                                Activity["Data"][chanIndex, Count] = Data[key][i]["Data"][0][j]
                            except Exception as e:
                                pass
                        Count += 1

                ChronicTimeline.append(Activity)

            else:
                for i in range(len(Data[key])):
                    if len(Data[key][i]["Data"]) > 0:
                        Activity = {
                            "AnalysisType": "CustomizedTimelineData",
                            "Time": Data[key][i]["Time"],
                            "Duration": np.diff(Data[key][i]["Time"]),
                            "ChannelNames": ["[Fitbit] " + key + " " + name for name in Data[key][i]["ChannelNames"]],
                            "ChannelUnits": ["" for name in Data[key][i]["ChannelNames"]],
                            "Data": np.array(Data[key][i]["Data"]).T.tolist(),
                        }

                        if not type(Data[key][i]["Duration"]) == int and not type(Data[key][i]["Duration"]) == float and not type(Data[key][i]["Duration"]) == np.float64:
                            Activity["Duration"] = Data[key][i]["Duration"]

                        for j in range(len(Activity["ChannelNames"])):
                            if Activity["ChannelNames"][j] in ["[Fitbit] sleep SleepStage"]:
                                Activity["ChannelUnits"][j] = "Category"
                                Activity["Data"][j] = []
                                for k in range(len(Data[key][i]["Data"])):
                                    for subkey in Data[key][i]["Metadata"]["SleepStages"].keys():
                                        if Data[key][i]["Metadata"]["SleepStages"][subkey] == Data[key][i]["Data"][k,j]:
                                            Activity["Data"][j].append(subkey)

                        ChronicTimeline.append(Activity)

    if models.Recording.include(source__owner=Participant, type="EmpaticaData"):
        Data = EmpaticaDataManager.loadEmpaticaDataOverview(Participant)
        AllChannels = []
        for i in range(len(Data)):
            for name in Data[i]["ChannelNames"]:
                if not name in AllChannels:
                    AllChannels.append(name)
        
        for i in range(len(AllChannels)):
            Activity = {
                "AnalysisType": "CustomizedTimelineData",
                "DataId": [Data[j]["Id"] for j in range(len(Data)) if AllChannels[i] in Data[j]["ChannelNames"]],
                "ChannelNames": ["[Empatica] " + AllChannels[i]],
                "ChannelUnits": [""]
            }
            ChronicTimeline.append(Activity)

    if models.SourceFile.include(owner=Participant, type="OuraRingAPISource"):
        Data = OuraDataManager.loadOuraRingData(Participant)
        for key in Data.keys():
            SingleTimePoint = False
            for i in range(len(Data[key])):
                if len(Data[key][i]["Data"]) == 0:
                    SingleTimePoint = True
                    break

            if SingleTimePoint:
                Activity = {
                    "AnalysisType": "CustomizedTimelineData",
                    "Time": [],
                    "Duration": [],
                    "ChannelNames": [],
                    "ChannelUnits": [],
                    "Data": [],
                }

                for i in range(len(Data[key])):
                    for descriptor in Data[key][i]["Descriptor"].keys():
                        if type(Data[key][i]["Descriptor"][descriptor]) == float or type(Data[key][i]["Descriptor"][descriptor]) == int:
                            if descriptor not in Activity["ChannelNames"]:
                                Activity["ChannelNames"].append(descriptor)
                                Activity["ChannelUnits"].append("")
                
                for i in range(len(Data[key])):
                    Activity["Time"].append(Data[key][i]["StartTime"])
                    Activity["Duration"].append(3600*24)

                    ChanData = []
                    for chan in Activity["ChannelNames"]:
                        ChanData.append(Data[key][i]["Descriptor"][chan])
                    Activity["Data"].append(ChanData)
                
                for i in range(len(Activity["ChannelNames"])):
                    Activity["ChannelNames"][i] = "[OURA] " + key + " " + Activity["ChannelNames"][i]
                
                Activity["Data"] = np.array(Activity["Data"]).T.tolist()
                ChronicTimeline.append(Activity)

            else:
                DescriptorActivity = {
                    "AnalysisType": "CustomizedTimelineData",
                    "Time": [],
                    "Duration": [],
                    "ChannelNames": [],
                    "ChannelUnits": [],
                    "Data": [],
                }

                for i in range(len(Data[key])):
                    for descriptor in Data[key][i]["Descriptor"].keys():
                        if type(Data[key][i]["Descriptor"][descriptor]) == float or type(Data[key][i]["Descriptor"][descriptor]) == int:
                            if descriptor not in DescriptorActivity["ChannelNames"]:
                                DescriptorActivity["ChannelNames"].append(descriptor)
                                DescriptorActivity["ChannelUnits"].append("")

                    if len(Data[key][i]["Data"]) > 0:
                        if not "Time" in Data[key][i].keys():
                            Data[key][i]["Time"] = [Data[key][i]["StartTime"] + j/Data[key][i]["SamplingRate"] for j in range(len(Data[key][i]["Data"]))]

                        Activity = {
                            "AnalysisType": "CustomizedTimelineData",
                            "Time": Data[key][i]["Time"],
                            "Duration": np.diff(Data[key][i]["Time"]),
                            "ChannelNames": ["[OURA] " + key + " " + name for name in Data[key][i]["ChannelNames"]],
                            "ChannelUnits": ["" for name in Data[key][i]["ChannelNames"]],
                            "Data": np.array(Data[key][i]["Data"]).T.tolist(),
                        }

                        for j in range(len(Activity["ChannelNames"])):
                            if Activity["ChannelNames"][j] in ["[OURA] Sleep Sleep Phase"]:
                                SleepStages = {
                                    "deep": 1,
                                    "light": 2,
                                    "rem": 3, 
                                    "awake": 4
                                }
                                Activity["ChannelUnits"][j] = "Category"
                                Activity["Data"][j] = []
                                for k in range(len(Data[key][i]["Data"])):
                                    for subkey in SleepStages.keys():
                                        if SleepStages[subkey] == int(Data[key][i]["Data"][k,j]):
                                            Activity["Data"][j].append(subkey)
                                
                        ChronicTimeline.append(Activity)

                for i in range(len(Data[key])):
                    DescriptorActivity["Time"].append(Data[key][i]["StartTime"])
                    DescriptorActivity["Duration"].append(3600*24)

                    ChanData = []
                    for chan in DescriptorActivity["ChannelNames"]:
                        ChanData.append(Data[key][i]["Descriptor"][chan])
                    DescriptorActivity["Data"].append(ChanData)

                for i in range(len(DescriptorActivity["ChannelNames"])):
                    DescriptorActivity["ChannelNames"][i] = "[OURA] " + key + " " + DescriptorActivity["ChannelNames"][i]

                DescriptorActivity["Data"] = np.array(DescriptorActivity["Data"]).T.tolist()
                ChronicTimeline.append(DescriptorActivity)

    if models.Recording.include(source__in=SourceFiles, type__in=["CustomizedStreamingData"], metadata__DataType="Scheduled Streams"):
        Recording = models.Recording.find(type="ProcessedCustomizedStreamingData", source__owner=Participant)
        if not Recording:
            Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["CustomizedStreamingData"], metadata__DataType="Scheduled Streams").order_by("date")
            Activity = {
                "AnalysisType": "ChronicSpectrum",
                "Time": [],
                "ChannelNames": [],
                "Frequency": [],
                "Data": [],
                "CLim": []
            }

            for i in range(len(Recordings)):
                recording = Recordings[i]
                RecordingInfo = recording.get_info()
                Data = Database.loadSourceFile(recording.pointer, recording.hashed)
                Data = processNeuralActivitySnapshot(recording, Data, config)

                for j in range(len(Data["ChannelNames"])):
                    if not Data["ChannelNames"][j] in Activity["ChannelNames"]:
                        Activity["ChannelNames"].append(Data["ChannelNames"][j])
                        Activity["Data"].append(np.zeros((len(Recordings), len(Data["PSD"][0]["Frequency"]))))
                        Activity["Frequency"].append(Data["PSD"][0]["Frequency"])
                        Activity["Time"].append(np.zeros(len(Recordings)))

                    for k in range(len(Activity["ChannelNames"])):
                        if Activity["ChannelNames"][k] == Data["ChannelNames"][j]:
                            Activity["Time"][k][i] = Data["StartTime"]
                            Activity["Data"][k][i,:] = Data["PSD"][j]["Power"]
                    
            for k in range(len(Activity["ChannelNames"])):
                SelectedData = Activity["Time"][k] != 0
                Activity["Data"][k] = 10*np.log10(Activity["Data"][k][SelectedData,:].T)
                Activity["Time"][k] = Activity["Time"][k][SelectedData]
                Activity["CLim"].append([np.percentile(Activity["Data"][k], 15), np.percentile(Activity["Data"][k], 95)*1.1])
            
            Activity["ChannelNames"] = [name + " Chronic Spectrum" for name in Activity["ChannelNames"]]
            source = models.SourceFile.find(name="ChronicNeuralActivitySource", type="ChronicNeuralActivitySource", owner=Participant)
            if not source:
                source = models.SourceFile(name="ChronicNeuralActivitySource", type="ChronicNeuralActivitySource", owner=Participant)
                source.save()

            recording = models.Recording(name="ChronicNeuralActivity", type="ProcessedCustomizedStreamingData", source=source)
            recording.pointer = DATABASE_PATH + "recordings" + os.path.sep + recording.source.owner.uid + os.path.sep + recording.uid + ".bdat"
            recording.hashed = Database.saveSourceFile(Activity, recording.pointer)
            recording.save()
        else:
            Activity = Database.loadSourceFile(Recording.pointer, Recording.hashed)

        ChronicTimeline.append(Activity)

    AllLinks = models.ParticipantLinkRel.find_all(participant=Participant)
    for link in AllLinks:
        form = link.record
        
        Activity = {
            "AnalysisType": "CustomizedSurveyData",
            "Time": [],
            "ChannelNames": [],
            "ChannelUnits": [],
            "Data": [],
        }

        if form.record_type == "Redcap Linked Survey":
            AllRecords = RedcapForm.queryRedcapFormRecords(Participant, form, recordId=link.link_code)
            for pageId in range(len(form.record["FieldMapping"])):
                for questionId in range(len(form.record["FieldMapping"][pageId]["questions"])):
                    if form.record["FieldMapping"][pageId]["questions"][questionId]["text"] == "Time":
                        for record in AllRecords:
                            Activity["Time"].append(datetime.datetime.fromisoformat(record["Result"][pageId][questionId]).timestamp())
                    else:
                        Activity["ChannelNames"].append("[REDCap] " + form.name + " - " + form.record["FieldMapping"][pageId]["questions"][questionId]["text"])
                        Activity["ChannelUnits"].append("")
                        Responses = []
                        for record in AllRecords:
                            Responses.append(record["Result"][pageId][questionId])
                        Activity["Data"].append(Responses)
        else:
            AllRecords = models.ScaleRecord.find_all(source=form, participant=Participant)
            AllRecords = [i.get_info() for i in AllRecords]
            AllRecords.sort(key=lambda x: x["Date"])
        
        ChronicTimeline.append(Activity)
        
    return ChronicTimeline, TimelineAnnotation

def queryChronicTimelineData(participant_uid, data_ids, channel, config):
    Participant = models.Participant.find(uid=participant_uid)
    SourceFiles = models.SourceFile.find_all(owner=Participant)

    Result = []
    if models.Recording.include(uid__in=data_ids, source__owner=Participant, type="EmpaticaData"):
        Recordings = models.Recording.find_all(uid__in=data_ids, source__owner=Participant, type="EmpaticaData")
        for recording in Recordings:
            Data = Database.loadSourceFile(recording.pointer, recording.hashed)
            for i in range(len(Data)):
                if channel.replace("[Empatica] ","") in Data[i]["ChannelNames"]:
                    chanIndex = Data[i]["ChannelNames"].index(channel.replace("[Empatica] ",""))
                    Data[i]["Data"][np.isnan(Data[i]["Data"])] = -1
                    Result.append({
                        "Time": Data[i]["Time"] + Data[i]["StartTime"],
                        "Duration": np.diff(Data[i]["Time"]),
                        "Data": [np.array(Data[i]["Data"]).T[chanIndex].tolist()],
                    })
                    
    return Result

def queryChronicNeuralActivity(participant_uid, config):
    Participant = models.Participant.find(uid=participant_uid)
    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    SourceFiles = models.SourceFile.find_all(owner=Participant)

    ChronicNeuralActivity = {"AnalysisType": "", "ChronicNeuralActivity": [], "Annotations": []}

    Annotations = Event.queryDBSEvents(participant_uid, "PatientControllerEvent", source_files=SourceFiles, data=True)
    Annotations = uniqueListOfDicts(Annotations, ["Name", "Type", "Date"])
    ChronicNeuralActivity["Annotations"].extend(Annotations)

    Annotations = Event.queryAnnotations(participant_uid, "ChronicCustomEvent")
    Annotations = uniqueListOfDicts(Annotations, ["Name", "Type", "Date"])
    ChronicNeuralActivity["Annotations"].extend(Annotations)

    ChronicNeuralActivity["Annotations"]
    
    if models.Recording.include(source__in=SourceFiles, type__in=["MedtronicChronicBrainSense"]):
        ChronicNeuralActivity["AnalysisType"] = "MedtronicChronicBrainSense"
        Recording = models.Recording.find(type="MedtronicChronicNeuralActivity", source__owner=Participant)
        if not Recording:
            Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicChronicBrainSense"])
            Activity = ChronicBrainSense.extractChronicNeuralActivity(Participant, DBSDevices, Recordings, config)
            Activity = uniqueListOfDicts(Activity, ["Device", "TherapyStartTime", "ChannelNames", "Time"])
            ChronicNeuralActivity["ChronicNeuralActivity"] = Activity

            source = models.SourceFile(name="ChronicNeuralActivitySource", type="ChronicNeuralActivitySource", owner=Participant)
            source.save()
            recording = models.Recording(name="ChronicNeuralActivity", type="MedtronicChronicNeuralActivity", source=source)
            recording.pointer = DATABASE_PATH + "recordings" + os.path.sep + recording.source.owner.uid + os.path.sep + recording.uid + ".bdat"
            recording.hashed = Database.saveSourceFile(Activity, recording.pointer)
            recording.save()
        else:
            ChronicNeuralActivity["ChronicNeuralActivity"] = Database.loadSourceFile(Recording.pointer, Recording.hashed)

        # Rename Channels
        for i in range(len(ChronicNeuralActivity["ChronicNeuralActivity"])):
            ChronicNeuralActivity["ChronicNeuralActivity"][i]["AnalysisType"] = "MedtronicChronicBrainSense"
            ChronicNeuralActivity["ChronicNeuralActivity"][i]["Device"] = DBSDevices.filter(uid=ChronicNeuralActivity["ChronicNeuralActivity"][i]["Device"]).first().get_info()
            for j in range(len(ChronicNeuralActivity["ChronicNeuralActivity"][i]["ChannelNames"])):
                for k in range(len(ChronicNeuralActivity["ChronicNeuralActivity"][i]["Device"]["Electrodes"])):
                    if ChronicNeuralActivity["ChronicNeuralActivity"][i]["ChannelNames"][j].startswith(ChronicNeuralActivity["ChronicNeuralActivity"][i]["Device"]["Electrodes"][k]["Target"].split(" ")[0]):
                        ChronicNeuralActivity["ChronicNeuralActivity"][i]["ChannelNames"][j] = ChronicNeuralActivity["ChronicNeuralActivity"][i]["Device"]["Electrodes"][k]["CustomName"] + " " + ChronicNeuralActivity["ChronicNeuralActivity"][i]["ChannelNames"][j].split(" ")[-1]
                        break
        
        # Annotation Events
        for i in range(len(ChronicNeuralActivity["Annotations"])):
            if ChronicNeuralActivity["Annotations"][i]["Type"] == "PatientControllerEvent":
                ChronicNeuralActivity["Annotations"][i]["EventPSDs"] = []
                if len(ChronicNeuralActivity["Annotations"][i]["Recording"]) > 0:
                    for j in range(len(ChronicNeuralActivity["Annotations"][i]["Recording"])):
                        EventPSDs = BrainSenseEvent.extractBrainSenseEventRecording(ChronicNeuralActivity["Annotations"][i]["Recording"][j], DBSDevices)
                        for k in range(len(EventPSDs)):
                            if len(EventPSDs[k]["Frequency"]) != 100:
                                NewFrequency = np.arange(100)*250/256
                                EventPSDs[k]["Power"] = np.interp(NewFrequency, EventPSDs[k]["Frequency"], EventPSDs[k]["Power"])
                                EventPSDs[k]["Frequency"] = NewFrequency
                                
                        ChronicNeuralActivity["Annotations"][i]["EventPSDs"].extend(EventPSDs)
            
                for j in range(len(ChronicNeuralActivity["Annotations"][i]["EventPSDs"])):
                    ChronicNeuralActivity["Annotations"][i]["EventPSDs"][j]["TherapyString"] = "Unknown"
                    for k in range(len(ChronicNeuralActivity["ChronicNeuralActivity"])):
                        if ChronicNeuralActivity["ChronicNeuralActivity"][k]["ChannelNames"][0].startswith(ChronicNeuralActivity["Annotations"][i]["EventPSDs"][j]["ChannelName"]):
                            if ChronicNeuralActivity["ChronicNeuralActivity"][k]["Device"]["Id"] == ChronicNeuralActivity["Annotations"][i]["EventPSDs"][j]["Device"]:
                                if ChronicNeuralActivity["Annotations"][i]["Date"] >= ChronicNeuralActivity["ChronicNeuralActivity"][k]["Time"][0] and ChronicNeuralActivity["Annotations"][i]["Date"] <= ChronicNeuralActivity["ChronicNeuralActivity"][k]["Time"][-1]:
                                    ChronicNeuralActivity["Annotations"][i]["EventPSDs"][j]["TherapyString"] = ChronicNeuralActivity["ChronicNeuralActivity"][k]["TherapyString"]
                                    break
                
                del ChronicNeuralActivity["Annotations"][i]["Recording"]

    return ChronicNeuralActivity

def handleSurveybasedWongAIContactSelection(participant_uid, config):
    Participant = models.Participant.find(uid=participant_uid)

    if config["RequestType"] == "RequestQualifyRecordings":
        SourceFiles = models.SourceFile.find_all(owner=Participant)
        Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages"])

        DBSDevices = models.DBSDevice.find_all(owner=Participant)
        DBSDeviceDictionary = {}
        for i in range(len(DBSDevices)):
            DBSDeviceDictionary[DBSDevices[i].uid] = DBSDevices[i].get_info()

        RecordingList = []
        for recording in Recordings:
            Description = recording.get_info()
            
            # This only give us results without segments
            Found = False
            if "Type" in Description["Metadata"] and Description["Metadata"]["Type"] == "MedtronicBrainSenseSurvey":
                for i in range(len(Description["Metadata"]["ChannelNames"])):
                    if "SEGMENT" in Description["Metadata"]["ChannelNames"][i]:
                        Found = True 
                        break

            if not Found:
                DBSDevice = DBSDeviceDictionary[Description["Device"]]
                for i in range(len(Description["Metadata"]["ChannelNames"])):
                    ElectrodeIdentifier = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], DBSDevice["Electrodes"])
                    Description["Metadata"]["ChannelNames"][i] = DBSDevice["Heritage"] + ": " + ElectrodeIdentifier

                RecordingList.append(Description)
        
        return RecordingList

    elif config["RequestType"] == "RequestAIResult":
        SourceFiles = models.SourceFile.find_all(owner=Participant)
        recording = models.Recording.find(uid=config["RecordingId"], source__in=SourceFiles, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages"])

        if not recording:
            return None
        Description = recording.get_info()

        DBSDevices = models.DBSDevice.find_all(owner=Participant)
        DBSDeviceDictionary = {}
        for i in range(len(DBSDevices)):
            DBSDeviceDictionary[DBSDevices[i].uid] = DBSDevices[i].get_info()

        # Run your AI Model here
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": {
            "TimeSeriesRecording": {
                "StandardFilter": {
                    "value": "Butterworth 1-100Hz"
                },
                "CardiacFilter": {
                    "value": "No Filter"
                },
                "SpectrogramMethod": {
                    "value": "Welch's Periodogram"
                }
            }
        }})
        userConfig["APIAccess"] = True

        Data = processNeuralActivitySnapshot(recording, Data, userConfig)
        Data["Channels"] = []
        for i in range(len(Data["ChannelNames"])):
            DBSDevice = DBSDeviceDictionary[recording.source.metadata["Device"]]
            Data["Channels"].append(DBSDevice["Heritage"] + ": " + BrainSenseStream.reformatChannelName(Data["ChannelNames"][i], DBSDevice["Electrodes"]))
        Data["PSDs"] = Data["PSD"]
        Results = ContactPredictor_VerWong2026(Data)
        return Results

    return None

def handleSurveybasedAIContactSelection(participant_uid, config):
    Participant = models.Participant.find(uid=participant_uid)

    if config["RequestType"] == "RequestQualifyRecordings":
        SourceFiles = models.SourceFile.find_all(owner=Participant)
        Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages"])

        DBSDevices = models.DBSDevice.find_all(owner=Participant)
        DBSDeviceDictionary = {}
        for i in range(len(DBSDevices)):
            DBSDeviceDictionary[DBSDevices[i].uid] = DBSDevices[i].get_info()

        RecordingList = []
        for recording in Recordings:
            Description = recording.get_info()
            
            # This only give us results without segments
            Found = False
            if "Type" in Description["Metadata"] and Description["Metadata"]["Type"] == "MedtronicBrainSenseSurvey":
                for i in range(len(Description["Metadata"]["ChannelNames"])):
                    if "SEGMENT" in Description["Metadata"]["ChannelNames"][i]:
                        Found = True 
                        break

            if not Found:
                DBSDevice = DBSDeviceDictionary[Description["Device"]]
                for i in range(len(Description["Metadata"]["ChannelNames"])):
                    ElectrodeIdentifier = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], DBSDevice["Electrodes"])
                    Description["Metadata"]["ChannelNames"][i] = DBSDevice["Heritage"] + ": " + ElectrodeIdentifier

                RecordingList.append(Description)
        
        return RecordingList

    elif config["RequestType"] == "RequestAIResult":
        SourceFiles = models.SourceFile.find_all(owner=Participant)
        recording = models.Recording.find(uid=config["RecordingId"], source__in=SourceFiles, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages"])

        if not recording:
            return None
        Description = recording.get_info()

        DBSDevices = models.DBSDevice.find_all(owner=Participant)
        DBSDeviceDictionary = {}
        for i in range(len(DBSDevices)):
            DBSDeviceDictionary[DBSDevices[i].uid] = DBSDevices[i].get_info()

        # Run your AI Model here
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": {
            "TimeSeriesRecording": {
                "StandardFilter": {
                    "value": "Butterworth 1-100Hz"
                },
                "CardiacFilter": {
                    "value": "No Filter"
                },
                "SpectrogramMethod": {
                    "value": "Welch's Periodogram"
                }
            }
        }})
        userConfig["APIAccess"] = True

        Data = processNeuralActivitySnapshot(recording, Data, userConfig)
        Data["Channels"] = []
        for i in range(len(Data["ChannelNames"])):
            DBSDevice = DBSDeviceDictionary[recording.source.metadata["Device"]]
            Data["Channels"].append(DBSDevice["Heritage"] + ": " + BrainSenseStream.reformatChannelName(Data["ChannelNames"][i], DBSDevice["Electrodes"]))
        Data["PSDs"] = Data["PSD"]
        Results = ContactPredictor(Data)
        return Results

    return None

def handleSurveybasedContactSelection(participant_uid, config):
    Participant = models.Participant.find(uid=participant_uid)

    if config["RequestType"] == "RequestQualifyRecordings":
        SourceFiles = models.SourceFile.find_all(owner=Participant)
        Recordings = models.Recording.find_all(source__in=SourceFiles, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages"])

        DBSDevices = models.DBSDevice.find_all(owner=Participant)
        DBSDeviceDictionary = {}
        for i in range(len(DBSDevices)):
            DBSDeviceDictionary[DBSDevices[i].uid] = DBSDevices[i].get_info()

        RecordingList = []
        for recording in Recordings:
            Description = recording.get_info()
            
            # This only give us results without segments
            Found = False
            if Description["Metadata"]["Type"] == "MedtronicBrainSenseSurvey":
                for i in range(len(Description["Metadata"]["ChannelNames"])):
                    if "SEGMENT" in Description["Metadata"]["ChannelNames"][i]:
                        Found = True 
                        break

            if Found:
                DBSDevice = DBSDeviceDictionary[Description["Device"]]
                for i in range(len(Description["Metadata"]["ChannelNames"])):
                    ElectrodeIdentifier = BrainSenseStream.reformatChannelName(Description["Metadata"]["ChannelNames"][i], DBSDevice["Electrodes"])
                    Description["Metadata"]["ChannelNames"][i] = DBSDevice["Heritage"] + ": " + ElectrodeIdentifier

                RecordingList.append(Description)
        
        return RecordingList

    elif config["RequestType"] == "RequestAIResult":
        SourceFiles = models.SourceFile.find_all(owner=Participant)
        recording = models.Recording.find(uid=config["RecordingId"], source__in=SourceFiles, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages"])

        if not recording:
            return None
        Description = recording.get_info()

        DBSDevices = models.DBSDevice.find_all(owner=Participant)
        DBSDeviceDictionary = {}
        for i in range(len(DBSDevices)):
            DBSDeviceDictionary[DBSDevices[i].uid] = DBSDevices[i].get_info()

        # Run your AI Model here
        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
        userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": {
            "TimeSeriesRecording": {
                "StandardFilter": {
                    "value": "Butterworth 1-100Hz"
                },
                "CardiacFilter": {
                    "value": "No Filter"
                },
                "SpectrogramMethod": {
                    "value": "Welch's Periodogram"
                }
            }
        }})
        userConfig["APIAccess"] = True

        Data = processNeuralActivitySnapshot(recording, Data, userConfig)
        Data["Channels"] = []
        for i in range(len(Data["ChannelNames"])):
            DBSDevice = DBSDeviceDictionary[recording.source.metadata["Device"]]
            Data["Channels"].append(BrainSenseStream.reformatChannelName(Data["ChannelNames"][i], DBSDevice["Electrodes"]))
        Data["PSDs"] = Data["PSD"]
        
        def MovingAverageFilter(signal, window_size):
            window = np.ones(window_size) / window_size
            return np.convolve(signal, window, mode='same')

        BandPowers = {
            "Channels": Data["Channels"],
            "BandPowers": []
        }
        for i in range(len(Data["PSDs"])):
            Peaks = []
            Data["PSDs"][i]["Power"] = MovingAverageFilter(Data["PSDs"][i]["Power"], 5)
            for f in range(1, len(Data["PSDs"][i]["Power"])-1):
                if Data["PSDs"][i]["Power"][f] > Data["PSDs"][i]["Power"][f-1] and Data["PSDs"][i]["Power"][f] > Data["PSDs"][i]["Power"][f+1]:
                    Peaks.append({
                        "Frequency": Data["PSDs"][i]["Frequency"][f],
                        "Power": Data["PSDs"][i]["Power"][f]
                    })

            BandPowers["BandPowers"].append({})
            for band in [("Delta", 1, 4), ("Theta", 4, 8), ("Alpha", 8, 12), ("Beta", 12, 30), ("Gamma", 30, 100)]:
                bandPower = 0
                bandFrequency = 0
                for p in range(len(Peaks)):
                    if Peaks[p]["Frequency"] >= band[1] and Peaks[p]["Frequency"] < band[2]:
                        if Peaks[p]["Power"] > bandPower:
                            bandPower = Peaks[p]["Power"]
                            bandFrequency = Peaks[p]["Frequency"]

                BandPowers["BandPowers"][i][band[0]] = {
                    "Frequency": bandFrequency,
                    "Power": bandPower
                }

        return BandPowers

def handleAutomatedBetaDetection(participant_uid, config):
    Participant = models.Participant.find(uid=participant_uid)

    if config["RequestType"] == "RequestQualifyRecordings":
        RecordingList = ExtractSpectralFeaturesDuringStimulation.ExtractAvailableDates(Participant.get_info())
        return RecordingList
    
    elif config["RequestType"] == "RequestAIResult":
        RecordingList = ExtractSpectralFeaturesDuringStimulation.ExtractAvailableDates(Participant.get_info())
        userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": {
            "TimeSeriesRecording": {
                "StandardFilter": {
                    "value": "Butterworth 1-100Hz"
                },
                "CardiacFilter": {
                    "value": "No Filter"
                },
                "SpectrogramMethod": {
                    "value": "Welch's Periodogram"
                }
            }
        }})
        userConfig["APIAccess"] = True

        Results = []
        for collection in RecordingList:
            if collection["Date"] == config["RecordingType"] and collection["TherapyParameters"] == config["TherapyParameters"] and collection["Contact"].startswith(config["Contact"]):
                Results.append(ExtractSpectralFeaturesDuringStimulation.ProcessCollection(collection, userConfig))

        return Results

def extractMachineLearningModels(participant_uid, model_key=None, config={}):
    models = {
        "Survey-based Contact Selection (Lavu et. al., 2025)": handleSurveybasedAIContactSelection,
        "Peak Beta Power in Survey": handleSurveybasedContactSelection,
        "Survey-based Contact Selection (Wong et. al., 2026)": handleSurveybasedWongAIContactSelection,
        "Automated Beta Detection (BRAVO)": handleAutomatedBetaDetection,
    }

    if model_key and model_key in models.keys():
        return models[model_key](participant_uid, config=config)

    return models.keys()

def extractMedtronicPowerBands(participant_uid, recording_type, recording_uids=None):
    Participant = models.Participant.find(uid=participant_uid)
    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    SourceFiles = models.SourceFile.find_all(owner=Participant)

    if recording_type == "MedicationCycle":
        Recordings = []
        PowerBands_Threshold = {}
        
        if not recording_uids:
            AllRecordings = models.Recording.find_all(type="MedtronicBrainSensePowerDomain", source__owner=Participant, 
                                                name__in=["MEDOFF_DBSOFF_UPDRS", "MEDOFF_THRESHOLD", "MEDOFF_DBSON_UPDRS",
                                                        "MEDON_DBSOFF_UPDRS", "MEDON_THRESHOLD", "MEDON_DBSON_UPDRS"])
            for recording in AllRecordings:
                RecordingInfo = recording.get_info()
                DBSDevice = models.DBSDevice.find(uid=recording.source.metadata["Device"]).get_info()
                Recordings.append(RecordingInfo)

        else:
            AllRecordings = models.Recording.find_all(uid__in=recording_uids, type="MedtronicBrainSensePowerDomain", source__owner=Participant, 
                                                name__in=["MEDOFF_DBSOFF_UPDRS", "MEDOFF_THRESHOLD", "MEDOFF_DBSON_UPDRS",
                                                        "MEDON_DBSOFF_UPDRS", "MEDON_THRESHOLD", "MEDON_DBSON_UPDRS"])

            for recording in AllRecordings:
                RecordingInfo = recording.get_info()
                DBSDevice = models.DBSDevice.find(uid=recording.source.metadata["Device"]).get_info()
                Data = Database.loadSourceFile(recording.pointer, recording.hashed)
                TherapySeries, TherapyGraph = BrainSenseStream.processTherapyInformation(Data, DBSDevice)
                TherapySeries = BrainSenseStream.extractPowerBands(Data, TherapySeries)
                for i in range(len(TherapySeries)):
                    TherapyString = BrainSenseStream.extractTherapyString(TherapySeries[i]["TherapyOverview"])
                    if not TherapyString in PowerBands_Threshold.keys():
                        PowerBands_Threshold[TherapyString] = {"MEDOFF": {}, "MEDON": {}}

                    if recording.name.startswith("MEDOFF"):
                        for key in TherapySeries[i].keys():
                            if key == "TherapyOverview" or key == "Time":
                                continue
                            
                            if len(TherapySeries[i][key]) == 0:
                                continue

                            if not key in PowerBands_Threshold[TherapyString]["MEDOFF"].keys():
                                PowerBands_Threshold[TherapyString]["MEDOFF"][key] = []
                            PowerBands_Threshold[TherapyString]["MEDOFF"][key].extend(TherapySeries[i][key])

                    elif recording.name.startswith("MEDON"):
                        for key in TherapySeries[i].keys():
                            if key == "TherapyOverview" or key == "Time":
                                continue
                            
                            if len(TherapySeries[i][key]) == 0:
                                continue

                            if not key in PowerBands_Threshold[TherapyString]["MEDON"].keys():
                                PowerBands_Threshold[TherapyString]["MEDON"][key] = []
                            PowerBands_Threshold[TherapyString]["MEDON"][key].extend(TherapySeries[i][key])

                Recordings.append(RecordingInfo)
        
        return {"Recordings": Recordings, "PowerBands": PowerBands_Threshold}