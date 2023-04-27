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
Therapy History Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(os.environ.get("PYTHON_UTILITY"))

from datetime import datetime
import copy
import numpy as np
import pandas as pd

from Backend import models
from modules import Database
from decoder import Percept

key = os.environ.get('ENCRYPTION_KEY')

def saveTherapySettings(deviceID, therapyList, sessionDate, type, sourceFile):
    """ Save Indefinite Streaming Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      therapyList: Array of Therapy Configuration structures extracted from Medtronic JSON file.
      sessionDate: DateTime object indicating when the therapy configuration is saved.
      type: One of three data types: ["Past Therapy","Pre-visit Therapy","Post-visit Therapy"].
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """

    NewTherapyFound = False
    TheraySavingList = list()
    for therapy in therapyList:
        TherapyObject = models.TherapyHistory.objects.filter(device_deidentified_id=deviceID, therapy_date=sessionDate, therapy_type=type, group_id=therapy["GroupId"]).all()
        TherapyFound = False

        for pastTherapy in TherapyObject:
            if pastTherapy.extractTherapy() == therapy:
                TherapyFound = True
                break
        if not TherapyFound:
            TheraySavingList.append(models.TherapyHistory(device_deidentified_id=deviceID, therapy_date=sessionDate, source_file=sourceFile,
                                  group_name=therapy["GroupName"], group_id=therapy["GroupId"], active_group=therapy["ActiveGroup"],
                                  therapy_type=type, therapy_details=therapy))
            NewTherapyFound = True

    if len(TheraySavingList) > 0:
        models.TherapyHistory.objects.bulk_create(TheraySavingList,ignore_conflicts=True)

    return NewTherapyFound

def queryImpedanceHistory(user, patientUniqueID, authority):
    ImpedanceHistory = list()
    if not authority["Permission"]:
        return ImpedanceHistory

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        DeviceName = device.device_name
        if DeviceName == "":
            DeviceName = device.getDeviceSerialNumber(key)
        ImpedanceLogs = models.ImpedanceHistory.objects.filter(device_deidentified_id=device.deidentified_id).order_by("session_date").all()
        ImpedanceHistory.extend([{"session_date": log.session_date.timestamp(), "log": log.impedance_record, "device": DeviceName} for log in ImpedanceLogs])
    return ImpedanceHistory

