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
        StreamDates.append(datetime.fromtimestamp(Percept.getTimestamp(stream["FirstPacketDateTime"]), tz=pytz.utc))
    UniqueSessionDates = np.unique(StreamDates)

    for date in UniqueSessionDates:
        recording_data = dict()
        for stream in streamList:
            if datetime.fromtimestamp(Percept.getTimestamp(stream["FirstPacketDateTime"]), tz=pytz.utc) == date:
                if len(recording_data.keys()) == 0:
                    recording_data["Time"] = stream["Time"]
                    recording_data["Missing"] = stream["Missing"]
                    recording_data["Channels"] = list()
                recording_data["Channels"].append(stream["Channel"])
                recording_data[stream["Channel"]] = stream["Data"]

        recording_info = {"Channel": recording_data["Channels"]}
        if not models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="IndefiniteStream", recording_date=date, recording_info=recording_info).exists():
            recording = models.BrainSenseRecording(device_deidentified_id=deviceID, recording_date=date, source_file=sourceFile,
                                  recording_type="IndefiniteStream", recording_info=recording_info)
            filename = Database.saveSourceFiles(recording_data, "IndefiniteStream", "Combined", recording.recording_id, recording.device_deidentified_id)
            recording.recording_datapointer = filename
            recording.recording_duration = recording_data["Time"][-1]
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
    stream["Spectrums"] = dict()
    for channel in stream["Channels"]:
        filtered = signal.filtfilt(b, a, stream[channel])
        stream["Spectrums"][channel] = SPU.defaultSpectrogram(filtered, window=1.0, overlap=0.5,frequency_resolution=1, fs=250)
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
                data["DeviceName"] = device.getDeviceSerialNumber(key)
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
                print(stream.keys())
                if not "Spectrums" in stream.keys():
                    stream = processMontageStreams(stream)
                    Database.saveSourceFiles(stream,recording.recording_type,"Combined",recording.recording_id, recording.device_deidentified_id)
                data = dict()
                data["Timestamp"] = recording.recording_date.timestamp()
                data["Time"] = stream["Time"]
                data["DeviceID"] = devices[i]
                data["Channels"] = stream["Channels"]
                data["ChannelNames"] = list()
                for channel in stream["Channels"]:
                    contacts, hemisphere = Percept.reformatChannelName(channel)
                    for lead in leads:
                        if lead["TargetLocation"].startswith(hemisphere):
                            data["ChannelNames"].append(lead["TargetLocation"] + f" E{contacts[0]:02}-E{contacts[1]:02}")
                for channel in stream["Channels"]:
                    data[channel] = stream[channel]
                data["Spectrums"] = stream["Spectrums"]
                BrainSenseData.append(data)
    return BrainSenseData
