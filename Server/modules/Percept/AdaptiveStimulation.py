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
Adaptive DBS Processing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(os.environ.get("PYTHON_UTILITY"))

import json
import uuid
import numpy as np
import copy
from shutil import copyfile, rmtree
from datetime import datetime, date, timedelta
import dateutil, pytz
import pickle, joblib
import pandas as pd

from scipy import signal, stats, optimize, interpolate

from decoder import Percept
from utility import SignalProcessingUtility as SPU
from utility.PythonUtility import *

from Backend import models
from modules import Database

key = os.environ.get('ENCRYPTION_KEY')

def processAdaptiveDutyCycle(ChronicData, timezoneOffset):
    for i in range(len(ChronicData)):
        if ChronicData[i]["Hemisphere"].startswith("Left"):
            hemisphere = "LeftHemisphere"
        else:
            hemisphere = "RightHemisphere"

        ChronicData[i]["DutyCycle"] = []

        for j in range(len(ChronicData[i]["Therapy"])):
            ChronicData[i]["DutyCycle"].append(list())
            if "AdaptiveSetup" in ChronicData[i]["Therapy"][j][hemisphere].keys():
                if not ChronicData[i]["Therapy"][j][hemisphere]["AdaptiveSetup"]["Status"] == "ADBSStatusDef.NOT_CONFIGURED":
                    if "AmplitudeThreshold" in ChronicData[i]["Therapy"][j][hemisphere].keys():
                        AmplitudeRange = ChronicData[i]["Therapy"][j][hemisphere]["AmplitudeThreshold"]
                        if (AmplitudeRange[1]-AmplitudeRange[0]) == 0:
                            if AmplitudeRange[1] == 0:
                                PercentRange = np.ones(len(ChronicData[i]["Amplitude"][j])) * 100
                            else:
                                PercentRange = np.zeros(len(ChronicData[i]["Amplitude"][j].shape))
                        else:
                            PercentRange = (np.array(ChronicData[i]["Amplitude"][j]) - AmplitudeRange[0]) / (AmplitudeRange[1]-AmplitudeRange[0]) * 100
                        PercentRange = SPU.smooth(PercentRange, 6)
                        ChronicData[i]["DutyCycle"][j] = PercentRange.tolist()

    return ChronicData