def queryTherapyHistory(user, patientUniqueID, authority):
    """ Extract all therapy change logs.

    This pipeline go through all therapy change logs and extract the time at which a group changes is made. 
    The pipeline will also extract the actual setting that the device is on before and after changes.

    Args:
      user: BRAVO Platform User object. 
      patientUniqueID: Deidentified patient ID as referenced in SQL Database. 
      authority: User permission structure indicating the type of access the user has.

    Returns:
      List of therapy group history ordered by time. 
    """

    TherapyHistoryContext = list()
    if not authority["Permission"]:
        return TherapyHistoryContext
    
    ImpedanceHistory = queryImpedanceHistory(user, patientUniqueID, authority)

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        TherapyChangeData = dict()
        TherapyChangeData["device"] = device.deidentified_id
        DeviceName = device.device_name
        if DeviceName == "":
            DeviceName = device.getDeviceSerialNumber(key)
        TherapyChangeData["device_name"] = DeviceName
        TherapyChangeHistory = models.TherapyChangeLog.objects.filter(device_deidentified_id=device.deidentified_id).order_by("date_of_change").all()
        if len(TherapyChangeHistory) > 0:
            TherapyChangeHistory = pd.DataFrame.from_records(TherapyChangeHistory.values("date_of_change", "previous_group", "new_group"))
            TherayHistoryObjs = models.TherapyHistory.objects.filter(device_deidentified_id=device.deidentified_id).order_by("therapy_date").all()
            TherapyHistory = pd.DataFrame.from_records(TherayHistoryObjs.values("therapy_date", "group_id", "therapy_type","therapy_details"))
            DateSelection = pd.to_datetime(TherapyChangeHistory["date_of_change"]).view(np.int64) > authority["Permission"][0]*1000000000
            if authority["Permission"][1] > 0:
                DateSelection = np.bitwise_and(DateSelection, pd.to_datetime(TherapyChangeHistory["date_of_change"]).view(np.int64) < authority["Permission"][1]*1000000000)
            TherapyChangeData["date_of_change"] = TherapyChangeHistory["date_of_change"].values[DateSelection].tolist()
            TherapyChangeData["previous_group"] = TherapyChangeHistory["previous_group"].values[DateSelection].tolist()
            TherapyChangeData["new_group"] = TherapyChangeHistory["new_group"].values[DateSelection].tolist()
            
            VisitTimestamps = np.unique(TherapyHistory["therapy_date"])
            for i in range(len(VisitTimestamps)):
                SessionTime = VisitTimestamps[i].timestamp() * 1000000000
                for j in range(1, len(TherapyChangeData["date_of_change"])):
                    if TherapyChangeData["date_of_change"][j] > SessionTime:
                        TherapyChangeData["date_of_change"].insert(j, SessionTime)
                        TherapyChangeData["previous_group"].insert(j, TherapyChangeData["new_group"][j-1])
                        TherapyChangeData["new_group"].insert(j, TherapyChangeData["new_group"][j-1])
                        break

            TherapyChangeData["therapy"] = list()
            for i in range(len(TherapyChangeData["date_of_change"])):
                DetailTherapy, DetailTherapy_date = getTherapyDetails(TherapyHistory, TherapyChangeData["date_of_change"][i]/1000000000, TherapyChangeData["new_group"][i], "Pre-visit Therapy")
                BriefTherapy, BriefTherapy_date = getTherapyDetails(TherapyHistory, TherapyChangeData["date_of_change"][i]/1000000000, TherapyChangeData["new_group"][i], "Past Therapy")
                PostVisitTherapy, PostVisitTherapy_date = getTherapyDetails(TherapyHistory, TherapyChangeData["date_of_change"][i]/1000000000, TherapyChangeData["new_group"][i], "Post-visit Therapy")

                if not DetailTherapy == None and not BriefTherapy == None:
                    if datetime.fromtimestamp(BriefTherapy_date).date() < datetime.fromtimestamp(DetailTherapy_date).date():
                        TherapyChangeData["therapy"].append(BriefTherapy)
                    else:
                        TherapyChangeData["therapy"].append(DetailTherapy)
                
                elif not DetailTherapy == None:
                    TherapyChangeData["therapy"].append(DetailTherapy)

                elif not PostVisitTherapy == None:
                    TherapyChangeData["therapy"].append(PostVisitTherapy)
                
                else:
                    TherapyChangeData["therapy"].append(BriefTherapy)
                
                if TherapyChangeData["therapy"][-1] and len(ImpedanceHistory) > 0:
                    impedanceIndex = np.argmin(np.abs(np.array([impedanceLog["session_date"] for impedanceLog in ImpedanceHistory]) - TherapyChangeData["date_of_change"][i]/1000000000))
                    TherapyChangeData["therapy"][-1]["Impedance"] = ImpedanceHistory[impedanceIndex]
                
            for i in range(len(TherapyHistory["therapy_date"])):
                if TherapyHistory["therapy_date"][i].timestamp() > TherapyChangeData["date_of_change"][-1]/1000000000 and (TherapyHistory["therapy_date"][i].timestamp() < authority["Permission"][1] or authority["Permission"][1] == 0):
                    TherapyChangeData["date_of_change"].append(TherapyHistory["therapy_date"][i].timestamp()*1000000000)
                    TherapyChangeData["previous_group"].append(TherapyChangeData["new_group"][-1])
                    TherapyChangeData["new_group"].append(TherapyChangeData["new_group"][-1])

                    DetailTherapy, DetailTherapy_date = getTherapyDetails(TherapyHistory, TherapyHistory["therapy_date"][i].timestamp(), TherapyChangeData["new_group"][-1], "Pre-visit Therapy")
                    BriefTherapy, BriefTherapy_date = getTherapyDetails(TherapyHistory, TherapyHistory["therapy_date"][i].timestamp(), TherapyChangeData["new_group"][-1], "Past Therapy")
                    PostVisitTherapy, PostVisitTherapy_date = getTherapyDetails(TherapyHistory, TherapyHistory["therapy_date"][i].timestamp(), TherapyChangeData["new_group"][-1], "Post-visit Therapy")
                    
                    if not DetailTherapy == None and not BriefTherapy == None:
                        if datetime.fromtimestamp(BriefTherapy_date).date() < datetime.fromtimestamp(DetailTherapy_date).date():
                            TherapyChangeData["therapy"].append(BriefTherapy)
                        else:
                            TherapyChangeData["therapy"].append(DetailTherapy)
                    
                    elif not DetailTherapy == None:
                        TherapyChangeData["therapy"].append(DetailTherapy)

                    elif not PostVisitTherapy == None:
                        TherapyChangeData["therapy"].append(PostVisitTherapy)
                    
                    else:
                        TherapyChangeData["therapy"].append(BriefTherapy)
                    
                    if TherapyChangeData["therapy"][-1] and len(ImpedanceHistory) > 0:
                        impedanceIndex = np.argmin(np.abs(np.array([impedanceLog["session_date"] for impedanceLog in ImpedanceHistory]) - TherapyHistory["therapy_date"][i].timestamp()))
                        TherapyChangeData["therapy"][-1]["Impedance"] = ImpedanceHistory[impedanceIndex]

            TherapyHistoryContext.append(TherapyChangeData)

    return TherapyHistoryContext

