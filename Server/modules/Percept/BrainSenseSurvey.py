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

def saveBrainSenseSurvey(deviceID, streamList, sourceFile):
    """ Save BrainSense Survey Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      surveyList: Array of BrainSense Survey structures extracted from Medtronic JSON file.
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """

    NewRecordingFound = False
    StreamDates = list()
    for stream in streamList:
        StreamDates.append(datetime.fromtimestamp(stream["FirstPacketDateTime"], tz=pytz.utc))
    UniqueSessionDates = np.unique(StreamDates)

    for date in UniqueSessionDates:
        Recording = dict()
        Recording["SamplingRate"] = streamList[0]["SamplingRate"]

        StreamGroupIndexes = [datetime.fromtimestamp(stream["FirstPacketDateTime"], tz=pytz.utc) == date for stream in streamList]
        Recording["ChannelNames"] = [streamList[i]["Channel"] for i in range(len(streamList)) if StreamGroupIndexes[i]]
        
        RecordingSize = [len(streamList[i]["Data"]) for i in range(len(streamList)) if StreamGroupIndexes[i]]
        if len(np.unique(RecordingSize)) > 1:
            print("Inconsistent Recording Size for BrainSense Survey")
            maxSize = np.max(RecordingSize)
            Recording["Data"] = np.zeros((maxSize, len(RecordingSize)))
            Recording["Missing"] = np.ones((maxSize, len(RecordingSize)))
            n = 0
            for i in range(len(streamList)): 
                if StreamGroupIndexes[i]:
                    Recording["Data"][:RecordingSize[n], n] = streamList[i]["Data"]
                    Recording["Missing"][:RecordingSize[n], n] = streamList[i]["Missing"]
                    Recording["StartTime"] = date.timestamp()
                    n += 1
        else:
            Recording["Data"] = np.zeros((RecordingSize[0], len(RecordingSize)))
            Recording["Missing"] = np.ones((RecordingSize[0], len(RecordingSize)))
            n = 0
            for i in range(len(streamList)): 
                if StreamGroupIndexes[i]:
                    Recording["Data"][:, n] = streamList[i]["Data"]
                    Recording["Missing"][:, n] = streamList[i]["Missing"]
                    Recording["StartTime"] = date.timestamp()
                    n += 1
        
        if "PSD" in streamList[i].keys():
            Recording["Descriptor"] = {
                "MedtronicPSD": streamList[i]["PSD"]
            }
            
        Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
        recording_info = {"Channel": Recording["ChannelNames"]}

        if not models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="BrainSenseSurvey", recording_date=date, recording_info=recording_info).exists():
            recording = models.BrainSenseRecording(device_deidentified_id=deviceID, recording_date=date, recording_type="BrainSenseSurvey", recording_info=recording_info, source_file=sourceFile)
            filename = Database.saveSourceFiles(Recording, "BrainSenseSurvey", "Combined", recording.recording_id, recording.device_deidentified_id)
            recording.recording_datapointer = filename
            recording.save()
            NewRecordingFound = True
            
    return NewRecordingFound

def querySurveyResults(user, patientUniqueID, options, requestRaw, authority):
    """ Extract all BrainSense Survey recordings and process for power spectrum.

    This pipeline will process all BrainSense Survey recordings recorded from one patient and output the average power spectrum. 

    Args:
      user: BRAVO Platform User object. 
      patientUniqueID: Deidentified patient ID as referenced in SQL Database. 
      options: BrainSenseSurvey Configuration dictionary
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
                Database.saveSourceFiles(survey, "BrainSenseSurvey", "Combined", recording.recording_id, recording.device_deidentified_id)
            
            if not "MedtronicPSD" in survey.keys():
                survey = processBrainSenseSurvey(survey)
                Database.saveSourceFiles(survey, "BrainSenseSurvey", "Combined", recording.recording_id, recording.device_deidentified_id)
            
            for i in range(len(survey["ChannelNames"])):
                data = dict()
                if device.device_name == "":
                    data["DeviceName"] = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)
                else:
                    data["DeviceName"] = device.device_name
                data["Timestamp"] = recording.recording_date.timestamp()
                data["Channel"], data["Hemisphere"] = Percept.reformatChannelName(survey["ChannelNames"][i])
                for lead in leads:
                    if lead["TargetLocation"].startswith(data["Hemisphere"]):
                        data["Hemisphere"] = lead["TargetLocation"]
                        data["CustomName"] = lead["CustomName"]
                        break

                if requestRaw:
                    data["Raw"] = survey["Data"].tolist()
                else:
                    if options["PSDMethod"]["value"] == "Estimated Medtronic PSD":
                        data["Frequency"] = survey["MedtronicPSD"][i]["Frequency"]
                        data["MeanPower"] = survey["MedtronicPSD"][i]["Power"].tolist()
                        data["StdPower"] = survey["MedtronicPSD"][i]["StdErr"].tolist()
                    elif options["PSDMethod"]["value"] == "Short-time Fourier Transform":
                        data["Frequency"] = survey["Spectrum"][i]["Frequency"]
                        data["MeanPower"] = np.mean(survey["Spectrum"][i]["Power"],axis=1).tolist()
                        data["StdPower"] = SPU.stderr(survey["Spectrum"][i]["Power"],axis=1).tolist()
                    else:
                        data["Frequency"] = survey["Spectrum"][i]["Frequency"]
                        data["MeanPower"] = np.mean(survey["Spectrum"][i]["Power"],axis=1).tolist()
                        data["StdPower"] = SPU.stderr(survey["Spectrum"][i]["Power"],axis=1).tolist()

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
    survey["Spectrum"] = []
    survey["MedtronicPSD"] = []
    for i in range(len(survey["ChannelNames"])):
        filtered = signal.filtfilt(b, a, survey["Data"][:,i])
        survey["MedtronicPSD"].append(SPU.MedtronicPSD(filtered))
        survey["Spectrum"].append(SPU.defaultSpectrogram(filtered, window=1.0, overlap=0.5, frequency_resolution=0.5, fs=survey["SamplingRate"]))
    return survey