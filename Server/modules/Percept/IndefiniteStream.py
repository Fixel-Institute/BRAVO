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
Indefinite Streaming Processing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(os.environ.get("PYTHON_UTILITY"))

import numpy as np
from datetime import datetime
import pytz

from scipy import signal

from decoder import Percept
from utility import SignalProcessingUtility as SPU
from utility.PythonUtility import *

from Backend import models
from modules import Database

key = os.environ.get('ENCRYPTION_KEY')

def saveMontageStreams(deviceID, streamList, sourceFile):
    """ Save Indefinite Streaming Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      streamList: Array of Indefinite Streaming structures extracted from Medtronic JSON file.
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
            print("Inconsistent Recording Size for Indefinite Stream")
            maxSize = np.max(RecordingSize)
            Recording["Data"] = np.zeros((maxSize, len(RecordingSize)))
            Recording["Missing"] = np.ones((maxSize, len(RecordingSize)))
            n = 0
            for i in range(len(streamList)): 
                if StreamGroupIndexes[i]:
                    Recording["Data"][:RecordingSize[n], n] = streamList[i]["Data"]
                    Recording["Missing"][:RecordingSize[n], n] = streamList[i]["Missing"]
                    Recording["StartTime"] = date.timestamp() + (streamList[i]["Ticks"][0]%1000)
                    n += 1
        else:
            Recording["Data"] = np.zeros((RecordingSize[0], len(RecordingSize)))
            Recording["Missing"] = np.ones((RecordingSize[0], len(RecordingSize)))
            n = 0
            for i in range(len(streamList)): 
                if StreamGroupIndexes[i]:
                    Recording["Data"][:, n] = streamList[i]["Data"]
                    Recording["Missing"][:, n] = streamList[i]["Missing"]
                    Recording["StartTime"] = date.timestamp() + (streamList[i]["Ticks"][0]%1000)
                    n += 1
            
        Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
        recording_info = {"Channel": Recording["ChannelNames"]}

        if not models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="IndefiniteStream", recording_date=date, recording_info=recording_info).exists():
            recording = models.BrainSenseRecording(device_deidentified_id=deviceID, recording_date=date, source_file=sourceFile,
                                  recording_type="IndefiniteStream", recording_info=recording_info)
            filename = Database.saveSourceFiles(Recording, "IndefiniteStream", "Combined", recording.recording_id, recording.device_deidentified_id)
            recording.recording_datapointer = filename
            recording.recording_duration = Recording["Duration"]
            recording.save()
            NewRecordingFound = True
    return NewRecordingFound

def processMontageStreams(stream, method="spectrogram"):
    """ Calculate BrainSense Survey Power Spectrum.

    The pipeline will filter all channels in the raw Indefinite Streaming with a zero-phase 5th-order Butterworth filter between 1-100Hz.
    Then time-frequency analysis is calculated using short-time Fourier Transform with 0.5Hz frequency resolution using 1.0 second 
    window and 500ms overlap. Zero-padding when neccessary to increase frequency resolution.

    Args:
      stream: Indefinite Stream raw object. 

    Returns:
      Processed Indefinite Streams with Spectrums.
    """

    [b,a] = signal.butter(5, np.array([1,100])*2/250, 'bp', output='ba')
    stream["Spectrums"] = []
    for i in range(len(stream["ChannelNames"])):
        filtered = signal.filtfilt(b, a, stream["Data"][:,i])
        stream["Spectrums"].append(SPU.defaultSpectrogram(filtered, window=1.0, overlap=0.5,frequency_resolution=1, fs=stream["SamplingRate"]))
    return stream

def queryMontageDataOverview(user, patientUniqueID, authority):
    """ Query available Indefinite Streaming data from specific patient requested

    This function will query all available Indefinite Streaming data that a specific user has access to for a specific patient. 

    Args:
      user: BRAVO Platform User object. 
      patientUniqueID: Deidentified patient ID as referenced in SQL Database. 
      authority: User permission structure indicating the type of access the user has.

    Returns:
      List of Indefinite Streaming data accessible.
    """

    BrainSenseData = list()
    if not authority["Permission"]:
        return BrainSenseData

    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        allSurveys = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type="IndefiniteStream").order_by("recording_date").all()
        if len(allSurveys) > 0:
            leads = device.device_lead_configurations

        for recording in allSurveys:
            if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
                continue

            data = dict()
            if device.device_name == "":
                data["DeviceName"] = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)
            else:
                data["DeviceName"] = device.device_name
            data["Timestamp"] = recording.recording_date.timestamp()
            data["Duration"] = recording.recording_duration
            data["DeviceID"] = device.deidentified_id
            data["DeviceLocation"] = device.device_location
            data["Channels"] = []

            Channels = recording.recording_info["Channel"]
            for channel in Channels:
                contacts, hemisphere = Percept.reformatChannelName(channel)
                for lead in leads:
                    if lead["TargetLocation"].startswith(hemisphere):
                        data["Channels"].append({"Hemisphere": lead["TargetLocation"], "Contacts": contacts})

            BrainSenseData.append(data)
    return BrainSenseData

def queryMontageData(user, devices, timestamps, authority):
    """ Query available Indefinite Streaming data from specific patient requested

    Query all data (which can be multiple recordings from the same day if data interruption exist) based on the 
    timestamps.

    Args:
      user: BRAVO Platform User object. 
      devices (list): Deidentified neurostimulator device IDs as referenced in SQL Database. 
      timestamps (list): Unix timestamps at which the recordings are collected.
      authority: User permission structure indicating the type of access the user has.

    Returns:
      List of Indefinite Streaming data accessible.
    """

    BrainSenseData = list()
    for i in range(len(devices)):
        device = models.PerceptDevice.objects.filter(deidentified_id=devices[i]).first()

        if not device == None:
            leads = device.device_lead_configurations
            recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=devices[i], recording_date=datetime.fromtimestamp(timestamps[i],tz=pytz.utc), recording_type="IndefiniteStream").first()
            if not recording == None:
                if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
                    continue

                stream = Database.loadSourceDataPointer(recording.recording_datapointer)
                if not "Spectrums" in stream.keys():
                    stream = processMontageStreams(stream)
                    Database.saveSourceFiles(stream,"IndefiniteStream","Combined",recording.recording_id, recording.device_deidentified_id)

                data = dict()
                data["Timestamp"] = stream["StartTime"]
                data["DeviceID"] = devices[i]
                data["Channels"] = stream["ChannelNames"]
                data["ChannelNames"] = list()
                for channel in stream["ChannelNames"]:
                    contacts, hemisphere = Percept.reformatChannelName(channel)
                    for lead in leads:
                        if lead["TargetLocation"].startswith(hemisphere):
                            data["ChannelNames"].append(lead["TargetLocation"] + f" E{contacts[0]:02}-E{contacts[1]:02}")

                data["Stream"] = []
                for j in range(len(stream["ChannelNames"])):
                    data["Stream"].append(stream["Data"][:,j].tolist())
                data["Spectrums"] = stream["Spectrums"]
                BrainSenseData.append(data)
    return BrainSenseData
