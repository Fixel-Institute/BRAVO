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
import pytz
import numpy as np
import pandas as pd

from Backend import models
from modules import Database
from decoder import Summit

key = os.environ.get('ENCRYPTION_KEY')

def saveTherapySettings(deviceID, therapyList, sessionDate, type, sourceFile):
    """ Save Summit Therapy Settings

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      therapyList: Array of Therapy Configuration structures extracted from JSON file.
      sessionDate: DateTime object indicating when the therapy configuration is saved.
      type: One of three data types: ["Past Therapy","Pre-visit Therapy","Post-visit Therapy"].
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """
    TheraySavingList = []
    for therapy in therapyList:
        therapyDate = datetime.fromtimestamp(therapy["Time"],tz=pytz.utc)
        for therapyGroup in therapy["Therapy"]:
            if therapyGroup["Valid"]:
                if not models.TherapyHistory.objects.filter(device_deidentified_id=deviceID, therapy_date=therapyDate, therapy_type=type, group_id=therapyGroup["GroupNumber"]).exists():
                    TheraySavingList.append(models.TherapyHistory(device_deidentified_id=deviceID, therapy_date=therapyDate, source_file=sourceFile,
                                        group_name=therapyGroup["GroupNumber"], group_id=therapyGroup["GroupNumber"], active_group=therapyGroup["ActiveGroup"],
                                        therapy_type=type, therapy_details=therapyGroup))

    if len(TheraySavingList) > 0:
        models.TherapyHistory.objects.bulk_create(TheraySavingList,ignore_conflicts=True)

def queryTherapyHistory(user, device, authority):
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
    deviceName = device.device_name
    if deviceName == "":
        deviceName = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)
    
    TherapyChangeData = dict()
    TherapyChangeData["device"] = str(device.deidentified_id)
    TherapyChangeData["device_name"] = deviceName
    TherapyChangeData["date_of_change"] = []
    TherapyChangeData["previous_group"] = []
    TherapyChangeData["new_group"] = []
    TherapyChangeData["date_of_status"] = []
    TherapyChangeData["new_status"] = []
    TherapyChangeData["previous_status"] = []
    TherapyChangeData["therapy"] = []

    TherapyGroupDict = {
        "GroupA": "GroupIdDef.GROUP_A",
        "GroupB": "GroupIdDef.GROUP_B",
        "GroupC": "GroupIdDef.GROUP_C",
        "GroupD": "GroupIdDef.GROUP_D"
    }

    TherapyHistoryObjs = models.TherapyHistory.objects.filter(device_deidentified_id=device.deidentified_id).order_by("therapy_date").all()
    for therapy in TherapyHistoryObjs:
        TherapyInfo = {"DeviceID": str(device.deidentified_id), "Device": deviceName, "DeviceLocation": device.device_location}
        TherapyInfo["TherapyDate"] = therapy.therapy_date.timestamp()*1000000000
        TherapyInfo["TherapyGroup"] = therapy.group_id
        TherapyInfo["TherapyType"] = therapy.therapy_type
        TherapyInfo["LogID"] = str(therapy.history_log_id)
        TherapyInfo["Therapy"] = therapy.therapy_details
        TherapyInfo["LeadInfo"] = device.device_lead_configurations

        if TherapyInfo["Therapy"]["ActiveGroup"]:
            if len(TherapyChangeData["date_of_change"]) == 0:
                TherapyChangeData["date_of_change"].append(TherapyInfo["TherapyDate"])
                TherapyChangeData["previous_group"].append(TherapyGroupDict[therapy.group_id])
                TherapyChangeData["new_group"].append(TherapyGroupDict[therapy.group_id])
                TherapyChangeData["therapy"].append(TherapyInfo["Therapy"])
            TherapyChangeData["date_of_change"].append(TherapyInfo["TherapyDate"])
            TherapyChangeData["previous_group"].append(TherapyChangeData["new_group"][-1])
            TherapyChangeData["new_group"].append(TherapyGroupDict[therapy.group_id])
            TherapyChangeData["therapy"].append(extractTherapyDetails(TherapyInfo))
    
    return TherapyChangeData

