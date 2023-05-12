# -*- coding: utf-8 -*-
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
Python Module for BrainSense Surveys
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(os.environ.get("PYTHON_UTILITY"))

from datetime import datetime
import pytz
import numpy as np
from scipy import signal

from Backend import models
from modules import Database

from decoder import Percept
from utility import SignalProcessingUtility as SPU

key = os.environ.get('ENCRYPTION_KEY')

def saveBrainSenseSurvey(deviceID, surveyList, sourceFile):
    """ Save BrainSense Survey Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      surveyList: Array of BrainSense Survey structures extracted from Medtronic JSON file.
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """

    NewRecordingFound = False
    for survey in surveyList:
        SurveyDate = datetime.fromtimestamp(Percept.getTimestamp(survey["FirstPacketDateTime"]), tz=pytz.utc)
        recording_info = {"Channel": survey["Channel"]}
        if not models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="BrainSenseSurvey", recording_date=SurveyDate, recording_info=recording_info).exists():
            recording = models.BrainSenseRecording(device_deidentified_id=deviceID, recording_date=SurveyDate, recording_type="BrainSenseSurvey", recording_info=recording_info, source_file=sourceFile)
            filename = Database.saveSourceFiles(survey, "BrainSenseSurvey", survey["Channel"], recording.recording_id, recording.device_deidentified_id)
            recording.recording_datapointer = filename
            recording.save()
            NewRecordingFound = True
    return NewRecordingFound

def querySurveyResults(user, patientUniqueID, authority):
    """ Extract all BrainSense Survey recordings and process for power spectrum.

    This pipeline will process all BrainSense Survey recordings recorded from one patient and output the average power spectrum. 

    Args:
      user: BRAVO Platform User object. 
      patientUniqueID: Deidentified patient ID as referenced in SQL Database. 
      authority: User permission structure indicating the type of access the user has.

    Returns:
      List of processed BrainSense Surveys without raw time-domain data. 
    """

    BrainSenseData = list()
    if not authority["Permission"]:
        return BrainSenseData

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        allSurveys = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type="BrainSenseSurvey").order_by("-recording_date").all()
        if len(allSurveys) > 0:
            leads = device.device_lead_configurations

        for recording in allSurveys:
            if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
                continue

            survey = Database.loadSourceDataPointer(recording.recording_datapointer)
            if not "Spectrum" in survey.keys():
                survey = processBrainSenseSurvey(survey)
                Database.saveSourceFiles(survey, "BrainSenseSurvey", survey["Channel"], recording.recording_id, recording.device_deidentified_id)
            data = dict()
            if device.device_name == "":
                data["DeviceName"] = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)
            else:
                data["DeviceName"] = device.device_name
            data["Timestamp"] = recording.recording_date.timestamp()
            data["Channel"], data["Hemisphere"] = Percept.reformatChannelName(recording.recording_info["Channel"])
            for lead in leads:
                if lead["TargetLocation"].startswith(data["Hemisphere"]):
                    data["Hemisphere"] = lead["TargetLocation"]
                    break
            data["Frequency"] = survey["Spectrum"]["Frequency"]
            data["MeanPower"] = np.mean(survey["Spectrum"]["Power"],axis=1).tolist()
            data["StdPower"] = SPU.stderr(survey["Spectrum"]["Power"],axis=1).tolist()
            BrainSenseData.append(data)
    return BrainSenseData

def processBrainSenseSurvey(survey, method="spectrogram"):
    """ Calculate BrainSense Survey Power Spectrum.

    The pipeline will filter the raw BrainSense Survey with a zero-phase 5th-order Butterworth filter between 1-100Hz.
    Then power spectrum is calculated using short-time Fourier Transform with 0.5Hz frequency resolution using 1.0 second window and 500ms overlap. 
    Zero-padding when neccessary to increase frequency resolution.

    Args:
      survey: BrainSense Survey raw object. 

    Returns:
      List of processed BrainSense Surveys without raw time-domain data. 
    """

    [b,a] = signal.butter(5, np.array([1,100])*2/250, 'bp', output='ba')
    filtered = signal.filtfilt(b, a, survey["Data"])
    survey["Spectrum"] = SPU.defaultSpectrogram(filtered, window=1.0, overlap=0.5,frequency_resolution=0.5, fs=250)
    return survey