def queryAdaptiveGroupForThreshold(user, patientUniqueID, authority):
    TherapyHistory = list()
    if not authority["Permission"]:
        return TherapyHistory

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        TherapyHistoryObjs = models.TherapyHistory.objects.filter(device_deidentified_id=device.deidentified_id, therapy_type="Post-visit Therapy").order_by("-therapy_date").all()
        for therapy in TherapyHistoryObjs:
            if therapy.therapy_date == TherapyHistoryObjs[0].therapy_date:
                TherapyInfo = {"DeviceID": str(device.deidentified_id), "Device": device.getDeviceSerialNumber(key), "DeviceLocation": device.device_location}
                TherapyInfo["TherapyDate"] = therapy.therapy_date.timestamp()
                TherapyInfo["TherapyGroup"] = therapy.group_id
                TherapyInfo["TherapyType"] = therapy.therapy_type
                TherapyInfo["LogID"] = str(therapy.history_log_id)
                TherapyInfo["Therapy"] = therapy.therapy_details

                if TherapyInfo["TherapyDate"] > authority["Permission"][0]:
                    if authority["Permission"][1] > 0 and TherapyInfo["TherapyDate"] < authority["Permission"][1]:
                        TherapyHistory.append(TherapyInfo)
                    elif authority["Permission"][1] == 0:
                        TherapyHistory.append(TherapyInfo)
                        
    TherapyHistory = sorted(TherapyHistory, key=lambda x: x["TherapyGroup"])
    return TherapyHistory

def queryTherapyConfigurations(user, patientUniqueID, authority, therapyType="Past Therapy"):
    """ Extract all therapy configurations at each programming session.

    This pipeline will go through all session files and extract the Therapy Groups and Therapy History objects 
    to provide user with the detail therapy options that the patient had at each timepoint. 

    Args:
      user: BRAVO Platform User object. 
      patientUniqueID: Deidentified patient ID as referenced in SQL Database. 
      authority: User permission structure indicating the type of access the user has.
      therapyType (string): The type of therapy that you want (Past Therapy, Pre-visit Therapy, and Post-visit Therapy).

    Returns:
      List of therapy configurations ordered by time. 
    """

    TherapyHistory = list()
    if not authority["Permission"]:
        return TherapyHistory

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        if therapyType == "":
            TherapyHistoryObjs = models.TherapyHistory.objects.filter(device_deidentified_id=device.deidentified_id).order_by("therapy_date").all()
        else:
            TherapyHistoryObjs = models.TherapyHistory.objects.filter(device_deidentified_id=device.deidentified_id, therapy_type=therapyType).order_by("therapy_date").all()

        deviceName = device.device_name
        if deviceName == "":
            deviceName = device.getDeviceSerialNumber(key)

        for therapy in TherapyHistoryObjs:
            TherapyInfo = {"DeviceID": str(device.deidentified_id), "Device": deviceName, "DeviceLocation": device.device_location}
            TherapyInfo["TherapyDate"] = therapy.therapy_date.timestamp()
            TherapyInfo["TherapyGroup"] = therapy.group_id
            TherapyInfo["TherapyType"] = therapy.therapy_type
            TherapyInfo["LogID"] = str(therapy.history_log_id)
            TherapyInfo["Therapy"] = therapy.therapy_details
            TherapyInfo["LeadInfo"] = device.device_lead_configurations

            if TherapyInfo["TherapyDate"] > authority["Permission"][0]:
                if authority["Permission"][1] > 0 and TherapyInfo["TherapyDate"] < authority["Permission"][1]:
                    TherapyHistory.append(TherapyInfo)
                elif authority["Permission"][1] == 0:
                    TherapyHistory.append(TherapyInfo)

    return TherapyHistory

