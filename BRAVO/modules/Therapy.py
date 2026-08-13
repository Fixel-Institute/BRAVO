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
Therapy Query Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os
from datetime import datetime
import copy
import numpy as np
import pandas as pd
import json
import uuid
from cryptography.fernet import Fernet

from Server import models

from openai import OpenAI
import json

if "GEMINI_API_KEY" in os.environ.keys():
    openai_client = OpenAI(
        api_key=os.environ.get("GEMINI_API_KEY"),
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
    )
else:
    openai_client = None

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')
key = os.environ.get('DATASERVER_ENCRYPTION')
secureEncoder = Fernet(key)

def queryTherapyHistory(Participant):
    """ Extract all therapy change logs in Percept related to a specific participant.

    This pipeline go through all therapy change logs and extract the time at which a group changes is made. 
    The pipeline will also extract the actual setting that the device is on before and after changes.

    Args:
    
    Returns:
      List of therapy group history ordered by time. 
    """

    TherapyModifications = []
    TherapyHistories = []
    TherapyDevices = []

    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    DBSDeviceDict = {}
    for i in range(len(DBSDevices)):
        if not DBSDevices[i].serial_number in DBSDeviceDict.keys():
            DBSDeviceDict[DBSDevices[i].serial_number] = []
        DBSDeviceDict[DBSDevices[i].serial_number].append(DBSDevices[i])

    for key in DBSDeviceDict.keys():
        LeadCount = 0
        for i in range(len(DBSDeviceDict[key])):
            DeviceInfoTemp = DBSDeviceDict[key][i].get_info()
            if len(DeviceInfoTemp["Electrodes"]) > LeadCount:
                LeadCount = len(DeviceInfoTemp["Electrodes"])
                DeviceInfo = {**DeviceInfoTemp}
        
        TherapyDevices.append(DeviceInfo)

        TherapyHistory = {
            "Device": DeviceInfo,
            "History": []
        }
        DeviceTherapyModification = {
            "Device": DeviceInfo,
            "History": []
        }

        for i in range(len(DBSDeviceDict[key])):
            device = DBSDeviceDict[key][i]
            SourceFiles = models.SourceFile.find_all(owner=Participant, metadata__Device=device.uid)
            TherapyHistory["History"].extend([i.get_info() for i in models.ElectricalTherapy.find_all(therapy__source__in=SourceFiles)])
            DeviceTherapyModification["History"].extend([i.get_info() for i in models.TherapyModification.find_all(source__in=SourceFiles)])

        DeviceTherapyModification["History"].sort(key=lambda x: x["Date"])
        TherapyHistory["History"] = [i for i in TherapyHistory["History"] if (i["Type"] in ["Pre-visit Therapy", "Post-visit Therapy", "Past Therapy"])]
        TherapyHistory["History"].sort(key=lambda x: x["Date"])
        TherapyHistories.append(TherapyHistory)
        
        LastTherapyChange = None
        VisitTimestamps = np.unique([i["Date"] for i in TherapyHistory["History"]])
        for i in range(len(VisitTimestamps)):
            LastTherapyChange = None
            Inserted = False
            for j in range(0, len(DeviceTherapyModification["History"])):
                if DeviceTherapyModification["History"][j]["Type"] == "TherapyChangeGroup":
                    if DeviceTherapyModification["History"][j]["Date"] > VisitTimestamps[i] and LastTherapyChange:
                        DeviceTherapyModification["History"].insert(j, {
                            "Id": uuid.uuid4().hex,
                            "Name": "",
                            "Type": "TherapyChangeGroup",
                            "Date": VisitTimestamps[i],
                            "Previous": LastTherapyChange,
                            "New": LastTherapyChange,
                        })
                        Inserted = True
                        break
                    LastTherapyChange = DeviceTherapyModification["History"][j]["New"]
            
            if not Inserted and LastTherapyChange:
                DeviceTherapyModification["History"].append({
                    "Id": uuid.uuid4().hex,
                    "Name": "",
                    "Type": "TherapyChangeGroup",
                    "Date": VisitTimestamps[i],
                    "Previous": LastTherapyChange,
                    "New": LastTherapyChange,
                })

        if LastTherapyChange:
            DeviceTherapyModification["History"].append({
                "Id": uuid.uuid4().hex,
                "Name": "",
                "Type": "TherapyChangeGroup",
                "Date": VisitTimestamps[-1],
                "Previous": LastTherapyChange,
                "New": LastTherapyChange,
            })
        
        TherapyModifications.append(DeviceTherapyModification)
    
    TherapyTimeline = createTherapyTimeline({
        "TherapyDevices": TherapyDevices,
        "TherapyModification": TherapyModifications, 
        "TherapyConfiguration": TherapyHistories
    })

    TherapyTimeline.sort(key=lambda x: x["Date"])
    for n in range(len(TherapyModifications)):
        TherapyModifications[n]["History"].sort(key=lambda x: x["Date"])
        for j in range(len(TherapyModifications[n]["History"])):
            if TherapyModifications[n]["History"][j]["Type"] == "TherapyChangeGroup":
                TherapyModifications[n]["History"][j]["Therapy"] = None
                for k in range(len(TherapyTimeline)):
                    if TherapyTimeline[k]["Date"] > TherapyModifications[n]["History"][j]["Date"] and not TherapyModifications[n]["History"][j]["Therapy"]:
                        for i in range(len(TherapyTimeline[k]["DefinedTherapies"])):
                            if TherapyTimeline[k]["DefinedTherapies"][i]["Device"]["Id"] == TherapyModifications[n]["Device"]["Id"]:
                                if TherapyTimeline[k]["DefinedTherapies"][i]["GroupId"] == TherapyModifications[n]["History"][j]["New"]:
                                    for therapyList in TherapyTimeline[k]["Therapies"]:
                                        if therapyList["GroupId"] == TherapyModifications[n]["History"][j]["New"]:
                                            for l in range(len(therapyList["Processed"])):
                                                if np.all(therapyList["Processed"][l]["TherapyIds"] == TherapyTimeline[k]["DefinedTherapies"][i]["Pre"]):
                                                    TherapyModifications[n]["History"][j]["Therapy"] = therapyList["Processed"][l]
                                                    break

    return {"TherapyModification": TherapyModifications, "TherapyDevices": TherapyDevices, "TherapyConfiguration": TherapyHistories, "TherapyTimeline": TherapyTimeline}

