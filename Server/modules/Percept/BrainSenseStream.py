# -*- coding: utf-8 -*-
""""""
"""
Python Module for BrainSense Streaming
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

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

def saveRealtimeStreams(deviceID, StreamingTD, StreamingPower, sourceFile):
    """ Save BrainSense Streaming Data in Database Storage

    Args:
      deviceID: UUID4 deidentified id for each unique Percept device.
      StreamingTD: BrainSense TimeDomain structure extracted from Medtronic JSON file.
      StreamingPower: BrainSense Power Channel structure extracted from Medtronic JSON file.
      sourceFile: filename of the raw JSON file that the original data extracted from.

    Returns:
      Boolean indicating if new data is found (to be saved).
    """

    NewRecordingFound = False
    StreamDates = list()
    for stream in StreamingTD:
        StreamDates.append(datetime.fromtimestamp(Percept.getTimestamp(stream["FirstPacketDateTime"]), tz=pytz.utc))
    UniqueSessionDates = np.unique(StreamDates)

    for date in UniqueSessionDates:
        selectedIndex = np.where(iterativeCompare(StreamDates, date, "equal").flatten())[0]
        recording_data = dict()
        recording_data["Missing"] = dict()
        recording_data["Channels"] = list()
        for index in selectedIndex:
            recording_data["Channels"].append(StreamingTD[index]["Channel"])
            recording_data[StreamingTD[index]["Channel"]] = StreamingTD[index]["Data"]
            recording_data["Time"] = StreamingTD[index]["Time"]
            recording_data["Missing"][StreamingTD[index]["Channel"]] = StreamingTD[index]["Missing"]
            recording_data["Stimulation"] = np.zeros((len(recording_data["Time"]),2))
            recording_data["PowerBand"] = np.zeros((len(recording_data["Time"]),2))
            for i in range(2):
                recording_data["Stimulation"][:,i] = np.interp(StreamingTD[index]["Time"], StreamingPower[index]["Time"], StreamingPower[index]["Stimulation"][:,i])
                recording_data["PowerBand"][:,i] = np.interp(StreamingTD[index]["Time"], StreamingPower[index]["Time"], StreamingPower[index]["Power"][:,i])
            recording_data["Therapy"] = StreamingPower[index]["TherapySnapshot"]

        recording_info = {"Channel": recording_data["Channels"], "Therapy": recording_data["Therapy"]}
        if not models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="BrainSenseStream", recording_date=date, recording_info__Channel=recording_data["Channels"]).exists():
            recording = models.BrainSenseRecording(device_deidentified_id=deviceID, recording_date=date, source_file=sourceFile, recording_type="BrainSenseStream", recording_info=recording_info)
            if len(selectedIndex) == 2:
                info = "Bilateral"
            else:
                info = "Unilateral"
            filename = Database.saveSourceFiles(recording_data, "BrainSenseStream", info, recording.recording_id, recording.device_deidentified_id)
            recording.recording_datapointer = filename
            recording.recording_duration = recording_data["Time"][-1]
            recording.save()
            NewRecordingFound = True
        else:
            recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=deviceID, recording_type="BrainSenseStream", recording_date=date, recording_info__Channel=recording_data["Channels"]).first()
            if len(selectedIndex) == 2:
                info = "Bilateral"
            else:
                info = "Unilateral"
            filename = Database.saveSourceFiles(recording_data, "BrainSenseStream", info, recording.recording_id, recording.device_deidentified_id)

    return NewRecordingFound

def processRealtimeStreams(stream, cardiacFilter=False):
    """ Process BrainSense Streaming Data 

    This is the primary processing function for all BrainSense Streaming data. 
    The server will attempt to calculate Short-time Fourier Transform (STFT) with 1.0 second window and 0.5 second overlap. 
    In addition to the STFT, the server will also calculate Wavelet Transform with a 500ms moving average window. 

    The user can request the server to perform cardiac removal using cardiacFilter argument. 
    If cardiac filter is used, the server will perform a template matching algorithm to remove cardiac signals.
    (TODO: details algorithm for later).

    Args:
      stream: BrainSense TimeDomain structure extracted from Medtronic JSON file
      cardiacFilter: Boolean indicating if you want to .

    Returns:
      Processed BrainSense TimeDomain structure
    """

    stream["Wavelet"] = dict()
    stream["Spectrogram"] = dict()
    stream["Filtered"] = dict()

    for channel in stream["Channels"]:
        [b,a] = signal.butter(5, np.array([1,100])*2/250, 'bp', output='ba')
        stream["Filtered"][channel] = signal.filtfilt(b, a, stream[channel])
        (channels, hemisphere) = Percept.reformatChannelName(channel)
        if hemisphere == "Left":
            StimulationSide = 0
        else:
            StimulationSide = 1

        if cardiacFilter:
            # Cardiac Filter
            posPeaks,_ = signal.find_peaks(stream["Filtered"][channel], prominence=[10,200], distance=250*0.5)
            PosCardiacVariability = np.std(np.diff(posPeaks))
            negPeaks,_ = signal.find_peaks(-stream["Filtered"][channel], prominence=[10,200], distance=250*0.5)
            NegCardiacVariability = np.std(np.diff(negPeaks))

            if PosCardiacVariability < NegCardiacVariability:
                peaks = posPeaks
            else:
                peaks = negPeaks
            CardiacRate = int(np.mean(np.diff(peaks)))

            PrePeak = int(CardiacRate*0.25)
            PostPeak = int(CardiacRate*0.65)
            EKGMatrix = np.zeros((len(peaks)-2,PrePeak+PostPeak))
            for i in range(1,len(peaks)-1):
                EKGMatrix[i-1,:] = stream["Filtered"][channel][peaks[i]-PrePeak:peaks[i]+PostPeak]

            EKGTemplate = np.mean(EKGMatrix,axis=0)
            EKGTemplate = EKGTemplate / (np.max(EKGTemplate)-np.min(EKGTemplate))

            def EKGTemplateFunc(xdata, amplitude, offset):
                return EKGTemplate * amplitude + offset

            for i in range(len(peaks)):
                if peaks[i]-PrePeak < 0:
                    pass
                elif peaks[i]+PostPeak >= len(stream["Filtered"][channel]) :
                    pass
                else:
                    sliceSelection = np.arange(peaks[i]-PrePeak,peaks[i]+PostPeak)
                    params, covmat = optimize.curve_fit(EKGTemplateFunc, sliceSelection, stream["Filtered"][channel][sliceSelection])
                    stream["Filtered"][channel][sliceSelection] = stream["Filtered"][channel][sliceSelection] - EKGTemplateFunc(sliceSelection, *params)

        # Wavelet Computation
        stream["Wavelet"][channel] = SPU.waveletTimeFrequency(stream["Filtered"][channel], freq=np.array(range(1,200))/2, ma=125, fs=250)
        stream["Wavelet"][channel]["Missing"] = stream["Missing"][channel][::int(250/2)]
        stream["Wavelet"][channel]["Power"] = stream["Wavelet"][channel]["Power"][:,::int(250/2)]
        stream["Wavelet"][channel]["Time"] = stream["Wavelet"][channel]["Time"][::int(250/2)]
        stream["Wavelet"][channel]["Type"] = "Wavelet"
        del(stream["Wavelet"][channel]["logPower"])

        # SFFT Computation
        stream["Spectrogram"][channel] = SPU.defaultSpectrogram(stream["Filtered"][channel], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=250)
        stream["Spectrogram"][channel]["Type"] = "Spectrogram"
        stream["Spectrogram"][channel]["Time"] += stream["Time"][0]
        stream["Spectrogram"][channel]["Missing"] = np.zeros(stream["Spectrogram"][channel]["Time"].shape, dtype=bool)
        for i in range(len(stream["Spectrogram"][channel]["Missing"])):
            if np.any(stream["Missing"][channel][rangeSelection(stream["Time"], [stream["Spectrogram"][channel]["Time"][i]-2, stream["Spectrogram"][channel]["Time"][i]+2])]):
                stream["Spectrogram"][channel]["Missing"][i] = True
        del(stream["Spectrogram"][channel]["logPower"])

    return stream

def queryRealtimeStreamOverview(user, patientUniqueID, authority):
    """ Query available BrainSense Streaming data from specific patient requested

    This function will query all available BrainSense Streaming data that a specific user has access to for a specific patient. 

    Args:
      user: BRAVO Platform User object. 
      patientUniqueID: Deidentified patient ID as referenced in SQL Database. 
      authority: User permission structure indicating the type of access the user has.

    Returns:
      List of BrainSense Streaming data accessible.
    """

    BrainSenseData = list()
    if not authority["Permission"]:
        return BrainSenseData

    includedRecording = list()
    availableDevices = Database.getPerceptDevices(user, patientUniqueID, authority)
    for device in availableDevices:
        allSurveys = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type="BrainSenseStream").order_by("-recording_date").all()
        if len(allSurveys) > 0:
            leads = device.device_lead_configurations

        for recording in allSurveys:
            if not recording.recording_id in authority["Permission"] and authority["Level"] == 2:
                continue

            data = dict()
            data["Timestamp"] = recording.recording_date.timestamp()
            data["Duration"] = recording.recording_duration

            if data["Timestamp"] in includedRecording:
                continue

            if data["Duration"] < 5:
                continue

            data["RecordingID"] = recording.recording_id
            data["DeviceName"] = device.device_name
            data["DeviceID"] = device.deidentified_id
            data["DeviceLocation"] = device.device_location
            data["Channels"] = list()
            data["ContactTypes"] = list()

            if not "Therapy" in recording.recording_info:
                if len(recording.recording_info["Channel"]) == 2:
                    info = "Bilateral"
                else:
                    info = "Unilateral"
                RawData = Database.loadSourceDataPointer(recording.recording_datapointer)
                recording.recording_info["Therapy"] = RawData["Therapy"]
                recording.save()
            data["Therapy"] = recording.recording_info["Therapy"]

            Channels = recording.recording_info["Channel"]
            if not "ContactType" in recording.recording_info:
                recording.recording_info["ContactType"] = ["Ring" for channel in Channels]
                recording.save()
            if not len(recording.recording_info["ContactType"]) == len(Channels):
                recording.recording_info["ContactType"] = ["Ring" for channel in Channels]
                recording.save()
            
            data["ContactType"] = recording.recording_info["ContactType"]
            for channel in Channels:
                contacts, hemisphere = Percept.reformatChannelName(channel)
                for lead in leads:
                    if lead["TargetLocation"].startswith(hemisphere):
                        data["Channels"].append({"Hemisphere": lead["TargetLocation"], "Contacts": contacts, "Type": lead["ElectrodeType"]})
                        if lead["ElectrodeType"].startswith("SenSight"):
                            data["ContactTypes"].append(["Ring","Segment A","Segment B","Segment C","Segment AB","Segment BC","Segment AC"])
                        else:
                            data["ContactTypes"].append(["Ring"])

            BrainSenseData.append(data)
            includedRecording.append(data["Timestamp"])
    return BrainSenseData

def queryRealtimeStreamRecording(user, recordingId, authority, cardiacFilter=False, refresh=False):
    """ Query BrainSense Streaming Data

    This function will query BrainSense recording data based on provided Recording ID.

    Args:
      user: BRAVO Platform User object. 
      recordingId:  Deidentified recording ID as referenced in SQL Database. 
      authority: User permission structure indicating the type of access the user has.
      cardiacFilter: Boolean indicator if the user want to apply cardiac filters (see processRealtimeStreams function)
      refresh: Boolean indicator if the user want to use cache data or reprocess the data.

    Returns:
      Returns a tuple (BrainSenseData, RecordingID) where BrainSenseData is the BrainSense streaming data structure in Database and RecordingID is the 
      deidentified id of the available data.
    """

    BrainSenseData = None
    RecordingID = None
    if authority["Level"] == 0:
        return BrainSenseData, RecordingID

    if not authority["Permission"]:
        return BrainSenseData, RecordingID

    recording = models.BrainSenseRecording.objects.filter(recording_id=recordingId, recording_type="BrainSenseStream").first()

    if not recording == None:
        if authority["Level"] == 2:
            if not recording.recording_id in authority["Permission"]:
                return BrainSenseData, RecordingID

        if len(recording.recording_info["Channel"]) == 2:
            info = "Bilateral"
        else:
            info = "Unilateral"

        BrainSenseData = Database.loadSourceDataPointer(recording.recording_datapointer)
        BrainSenseData["Info"] = recording.recording_info

        if not "CardiacFilter" in recording.recording_info:
            recording.recording_info["CardiacFilter"] = cardiacFilter
            recording.save()

        if not "Spectrogram" in BrainSenseData.keys() or (refresh and not recording.recording_info["CardiacFilter"] == cardiacFilter):
            recording.recording_info["CardiacFilter"] = cardiacFilter
            BrainSenseData = processRealtimeStreams(BrainSenseData, cardiacFilter=cardiacFilter)
            Database.saveSourceFiles(BrainSenseData,recording.recording_type,info,recording.recording_id, recording.device_deidentified_id)
            recording.save()
        
        for channel in BrainSenseData["Channels"]:
            if not "Missing" in BrainSenseData["Spectrogram"][channel].keys():
                BrainSenseData = processRealtimeStreams(BrainSenseData, cardiacFilter=cardiacFilter)
                Database.saveSourceFiles(BrainSenseData,recording.recording_type,info,recording.recording_id, recording.device_deidentified_id)
                break
        
        for channel in BrainSenseData["Filtered"].keys():
            if not BrainSenseData["Filtered"][channel].shape == BrainSenseData[channel].shape:
                recording.recording_info["CardiacFilter"] = cardiacFilter
                BrainSenseData = processRealtimeStreams(BrainSenseData, cardiacFilter=cardiacFilter)
                Database.saveSourceFiles(BrainSenseData,recording.recording_type,info,recording.recording_id, recording.device_deidentified_id)
                recording.save()

        BrainSenseData["Timestamp"] = recording.recording_date.timestamp();
        BrainSenseData["Info"] = recording.recording_info;
        RecordingID = recording.recording_id
    return BrainSenseData, RecordingID

def queryMultipleSegmentComparison(user, recordingIds, authority):
    """ Query Multiple Segment Comparison

    This function will query BrainSense recording data based on provided Recording ID.

    Args:
      user: BRAVO Platform User object. 
      recordingIds:  List of deidentified recording IDs as referenced in SQL Database. 
      authority: User permission structure indicating the type of access the user has.

    Returns:
      Returns a dictionary (SegmentSummaries) which contains average power spectrum and respective stimulation settings.
    """

    if authority["Level"] == 0:
        return None

    if not authority["Permission"]:
        return None
    
    SegmentSummaries = {}

    recordings = models.BrainSenseRecording.objects.filter(recording_id__in=recordingIds, recording_type="BrainSenseStream").all()
    for recording in recordings:
        if str(recording.device_deidentified_id) in authority["Devices"]:
            BrainSenseData = Database.loadSourceDataPointer(recording.recording_datapointer)

            if len(recording.recording_info["Channel"]) == 2:
                info = "Bilateral"
            else:
                info = "Unilateral"

            if not "Spectrogram" in BrainSenseData.keys():
                BrainSenseData = processRealtimeStreams(BrainSenseData)
                Database.saveSourceFiles(BrainSenseData, recording.recording_type, info, recording.recording_id, recording.device_deidentified_id)
                recording.save()
            
            BrainSenseData["Stimulation"] = processRealtimeStreamStimulationAmplitude(BrainSenseData)
            for StimulationSeries in BrainSenseData["Stimulation"]:

                if StimulationSeries["Name"].endswith("LEFT"):
                    StimFrequency = BrainSenseData["Therapy"]["Left"]["RateInHertz"]
                    StimPulse = BrainSenseData["Therapy"]["Left"]["PulseWidthInMicroSecond"]
                    StimContact = recording.recording_info["ContactType"][0]
                else:
                    StimFrequency = BrainSenseData["Therapy"]["Right"]["RateInHertz"]
                    StimPulse = BrainSenseData["Therapy"]["Right"]["PulseWidthInMicroSecond"]
                    StimContact = recording.recording_info["ContactType"][-1]

                if not StimulationSeries["Name"] in SegmentSummaries.keys():
                    SegmentSummaries[StimulationSeries["Name"]] = []

                cIndex = 0;
                for i in range(1,len(StimulationSeries["Time"])):
                    StimulationDuration = StimulationSeries["Time"][i] - StimulationSeries["Time"][i-1]
                    if StimulationDuration < 5:
                        continue
                    cIndex += 1

                    timeSelection = rangeSelection(BrainSenseData["Spectrogram"][StimulationSeries["Name"]]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
                    SegmentSummaries[StimulationSeries["Name"]].append({
                        "PSD": np.mean(BrainSenseData["Spectrogram"][StimulationSeries["Name"]]["Power"][:,timeSelection],axis=1),
                        "Therapy": {
                            "Amplitude": StimulationSeries["Amplitude"][i],
                            "Frequency": StimFrequency,
                            "Pulsewidth": StimPulse,
                            "Contact": StimContact,
                        },
                        "RecordingID": recording.recording_id
                    })
            
    return SegmentSummaries

def queryRealtimeStreamData(user, device, timestamp, authority, cardiacFilter=False, refresh=False):
    """ Query BrainSense Streaming Data

    This function will query BrainSense recording data based on provided Device ID and Timestamp of the recording.

    Args:
      user: BRAVO Platform User object. 
      device:  Deidentified neurostimulator device ID as referenced in SQL Database. 
      timestamp:  Unix timestamp at which the recording is collected.
      authority: User permission structure indicating the type of access the user has.
      cardiacFilter: Boolean indicator if the user want to apply cardiac filters (see processRealtimeStreams function)
      refresh: Boolean indicator if the user want to use cache data or reprocess the data.

    Returns:
      Returns a tuple (BrainSenseData, RecordingID) where BrainSenseData is the BrainSense streaming data structure in Database and RecordingID is the 
      deidentified id of the available data.
    """

    BrainSenseData = None
    RecordingID = None
    if authority["Level"] == 0:
        return BrainSenseData, RecordingID

    if not authority["Permission"]:
        return BrainSenseData, RecordingID

    recording_info = {"CardiacFilter": cardiacFilter}
    if models.BrainSenseRecording.objects.filter(device_deidentified_id=device, recording_date=datetime.fromtimestamp(timestamp,tz=pytz.utc), recording_type="BrainSenseStream", recording_info__contains=recording_info).exists():
        recording = models.BrainSenseRecording.objects.get(device_deidentified_id=device, recording_date=datetime.fromtimestamp(timestamp,tz=pytz.utc), recording_type="BrainSenseStream", recording_info__contains=recording_info)
    else:
        recording = models.BrainSenseRecording.objects.filter(device_deidentified_id=device, recording_date=datetime.fromtimestamp(timestamp,tz=pytz.utc), recording_type="BrainSenseStream").first()

    if not recording == None:
        if authority["Level"] == 2:
            if not recording.recording_id in authority["Permission"]:
                return BrainSenseData, RecordingID

        if len(recording.recording_info["Channel"]) == 2:
            info = "Bilateral"
        else:
            info = "Unilateral"

        BrainSenseData = Database.loadSourceDataPointer(recording.recording_datapointer)
        BrainSenseData["Info"] = recording.recording_info;

        if not "CardiacFilter" in recording.recording_info:
            recording.recording_info["CardiacFilter"] = cardiacFilter
            recording.save()

        if not "Spectrogram" in BrainSenseData.keys() or (refresh and (not recording.recording_info["CardiacFilter"] == cardiacFilter)):
            recording.recording_info["CardiacFilter"] = cardiacFilter
            BrainSenseData = processRealtimeStreams(BrainSenseData, cardiacFilter=cardiacFilter)
            Database.saveSourceFiles(BrainSenseData,recording.recording_type,info,recording.recording_id, recording.device_deidentified_id)
            recording.save()

        BrainSenseData["Timestamp"] = recording.recording_date.timestamp();
        BrainSenseData["Info"] = recording.recording_info;
        RecordingID = recording.recording_id
    return BrainSenseData, RecordingID

def mergeRealtimeStreamData(recordings):
    BrainSenseData = []
    Therapies = []
    for recording in recordings:
        BrainSenseData.append(Database.loadSourceDataPointer(recording.recording_datapointer))
        Therapies.append(BrainSenseData[-1]["Therapy"])
    
    for Therapy in Therapies:
        for side in ["Left", "Right"]:
            if side in Therapy.keys():
                Therapy[side]["UpperLimitInMilliAmps"] = 0
                Therapy[side]["LowerLimitInMilliAmps"] = 0
                
    Therapies = uniqueList(Therapies)
    if len(Therapies) > 1:
        return False
    
    CombinedData = copy.deepcopy(BrainSenseData[0])
    CurrentTime = recordings[0].recording_date.timestamp()
    CombinedData["Time"] += CurrentTime
    for i in range(1, len(recordings)):
        CurrentTime = recordings[i].recording_date.timestamp()
        BrainSenseData[i]["Time"] += CurrentTime
        Timeskip = int((CurrentTime - CombinedData["Time"][-1]) * 250)
        for channel in CombinedData["Channels"]:
            CombinedData["Missing"][channel] = np.concatenate((CombinedData["Missing"][channel], np.ones(Timeskip), BrainSenseData[i]["Missing"][channel]))
            CombinedData[channel] = np.concatenate((CombinedData[channel], np.zeros(Timeskip), BrainSenseData[i][channel]))
        CombinedData["Stimulation"] = np.concatenate((CombinedData["Stimulation"], np.ones((Timeskip, 2))*CombinedData["Stimulation"][-1,:], BrainSenseData[i]["Stimulation"]))
        CombinedData["PowerBand"] = np.concatenate((CombinedData["PowerBand"], np.ones((Timeskip, 2)), BrainSenseData[i]["PowerBand"]))
        CombinedData["Time"] = np.arange(CombinedData["Stimulation"].shape[0]) / 250
    
    if len(CombinedData["Channels"]) == 2:
        info = "Bilateral"
    else:
        info = "Unilateral"
        
    Database.saveSourceFiles(CombinedData, recordings[0].recording_type, info, recordings[0].recording_id, recordings[0].device_deidentified_id)
    recordings[0].recording_duration = CombinedData["Time"][-1]
    recordings[0].save()

    for i in range(1, len(recordings)):
        try:
            os.remove(DATABASE_PATH + "recordings" + os.path.sep + recordings[i].recording_datapointer)
        except:
            pass
        recordings[i].delete()
    
    return True

def processRealtimeStreamRenderingData(stream, options=dict(), centerFrequencies=[0,0]):
    """ Process BrainSense Streaming Data to be used for Plotly rendering.

    This function takes the processRealtimeStreams BrainSense Stream object and further process it for frontend rendering system.
    This is to reduce some computational requirement for the frontend, and because Python signal processing is more efficient than 
    Javascript frontend. 

    This function wrap around ``processRealtimeStreamStimulationPSD`` function to generate stimulation related PSD at different stimulation state.

    Args:
      stream: processed BrainSense TimeDomain structure (see processRealtimeStreams function)
      options: Signal processing module configurations. 
      centerFrequencies: The center frequencies (Left and Right hemisphere) used to obtain Power-band box plot.

    Returns:
      Returns processed data object with content sufficient for React.js to render Plotly graphs.
    """
    
    stream["Stimulation"] = processRealtimeStreamStimulationAmplitude(stream)
    stream["PowerBand"] = processRealtimeStreamPowerBand(stream)
    data = dict()
    data["Channels"] = stream["Channels"]
    data["Stimulation"] = stream["Stimulation"]
    data["PowerBand"] = stream["PowerBand"]
    data["Info"] = stream["Info"]
    data["Timestamp"] = stream["Timestamp"]

    if len(centerFrequencies) < len(stream["Channels"]):
        centerFrequencies.append(0)
        
    counter = 0
    for channel in stream["Channels"]:
        data[channel] = dict()
        data[channel]["Time"] = stream["Time"]
        data[channel]["RawData"] = stream["Filtered"][channel]
        if options["SpectrogramMethod"]["value"] == "Spectrogram":
            data[channel]["Spectrogram"] = copy.deepcopy(stream["Spectrogram"][channel])
            data[channel]["Spectrogram"]["Power"][data[channel]["Spectrogram"]["Power"] == 0] = 1e-10
            data[channel]["Spectrogram"]["Power"] = np.log10(data[channel]["Spectrogram"]["Power"])*10
            data[channel]["Spectrogram"]["ColorRange"] = [-20,20]
        elif options["SpectrogramMethod"]["value"]  == "Wavelet":
            data[channel]["Spectrogram"] = copy.deepcopy(stream["Wavelet"][channel])
            data[channel]["Spectrogram"]["Power"][data[channel]["Spectrogram"]["Power"] == 0] = 1e-10
            data[channel]["Spectrogram"]["Power"] = np.log10(data[channel]["Spectrogram"]["Power"])*10
            data[channel]["Spectrogram"]["ColorRange"] = [-10,20]

        if options["PSDMethod"]["value"] == "Time-Frequency Analysis":
            data[channel]["StimPSD"] = processRealtimeStreamStimulationPSD(stream, channel, method=options["SpectrogramMethod"]["value"], stim_label="Ipsilateral", centerFrequency=centerFrequencies[counter])
        else:
            data[channel]["StimPSD"] = processRealtimeStreamStimulationPSD(stream, channel, method=options["PSDMethod"]["value"], stim_label="Ipsilateral", centerFrequency=centerFrequencies[counter])
        counter += 1

    return data

def processRealtimeStreamStimulationAmplitude(stream):
    """ Process BrainSense Streaming Data to extract data segment at different stimulation amplitude.

    Args:
      stream: processed BrainSense TimeDomain structure (see processRealtimeStreams function)

    Returns:
      Returns list of stimulation series.
    """

    StimulationSeries = list()
    Hemisphere = ["Left","Right"]
    for StimulationSide in range(2):
        if Hemisphere[StimulationSide] in stream["Therapy"].keys():
            Stimulation = np.around(stream["Stimulation"][:,StimulationSide],2)
            indexOfChanges = np.where(np.abs(np.diff(Stimulation)) > 0)[0]-1
            if len(indexOfChanges) == 0:
                indexOfChanges = np.insert(indexOfChanges,0,0)
            elif indexOfChanges[0] < 0:
                indexOfChanges[0] = 0
            else:
                indexOfChanges = np.insert(indexOfChanges,0,0)
            indexOfChanges = np.insert(indexOfChanges,len(indexOfChanges),len(Stimulation)-1)
            for channelName in stream["Channels"]:
                channels, hemisphere = Percept.reformatChannelName(channelName)
                if hemisphere == Hemisphere[StimulationSide]:
                    StimulationSeries.append({"Name": channelName, "Hemisphere": hemisphere, "Time": stream["Time"][indexOfChanges], "Amplitude": np.around(stream["Stimulation"][indexOfChanges,StimulationSide],2)})
    return StimulationSeries

def processRealtimeStreamPowerBand(stream):
    """ Extract Onboard Power-band recording.

    Additional filtering is done by performing zscore normalization. Outliers are removed. 

    Args:
      stream: processed BrainSense TimeDomain structure (see processRealtimeStreams function)

    Returns:
      Returns list of stimulation series.
    """

    PowerSensing = list()
    Hemisphere = ["Left","Right"]
    for StimulationSide in range(2):
        if Hemisphere[StimulationSide] in stream["Therapy"].keys():
            Power = stream["PowerBand"][:,StimulationSide]
            selectedData = np.abs(stats.zscore(Power)) < 3
            for channelName in stream["Channels"]:
                channels, hemisphere = Percept.reformatChannelName(channelName)
                if hemisphere == Hemisphere[StimulationSide]:
                    PowerSensing.append({"Name": channelName, "Time": stream["Time"][selectedData], "Power": stream["PowerBand"][selectedData,StimulationSide]})
    return PowerSensing

def processRealtimeStreamStimulationPSD(stream, channel, method="Spectrogram", stim_label="Ipsilateral", centerFrequency=0):
    """ Process BrainSense Stream Stimulation-specific Power Spectrum

    The process will take in stimulation epochs and compute Power Spectral Density using methods specified in parameters.
    Stimulation epochs with less than 7 seconds of recording are skipped.
    2 seconds before and after stimulation changes are skipped to avoid transition artifacts. 

    Standard method uses 1 second Window and 0.5 seconds overlap. Standard Spectral Feature bandwidth is +/- 2Hz. 

    Args:
      stream: processed BrainSense TimeDomain structure (see processRealtimeStreams function)
      channel: BrainSense TimeDomain data channel name.
      method (string): Processing method. Default to "Spectrogram" method, can be one of (Welch, Spectrogram, or Wavelet).
      stim_label (string): Using "Ipsilateral" stimulation label or "Contralateral" stimulation label. 
      centerFrequency (int): The center frequency at which the spectral features are extracted from PSD. 

    Returns:
      Returns average PSD at each stimulation amplitude, and Spectral Features extracted from desired frequency band. 
    """

    if stim_label == "Ipsilateral":
        for Stimulation in stream["Stimulation"]:
            if Stimulation["Name"] == channel:
                StimulationSeries = Stimulation
    else:
        for Stimulation in stream["Stimulation"]:
            if not Stimulation["Name"] == channel:
                StimulationSeries = Stimulation

    if not "StimulationSeries" in locals():
        raise Exception("Data not available")
    
    cIndex = 0
    StimulationEpochs = list()
    for i in range(1,len(StimulationSeries["Time"])):
        cIndex += 1 

        if method == "Welch":
            timeSelection = rangeSelection(stream["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            timeSelection = np.bitwise_and(timeSelection, stream["Missing"][channel] == 0)
            if np.sum(timeSelection) < 250 * 5:
                continue
            StimulationEpoch = stream["Filtered"][channel][timeSelection]
            fxx, pxx = signal.welch(StimulationEpoch, fs=250, nperseg=250 * 1, noverlap=250 * 0.5, nfft=250 * 2, scaling="density")
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i], "Frequency": fxx, "PSD": pxx})
            timeSelection = rangeSelection(stream["Spectrogram"][channel]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])

        elif method == "Spectrogram":
            timeSelection = rangeSelection(stream["Spectrogram"][channel]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            timeSelection = np.bitwise_and(timeSelection, stream["Spectrogram"][channel]["Missing"] == 0)
            if np.sum(timeSelection) < 2 * 5:
                continue
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i], "Frequency": stream["Spectrogram"][channel]["Frequency"], "PSD": np.mean(stream["Spectrogram"][channel]["Power"][:,timeSelection],axis=1)})

        elif method == "Wavelet":
            timeSelection = rangeSelection(stream["Wavelet"][channel]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            if np.sum(timeSelection) < 250 * 5:
                continue
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i], "Frequency": stream["Wavelet"][channel]["Frequency"], "PSD": np.mean(stream["Wavelet"][channel]["Power"][:,timeSelection],axis=1)})

        StimulationEpochs[-1]["TimeSelection"] = timeSelection

    if len(StimulationEpochs) == 0:
        return StimulationEpochs

    StimulationEpochs = sorted(StimulationEpochs, key=lambda epoch: epoch["Stimulation"])
    if centerFrequency == 0:
        try:
            centerFrequency = stream["Info"]["CenterFrequency"][channel]
        except:
            centerFrequency = 22

    frequencySelection = rangeSelection(StimulationEpochs[0]["Frequency"], [centerFrequency-2,centerFrequency+2])

    for i in range(len(StimulationEpochs)):
        StimulationEpochs[i]["CenterFrequency"] = centerFrequency
        timeSelection = StimulationEpochs[i]["TimeSelection"]

        if method == "Wavelet":
            timeSelection = np.bitwise_and(timeSelection, stream["Missing"][channel] == 0)
            StimulationEpochs[i]["SpectralFeatures"] = stream["Wavelet"][channel]["Power"][:,timeSelection]
        else:
            timeSelection = np.bitwise_and(timeSelection, stream["Spectrogram"][channel]["Missing"] == 0)
            StimulationEpochs[i]["SpectralFeatures"] = stream["Spectrogram"][channel]["Power"][:,timeSelection]

        StimulationEpochs[i]["SpectralFeatures"] = np.mean(StimulationEpochs[i]["SpectralFeatures"][frequencySelection,:],axis=0)
        del(StimulationEpochs[i]["TimeSelection"])

    return StimulationEpochs