def getTherapyDetails(TherapyHistory, timestamp, groupID, typeID):
    """ Extract detail therapy configuration of specific group at specific time.

    This pipeline will go through all configurations and extract the detail therapy configurations 
    based on the user's request. 

    For example, if Group A configuration is desired for Jan 01, 2021. The pipeline will go through all 
    configurations and find the last therapy settings before Jan 01, 2021 for Group A and return that to you.

    Args:
      TherapyHistory: List of therapy configurations ordered by time extracted from ``queryTherapyConfigurations``. 
      timestamp: A timestamp at which therapy configurations is wanted. 
      groupID: Medtronic Group ID (Group_A to Group_D).
      typeID (string): The type of therapy that you want (Past Therapy, Pre-visit Therapy, and Post-visit Therapy).

    Returns:
      A tuple of Therapy Details dictionary and unix timestamp at which the setting is programmed.
    """

    DateFound = 0
    if typeID == "Post-visit Therapy":
        for j in range(len(TherapyHistory["therapy_date"])-1, -1, -1):
            if TherapyHistory["therapy_type"][j] == typeID:
                if TherapyHistory["therapy_date"][j].timestamp() < timestamp:
                    if DateFound == 0:
                        DateFound = TherapyHistory["therapy_date"][j].timestamp()
                    elif TherapyHistory["therapy_date"][j].timestamp() < DateFound:
                        return None, None

                    if TherapyHistory["group_id"][j] == groupID:
                        therapy_details = copy.deepcopy(TherapyHistory["therapy_details"][j])
                        if "LeftHemisphere" in therapy_details.keys():
                            if type(therapy_details["LeftHemisphere"]["Channel"][0]) == list:
                                for i in range(len(therapy_details["LeftHemisphere"]["Channel"])):
                                    therapy_details["LeftHemisphere"]["Channel"][i] = Percept.reformatStimulationChannel(therapy_details["LeftHemisphere"]["Channel"][i])
                            else:
                                therapy_details["LeftHemisphere"]["Channel"] = Percept.reformatStimulationChannel(therapy_details["LeftHemisphere"]["Channel"])
                        if "RightHemisphere" in therapy_details.keys():
                            if type(therapy_details["RightHemisphere"]["Channel"][0]) == list:
                                for i in range(len(therapy_details["RightHemisphere"]["Channel"])):
                                    therapy_details["RightHemisphere"]["Channel"][i] = Percept.reformatStimulationChannel(therapy_details["RightHemisphere"]["Channel"][i])
                            else:
                                therapy_details["RightHemisphere"]["Channel"] = Percept.reformatStimulationChannel(therapy_details["RightHemisphere"]["Channel"])
                        return therapy_details, TherapyHistory["therapy_date"][j].timestamp()

    for j in range(len(TherapyHistory["therapy_date"])):
        if TherapyHistory["therapy_type"][j] == typeID:
            if TherapyHistory["therapy_date"][j].timestamp() > timestamp:
                if DateFound == 0:
                    DateFound = TherapyHistory["therapy_date"][j].timestamp()
                elif TherapyHistory["therapy_date"][j].timestamp() > (DateFound + 3600*24):
                    return None, None

                if TherapyHistory["group_id"][j] == groupID:
                    therapy_details = copy.deepcopy(TherapyHistory["therapy_details"][j])
                    if "LeftHemisphere" in therapy_details.keys():
                        if type(therapy_details["LeftHemisphere"]["Channel"][0]) == list:
                            for i in range(len(therapy_details["LeftHemisphere"]["Channel"])):
                                therapy_details["LeftHemisphere"]["Channel"][i] = Percept.reformatStimulationChannel(therapy_details["LeftHemisphere"]["Channel"][i])
                        else:
                            therapy_details["LeftHemisphere"]["Channel"] = Percept.reformatStimulationChannel(therapy_details["LeftHemisphere"]["Channel"])
                    if "RightHemisphere" in therapy_details.keys():
                        if type(therapy_details["RightHemisphere"]["Channel"][0]) == list:
                            for i in range(len(therapy_details["RightHemisphere"]["Channel"])):
                                therapy_details["RightHemisphere"]["Channel"][i] = Percept.reformatStimulationChannel(therapy_details["RightHemisphere"]["Channel"][i])
                        else:
                            therapy_details["RightHemisphere"]["Channel"] = Percept.reformatStimulationChannel(therapy_details["RightHemisphere"]["Channel"])
                    return therapy_details, TherapyHistory["therapy_date"][j].timestamp()
    return None, None

