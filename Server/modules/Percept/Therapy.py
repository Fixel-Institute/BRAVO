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

def queryTherapyHistory(user, patientUniqueID, authority):
    TherapyHistoryContext = list()
    if not authority["Permission"]:
        return TherapyHistoryContext

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        TherapyChangeData = dict()
        TherapyChangeData["device"] = device.deidentified_id
        TherapyChangeData["device_name"] = device.getDeviceSerialNumber(key)
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
            TherapyChangeData["therapy"] = list()
            for i in range(len(TherapyChangeData["date_of_change"])):
                DetailTherapy, DetailTherapy_date = getTherapyDetails(TherapyHistory, TherapyChangeData["date_of_change"][i]/1000000000, TherapyChangeData["new_group"][i], "Pre-visit Therapy")
                BriefTherapy, BriefTherapy_date = getTherapyDetails(TherapyHistory, TherapyChangeData["date_of_change"][i]/1000000000, TherapyChangeData["new_group"][i], "Past Therapy")
                PostVisitTherapy, PostVisitTherapy_date = getTherapyDetails(TherapyHistory, TherapyChangeData["date_of_change"][i]/1000000000, TherapyChangeData["new_group"][i], "Post-visit Therapy")
                if DetailTherapy == None:
                    if not BriefTherapy == None:
                        TherapyChangeData["therapy"].append(BriefTherapy)
                    elif not PostVisitTherapy == None:
                        TherapyChangeData["therapy"].append(PostVisitTherapy)
                else:
                    if BriefTherapy == None:
                        TherapyChangeData["therapy"].append(DetailTherapy)
                    elif datetime.fromtimestamp(BriefTherapy_date).date() < datetime.fromtimestamp(DetailTherapy_date).date():
                        TherapyChangeData["therapy"].append(BriefTherapy)
                    else:
                        TherapyChangeData["therapy"].append(DetailTherapy)

            for i in range(len(TherapyHistory["therapy_date"])):
                if TherapyHistory["therapy_date"][i].timestamp() > TherapyChangeData["date_of_change"][-1]/1000000000 and (TherapyHistory["therapy_date"][i].timestamp() < authority["Permission"][1] or authority["Permission"][1] == 0):
                    TherapyChangeData["date_of_change"].append(TherapyHistory["therapy_date"][i].timestamp()*1000000000)
                    TherapyChangeData["previous_group"].append(TherapyChangeData["new_group"][-1])
                    TherapyChangeData["new_group"].append(TherapyChangeData["new_group"][-1])

                    DetailTherapy, DetailTherapy_date = getTherapyDetails(TherapyHistory, TherapyHistory["therapy_date"][i].timestamp(), TherapyChangeData["new_group"][-1], "Pre-visit Therapy")
                    BriefTherapy, BriefTherapy_date = getTherapyDetails(TherapyHistory, TherapyHistory["therapy_date"][i].timestamp(), TherapyChangeData["new_group"][-1], "Past Therapy")
                    PostVisitTherapy, PostVisitTherapy_date = getTherapyDetails(TherapyHistory, TherapyHistory["therapy_date"][i].timestamp(), TherapyChangeData["new_group"][-1], "Post-visit Therapy")
                    if DetailTherapy == None:
                        if not BriefTherapy == None:
                            TherapyChangeData["therapy"].append(BriefTherapy)
                        elif not PostVisitTherapy == None:
                            TherapyChangeData["therapy"].append(PostVisitTherapy)
                    else:
                        if BriefTherapy == None:
                            TherapyChangeData["therapy"].append(DetailTherapy)
                        elif datetime.fromtimestamp(BriefTherapy_date).date() < datetime.fromtimestamp(DetailTherapy_date).date():
                            TherapyChangeData["therapy"].append(BriefTherapy)
                        else:
                            TherapyChangeData["therapy"].append(DetailTherapy)

            TherapyHistoryContext.append(TherapyChangeData)

    return TherapyHistoryContext

