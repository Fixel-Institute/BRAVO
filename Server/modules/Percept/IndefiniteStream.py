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

def saveIndefiniteStreams(participant, device, streamList):
    """ Save Indefinite Streaming Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      streamList: Array of Indefinite Streaming structures extracted from Medtronic JSON file.
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """

    NewRecordings = []
    StreamDates = list()
    for stream in streamList:
        StreamDates.append(stream["FirstPacketDateTime"])
    UniqueSessionDates = np.unique(StreamDates)

    for date in UniqueSessionDates:
        recording = device.recordings.get_or_none(type="IndefiniteStream", date=date)
        if not recording:
            Recording = dict()
            Recording["SamplingRate"] = streamList[0]["SamplingRate"]
            StreamGroupIndexes = [stream["FirstPacketDateTime"] == date for stream in streamList]
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
                        if streamList[i]["Ticks"][0] > 3276800:
                            streamList[i]["Ticks"][0] -= 3276800
                        Recording["StartTime"] = date + (streamList[i]["Ticks"][0]%1000)/1000
                        n += 1
            else:
                Recording["Data"] = np.zeros((RecordingSize[0], len(RecordingSize)))
                Recording["Missing"] = np.ones((RecordingSize[0], len(RecordingSize)))
                n = 0
                for i in range(len(streamList)): 
                    if StreamGroupIndexes[i]:
                        Recording["Data"][:, n] = streamList[i]["Data"]
                        Recording["Missing"][:, n] = streamList[i]["Missing"]
                        if streamList[i]["Ticks"][0] > 3276800:
                            streamList[i]["Ticks"][0] -= 3276800
                        Recording["StartTime"] = date + (streamList[i]["Ticks"][0]%1000)/1000
                        n += 1
                
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]


            recording = models.TimeSeriesRecording(type="IndefiniteStream", date=date, 
                                                    sampling_rate=Recording["SamplingRate"], duration=Recording["Duration"]).save()
            filename = Database.saveSourceFiles(Recording, "IndefiniteStream", recording.uid, participant.uid)
            recording.data_pointer = filename
            recording.channel_names = Recording["ChannelNames"]
            recording.save()
            recording.devices.connect(device)
            device.recordings.connect(recording)
            NewRecordings.append(recording)
            
    return NewRecordings

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
        allSurveys = models.NeuralActivityRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type="IndefiniteStream").order_by("recording_date").all()
        if len(allSurveys) > 0:
            leads = device.device_lead_configurations

        for recording in allSurveys:
            if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
                continue
            
            # Skip data with less than 1 second data
            if recording.recording_duration < 1:
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
            recording = models.NeuralActivityRecording.objects.filter(device_deidentified_id=devices[i], recording_date=datetime.fromtimestamp(timestamps[i],tz=pytz.utc), recording_type="IndefiniteStream").first()
            if not recording == None:
                if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
                    continue

                stream = Database.loadSourceDataPointer(recording.recording_datapointer)

                # Skip this because this recording doesn't have enough data
                if stream["Duration"] < 1:
                    continue 

                if not "Spectrums" in stream.keys():
                    stream = processMontageStreams(stream)
                    Database.saveSourceFiles(stream,"IndefiniteStream","Combined",recording.recording_id, recording.device_deidentified_id)

                data = dict()
                data["Timestamp"] = stream["StartTime"]
                data["Duration"] = stream["Duration"]
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

def processAnnotationAnalysis(data):
    EventOnsetSpectrum = {}
    EventPSDs = {}
    for i in range(len(data)):
        if "Annotations" in data[i].keys():
            for j in range(len(data[i]["Annotations"])):
                if data[i]["Annotations"][j]["Duration"] > 0:
                    if not data[i]["Annotations"][j]["Name"] in EventPSDs.keys():
                        EventPSDs[data[i]["Annotations"][j]["Name"]] = []

                    EventStartTime = data[i]["Annotations"][j]["Time"] - data[i]["Timestamp"]
                    for k in range(len(data[i]["Spectrums"])):
                        ChannelFound = -1
                        for l in range(len(EventPSDs[data[i]["Annotations"][j]["Name"]])):
                            if EventPSDs[data[i]["Annotations"][j]["Name"]][l]["Channel"] == data[i]["ChannelNames"][k]:
                                ChannelFound = l
                                break

                        if not ChannelFound >= 0:
                            EventPSDs[data[i]["Annotations"][j]["Name"]].append({
                                "Channel": data[i]["ChannelNames"][k],
                                "Count": 0,
                                "MeanPower": [],
                                "StdPower": [],
                                "Frequency": []
                            })
                            ChannelFound = len(EventPSDs[data[i]["Annotations"][j]["Name"]]) - 1
                        
                        TimeSelection = rangeSelection(data[i]["Spectrums"][k]["Time"], [EventStartTime, EventStartTime+data[i]["Annotations"][j]["Duration"]])
                        PSDs = data[i]["Spectrums"][k]["Power"][:, TimeSelection]
                        EventPSDs[data[i]["Annotations"][j]["Name"]][ChannelFound]["Count"] += 1
                        EventPSDs[data[i]["Annotations"][j]["Name"]][ChannelFound]["MeanPower"].append(np.mean(PSDs, axis=1))
                        EventPSDs[data[i]["Annotations"][j]["Name"]][ChannelFound]["Frequency"] = data[i]["Spectrums"][k]["Frequency"]
                else:
                    for k in range(len(data[i]["Spectrums"])):
                        key = data[i]["ChannelNames"][k] + " " + data[i]["Annotations"][j]["Name"]
                        
                        if not key in EventOnsetSpectrum.keys():
                            EventOnsetSpectrum[key] = {
                                "Count": 0,
                                "Time": [],
                                "Frequency": [],
                                "Spectrum": []
                            }

                        EventStartTime = data[i]["Annotations"][j]["Time"] - data[i]["Timestamp"]
                        TimeSelection = rangeSelection(data[i]["Spectrums"][k]["Time"], [EventStartTime-5, EventStartTime+5])
                        EventOnsetSpectrum[key]["Frequency"] = data[i]["Spectrums"][k]["Frequency"]
                        EventOnsetSpectrum[key]["Time"] = data[i]["Spectrums"][k]["Time"][TimeSelection] - EventStartTime

                        PSDs = data[i]["Spectrums"][k]["logPower"][:, TimeSelection]
                        EventOnsetSpectrum[key]["Count"] += 1
                        EventOnsetSpectrum[key]["Spectrum"].append(PSDs)

    for key in EventOnsetSpectrum.keys():
        EventOnsetSpectrum[key]["Spectrum"] = np.mean(np.array(EventOnsetSpectrum[key]["Spectrum"]), axis=0).tolist()
        EventOnsetSpectrum[key]["Frequency"] = EventOnsetSpectrum[key]["Frequency"].tolist()
        EventOnsetSpectrum[key]["Time"] = EventOnsetSpectrum[key]["Time"].tolist()

    for key in EventPSDs.keys():
        for channel in range(len(EventPSDs[key])):
            EventPSDs[key][channel]["StdPower"] = SPU.stderr(np.array(EventPSDs[key][channel]["MeanPower"]), axis=0).tolist()
            EventPSDs[key][channel]["MeanPower"] = np.mean(np.array(EventPSDs[key][channel]["MeanPower"]), axis=0).tolist()
            EventPSDs[key][channel]["Frequency"] = EventPSDs[key][channel]["Frequency"].tolist()

    return EventPSDs, EventOnsetSpectrum