def extractTherapyDetails(TherapyConfigurations, TherapyChangeLog=[], resolveConflicts=False):
    """ General pipeline to extract therapy details for visualization. 

    The pipeline will go through all timestamp first to identify all unique programming dates.
    The unique dates were used to identify all TherapyChangeLog between visits to calculate percent time 
    for each group in between visit. 

    Then a processed organized dictionary of therapy settings called "Overview" will be generated for each therapy group. 

    Args:
      TherapyConfigurations: List of therapy configurations ordered by time extracted from ``queryTherapyConfigurations``. 
      TherapyChangeLog: List of therapy change logs ordered by time extracted from ``queryTherapyHistory``. 

    Returns:
      A list of processed Therapy Data organized by time and by group.
    """

    TherapyData = dict()

    # Normalize Timestamp
    DeviceTimestamp = dict()
    for i in range(0,len(TherapyConfigurations)):
        if not TherapyConfigurations[i]["DeviceID"] in DeviceTimestamp.keys():
            DeviceTimestamp[TherapyConfigurations[i]["DeviceID"]] = {}
    
    # Session Timestamp
    SessionTimestamp = {}

    # Sort Timestamp by DeviceID, TherapyType, and TherapyGroup
    for deviceID in DeviceTimestamp.keys():
        for i in range(len(TherapyConfigurations)):
            if TherapyConfigurations[i]["DeviceID"] == deviceID:
                if not TherapyConfigurations[i]["TherapyType"] in DeviceTimestamp[deviceID].keys():
                    DeviceTimestamp[deviceID][TherapyConfigurations[i]["TherapyType"]] = []
                if not TherapyConfigurations[i]["TherapyDate"] in DeviceTimestamp[deviceID][TherapyConfigurations[i]["TherapyType"]]:
                    DeviceTimestamp[deviceID][TherapyConfigurations[i]["TherapyType"]].append(TherapyConfigurations[i]["TherapyDate"])
        
        if "Past Therapy" in DeviceTimestamp[deviceID].keys() and "Pre-visit Therapy" in DeviceTimestamp[deviceID].keys():
            for i in range(len(DeviceTimestamp[deviceID]["Past Therapy"])):
                matchSession = np.where(np.abs(np.array(DeviceTimestamp[deviceID]["Pre-visit Therapy"]) - DeviceTimestamp[deviceID]["Past Therapy"][i]) < 3600*24)[0]
                if len(matchSession) > 0:
                    continue
                DeviceTimestamp[deviceID]["Pre-visit Therapy"].append(DeviceTimestamp[deviceID]["Past Therapy"][i])
        
            DeviceTimestamp[deviceID]["Pre-visit Therapy"] = sorted(DeviceTimestamp[deviceID]["Pre-visit Therapy"])

    for deviceID in DeviceTimestamp.keys():
        for typeName in DeviceTimestamp[deviceID].keys():
            if typeName == "Post-visit Therapy":
                continue

            for timestamp in range(1, len(DeviceTimestamp[deviceID][typeName])):
                if timestamp == 0:
                    lastMeasuredTimestamp = 0
                else:
                    lastMeasuredTimestamp = DeviceTimestamp[deviceID][typeName][timestamp-1]

                TherapyDutyPercent = dict()
                for i in range(len(TherapyChangeLog)):
                    if str(TherapyChangeLog[i]["device"]) == deviceID:
                        if TherapyChangeLog[i]["date_of_change"][0]/1000000000 > lastMeasuredTimestamp:
                            if not TherapyChangeLog[i]["previous_group"][0] in TherapyDutyPercent.keys():
                                TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][0]] = 0
                            if TherapyChangeLog[i]["date_of_change"][0]/1000000000 > DeviceTimestamp[deviceID][typeName][timestamp]:
                                TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][0]] += (DeviceTimestamp[deviceID][typeName][timestamp]-lastMeasuredTimestamp)
                                lastMeasuredTimestamp = DeviceTimestamp[deviceID][typeName][timestamp]
                            else:
                                TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][0]] += (TherapyChangeLog[i]["date_of_change"][0]/1000000000-lastMeasuredTimestamp)
                                lastMeasuredTimestamp = TherapyChangeLog[i]["date_of_change"][0]/1000000000

                        for k in range(1, len(TherapyChangeLog[i]["date_of_change"])):
                            if TherapyChangeLog[i]["previous_group"][k] == TherapyChangeLog[i]["new_group"][k-1] or TherapyChangeLog[i]["previous_group"][k] == -1:
                                if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > lastMeasuredTimestamp:
                                    if not TherapyChangeLog[i]["previous_group"][k] in TherapyDutyPercent.keys():
                                        TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] = 0
                                    if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > DeviceTimestamp[deviceID][typeName][timestamp]:
                                        TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (DeviceTimestamp[deviceID][typeName][timestamp]-lastMeasuredTimestamp)
                                        lastMeasuredTimestamp = DeviceTimestamp[deviceID][typeName][timestamp]
                                    else:
                                        TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (TherapyChangeLog[i]["date_of_change"][k]/1000000000-lastMeasuredTimestamp)
                                        lastMeasuredTimestamp = TherapyChangeLog[i]["date_of_change"][k]/1000000000

                for i in range(len(TherapyConfigurations)):
                    if TherapyConfigurations[i]["DeviceID"] == deviceID and TherapyConfigurations[i]["TherapyDate"] == DeviceTimestamp[deviceID][typeName][timestamp] and TherapyConfigurations[i]["TherapyType"] == typeName:
                        TherapyConfigurations[i]["TherapyDutyPercent"] = TherapyDutyPercent

    existingGroups = []
    for nConfig in range(len(TherapyConfigurations)):
        therapy = TherapyConfigurations[nConfig]
        if not int(therapy["TherapyDate"]) in TherapyData.keys():
            TherapyData[int(therapy["TherapyDate"])] = list()
        therapy["Overview"] = dict()
        if "TherapyDutyPercent" in therapy.keys():
            totalHours = np.sum([therapy["TherapyDutyPercent"][key] for key in therapy["TherapyDutyPercent"].keys()])
            if not therapy["Therapy"]["GroupId"] in therapy["TherapyDutyPercent"].keys():
                therapy["Overview"]["DutyPercent"] = "(0%)"
            else:
                therapy["Overview"]["DutyPercent"] = f"({therapy['TherapyDutyPercent'][therapy['Therapy']['GroupId']]/totalHours*100:.2f}%)"

        therapy["Overview"]["GroupName"] = therapy["Therapy"]["GroupId"].replace("GroupIdDef.GROUP_","Group ")

        therapy["Overview"]["TherapyUsage"] = 0
        for hemisphere in ["LeftHemisphere","RightHemisphere"]:
            if hemisphere in therapy["Therapy"].keys():
                if therapy["Therapy"][hemisphere]["Mode"] == "Interleaving":
                    for i in range(len(therapy['Therapy'][hemisphere]['Channel'])):
                        for contact in therapy['Therapy'][hemisphere]['Channel'][i]:
                            if contact["ElectrodeStateResult"] == "ElectrodeStateDef.Negative":
                                ContactPolarity = '-'
                            elif contact["ElectrodeStateResult"] == "ElectrodeStateDef.Positive":
                                ContactPolarity = '+'
                            else:
                                ContactPolarity = ""

                            ContactName, ContactID = Percept.reformatElectrodeDef(contact["Electrode"])
                            if not ContactName == "CAN" or len(therapy['Therapy'][hemisphere]['Channel']) == 2:
                                contact["Electrode"] = ContactName + ContactPolarity
                else:
                    for contact in therapy['Therapy'][hemisphere]['Channel']:
                        if contact["ElectrodeStateResult"] == "ElectrodeStateDef.Negative":
                            ContactPolarity = '-'
                        elif contact["ElectrodeStateResult"] == "ElectrodeStateDef.Positive":
                            ContactPolarity = '+'
                        else:
                            ContactPolarity = ""

                        ContactName, ContactID = Percept.reformatElectrodeDef(contact["Electrode"])
                        if not ContactName == "CAN" or len(therapy['Therapy'][hemisphere]['Channel']) == 2:
                            contact["Electrode"] = ContactName + ContactPolarity

        key = str(therapy["TherapyDate"]) + "_" + therapy["Therapy"]["GroupId"] + "_" + therapy["TherapyType"] + "_" + TherapyConfigurations[nConfig]["DeviceID"]
        if not key in existingGroups:
            TherapyData[int(therapy["TherapyDate"])].append(therapy)
            existingGroups.append(key)
            
    for key in TherapyData.keys():
        TherapyData[key] = sorted(TherapyData[key], key=lambda therapy: therapy["Overview"]["GroupName"])

    return TherapyData
