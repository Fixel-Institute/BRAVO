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
    
def queryTherapyHistory(participant):
    """ Extract all therapy change logs in Percept related to a specific participant.

    This pipeline go through all therapy change logs and extract the time at which a group changes is made. 
    The pipeline will also extract the actual setting that the device is on before and after changes.

    Args:
    
    Returns:
      List of therapy group history ordered by time. 
    """

    TherapyModifications = []
    TherapyHistories = []
    TherapyDevices = {}
    for experiment in participant.experiments:
        for source_file in experiment.source_files:
            DeviceTherapyModification = [event.getInfo() for event in source_file.events if type(event) == models.TherapyModification]
            DeviceIdentifier = source_file.device.get_or_none()
            if DeviceIdentifier:
                DBSDevice = DeviceIdentifier.getInfo()
                TherapyDevices[DBSDevice["uid"]] = DBSDevice
                for i in range(len(DeviceTherapyModification)):
                    DeviceTherapyModification[i]["device"] = DBSDevice["uid"]
            TherapyModifications.extend(DeviceTherapyModification)

            TherapyHistory = [therapy.getInfo() for therapy in source_file.therapies if type(therapy) == models.ElectricalTherapy and (therapy.type == "Post-visit Therapy" or therapy.type == "Pre-visit Therapy")]
            TherapyHistories.extend(TherapyHistory)
    
    TherapyHistories.sort(key=lambda x: x["Date"])
    TherapyConfigurations = {}
    for i in range(len(TherapyHistories)):
        if not str(TherapyHistories[i]["Date"]) in TherapyConfigurations.keys():
            TherapyConfigurations[str(TherapyHistories[i]["Date"])] = {"Pre-visit Therapy": [], "Post-visit Therapy": []}
        TherapyConfigurations[str(TherapyHistories[i]["Date"])][TherapyHistories[i]["Type"]].append(TherapyHistories[i])

    for key in TherapyConfigurations.keys():
        for subkey in TherapyConfigurations[key].keys():
            TherapyConfigurations[key][subkey].sort(key=lambda x: x["GroupId"])

    return {"TherapyModification": TherapyModifications, "TherapyDevices": TherapyDevices, "TherapyConfigurations": TherapyConfigurations}



