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
Python Module for Baseline Surveys
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
    """ Save Survey Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      surveyList: Array of Survey structures extracted from JSON file.
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

        if not models.NeuralActivityRecording.objects.filter(device_deidentified_id=deviceID, recording_type="BrainSenseSurvey", recording_date=date, recording_info=recording_info).exists():
            recording = models.NeuralActivityRecording(device_deidentified_id=deviceID, recording_date=date, recording_type="BrainSenseSurvey", recording_info=recording_info, source_file=sourceFile)
            filename = Database.saveSourceFiles(Recording, "BrainSenseSurvey", "Combined", recording.recording_id, recording.device_deidentified_id)
            recording.recording_datapointer = filename
            recording.save()
            NewRecordingFound = True
            
    return NewRecordingFound

def querySurveyResults(user, patientUniqueID, options, requestRaw, authority):
    """ Extract all Baseline Survey recordings and process for power spectrum.

    This pipeline will process all Baseline Survey recordings recorded from one patient and output the average power spectrum. 

    Args:
      user: BRAVO Platform User object. 
      patientUniqueID: Deidentified patient ID as referenced in SQL Database. 
      options: BaselineSurvey Configuration dictionary
      authority: User permission structure indicating the type of access the user has.

    Returns:
      List of processed Baseline Surveys without raw time-domain data. 
    """

    BrainSenseData = list()
    if not authority["Permission"]:
        return BrainSenseData

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        allSurveys = models.NeuralActivityRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type="BrainSenseSurvey").order_by("-recording_date").all()
        if len(allSurveys) > 0:
            leads = device.device_lead_configurations

        for recording in allSurveys:
            if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
                continue

            survey = Database.loadSourceDataPointer(recording.recording_datapointer)
            if not "Descriptor" in survey.keys():
                survey["Descriptor"] = {}
                
            if not "PSDMethod" in survey["Descriptor"].keys():
                survey = processBrainSenseSurvey(survey, options["PSDMethod"]["value"])
                Database.saveSourceFiles(survey, "BrainSenseSurvey", "Combined", recording.recording_id, recording.device_deidentified_id)
            
            if not options["PSDMethod"]["value"] == survey["Descriptor"]["PSDMethod"]:
                survey = processBrainSenseSurvey(survey, options["PSDMethod"]["value"])
                Database.saveSourceFiles(survey, "BrainSenseSurvey", "Combined", recording.recording_id, recording.device_deidentified_id)

            # Monopolar Estimation

            MonopolarEstimation = []
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
                        data["CustomName"] = lead["CustomName"] if lead["CustomName"] else lead["TargetLocation"]
                        break
                
                if requestRaw:
                    data["Raw"] = survey["Data"][:,i].tolist()
                else:
                    if options["PSDMethod"]["value"] == "Estimated Medtronic PSD":
                        data["Frequency"] = survey["Spectrum"][i]["Frequency"]
                        data["MeanPower"] = survey["Spectrum"][i]["Power"].tolist()
                        data["StdPower"] = survey["Spectrum"][i]["StdErr"].tolist()
                    elif options["PSDMethod"]["value"] == "Short-time Fourier Transform":
                        data["Frequency"] = survey["Spectrum"][i]["Frequency"]
                        data["MeanPower"] = np.mean(survey["Spectrum"][i]["Power"],axis=1).tolist()
                        data["StdPower"] = SPU.stderr(survey["Spectrum"][i]["Power"],axis=1).tolist()
                    elif options["PSDMethod"]["value"] == "Autoregressive Model":
                        data["Frequency"] = survey["Spectrum"][i]["Frequency"]
                        data["MeanPower"] = np.mean(survey["Spectrum"][i]["Power"],axis=1).tolist()
                        data["StdPower"] = SPU.stderr(survey["Spectrum"][i]["Power"],axis=1).tolist()
                    elif options["PSDMethod"]["value"] == "Welch's Periodogram":
                        data["Frequency"] = survey["Spectrum"][i]["Frequency"]
                        data["MeanPower"] = np.mean(survey["Spectrum"][i]["Power"],axis=1).tolist()
                        data["StdPower"] = SPU.stderr(survey["Spectrum"][i]["Power"],axis=1).tolist()
                    else:
                        data["Frequency"] = survey["Spectrum"][i]["Frequency"]
                        data["MeanPower"] = np.mean(survey["Spectrum"][i]["Power"],axis=1).tolist()
                        data["StdPower"] = SPU.stderr(survey["Spectrum"][i]["Power"],axis=1).tolist()

                MonopolarEstimation.append(data)

            if options["MonopolarEstimation"]["value"] == "DETEC Algorithm (Strelow et. al., 2022)":
                for hemisphere in ["Left", "Right"]:
                    HemisphereCount = [MonopolarEstimation[i]["Hemisphere"] for i in range(len(MonopolarEstimation)) if MonopolarEstimation[i]["Hemisphere"].startswith(hemisphere)]
                    
                    for channel in [0,1,2,3]:
                        if len([i for i in HemisphereCount if not "." in HemisphereCount]) <= 3:
                            continue

                        data = dict()
                        data["Channel"] = [channel]
                        data["MeanPower"] = []
                        Estimator = 0
                        for i in range(len(MonopolarEstimation)):
                            if channel in MonopolarEstimation[i]["Channel"] and MonopolarEstimation[i]["Hemisphere"].startswith(hemisphere):
                                if len(data["MeanPower"]) == 0:
                                    data["DeviceName"] = MonopolarEstimation[i]["DeviceName"]
                                    data["Timestamp"] = MonopolarEstimation[i]["Timestamp"]
                                    data["Hemisphere"] = MonopolarEstimation[i]["Hemisphere"]
                                    data["CustomName"] = MonopolarEstimation[i]["CustomName"]
                                    data["Frequency"] = MonopolarEstimation[i]["Frequency"]
                                    data["MeanPower"] = np.array(MonopolarEstimation[i]["MeanPower"]) / np.diff(MonopolarEstimation[i]["Channel"])
                                    data["StdPower"] = np.zeros(len(MonopolarEstimation[i]["Frequency"]))
                                else:
                                    data["MeanPower"] += np.array(MonopolarEstimation[i]["MeanPower"]) / np.diff(MonopolarEstimation[i]["Channel"])
                                Estimator += (1/np.diff(MonopolarEstimation[i]["Channel"]))
                        
                        if Estimator > 0:
                            data["MeanPower"] /= Estimator
                            BrainSenseData.append(data)
  
                    for channel in [1.1,1.2,1.3,2.1,2.2,2.3]:
                        if len([i for i in HemisphereCount if "." in HemisphereCount]) <= 3:
                            continue

                        data = dict()
                        data["Channel"] = [channel]
                        data["MeanPower"] = []
                        Estimator = 0
                        for i in range(len(MonopolarEstimation)):
                            if channel in MonopolarEstimation[i]["Channel"] and MonopolarEstimation[i]["Hemisphere"].startswith(hemisphere):
                                if len(data["MeanPower"]) == 0:
                                    data["DeviceName"] = MonopolarEstimation[i]["DeviceName"]
                                    data["Timestamp"] = MonopolarEstimation[i]["Timestamp"]
                                    data["Hemisphere"] = MonopolarEstimation[i]["Hemisphere"]
                                    data["CustomName"] = MonopolarEstimation[i]["CustomName"]
                                    data["Frequency"] = MonopolarEstimation[i]["Frequency"]
                                    data["MeanPower"] = np.array(MonopolarEstimation[i]["MeanPower"]) / np.diff(MonopolarEstimation[i]["Channel"])
                                    data["StdPower"] = np.zeros(len(MonopolarEstimation[i]["Frequency"]))
                                else:
                                    data["MeanPower"] += np.array(MonopolarEstimation[i]["MeanPower"]) / np.diff(MonopolarEstimation[i]["Channel"])
                                Estimator += (1/np.diff(MonopolarEstimation[i]["Channel"]))
                        
                        if Estimator > 0:
                            data["MeanPower"] /= Estimator
                            BrainSenseData.append(data)
            else:
                BrainSenseData.extend(MonopolarEstimation)
    return BrainSenseData

def processBrainSenseSurvey(survey, method="Short-time Fourier Transform"):
    """ Calculate Baseline Survey Power Spectrum.

    The pipeline will filter the raw Baseline Survey with a zero-phase 5th-order Butterworth filter between 1-100Hz.
    Then power spectrum is calculated using short-time Fourier Transform with 0.5Hz frequency resolution using 1.0 second window and 500ms overlap. 
    Zero-padding when neccessary to increase frequency resolution.

    Args:
      survey: Baseline Survey raw object. 

    Returns:
      List of processed Baseline Surveys without raw time-domain data. 
    """

    [b,a] = signal.butter(5, np.array([1,100])*2/250, 'bp', output='ba')

    if method == "Short-time Fourier Transform":
        survey["Spectrum"] = []
        survey["Descriptor"]["PSDMethod"] = method
        for i in range(len(survey["ChannelNames"])):
            filtered = signal.filtfilt(b, a, survey["Data"][:,i])
            survey["Spectrum"].append(SPU.defaultSpectrogram(filtered, window=1.0, overlap=0.5, frequency_resolution=0.5, fs=survey["SamplingRate"]))
        return survey
    
    elif method == "Welch's Periodogram":
        survey["Spectrum"] = []
        survey["Descriptor"]["PSDMethod"] = method
        for i in range(len(survey["ChannelNames"])):
            filtered = signal.filtfilt(b, a, survey["Data"][:,i])
            survey["Spectrum"].append(SPU.welchSpectrogram(filtered, window=10.0, overlap=7.5, frequency_resolution=0.5, fs=survey["SamplingRate"]))
        return survey

    elif method == "Autoregressive Model":
        survey["Spectrum"] = []
        survey["Descriptor"]["PSDMethod"] = method
        for i in range(len(survey["ChannelNames"])):
            filtered = signal.filtfilt(b, a, survey["Data"][:,i])
            survey["Spectrum"].append(SPU.autoregressiveSpectrogram(filtered, window=5.0, overlap=2.5, frequency_resolution=0.5, fs=survey["SamplingRate"], order=30))
        return survey

    elif method == "Estimated Medtronic PSD":
        survey["Spectrum"] = []
        survey["Descriptor"]["PSDMethod"] = method
        for i in range(len(survey["ChannelNames"])):
            filtered = signal.filtfilt(b, a, survey["Data"][:,i])
            survey["Spectrum"].append(SPU.MedtronicPSD(filtered))
        return survey
    