def queryTherapyHistoryMetadata(Participant):
    TherapyVisitDates = models.Therapy.find_all(source__owner=Participant, type__in=["Pre-visit Therapy", "Post-visit Therapy", "Past Therapy"]).values_list("date", "source__metadata__Device").distinct()
    TherapyVisitDates = [{"Date": i[0], "Device": i[1]} for i in TherapyVisitDates]
    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    DBSDevices = [i.get_info() for i in DBSDevices]
    return {"TherapyVisitDates": TherapyVisitDates, "DBSDevices": DBSDevices}

def queryTherapyModification(Participant):
    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    TherapyModifications = []
    for device in DBSDevices:
        SourceFiles = models.SourceFile.find_all(owner=Participant, metadata__Device=device.uid)
        TherapyModification = [{**i.get_info(), **{"Device": device.uid}} for i in models.TherapyModification.find_all(source__in=SourceFiles)]
        TherapyModifications.extend(TherapyModification)
    return TherapyModifications

def queryTherapyGroups(Participant):
    DBSDevices = models.DBSDevice.find_all(owner=Participant)
    TherapyGroups = []
    for device in DBSDevices:
        SourceFiles = models.SourceFile.find_all(owner=Participant, metadata__Device=device.uid)
        if len(SourceFiles) > 0:
            TherapyGroup = [{**i.get_info(), **{"Device": device.uid}} for i in models.ElectricalTherapy.find_all(therapy__source__in=SourceFiles)]
            TherapySources = np.unique([group["SourceId"] for group in TherapyGroup])
            TherapyGroupDates = np.unique([group["Date"] for group in TherapyGroup])
            TherapyGroupIds = np.unique([group["GroupId"] for group in TherapyGroup])
            TherapyTypes = ["Pre-visit Therapy", "Post-visit Therapy", "Past Therapy"]
            for SourceId in TherapySources:
                for GroupDate in TherapyGroupDates:
                    for GroupId in TherapyGroupIds:
                        for GroupType in TherapyTypes:
                            TherapyGroupSubset = sorted([group for group in TherapyGroup if group["GroupId"] == GroupId and group["Date"] == GroupDate and group["Type"] == GroupType and group["SourceId"] == SourceId], key=lambda x: x["Date"])
                            if len(TherapyGroupSubset) > 0:
                                if len(TherapyGroupSubset) > 1:
                                    for i in range(1, len(TherapyGroupSubset)):
                                        TherapyGroupSubset[0]["StimulationSettings"].extend(TherapyGroupSubset[i]["StimulationSettings"])
                                        TherapyGroupSubset[0]["AdaptiveSettings"].extend(TherapyGroupSubset[i]["AdaptiveSettings"])
                                TherapyGroups.append(TherapyGroupSubset[0])
    return TherapyGroups