def queryTherapyConfigurations(user, device, TherapyHistoryObjs, authority):
    TherapyHistory = []

    LastTherapyConfig = {}

    deviceName = device.device_name
    if deviceName == "":
        deviceName = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)

    TherapyHistoryObjs = sorted(TherapyHistoryObjs, key=lambda therapy: therapy.therapy_date)
    for therapy in TherapyHistoryObjs:
        TherapyInfo = {"DeviceID": str(device.deidentified_id), "Device": deviceName, "DeviceLocation": device.device_location}
        TherapyInfo["TherapyDate"] = therapy.therapy_date.timestamp()
        TherapyInfo["TherapyGroup"] = therapy.group_id
        TherapyInfo["TherapyType"] = therapy.therapy_type
        TherapyInfo["LogID"] = str(therapy.history_log_id)
        TherapyInfo["Therapy"] = therapy.therapy_details
        TherapyInfo["LeadInfo"] = device.device_lead_configurations

        TherapyDetails = extractTherapyDetails(TherapyInfo)["Therapy"]
        TherapyDetails["ActiveGroup"] = False 
        TherapyDetails["TherapyStatus"] = 0 
        
        if TherapyInfo["TherapyDate"] > authority["Permission"][0]:
            if authority["Permission"][1] > 0 and TherapyInfo["TherapyDate"] < authority["Permission"][1]:
                TherapyHistory.append(TherapyInfo)

            elif authority["Permission"][1] == 0:
                TherapyHistory.append(TherapyInfo)
    
    return TherapyHistory

def extractTherapyDetails(therapy):
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
    therapy["Overview"] = dict()
    therapy["Overview"]["GroupName"] = therapy["TherapyGroup"]
    therapy["Overview"]["TherapyUsage"] = 0

    # Format for Cycling
    if "Cycling" in therapy["Therapy"].keys():
        therapy["Therapy"]["GroupSettings"] = {
            "Cycling": {
                "Enabled": therapy["Therapy"]["Cycling"]["Enabled"]
            }
        }
        if therapy["Therapy"]["GroupSettings"]["Cycling"]["Enabled"]:
            therapy["Therapy"]["GroupSettings"]["Cycling"]["OnDurationInMilliSeconds"] = therapy["Therapy"]["Cycling"]["OnTime"]*1000
            therapy["Therapy"]["GroupSettings"]["Cycling"]["OffDurationInMilliSeconds"] = therapy["Therapy"]["Cycling"]["OffTime"]*1000

    for program in therapy["Therapy"]["Programs"]:
        if program["Valid"]:
            for i in range(len(program["ElectrodeList"])):
                if type(program["ElectrodeList"][i]["Channel"]) == int:
                    if program["ElectrodeList"][i]["Channel"] < 8:
                        hemisphere = "LeftHemisphere"
                    else:
                        hemisphere = "RightHemisphere"
            
            therapy["Therapy"][hemisphere] = {}
            therapy["Therapy"][hemisphere]["Channel"] = [{
                "ElectrodeStateResult": program["ElectrodeList"][i]["ElectrodeState"],
                "Electrode": f"E{program['ElectrodeList'][i]['Channel']:02}" + program["ElectrodeList"][i]["ElectrodeState"],
            } for i in range(len(program["ElectrodeList"])) if not program["ElectrodeList"][i]["Channel"] == "CAN"]
            therapy["Therapy"][hemisphere]["Frequency"] = therapy["Therapy"]["Frequency"]
            therapy["Therapy"][hemisphere]["PulseWidth"] = program["PulseWidth"]
            therapy["Therapy"][hemisphere]["Amplitude"] = program["Amplitude"]
            therapy["Therapy"][hemisphere]["Unit"] = "mA"
            therapy["Therapy"][hemisphere]["Mode"] = "Standard"
        
            if "Adaptive" in therapy["Therapy"].keys():
                if "Adaptive" in therapy["Therapy"]["Adaptive"].keys() and "Detector" in therapy["Therapy"]["Adaptive"].keys():
                    therapy["Therapy"][hemisphere]["Mode"] = "SummitAdaptive"
                    therapy["Therapy"][hemisphere]["Adaptive"] = therapy["Therapy"]["Adaptive"]
    return therapy