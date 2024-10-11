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

import os
from datetime import datetime
import copy
import numpy as np
import pandas as pd

from Backend import models
from decoder import Percept
from neomodel import Q

key = os.environ.get('ENCRYPTION_KEY')

def matchAttribute(obj, item):
    for key in item.keys():
        if not obj.__getattribute__(key) == item[key]:
            return False 
    return True
    
def saveTherapyEvents(therapyList):
    """ Save Therapy Change History in Database

    Args:
      participant: Participant node object. Therapy is direct child node of Participant
      device: Device Object that the therapy is delivered from.
      therapyList: Array of Therapy Configuration structures extracted from Medtronic JSON file.

    Returns:
      Array of Newly Created Therapy History
    """

    NewTherapies = list()
    for therapy in therapyList:
        if "TherapyStatus" in therapy.keys():
            event = models.TherapyModification(name="TherapyStatus", type="TherapyStatus", date=therapy["DateTime"].timestamp())
            event.new_group = "ON" if therapy["TherapyStatus"] else "OFF"
            event.old_group = "OFF" if therapy["TherapyStatus"] else "ON"
            event.save()
            NewTherapies.append(event)

    for therapy in therapyList:
        if not "TherapyStatus" in therapy.keys():
            event = models.TherapyModification(name="TherapyChangeGroup", type="TherapyChangeGroup", date=therapy["DateTime"].timestamp(),
                                                new_group=therapy["NewGroupId"], old_group=therapy["OldGroupId"]).save()
            NewTherapies.append(event)

    return NewTherapies

def saveTherapySettings(device, therapyList, sessionDate, type):
    """ Save Therapy Settings in Database

    Args:
      participant: Participant node object. Therapy is direct child node of Participant
      device: Device Object that the therapy is delivered from.
      therapyList: Array of Therapy Configuration structures extracted from Medtronic JSON file.
      sessionDate: DateTime object indicating when the therapy configuration is saved.
      type: One of three data types: ["Past Therapy","Pre-visit Therapy","Post-visit Therapy"].

    Returns:
      Array of Newly Created Therapy Settings
    """

    NewTherapies = []
    for therapy in therapyList:
        for hemisphere in ["LeftHemisphere", "RightHemisphere"]:
            if hemisphere in therapy.keys():
                if therapy[hemisphere]["Mode"] == "Adaptive":
                    therapyObject = models.AdaptiveTherapy(
                        name= "Left Channel DBS Setting" if hemisphere == "LeftHemisphere" else "Right Channel DBS Setting",
                        group_name= therapy["GroupId"] if therapy["GroupName"] == "" else therapy["GroupName"],
                        group_id= therapy["GroupId"],
                        type= type,
                        date= sessionDate,
                    )
                    
                else:
                    therapyObject = models.ElectricalTherapy(
                        name= "Left Channel DBS Setting" if hemisphere == "LeftHemisphere" else "Right Channel DBS Setting",
                        group_name= therapy["GroupId"] if therapy["GroupName"] == "" else therapy["GroupName"],
                        group_id= therapy["GroupId"],
                        type= type,
                        date= sessionDate,
                    )
                
                if len(therapyObject.settings) > 0:
                    continue 
                
                therapyObject.stimulation_type = therapy[hemisphere]["Mode"]
                therapyObject.save()
                NewTherapies.append(therapyObject)

                if therapyObject.stimulation_type == "Interleaving":
                    for i in range(len(therapy[hemisphere]["Frequency"])):
                        stimulationSetting = models.ElectricalStimulation(amplitude_unit=therapy[hemisphere]["Unit"][i],
                                                                        pulsewidth=therapy[hemisphere]["PulseWidth"][i],
                                                                        pulsewidth_unit="uS",
                                                                        frequency=therapy[hemisphere]["Frequency"][i])
                        
                        contact = []
                        amplitude = []
                        return_contact = []
                        for channel in therapy[hemisphere]["Channel"][i]:
                            ChannelName, ChannelIndex = Percept.reformatElectrodeDef(channel["Electrode"])
                            if channel["ElectrodeStateResult"] == "ElectrodeStateDef.Positive":
                                stimulationSetting.return_contact = ChannelIndex
                                return_contact.append(ChannelIndex)
                            elif channel["ElectrodeStateResult"] == "ElectrodeStateDef.Negative":
                                contact.append(ChannelIndex)
                                if "ElectrodeAmplitudeInMilliAmps" in channel.keys():
                                    amplitude.append(channel["ElectrodeAmplitudeInMilliAmps"])
                                else:
                                    amplitude.append(therapy[hemisphere]["Amplitude"][i])
                        
                        stimulationSetting.amplitude = amplitude
                        stimulationSetting.contact = contact
                        stimulationSetting.return_contact = return_contact
                        
                        try:
                            if therapy["GroupSettings"]["Cycling"]["Enabled"]:
                                stimulationSetting.cycling_period = therapy["GroupSettings"]["Cycling"]["OnDurationInMilliSeconds"] + therapy["GroupSettings"]["Cycling"]["OffDurationInMilliSeconds"]
                                stimulationSetting.cycling = therapy["GroupSettings"]["Cycling"]["OnDurationInMilliSeconds"] / stimulationSetting.cycling_period
                            else:
                                stimulationSetting.cycling = 1
                        except:
                            pass

                        stimulationSetting.save()
                        therapyObject.settings.connect(stimulationSetting)
                        for electrode in device.electrodes:
                            if hemisphere.startswith(electrode.name.split(" ")[0]):
                                stimulationSetting.electrode.connect(electrode)
                                break

                elif therapyObject.stimulation_type == "Standard" or therapyObject.stimulation_type == "BrainSense" or therapyObject.stimulation_type == "Adaptive":
                    stimulationSetting = models.ElectricalStimulation(amplitude_unit=therapy[hemisphere]["Unit"],
                                                                    pulsewidth=therapy[hemisphere]["PulseWidth"],
                                                                    pulsewidth_unit="uS",
                                                                    frequency=therapy[hemisphere]["Frequency"])
                    
                    contact = []
                    return_contact = []
                    amplitude = []
                    for channel in therapy[hemisphere]["Channel"]:
                        ChannelName, ChannelIndex = Percept.reformatElectrodeDef(channel["Electrode"])
                        if channel["ElectrodeStateResult"] == "ElectrodeStateDef.Positive":
                            return_contact.append(ChannelIndex)
                        elif channel["ElectrodeStateResult"] == "ElectrodeStateDef.Negative":
                            contact.append(ChannelIndex)
                            if "ElectrodeAmplitudeInMilliAmps" in channel.keys():
                                amplitude.append(channel["ElectrodeAmplitudeInMilliAmps"])
                            else:
                                amplitude.append(therapy[hemisphere]["Amplitude"])
                            
                    stimulationSetting.amplitude = amplitude
                    stimulationSetting.contact = contact
                    stimulationSetting.return_contact = return_contact

                    try:
                        if therapy["GroupSettings"]["Cycling"]["Enabled"]:
                            stimulationSetting.cycling_period = therapy["GroupSettings"]["Cycling"]["OnDurationInMilliSeconds"] + therapy["GroupSettings"]["Cycling"]["OffDurationInMilliSeconds"]
                            stimulationSetting.cycling = therapy["GroupSettings"]["Cycling"]["OnDurationInMilliSeconds"] / stimulationSetting.cycling_period
                        else:
                            stimulationSetting.cycling = 1
                    except:
                        pass

                    stimulationSetting.save()
                    therapyObject.settings.connect(stimulationSetting)
                    for electrode in device.electrodes:
                        if hemisphere.startswith(electrode.name.split(" ")[0]):
                            stimulationSetting.electrode.connect(electrode)
                            break

    return NewTherapies

