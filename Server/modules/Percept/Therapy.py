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

def queryTherapyHistory(user, device, authority):
    """ Extract all therapy change logs related to a specific device.

    This pipeline go through all therapy change logs and extract the time at which a group changes is made. 
    The pipeline will also extract the actual setting that the device is on before and after changes.

    Args:
      user: BRAVO Platform User object. 
      device: QuerySet Device Object. 
      authority: User permission structure indicating the type of access the user has.

    Returns:
      List of therapy group history ordered by time. 
    """

    TherapyChangeData = dict()
    TherapyChangeData["device"] = device.deidentified_id
    DeviceName = device.device_name
    if DeviceName == "":
        DeviceName = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)
    TherapyChangeData["device_name"] = DeviceName
    TherapyChangeHistory = models.TherapyChangeLog.objects.filter(device_deidentified_id=device.deidentified_id).order_by("date_of_change").all()
    if len(TherapyChangeHistory) > 0:
        TherapyChangeHistory = pd.DataFrame.from_records(TherapyChangeHistory.values("date_of_change", "previous_group", "new_group"))
        TherayHistoryObjs = models.TherapyHistory.objects.filter(device_deidentified_id=device.deidentified_id).order_by("therapy_date").all()
        TherapyHistory = pd.DataFrame.from_records(TherayHistoryObjs.values("therapy_date", "group_id", "therapy_type","therapy_details"))
        DateSelection = pd.to_datetime(TherapyChangeHistory["date_of_change"]).view(np.int64) > authority["Permission"][0]*1000000000
        if authority["Permission"][1] > 0:
            DateSelection = np.bitwise_and(DateSelection, pd.to_datetime(TherapyChangeHistory["date_of_change"]).view(np.int64) < authority["Permission"][1]*1000000000)
        TherapyGroupSelection = [not TherapyChangeHistory["previous_group"][i].startswith("TherapyChangeStatusDef") for i in range(len(TherapyChangeHistory["previous_group"]))]
        
        if np.sum(TherapyGroupSelection) == 0:
            return None

        TherapyChangeData["date_of_change"] = TherapyChangeHistory["date_of_change"].values[np.bitwise_and(DateSelection, TherapyGroupSelection)].tolist()
        TherapyChangeData["previous_group"] = TherapyChangeHistory["previous_group"].values[np.bitwise_and(DateSelection, TherapyGroupSelection)].tolist()
        TherapyChangeData["new_group"] = TherapyChangeHistory["new_group"].values[np.bitwise_and(DateSelection, TherapyGroupSelection)].tolist()
        
        TherapyChangeData["date_of_status"] = TherapyChangeHistory["date_of_change"].values[np.bitwise_and(DateSelection, [not i for i in TherapyGroupSelection])].tolist()
        TherapyChangeData["new_status"] = TherapyChangeHistory["new_group"].values[np.bitwise_and(DateSelection, [not i for i in TherapyGroupSelection])].tolist()
        TherapyChangeData["previous_status"] = TherapyChangeHistory["previous_group"].values[np.bitwise_and(DateSelection, [not i for i in TherapyGroupSelection])].tolist()
        TherapyChangeData["previous_status"] = [i == "TherapyChangeStatusDef.ON" for i in TherapyChangeData["previous_status"]]
        TherapyChangeData["new_status"] = [i == "True" for i in TherapyChangeData["new_status"]]

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
                
        # 5 Seconds Adjustment Due to TherapyChangeDate is actually logged slightly later than when the Group is actually changed.
        TherapyChangeData["date_of_change"] = np.array(TherapyChangeData["date_of_change"]) - 5*1000000000

    return TherapyChangeData

def queryTherapyConfigurations(user, device, TherapyHistoryObjs, authority):
    TherapyHistory = []

    deviceName = device.device_name
    if deviceName == "":
        deviceName = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)

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
                        therapy_details["TherapyDate"] = TherapyHistory["therapy_date"][j].timestamp()
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
                    therapy_details["TherapyDate"] = TherapyHistory["therapy_date"][j].timestamp()
                    return therapy_details, TherapyHistory["therapy_date"][j].timestamp()
    return None, None

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
    return therapy