def queryTherapyConfigurations(user, patientUniqueID, authority, therapy_type="Past Therapy"):
    TherapyHistory = list()
    if not authority["Permission"]:
        return TherapyHistory

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        if therapy_type == "":
            TherapyHistoryObjs = models.TherapyHistory.objects.filter(device_deidentified_id=device.deidentified_id).order_by("therapy_date").all()
        else:
            TherapyHistoryObjs = models.TherapyHistory.objects.filter(device_deidentified_id=device.deidentified_id, therapy_type=therapy_type).order_by("therapy_date").all()

        for therapy in TherapyHistoryObjs:
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

    return TherapyHistory

def getTherapyDetails(TherapyHistory, timestamp, group_id, typeID):
    for j in range(len(TherapyHistory["therapy_date"])):
        if TherapyHistory["therapy_date"][j].timestamp() > timestamp and TherapyHistory["group_id"][j] == group_id and TherapyHistory["therapy_type"][j] == typeID:
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
    TherapyData = dict()

    # Normalize Timestamp
    DeviceTimestamp = dict()
    for i in range(0,len(TherapyConfigurations)):
        if not TherapyConfigurations[i]["DeviceID"] in DeviceTimestamp.keys():
            DeviceTimestamp[TherapyConfigurations[i]["DeviceID"]] = list()

    ExistingTimestamp = list()
    for deviceID in DeviceTimestamp.keys():
        for i in range(len(TherapyConfigurations)):
            if TherapyConfigurations[i]["DeviceID"] == deviceID:
                TimeDifferences = np.array([np.abs(TherapyConfigurations[i]["TherapyDate"] - time) for time in ExistingTimestamp])
                Indexes = np.where(TimeDifferences < 3600*24)[0]
                if len(Indexes > 0):
                    TherapyConfigurations[i]["TherapyDate"] = ExistingTimestamp[Indexes[0]]
                else:
                    ExistingTimestamp.append(TherapyConfigurations[i]["TherapyDate"])

                if not TherapyConfigurations[i]["TherapyDate"] in DeviceTimestamp[deviceID]:
                    DeviceTimestamp[deviceID].append(TherapyConfigurations[i]["TherapyDate"])

    for deviceID in DeviceTimestamp.keys():
        for nConfig in range(len(DeviceTimestamp[deviceID])):
            if nConfig == 0:
                lastMeasuredTimestamp = 0
            else:
                lastMeasuredTimestamp = DeviceTimestamp[deviceID][nConfig-1]

            TherapyDutyPercent = dict()
            for i in range(len(TherapyChangeLog)):
                if str(TherapyChangeLog[i]["device"]) == deviceID:
                    for k in range(len(TherapyChangeLog[i]["date_of_change"])):
                        if lastMeasuredTimestamp < DeviceTimestamp[deviceID][nConfig]:
                            if k > 0:
                                if TherapyChangeLog[i]["previous_group"][k] == TherapyChangeLog[i]["new_group"][k-1] or TherapyChangeLog[i]["previous_group"][k] == -1:
                                    if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > lastMeasuredTimestamp:
                                        if not TherapyChangeLog[i]["previous_group"][k] in TherapyDutyPercent.keys():
                                            TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] = 0
                                        if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > DeviceTimestamp[deviceID][nConfig]:
                                            TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (DeviceTimestamp[deviceID][nConfig]-lastMeasuredTimestamp)
                                            lastMeasuredTimestamp = DeviceTimestamp[deviceID][nConfig]
                                        else:
                                            TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (TherapyChangeLog[i]["date_of_change"][k]/1000000000-lastMeasuredTimestamp)
                                            lastMeasuredTimestamp = TherapyChangeLog[i]["date_of_change"][k]/1000000000
                            else:
                                if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > lastMeasuredTimestamp:
                                    if not TherapyChangeLog[i]["previous_group"][k] in TherapyDutyPercent.keys():
                                        TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] = 0
                                    if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > DeviceTimestamp[deviceID][nConfig]:
                                        TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (DeviceTimestamp[deviceID][nConfig]-lastMeasuredTimestamp)
                                        lastMeasuredTimestamp = DeviceTimestamp[deviceID][nConfig]
                                    else:
                                        TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (TherapyChangeLog[i]["date_of_change"][k]/1000000000-lastMeasuredTimestamp)
                                        lastMeasuredTimestamp = TherapyChangeLog[i]["date_of_change"][k]/1000000000

            for i in range(len(TherapyConfigurations)):
                if TherapyConfigurations[i]["DeviceID"] == deviceID and TherapyConfigurations[i]["TherapyDate"] == DeviceTimestamp[deviceID][nConfig]:
                    TherapyConfigurations[i]["TherapyDutyPercent"] = TherapyDutyPercent

    existingGroups = []
    for nConfig in range(len(TherapyConfigurations)):
        therapy = TherapyConfigurations[nConfig]
        if not int(therapy["TherapyDate"]) in TherapyData.keys():
            TherapyData[int(therapy["TherapyDate"])] = list()
        therapy["Overview"] = dict()
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
        key = str(therapy["TherapyDate"]) + "_" + therapy["Therapy"]["GroupId"] + "_" + therapy["TherapyType"]
        if not key in existingGroups:
            TherapyData[int(therapy["TherapyDate"])].append(therapy)
            existingGroups.append(key)

    for key in TherapyData.keys():
        TherapyData[key] = sorted(TherapyData[key], key=lambda therapy: therapy["Overview"]["GroupName"])

    return TherapyData