def queryTherapyHistory(participant):
    """ Extract all therapy change logs in Percept related to a specific participant.

    This pipeline go through all therapy change logs and extract the time at which a group changes is made. 
    The pipeline will also extract the actual setting that the device is on before and after changes.

    Args:
      user: BRAVO Platform User object. 
      participant: Participant object (for uid). 

    Returns:
      List of therapy group history ordered by time. 
    """

    TherapyChangeData = list()
    TherapyChangeHistory = sorted(models.filterNodesByType(participant.events, models.TherapyModification, Q(type="TherapyChangeGroup")), key=lambda item: item.date)
    TherapyHistoryObjs = sorted(models.filterNodesByType(participant.therapies, models.ElectricalTherapy), key=lambda item: item.date)
    for device in participant.devices:
        DeviceTherapyChange = [item for item in TherapyChangeHistory if item.device == device.uid]
        DeviceTherapyHistory = [item for item in TherapyHistoryObjs if item.device == device.uid]

        VisitTimestamps = np.unique([item.date for item in DeviceTherapyHistory])
        for i in range(len(VisitTimestamps)):
            SessionTime = VisitTimestamps[i]
            for j in range(1, len(DeviceTherapyChange)):
                if DeviceTherapyChange[j].date > SessionTime:
                    DeviceTherapyChange.insert(j, models.TherapyModification(date=SessionTime, old_group=DeviceTherapyChange[j-1].new_group,
                                                                             new_group= DeviceTherapyChange[j-1].new_group))
                    break
        
        TherapyChangeData.append({
            "device": device.getDeviceName(),
            "device_inheritance": device.implanted_location,
            # 5 Seconds Adjustment Due to TherapyChangeDate is actually logged slightly later than when the Group is actually changed.
            "date_of_change": [item.date-5 for item in DeviceTherapyChange],
            "new_group": [item.new_group.replace("GroupIdDef.","").replace("_"," ").title() for item in DeviceTherapyChange],
            "old_group": [item.old_group.replace("GroupIdDef.","").replace("_"," ").title() for item in DeviceTherapyChange],
            "therapy": getTherapyDetails(DeviceTherapyHistory),
            "electrodes": [electrode.__properties__ for electrode in device.electrodes]
        })
    return TherapyChangeData

def getTherapyDetails(TherapyHistory):
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

    therapyDetails = []
    for therapy in TherapyHistory:
        therapyDetail = {"name": therapy.group_name, "mode": therapy.stimulation_type, 
                           "date": therapy.date, "type": therapy.type, 
                           "channel": therapy.name.replace(" DBS Setting",""),
                           "settings": []}
        for setting in therapy.settings:
            stimSetting = setting.__properties__
            therapyDetail["settings"].append(stimSetting)
        therapyDetails.append(therapyDetail)
    return therapyDetails