def createAgenticAIOverview(PreGroup, PostGroup):
    with open(os.path.join(os.path.dirname(__file__), "AgenticAI", "TherapyGroupComparison.md"), "r") as f:
        SYSTEM_PROMPT = f.read()

    AI_input_token = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": f""" Pre-Visit Therapy:
                {json.dumps(PreGroup, indent=2)}

                Post-Visit Therapy:
                {json.dumps(PostGroup, indent=2)}
            """
        }
    ]

    cache = models.LLMCache.get_LLMCache(
        name="",
        type="TherapyGroupComparison",
        message=AI_input_token,
        metadata={
            "model": "gemini-3.5-flash"
        }
    )

    if not cache and openai_client:
        print("Regenerating Therapy Comparison Summary with Gemini API")
        response = openai_client.chat.completions.create(
            model="gemini-3.5-flash",
            messages=AI_input_token,
            temperature=0.1
        )
        try:
            summary = response.choices[0].message.content
            models.LLMCache.add_LLMCache(
                name="",
                type="TherapyGroupComparison",
                message=AI_input_token,
                response=summary,
                metadata={
                    "model": "gemini-3.5-flash"
                }
            )
        except Exception as e:
            print(f"Error occurred while processing the response: {e}")
            summary = "Error occurred while processing the response."
        return summary
    
    else:
        return cache.response if cache else "Error: No cache found and Gemini API is not available."

def createTherapyTimeline(TherapyHistory):
    AllSessionDates = []
    AllTherapyGroups = []
    for i in range(len(TherapyHistory["TherapyConfiguration"])):
        TherapyHistory["TherapyConfiguration"][i]["History"].sort(key=lambda x: x["Date"])
        AllSessionDates.extend([history["Date"] for history in TherapyHistory["TherapyConfiguration"][i]["History"]])
        AllTherapyGroups.extend([history["GroupId"] for history in TherapyHistory["TherapyConfiguration"][i]["History"]])

    AllSessionDates.extend([device["Date"] for device in TherapyHistory["TherapyDevices"]])

    AllSessionDates = np.unique(AllSessionDates)
    AllSessionDates.sort()
    AllTherapyGroups = np.unique(AllTherapyGroups)
    AllTherapyGroups.sort()

    SessionDates = [AllSessionDates[0]]
    for i in range(1, len(AllSessionDates)):
        if AllSessionDates[i] - SessionDates[-1] > 3600*12:
            SessionDates.append(AllSessionDates[i])

    if not SessionDates[-1] == AllSessionDates[-1]:
        SessionDates.append(AllSessionDates[-1])
    
    TherapyTimeline = []
    for n in range(len(SessionDates)):
        TimelineEntry = {"Date": SessionDates[n], "Therapies": []}

        KnownTherapyEntries = []
        for i in range(len(TherapyHistory["TherapyConfiguration"])):
            for history in TherapyHistory["TherapyConfiguration"][i]["History"]:
                if history["Date"] >= SessionDates[n] and history["Date"] < SessionDates[n] + 3600*12:
                    KnownTherapyEntries.append({**history, **{"Device": TherapyHistory["TherapyConfiguration"][i]["Device"]}})
        
        for id in AllTherapyGroups:
            GroupEntries = [history for history in KnownTherapyEntries if history["GroupId"] == id]
            GroupEntries.sort(key=lambda x: (x["Date"], x["Type"]))
            TimelineEntry["Therapies"].append({
                "GroupId": id,
                "GroupEntries": GroupEntries,
                "Processed": []
            })
        TherapyTimeline.append(TimelineEntry)
    
    for n in range(len(TherapyTimeline)):
        for device in TherapyHistory["TherapyDevices"]:
            for g in range(len(TherapyTimeline[n]["Therapies"])):
                GroupId = TherapyTimeline[n]["Therapies"][g]["GroupId"]
                AllTherapies = [TherapyTimeline[n]["Therapies"][g]["GroupEntries"][i] for i in range(len(TherapyTimeline[n]["Therapies"][g]["GroupEntries"])) if TherapyTimeline[n]["Therapies"][g]["GroupEntries"][i]["Device"]["Id"] == device["Id"]]

                for therapyType in ["Past Therapy", "Pre-visit Therapy", "Post-visit Therapy"]:
                    AvailableTherapies = [AllTherapies[i] for i in range(len(AllTherapies)) if AllTherapies[i]["Type"] == therapyType]
                    if len(AvailableTherapies) == 0:
                        continue
                    
                    UniqueDates = np.unique([AvailableTherapies[i]["Date"] for i in range(len(AvailableTherapies))])
                    for date in UniqueDates:
                        UniqueSources = np.unique([AvailableTherapies[i]["SourceId"] for i in range(len(AvailableTherapies)) if AvailableTherapies[i]["Date"] == date])
                        for source in UniqueSources:
                            UniqueSettings = [AvailableTherapies[i] for i in range(len(AvailableTherapies)) if AvailableTherapies[i]["Date"] == date and AvailableTherapies[i]["SourceId"] == source]
                            DefinedTherapy = {
                                "Device": device,
                                "Name": "",  "Type": therapyType,
                                "Date": date, "Timezone": "", "SourceId": source,
                                "GroupId": GroupId, "GroupName": "", "GroupType": "",
                                "TherapyLabel": "",
                                "Electrodes": [], "Stimulation": [], "Adaptive": [],
                                "TherapyIds": []
                            }

                            for electrode in device["Electrodes"]:
                                DefinedTherapy["Electrodes"].append(electrode)

                                KnownSettings = []
                                for therapy in UniqueSettings:
                                    for j in range(len(therapy["StimulationSettings"])):
                                        if therapy["StimulationSettings"][j]["Electrode"]["Hemisphere"] == electrode["Hemisphere"]:
                                            KnownSettings.append({**{"TherapyId": therapy["Id"], "Label": therapy["Label"], "Date": therapy["Date"]},**therapy["StimulationSettings"][j]})
                                DefinedTherapy["Stimulation"].append(KnownSettings)
                                DefinedTherapy["TherapyIds"].extend([therapy["TherapyId"] for therapy in KnownSettings])
                                for j in range(len(KnownSettings)):
                                    if KnownSettings[j]["Label"] != "":
                                        DefinedTherapy["TherapyLabel"] = KnownSettings[j]["Label"]

                                KnownSettings = []
                                for therapy in UniqueSettings:
                                    for j in range(len(therapy["StimulationSettings"])):
                                        if therapy["StimulationSettings"][j]["Electrode"]["Hemisphere"] == electrode["Hemisphere"]:
                                            DefinedTherapy["GroupType"] = therapy["GroupType"]
                                            KnownSettings.append({**{"TherapyId": therapy["Id"], "Label": therapy["Label"], "Date": therapy["Date"]},**therapy["AdaptiveSettings"][j]})
                                DefinedTherapy["Adaptive"].append(KnownSettings)
                                DefinedTherapy["TherapyIds"].extend([therapy["TherapyId"] for therapy in KnownSettings])

                            DefinedTherapy["TherapyIds"] = list(np.unique(DefinedTherapy["TherapyIds"]))
                            TherapyTimeline[n]["Therapies"][g]["Processed"].append(DefinedTherapy)
                        
    for n in range(len(TherapyTimeline)):
        TherapyTimeline[n]["DefinedTherapies"] = []
        for device in TherapyHistory["TherapyDevices"]:
            for g in range(len(TherapyTimeline[n]["Therapies"])):
                ProcessedTherapyList = [TherapyTimeline[n]["Therapies"][g]["Processed"][i] for i in range(len(TherapyTimeline[n]["Therapies"][g]["Processed"])) if TherapyTimeline[n]["Therapies"][g]["Processed"][i]["Device"]["Id"] == device["Id"]]
                ProcessedTherapyList.sort(key=lambda x: x["Date"])

                DefinedTherapy = {
                    "Device": device,
                    "Name": "",  "Type": "Defined Therapy",
                    "Date": TherapyTimeline[n]["Date"], "Timezone": "",
                    "GroupId": TherapyTimeline[n]["Therapies"][g]["GroupId"], "GroupName": "", "GroupType": "",
                    "Pre": [], "Post": [],
                }
                
                if len(ProcessedTherapyList) == 0:
                    #TherapyTimeline[n]["DefinedTherapies"].append(DefinedTherapy)
                    continue

                for i in range(len(ProcessedTherapyList)):
                    if ProcessedTherapyList[i]["TherapyLabel"] == "Pre-visit Preferred":
                        DefinedTherapy["Pre"] = ProcessedTherapyList[i]["TherapyIds"]

                if len(DefinedTherapy["Pre"]) == 0:
                    PreTherapy = [therapy for therapy in ProcessedTherapyList if therapy["Type"] in ["Pre-visit Therapy"]]
                    if len(PreTherapy) > 0:
                        DefinedTherapy["Pre"] = PreTherapy[0]["TherapyIds"]
                    else:
                        PreTherapy = [therapy for therapy in ProcessedTherapyList if therapy["Type"] in ["Pre-visit Therapy", "Past Therapy"]]
                        DefinedTherapy["Pre"] = PreTherapy[0]["TherapyIds"] if len(PreTherapy) > 0 else []

                for i in range(len(ProcessedTherapyList)):
                    if ProcessedTherapyList[i]["TherapyLabel"] == "Post-visit Preferred":
                        DefinedTherapy["Post"] = ProcessedTherapyList[i]["TherapyIds"]

                if len(DefinedTherapy["Post"]) == 0:
                    PostTherapy = [therapy for therapy in ProcessedTherapyList if therapy["Type"] in ["Post-visit Therapy"]]
                    DefinedTherapy["Post"] = PostTherapy[-1]["TherapyIds"] if len(PostTherapy) > 0 else []
                    
                TherapyTimeline[n]["DefinedTherapies"].append(DefinedTherapy)
    
    for device in TherapyHistory["TherapyDevices"]:
        SessionTimestamps = []
        for i in range(len(TherapyTimeline)):
            for j in range(len(TherapyTimeline[i]["DefinedTherapies"])):
                if TherapyTimeline[i]["DefinedTherapies"][j]["Device"]["Id"] == device["Id"]:
                    SessionTimestamps.append(TherapyTimeline[i]["Date"])
                    break
        SessionTimestamps.sort()

        for i in range(len(TherapyHistory["TherapyModification"])):
            if TherapyHistory["TherapyModification"][i]["Device"]["Id"] == device["Id"]:
                TherapyModification = [history for history in TherapyHistory["TherapyModification"][i]["History"] if history["Type"] == "TherapyChangeGroup"]
                TherapyModification.sort(key=lambda x: x["Date"])

                if len(TherapyModification) == 0:
                    continue

                for n in range(len(TherapyModification)-1):
                    if not (TherapyModification[n]["New"] == TherapyModification[n+1]["Previous"]):
                        TherapyModification[n]["EndDate"] = None
                    else:
                        TherapyModification[n]["EndDate"] = TherapyModification[n+1]["Date"]
                TherapyModification[-1]["EndDate"] = None

                for k in range(1, len(SessionTimestamps)):
                    DutyCycleCalculation = {}
                    for n in range(len(TherapyModification)-1):
                        if not TherapyModification[n]["New"] in DutyCycleCalculation.keys():
                            DutyCycleCalculation[TherapyModification[n]["New"]] = 0

                        if TherapyModification[n+1]["Date"] > SessionTimestamps[k-1] and TherapyModification[n]["Date"] < SessionTimestamps[k]:
                            if TherapyModification[n]["Date"] < SessionTimestamps[k-1]:
                                DutyCycleCalculation[TherapyModification[n]["New"]] += TherapyModification[n+1]["Date"] - SessionTimestamps[k-1]
                            else:
                                DutyCycleCalculation[TherapyModification[n]["New"]] += TherapyModification[n+1]["Date"] - TherapyModification[n]["Date"]

                            if TherapyModification[n+1]["Date"] > SessionTimestamps[k]:
                                DutyCycleCalculation[TherapyModification[n]["New"]] -= TherapyModification[n+1]["Date"] - SessionTimestamps[k]

                    TotalTime = np.sum([value for key, value in DutyCycleCalculation.items()])
                    if TotalTime == 0:
                        TotalTime = 1 # Prevent Division by Zero

                    for key in DutyCycleCalculation.keys():
                        if TotalTime > 0:
                            DutyCycleCalculation[key] = DutyCycleCalculation[key] / TotalTime
                        else:
                            DutyCycleCalculation[key] = 0

                        for j in range(len(TherapyTimeline)):
                            if TherapyTimeline[j]["Date"] == SessionTimestamps[k]:
                                for m in range(len(TherapyTimeline[j]["DefinedTherapies"])):
                                    if TherapyTimeline[j]["DefinedTherapies"][m]["Device"]["Id"] == device["Id"]:
                                        if TherapyTimeline[j]["DefinedTherapies"][m]["GroupId"] == key:
                                            TherapyTimeline[j]["DefinedTherapies"][m]["PercentUsage"] = DutyCycleCalculation[key]
                            
    if TherapyTimeline[-1]["Date"] - TherapyTimeline[-2]["Date"] < 3600*12:
        TherapyTimeline[-1] = copy.deepcopy(TherapyTimeline[-2])

    return TherapyTimeline

def findSameSourceTherapy(source_uid, hemisphere, group, TherapyHistories):
    for history in TherapyHistories:
        for j in range(len(history["StimulationSettings"])):
            if history["SourceId"] == source_uid and history["GroupId"].startswith(group) and history["StimulationSettings"][j]["Electrode"]["Target"].startswith(hemisphere) and history["Type"] == "Pre-visit Therapy":
                return {
                    "Type": "Pre-visit Therapy",
                    "TherapyId": history["Id"],
                    "Date": history["Date"],
                    "Stimulation": history["StimulationSettings"][j],
                    "Adaptive": history["AdaptiveSettings"][j]
                }
    
    return None

def findClosestTherapy(timestamp, hemisphere, group, TherapyHistories):
    TherapyHistories.sort(key=lambda x: x["Date"])
    ClosestTherapy = {"Pre": None, "Post": None}
    for i in range(len(TherapyHistories)):
        for j in range(len(TherapyHistories[i]["StimulationSettings"])):
            if TherapyHistories[i]["StimulationSettings"][j]["Electrode"]["Target"].startswith(hemisphere):
                if TherapyHistories[i]["GroupId"].startswith(group):
                    if TherapyHistories[i]["Date"] >= timestamp:
                        if TherapyHistories[i]["Type"] == "Pre-visit Therapy":
                            if not ClosestTherapy["Post"]:
                                ClosestTherapy["Post"] = {
                                    "Type": "Pre-visit Therapy",
                                    "TherapyId": TherapyHistories[i]["Id"],
                                    "Date": TherapyHistories[i]["Date"],
                                    "Stimulation": TherapyHistories[i]["StimulationSettings"][j],
                                    "Adaptive": TherapyHistories[i]["AdaptiveSettings"][j]
                                }
                            elif TherapyHistories[i]["Date"] - ClosestTherapy["Post"]["Date"] < 3600*24 and ClosestTherapy["Post"]["Type"] == "Past Therapy":
                                ClosestTherapy["Post"] = {
                                    "Type": "Pre-visit Therapy",
                                    "TherapyId": TherapyHistories[i]["Id"],
                                    "Date": TherapyHistories[i]["Date"],
                                    "Stimulation": TherapyHistories[i]["StimulationSettings"][j],
                                    "Adaptive": TherapyHistories[i]["AdaptiveSettings"][j]
                                }
                                
                        elif TherapyHistories[i]["Type"] == "Past Therapy" and not ClosestTherapy["Post"]:
                            ClosestTherapy["Post"] = {
                                "Type": "Past Therapy",
                                "TherapyId": TherapyHistories[i]["Id"],
                                "Date": TherapyHistories[i]["Date"],
                                "Stimulation": TherapyHistories[i]["StimulationSettings"][j],
                                "Adaptive": TherapyHistories[i]["AdaptiveSettings"][j]
                            }

                    if TherapyHistories[i]["Date"] < timestamp:
                        if TherapyHistories[i]["Type"] == "Post-visit Therapy":
                            ClosestTherapy["Pre"] = {
                                "Type": "Post-visit Therapy",
                                "TherapyId": TherapyHistories[i]["Id"],
                                "Date": TherapyHistories[i]["Date"],
                                "Stimulation": TherapyHistories[i]["StimulationSettings"][j],
                                "Adaptive": TherapyHistories[i]["AdaptiveSettings"][j]
                            }
                        elif TherapyHistories[i]["Type"] == "Past Therapy" and ClosestTherapy["Pre"]:
                            if TherapyHistories[i]["Date"] > ClosestTherapy["Pre"]["Date"] + 3600*12:
                                ClosestTherapy["Pre"] = None
                                
    return ClosestTherapy

def queryElectrodeImpedances(participant):
    SourceFiles = models.SourceFile.find_all(owner=participant)
    ImpedanceRecordss = models.DBSEvent.find_all(type__endswith="Impedance", source__in=SourceFiles)
    ElectrodeImpedances = []
    for impedance in ImpedanceRecordss:
        Descriptor = impedance.get_info(data=True)
        ElectrodeImpedances.append(Descriptor)
    
    ElectrodeImpedances = sorted(ElectrodeImpedances, key=lambda x: x["Date"])
    
    DBSDevices = [device.get_info() for device in models.DBSDevice.find_all(owner=participant)]
    for impedance in ElectrodeImpedances:
        for device in DBSDevices:
            if len(impedance["Recording"]) > 0 and impedance["Recording"][0]["Device"] == device["Id"]:
                impedance["DeviceHeritage"] = device["Name"]

    return ElectrodeImpedances
    
def findClosestAdaptiveTherapy(timestamp, ClosestTherapy):
    # This is a new function based on SourceFile JSON ID
    if ClosestTherapy["Post"]:
        return ClosestTherapy["Post"]

    if not ClosestTherapy["Post"] and not ClosestTherapy["Pre"]:
        return None
    elif not ClosestTherapy["Post"]:
        return ClosestTherapy["Pre"] if ClosestTherapy["Pre"]["Adaptive"] else None
    elif not ClosestTherapy["Pre"]:
        return ClosestTherapy["Post"] if ClosestTherapy["Post"]["Adaptive"] else None
    else:
        if ClosestTherapy["Post"]["Date"] - timestamp < timestamp - ClosestTherapy["Pre"]["Date"]:
            if "SensingSetup" in ClosestTherapy["Post"]["Adaptive"]["RecordingConfiguration"]["Config"]:
                return ClosestTherapy["Post"]
            elif "SensingSetup" in ClosestTherapy["Pre"]["Adaptive"]["RecordingConfiguration"]["Config"]:
                return ClosestTherapy["Pre"]
            
        else:
            if "SensingSetup" in ClosestTherapy["Pre"]["Adaptive"]["RecordingConfiguration"]["Config"]:
                return ClosestTherapy["Pre"]
            elif "SensingSetup" in ClosestTherapy["Post"]["Adaptive"]["RecordingConfiguration"]["Config"]:
                return ClosestTherapy["Post"]
    return None

def checkDuplicate(device, electrode, therapy):
    AllTherapies = models.Therapy.find_all(source__metadata__Device=device.uid, type=therapy["type"], date=therapy["date"])
    if len(AllTherapies) == 0:
        return False
    
    AllElectricalTherapy = models.ElectricalTherapy.find_all(group_type=therapy["group_type"], group_id=therapy["group_id"], stimulation_type=therapy["stimulation_type"], therapy__in=AllTherapies)
    if len(AllElectricalTherapy) == 0:
        return False

    for electrical_therapy in AllElectricalTherapy:
        AllTrue = True
        for i in range(len(therapy["stimulation_settings"])):
            setting = therapy["stimulation_settings"][i]
            if not electrical_therapy.stimulation_settings.filter(electrode=electrode, **{key: setting[key] for key in setting.keys() if key in ["contact", "return_contact", "amplitude", "amplitude_fraction", "amplitude_unit", "pulsewidth", "pulsewidth_unit", "frequency", "cycling", "cycling_period"]}).exists():
                AllTrue = False
        
        if AllTrue:
            return True
        
    return False
                