def processTherapyDetails(TherapyConfigurations, TherapyChangeLog=[], resolveConflicts=True):
    TherapyData = dict()

    # Normalize Timestamp
    DeviceTimestamp = dict()
    for i in range(0,len(TherapyConfigurations)):
        if not TherapyConfigurations[i]["DeviceID"] in DeviceTimestamp.keys():
            DeviceTimestamp[TherapyConfigurations[i]["DeviceID"]] = list()

    ExistingTimestamp = list()
    for deviceID in DeviceTimestamp.keys():
        for i in range(len(TherapyConfigurations)):
            if TherapyConfigurations[i]["DeviceID"] == deviceID:
                TimeDifferences = np.array([np.abs(TherapyConfigurations[i]["TherapyDate"] - time) for time in ExistingTimestamp])
                Indexes = np.where(TimeDifferences < 3600*24)[0]
                if len(Indexes > 0):
                    TherapyConfigurations[i]["TherapyDate"] = ExistingTimestamp[Indexes[0]]
                else:
                    ExistingTimestamp.append(TherapyConfigurations[i]["TherapyDate"])

                if not TherapyConfigurations[i]["TherapyDate"] in DeviceTimestamp[deviceID]:
                    DeviceTimestamp[deviceID].append(TherapyConfigurations[i]["TherapyDate"])

    for deviceID in DeviceTimestamp.keys():
        for nConfig in range(len(DeviceTimestamp[deviceID])):
            if nConfig == 0:
                lastMeasuredTimestamp = 0
            else:
                lastMeasuredTimestamp = DeviceTimestamp[deviceID][nConfig-1]

            TherapyDutyPercent = dict()
            for i in range(len(TherapyChangeLog)):
                if str(TherapyChangeLog[i]["device"]) == deviceID:
                    for k in range(len(TherapyChangeLog[i]["date_of_change"])):
                        if lastMeasuredTimestamp < DeviceTimestamp[deviceID][nConfig]:
                            if k > 0:
                                if TherapyChangeLog[i]["previous_group"][k] == TherapyChangeLog[i]["new_group"][k-1] or TherapyChangeLog[i]["previous_group"][k] == -1:
                                    if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > lastMeasuredTimestamp:
                                        if not TherapyChangeLog[i]["previous_group"][k] in TherapyDutyPercent.keys():
                                            TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] = 0
                                        if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > DeviceTimestamp[deviceID][nConfig]:
                                            TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (DeviceTimestamp[deviceID][nConfig]-lastMeasuredTimestamp)
                                            lastMeasuredTimestamp = DeviceTimestamp[deviceID][nConfig]
                                        else:
                                            TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (TherapyChangeLog[i]["date_of_change"][k]/1000000000-lastMeasuredTimestamp)
                                            lastMeasuredTimestamp = TherapyChangeLog[i]["date_of_change"][k]/1000000000
                            else:
                                if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > lastMeasuredTimestamp:
                                    if not TherapyChangeLog[i]["previous_group"][k] in TherapyDutyPercent.keys():
                                        TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] = 0
                                    if TherapyChangeLog[i]["date_of_change"][k]/1000000000 > DeviceTimestamp[deviceID][nConfig]:
                                        TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (DeviceTimestamp[deviceID][nConfig]-lastMeasuredTimestamp)
                                        lastMeasuredTimestamp = DeviceTimestamp[deviceID][nConfig]
                                    else:
                                        TherapyDutyPercent[TherapyChangeLog[i]["previous_group"][k]] += (TherapyChangeLog[i]["date_of_change"][k]/1000000000-lastMeasuredTimestamp)
                                        lastMeasuredTimestamp = TherapyChangeLog[i]["date_of_change"][k]/1000000000

            for i in range(len(TherapyConfigurations)):
                if TherapyConfigurations[i]["DeviceID"] == deviceID and TherapyConfigurations[i]["TherapyDate"] == DeviceTimestamp[deviceID][nConfig]:
                    TherapyConfigurations[i]["TherapyDutyPercent"] = TherapyDutyPercent
            print(TherapyDutyPercent)
    for nConfig in range(len(TherapyConfigurations)):
        therapy = TherapyConfigurations[nConfig]
        if not int(therapy["TherapyDate"]) in TherapyData.keys():
            TherapyData[int(therapy["TherapyDate"])] = list()
        therapy["Overview"] = dict()
        totalHours = np.sum([therapy["TherapyDutyPercent"][key] for key in therapy["TherapyDutyPercent"].keys()])
        if not therapy["Therapy"]["GroupId"] in therapy["TherapyDutyPercent"].keys():
            therapy["Overview"]["DutyPercent"] = "(0%)"
        else:
            therapy["Overview"]["DutyPercent"] = f"({therapy['TherapyDutyPercent'][therapy['Therapy']['GroupId']]/totalHours*100:.2f}%)"

        therapy["Overview"]["GroupName"] = therapy["Therapy"]["GroupId"].replace("GroupIdDef.GROUP_","Group ")
        therapy["Overview"]["TherapyLogID"] = therapy["LogID"]
        therapy["Overview"]["TherapyType"] = therapy["TherapyType"]
        therapy["Overview"]["TherapyUsage"] = 0

        therapy["Overview"]["Frequency"] = ""
        therapy["Overview"]["Amplitude"] = ""
        therapy["Overview"]["PulseWidth"] = ""
        therapy["Overview"]["Contacts"] = ""
        therapy["Overview"]["BrainSense"] = ""
        for hemisphere in ["LeftHemisphere","RightHemisphere"]:
            if hemisphere in therapy["Therapy"].keys():
                if hemisphere == "LeftHemisphere":
                    symbol = '<div class="d-flex align-items-center"><span class="badge badge-primary">L</span>'
                else:
                    symbol = '<div class="d-flex align-items-center"><span class="badge badge-warning">R</span>'

                if therapy["Therapy"][hemisphere]["Mode"] == "Interleaving":
                    for i in range(len(therapy['Therapy'][hemisphere]['Frequency'])):
                        therapy["Overview"]["Frequency"] += symbol + '<h6 class="text-sm mb-0">' + f"{therapy['Therapy'][hemisphere]['Frequency'][i]} Hz" + '</h6></div>'
                    for i in range(len(therapy['Therapy'][hemisphere]['Amplitude'])):
                        therapy["Overview"]["Amplitude"] += symbol + '<h6 class="text-sm mb-0">' + f"{therapy['Therapy'][hemisphere]['Amplitude'][i]} mA" + '</h6></div>'
                    for i in range(len(therapy['Therapy'][hemisphere]['PulseWidth'])):
                        therapy["Overview"]["PulseWidth"] += symbol + '<h6 class="text-sm mb-0">' + f"{therapy['Therapy'][hemisphere]['PulseWidth'][i]} μS" + '</h6></div>'
                    for i in range(len(therapy['Therapy'][hemisphere]['Channel'])):
                        therapy["Overview"]["Contacts"] += '<div class="d-flex align-items-center">'
                        for contact in therapy['Therapy'][hemisphere]['Channel'][i]:
                            if contact["ElectrodeStateResult"] == "ElectrodeStateDef.Negative":
                                ContactPolarity = '<span class="text-md badge badge-info">'
                                ContactSign = "-"
                            elif contact["ElectrodeStateResult"] == "ElectrodeStateDef.Positive":
                                ContactPolarity = '<span class="text-md badge badge-danger">'
                                ContactSign = "+"
                            else:
                                ContactPolarity = '<span class="text-md badge badge-success">'
                                ContactSign = ""
                            ContactName, ContactID = Percept.reformatElectrodeDef(contact["Electrode"])
                            if not ContactName == "CAN" or len(therapy['Therapy'][hemisphere]['Channel']) == 2:
                                therapy["Overview"]["Contacts"] += ContactPolarity + ContactName.replace("E","") + ContactSign + '</span>'
                        therapy["Overview"]["Contacts"] += '</div>'
                else:
                    if therapy["Therapy"][hemisphere]["Mode"] == "BrainSense":
                        therapy["Overview"]["BrainSense"] += symbol + '<h6 class="text-sm mb-0">' + f"{therapy['Therapy'][hemisphere]['SensingSetup']['FrequencyInHertz']} Hz" + '</h6></div>'
                    therapy["Overview"]["Frequency"] += symbol + '<h6 class="text-sm mb-0">' + f"{therapy['Therapy'][hemisphere]['Frequency']} Hz" + '</h6></div>'
                    therapy["Overview"]["Amplitude"] += symbol + '<h6 class="text-sm mb-0">' + f"{therapy['Therapy'][hemisphere]['Amplitude']} mA" + '</h6></div>'
                    therapy["Overview"]["PulseWidth"] += symbol + '<h6 class="text-sm mb-0">' + f"{therapy['Therapy'][hemisphere]['PulseWidth']} μS" + '</h6></div>'
                    therapy["Overview"]["Contacts"] += '<div class="d-flex align-items-center">'
                    for contact in therapy['Therapy'][hemisphere]['Channel']:
                        if contact["ElectrodeStateResult"] == "ElectrodeStateDef.Negative":
                            ContactPolarity = '<span class="text-md badge badge-info">'
                            ContactSign = "-"
                        elif contact["ElectrodeStateResult"] == "ElectrodeStateDef.Positive":
                            ContactPolarity = '<span class="text-md badge badge-danger">'
                            ContactSign = "+"
                        else:
                            ContactPolarity = '<span class="text-md badge badge-success">'
                            ContactSign = ""
                        ContactName, ContactID = Percept.reformatElectrodeDef(contact["Electrode"])
                        if not ContactName == "CAN" or len(therapy['Therapy'][hemisphere]['Channel']) == 2:
                            therapy["Overview"]["Contacts"] += ContactPolarity + ContactName.replace("E","") + ContactSign + '</span>'
                    therapy["Overview"]["Contacts"] += '</div>'

        TherapyData[int(therapy["TherapyDate"])].append(therapy)

    for key in TherapyData.keys():
        TherapyData[key] = sorted(TherapyData[key], key=lambda therapy: therapy["Overview"]["GroupName"])
        if resolveConflicts:
            existList = list(); i = 0;
            while i < len(TherapyData[key]):
                if not (TherapyData[key][i]["Overview"]["GroupName"] + TherapyData[key][i]["Device"]) in existList and not TherapyData[key][i]["Overview"]["Frequency"] == "":
                    existList.append(TherapyData[key][i]["Overview"]["GroupName"] + TherapyData[key][i]["Device"])
                    i += 1
                else:
                    del(TherapyData[key][i])

    return TherapyData
