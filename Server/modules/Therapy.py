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
from modules.Percept import Therapy as PerceptTherapy
from modules.Summit import Therapy as SummitTherapy

from decoder import Percept

key = os.environ.get('ENCRYPTION_KEY')

def queryImpedanceHistory(user, patientUniqueID, authority):
    ImpedanceHistory = list()
    if not authority["Permission"]:
        return ImpedanceHistory

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        DeviceName = device.device_name
        if DeviceName == "":
            DeviceName = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)
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
            if device.device_type == "Summit RC+S":
                TherapyChangeData = SummitTherapy.queryTherapyHistory(user, device, authority) 
                if not TherapyChangeData:
                    continue
                TherapyHistoryContext.append(TherapyChangeData)
                
            else:
                TherapyChangeData = PerceptTherapy.queryTherapyHistory(user, device, authority)
                if not TherapyChangeData:
                    continue 

                for i in range(len(TherapyChangeData["therapy"])):
                    if TherapyChangeData["therapy"][i] and len(ImpedanceHistory) > 0:
                        impedanceIndex = np.argmin(np.abs(np.array([impedanceLog["session_date"] for impedanceLog in ImpedanceHistory]) - TherapyChangeData["therapy"][i]["TherapyDate"]))
                        TherapyChangeData["therapy"][i]["Impedance"] = ImpedanceHistory[impedanceIndex]
                TherapyHistoryContext.append(TherapyChangeData)

    return TherapyHistoryContext

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
            deviceName = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)

        if device.device_type == "Summit RC+S":
            TherapyHistory.extend(SummitTherapy.queryTherapyConfigurations(user, device, TherapyHistoryObjs, authority))
        else:
            TherapyHistory.extend(PerceptTherapy.queryTherapyConfigurations(user, device, TherapyHistoryObjs, authority))

    return TherapyHistory

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
            if typeName == "Post-visit Therapy" or typeName == "SummitTherapy":
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

        if therapy["TherapyType"] == "SummitTherapy":
            therapy = SummitTherapy.extractTherapyDetails(therapy)

            key = str(therapy["TherapyDate"]) + "_" + therapy["TherapyGroup"] + "_" + therapy["TherapyType"] + "_" + TherapyConfigurations[nConfig]["DeviceID"]
            if not key in existingGroups:
                TherapyData[int(therapy["TherapyDate"])].append(therapy)
                existingGroups.append(key)
            
        else:
            therapy = PerceptTherapy.extractTherapyDetails(therapy)
            key = str(therapy["TherapyDate"]) + "_" + therapy["Therapy"]["GroupId"] + "_" + therapy["TherapyType"] + "_" + TherapyConfigurations[nConfig]["DeviceID"]
            if not key in existingGroups:
                TherapyData[int(therapy["TherapyDate"])].append(therapy)
                existingGroups.append(key)
            
    for key in TherapyData.keys():
        TherapyData[key] = sorted(TherapyData[key], key=lambda therapy: therapy["Overview"]["GroupName"])

    return TherapyData
