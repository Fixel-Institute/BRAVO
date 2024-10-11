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

def saveBrainSenseSurvey(participant, streamList, type):
    """ Save BrainSense Survey Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      surveyList: Array of BrainSense Survey structures extracted from Medtronic JSON file.
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """

    NewRecordings = []
    for stream in streamList:
        Recording = dict()
        Recording["SamplingRate"] = stream["SamplingRate"]
        Recording["ChannelNames"] = [stream["Channel"]]
        Recording["Data"] = stream["Data"]
        Recording["Missing"] = stream["Missing"]
        Recording["StartTime"] = stream["FirstPacketDateTime"]
        Recording["Descriptor"] = {}
        if "PSD" in stream.keys():
            Recording["Descriptor"]["MedtronicPSD"] = stream["PSD"]
        Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]

        recording = models.TimeSeriesRecording(type=type, date=Recording["StartTime"], 
                                                sampling_rate=Recording["SamplingRate"], duration=Recording["Duration"]).save()
        filename, hashed = Database.saveSourceFiles(Recording, type, recording.uid, participant.uid)
        recording.hashed = hashed
        recording.data_pointer = filename
        recording.channel_names = Recording["ChannelNames"]
        recording.save()
        NewRecordings.append(recording)

    return NewRecordings

def querySurveyResults(participant, options={}, requestRaw=False):
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
    BrainSenseData = []
    for device in participant.devices:
        allSurveys = device.recordings.filter(type="BrainSenseSurvey").all()
        if len(allSurveys) > 0:
            leads = [item.__properties__ for item in device.electrodes]

        for recording in allSurveys:
            survey = Database.loadSourceDataPointer(recording.data_pointer)
            if not "Spectrum" in survey.keys():
                survey = processBrainSenseSurvey(survey, options)
                Database.saveSourceFiles(survey, "BrainSenseSurvey", recording.uid, participant.uid)
            
            # Monopolar Estimation
            if not options["MonopolarEstimation"]["value"] == "No Estimation":
                if not "Monopolar" in survey.keys():
                    survey = processBrainSenseSurvey(survey, options) 
                elif not survey["Monopolar"] == options["MonopolarEstimation"]["value"]:
                    survey = processBrainSenseSurvey(survey, options) 
            else:
                if "Monopolar" in survey.keys():
                    survey = processBrainSenseSurvey(survey, options)

            MonopolarEstimation = []
            for i in range(len(survey["ChannelNames"])):
                data = dict()
                data["DeviceName"] = device.getDeviceName()
                data["Timestamp"] = recording.date
                data["Channel"], data["Hemisphere"] = Percept.reformatChannelName(survey["ChannelNames"][i])
                for lead in leads:
                    if lead["name"].startswith(data["Hemisphere"]):
                        data["Hemisphere"] = lead["name"]
                        data["CustomName"] = lead["custom_name"]
                        break

                if requestRaw:
                    data["Raw"] = survey["Data"][:,i].tolist()
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

                MonopolarEstimation.append(data)
            BrainSenseData.extend(MonopolarEstimation)
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