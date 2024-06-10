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
    TimeDomainRecordings = []
    PowerDomainRecordings = []

    StreamingTD.sort(key=lambda element: element["FirstPacketDateTime"] + len(element["Data"])/element["SamplingRate"])
    StreamingPower.sort(key=lambda element: element["FirstPacketDateTime"] + len(element["Power"])/element["SamplingRate"])

    n = 0
    while n < len(StreamingTD):
        if n+1 >= len(StreamingTD):
            Recording = dict()
            Recording["SamplingRate"] = StreamingTD[n]["SamplingRate"]
            Recording["ChannelNames"] = [StreamingTD[n]["Channel"]]
            Recording["Data"] = np.zeros((len(StreamingTD[n]["Data"]), 1))
            Recording["Data"][:,0] = StreamingTD[n]["Data"]
            Recording["Missing"] = np.zeros((len(StreamingTD[n]["Missing"]), 1))
            Recording["Missing"][:,0] = StreamingTD[n]["Missing"]
            if StreamingTD[n]["Ticks"][0] > 3276800:
                StreamingTD[n]["Ticks"][0] -= 3276800
            Recording["StartTime"] = StreamingTD[n]["FirstPacketDateTime"] + (StreamingTD[n]["Ticks"][0]%1000)/1000
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            TimeDomainRecordings.append(Recording)
            n += 1

        elif StreamingTD[n]["FirstPacketDateTime"] == StreamingTD[n+1]["FirstPacketDateTime"]:
            Recording = dict()
            Recording["SamplingRate"] = StreamingTD[n]["SamplingRate"]
            Recording["ChannelNames"] = [StreamingTD[n]["Channel"], StreamingTD[n+1]["Channel"]]
            
            if not len(StreamingTD[n]["Data"]) == len(StreamingTD[n+1]["Data"]):
                Recording["Data"] = np.zeros((np.max((len(StreamingTD[n]["Data"]),len(StreamingTD[n+1]["Data"]))), 2))
                Recording["Missing"] = np.ones((np.max((len(StreamingTD[n]["Data"]),len(StreamingTD[n+1]["Data"]))), 2))
                Recording["Data"][:len(StreamingTD[n]["Data"]),0] = StreamingTD[n]["Data"]
                Recording["Data"][:len(StreamingTD[n+1]["Data"]),1] = StreamingTD[n+1]["Data"]
                Recording["Missing"][:len(StreamingTD[n]["Data"]),0] = StreamingTD[n]["Missing"]
                Recording["Missing"][:len(StreamingTD[n+1]["Data"]),1] = StreamingTD[n+1]["Missing"]
            else:
                Recording["Data"] = np.zeros((len(StreamingTD[n]["Data"]), 2))
                Recording["Missing"] = np.ones((len(StreamingTD[n]["Missing"]), 2))
                Recording["Data"][:,0] = StreamingTD[n]["Data"]
                Recording["Data"][:,1] = StreamingTD[n+1]["Data"]
                Recording["Missing"][:,0] = StreamingTD[n]["Missing"]
                Recording["Missing"][:,1] = StreamingTD[n+1]["Missing"]

            if StreamingTD[n]["Ticks"][0] > 3276800:
                StreamingTD[n]["Ticks"][0] -= 3276800
            Recording["StartTime"] = StreamingTD[n]["FirstPacketDateTime"] + (StreamingTD[n]["Ticks"][0]%1000)/1000
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            TimeDomainRecordings.append(Recording)
            n += 2

        else:
            Recording = dict()
            Recording["SamplingRate"] = StreamingTD[n]["SamplingRate"]
            Recording["ChannelNames"] = [StreamingTD[n]["Channel"]]
            Recording["Data"] = np.zeros((len(StreamingTD[n]["Data"]), 1))
            Recording["Data"][:,0] = StreamingTD[n]["Data"]
            Recording["Missing"] = np.zeros((len(StreamingTD[n]["Missing"]), 1))
            Recording["Missing"][:,0] = StreamingTD[n]["Missing"]
            if StreamingTD[n]["Ticks"][0] > 3276800:
                StreamingTD[n]["Ticks"][0] -= 3276800
            Recording["StartTime"] = StreamingTD[n]["FirstPacketDateTime"] + (StreamingTD[n]["Ticks"][0]%1000)/1000
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            TimeDomainRecordings.append(Recording)
            n += 1

    for n in range(len(StreamingPower)):
        Recording = dict()
        Recording["SamplingRate"] = StreamingPower[n]["SamplingRate"]
        Channel = StreamingPower[n]["Channel"].split(",")
        if len(Channel) == 1:
            Recording["ChannelNames"] = [Channel[0] + " Power", Channel[0] + " Stimulation"]
            ChannelIndex = 0 if np.all(np.array(StreamingPower[n]["Power"][:,1]) == 0) else 1
            Recording["Data"] = np.zeros((len(StreamingPower[n]["Power"]), 2))
            Recording["Missing"] = np.zeros((len(StreamingPower[n]["Missing"]), 2))
            Recording["Data"][:,0] = StreamingPower[n]["Power"][:,ChannelIndex]
            Recording["Data"][:,1] = StreamingPower[n]["Stimulation"][:,ChannelIndex]
            Recording["Missing"][:,0] = StreamingPower[n]["Missing"][:,ChannelIndex]
            Recording["Missing"][:,1] = StreamingPower[n]["Missing"][:,ChannelIndex]
        else:
            Recording["ChannelNames"] = [Channel[0] + " Power", Channel[1] + " Power", Channel[0] + " Stimulation", Channel[1] + " Stimulation"]
            Recording["Data"] = np.zeros((len(StreamingPower[n]["Power"]), 4))
            Recording["Missing"] = np.zeros((len(StreamingPower[n]["Missing"]), 4))
            Recording["Data"][:,:2] = StreamingPower[n]["Power"]
            Recording["Data"][:,2:] = StreamingPower[n]["Stimulation"]
            Recording["Missing"][:,:2] = StreamingPower[n]["Missing"]
            Recording["Missing"][:,2:] = StreamingPower[n]["Missing"]

        if StreamingPower[n]["InitialTickInMs"] > 3276800:
            StreamingPower[n]["InitialTickInMs"] -= 3276800
        Recording["StartTime"] = StreamingPower[n]["FirstPacketDateTime"] + (StreamingPower[n]["InitialTickInMs"]%1000)/1000
        Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
        Recording["Descriptor"] = {
            "Therapy": StreamingPower[n]["TherapySnapshot"]
        }
        
        PowerDomainRecordings.append(Recording)

    if len(TimeDomainRecordings) == len(PowerDomainRecordings):
        # Fix Breaking TimeDomain Recording based on PowerDomain Recordings (Therapy) Descriptor
        i = 1
        while i < len(TimeDomainRecordings):
            # if Channel Name is not matching:
            if not TimeDomainRecordings[i]["ChannelNames"] == TimeDomainRecordings[i-1]["ChannelNames"] or not PowerDomainRecordings[i]["ChannelNames"] == PowerDomainRecordings[i-1]["ChannelNames"]:
                i += 1
                continue

            # if Therapy is not matching
            # First, we will remove LowerLimitInMilliAmps and UpperLimitInMilliAmps from comparison.
            # Because adjustment of amplitude could change such limit. 
            for ChannelName in TimeDomainRecordings[i]["ChannelNames"]:
                channels, hemisphere = Percept.reformatChannelName(ChannelName)
                PowerDomainRecordings[i]["Descriptor"]["Therapy"][hemisphere]["LowerLimitInMilliAmps"] = 0
                PowerDomainRecordings[i]["Descriptor"]["Therapy"][hemisphere]["UpperLimitInMilliAmps"] = 0
                PowerDomainRecordings[i-1]["Descriptor"]["Therapy"][hemisphere]["LowerLimitInMilliAmps"] = 0
                PowerDomainRecordings[i-1]["Descriptor"]["Therapy"][hemisphere]["UpperLimitInMilliAmps"] = 0 
            
            if not Percept.dictionaryCompare(PowerDomainRecordings[i]["Descriptor"]["Therapy"], PowerDomainRecordings[i-1]["Descriptor"]["Therapy"]):
                i += 1
                continue

            # Now that we know they are supposed to be identical. There is still the concern that "Segmented Stimulation" is not stored in SenSight Leads.
            # Our Criteria should be the following:
            #       1) 2nd Stream start stimulation amplitude = 1st Stream
            #       2) If both end/start are 0, the 1st Stream does not contain high stimulation amplitude.
            StimulationChannelIndexes = [n for n in range(len(PowerDomainRecordings[i]["ChannelNames"])) if PowerDomainRecordings[i]["ChannelNames"][n].endswith("Stimulation")]
            StartAmplitude = PowerDomainRecordings[i]["Data"][0, StimulationChannelIndexes].tolist()
            EndAmplitude = PowerDomainRecordings[i-1]["Data"][-1, StimulationChannelIndexes].tolist()
            if not StartAmplitude == EndAmplitude: 
                i += 1
                continue

            if np.max(StartAmplitude) == 0:
                PreviousUniqueAmplitudes = []
                for n in StimulationChannelIndexes:
                    PreviousUniqueAmplitudes.extend(np.unique(PowerDomainRecordings[i-1]["Data"][:, n]).tolist())

                # Stimulation Unchanged
                if not len(PreviousUniqueAmplitudes) == len(StimulationChannelIndexes): 
                    i += 1
                    continue
            
            Timeskip = TimeDomainRecordings[i]["StartTime"] - (TimeDomainRecordings[i-1]["StartTime"] + TimeDomainRecordings[i-1]["Duration"])
            if Timeskip > 120:
                i += 1
                continue

            if Timeskip < -1:
                print("Timeskip is negative. Failure in identifying StartTime?")
                i += 1
                continue

            # To Merge
            nSampleSkipped = int(Timeskip * TimeDomainRecordings[i]["SamplingRate"])
            if nSampleSkipped < 0: 
                nSampleSkipped = 0
                
            TimeDomainRecordings[i-1]["Data"] = np.concatenate((TimeDomainRecordings[i-1]["Data"], np.zeros((nSampleSkipped, TimeDomainRecordings[i-1]["Data"].shape[1])), TimeDomainRecordings[i]["Data"]))
            TimeDomainRecordings[i-1]["Missing"] = np.concatenate((TimeDomainRecordings[i-1]["Missing"], np.ones((nSampleSkipped, TimeDomainRecordings[i-1]["Missing"].shape[1])), TimeDomainRecordings[i]["Missing"]))
            TimeDomainRecordings[i-1]["Duration"] = TimeDomainRecordings[i]["StartTime"] + TimeDomainRecordings[i]["Duration"] - TimeDomainRecordings[i-1]["StartTime"]

            nSampleSkipped = int(Timeskip * PowerDomainRecordings[i]["SamplingRate"])
            if nSampleSkipped < 0: 
                nSampleSkipped = 0

            FillingData = np.zeros((nSampleSkipped, PowerDomainRecordings[i-1]["Data"].shape[1]))
            FillingData[:, StimulationChannelIndexes] = StartAmplitude
            PowerDomainRecordings[i-1]["Data"] = np.concatenate((PowerDomainRecordings[i-1]["Data"], FillingData, PowerDomainRecordings[i]["Data"]))
            PowerDomainRecordings[i-1]["Missing"] = np.concatenate((PowerDomainRecordings[i-1]["Missing"], np.ones((nSampleSkipped, PowerDomainRecordings[i-1]["Missing"].shape[1])), PowerDomainRecordings[i]["Missing"]))
            PowerDomainRecordings[i-1]["Duration"] = PowerDomainRecordings[i]["StartTime"] + PowerDomainRecordings[i]["Duration"] - PowerDomainRecordings[i-1]["StartTime"]

            del(PowerDomainRecordings[i])
            del(TimeDomainRecordings[i])
    
    TimeDomainRecordingModel = []
    for i in range(len(TimeDomainRecordings)):
        recording_date = datetime.fromtimestamp(TimeDomainRecordings[i]["StartTime"]).astimezone(tz=pytz.utc)
        recording_info = {"Channel": TimeDomainRecordings[i]["ChannelNames"]}
        if not models.NeuralActivityRecording.objects.filter(device_deidentified_id=deviceID, recording_type="BrainSenseStreamTimeDomain", recording_date=recording_date, recording_info__Channel=TimeDomainRecordings[i]["ChannelNames"]).exists():
            recording = models.NeuralActivityRecording(device_deidentified_id=deviceID, recording_date=recording_date, source_file=sourceFile, recording_type="BrainSenseStreamTimeDomain", recording_info=recording_info)
            filename = Database.saveSourceFiles(TimeDomainRecordings[i], "BrainSenseStreamTimeDomain", "Raw", recording.recording_id, recording.device_deidentified_id)
            recording.recording_datapointer = filename
            recording.recording_duration = TimeDomainRecordings[i]["Duration"]
            recording.save()
            TimeDomainRecordingModel.append(recording)
            NewRecordingFound = True
        else:
            recording = models.NeuralActivityRecording.objects.filter(device_deidentified_id=deviceID, recording_type="BrainSenseStreamTimeDomain", recording_date=recording_date, recording_info__Channel=TimeDomainRecordings[i]["ChannelNames"]).first()
            TimeDomainRecordingModel.append(recording)

    PowerDomainRecordingModel = []
    for i in range(len(PowerDomainRecordings)):
        recording_date = datetime.fromtimestamp(PowerDomainRecordings[i]["StartTime"]).astimezone(tz=pytz.utc)
        recording_info = {"Channel": PowerDomainRecordings[i]["ChannelNames"]}
        if not models.NeuralActivityRecording.objects.filter(device_deidentified_id=deviceID, recording_type="BrainSenseStreamPowerDomain", recording_date=recording_date, recording_info__Channel=PowerDomainRecordings[i]["ChannelNames"]).exists():
            recording = models.NeuralActivityRecording(device_deidentified_id=deviceID, recording_date=recording_date, source_file=sourceFile, recording_type="BrainSenseStreamPowerDomain", recording_info=recording_info)
            filename = Database.saveSourceFiles(PowerDomainRecordings[i], "BrainSenseStreamPowerDomain", "Raw", recording.recording_id, recording.device_deidentified_id)
            recording.recording_datapointer = filename
            recording.recording_duration = PowerDomainRecordings[i]["Duration"]
            recording.save()
            PowerDomainRecordingModel.append(recording)
            NewRecordingFound = True
        else:
            recording = models.NeuralActivityRecording.objects.filter(device_deidentified_id=deviceID, recording_type="BrainSenseStreamPowerDomain", recording_date=recording_date, recording_info__Channel=PowerDomainRecordings[i]["ChannelNames"]).first()
            PowerDomainRecordingModel.append(recording)

    for i in range(len(TimeDomainRecordings)):
        recording_date = datetime.fromtimestamp(TimeDomainRecordings[i]["StartTime"]).astimezone(tz=pytz.utc)
        CorrespondingRecordingFound = False
        for j in range(len(PowerDomainRecordings)):
            LatestStartTime = np.max((PowerDomainRecordings[j]["StartTime"], TimeDomainRecordings[i]["StartTime"]))
            EarliestEndTime = np.min((PowerDomainRecordings[j]["StartTime"] + PowerDomainRecordings[j]["Duration"], TimeDomainRecordings[i]["StartTime"] + TimeDomainRecordings[i]["Duration"]))
            ShortestDuration = np.min((PowerDomainRecordings[j]["Duration"], TimeDomainRecordings[i]["Duration"]))
            if LatestStartTime <= EarliestEndTime:
                Overlap = (EarliestEndTime - LatestStartTime) / ShortestDuration
                if Overlap > 0.7 and Overlap < 1.3:
                    if CorrespondingRecordingFound:
                        raise Exception("Multiple Corresponding Power Channel?")
                
                    if not models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=deviceID, analysis_name="DefaultBrainSenseStreaming", analysis_date=recording_date).exists():
                        recording_list = [str(TimeDomainRecordingModel[i].recording_id), str(PowerDomainRecordingModel[j].recording_id)]
                        recording_type = ["BrainSenseRecording", "BrainSenseRecording"]
                        models.CombinedRecordingAnalysis(device_deidentified_id=deviceID, analysis_name="DefaultBrainSenseStreaming", analysis_date=recording_date, 
                                                                    recording_list=recording_list, recording_type=recording_type).save()
                        CorrespondingRecordingFound = True
                else:
                    print(f"Matching Data with low overlap: {Overlap} - {ShortestDuration}")
    
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

    stream["TimeDomain"]["Wavelet"] = list()
    stream["TimeDomain"]["Spectrogram"] = list()
    stream["TimeDomain"]["Filtered"] = list()

    for i in range(len(stream["TimeDomain"]["ChannelNames"])):
        [b,a] = signal.butter(5, np.array([1,100])*2/stream["TimeDomain"]["SamplingRate"], 'bp', output='ba')
        stream["TimeDomain"]["Filtered"].append(signal.filtfilt(b, a, stream["TimeDomain"]["Data"][:,i]))

        if cardiacFilter:
            # Cardiac Filter
            posPeaks,_ = signal.find_peaks(stream["TimeDomain"]["Filtered"][i], prominence=[10,200], distance=stream["TimeDomain"]["SamplingRate"]*0.5)
            PosCardiacVariability = np.std(np.diff(posPeaks))
            negPeaks,_ = signal.find_peaks(-stream["TimeDomain"]["Filtered"][i], prominence=[10,200], distance=stream["TimeDomain"]["SamplingRate"]*0.5)
            NegCardiacVariability = np.std(np.diff(negPeaks))

            if PosCardiacVariability < NegCardiacVariability:
                peaks = posPeaks
            else:
                peaks = negPeaks
            CardiacRate = int(np.mean(np.diff(peaks)))

            PrePeak = int(CardiacRate*0.25)
            PostPeak = int(CardiacRate*0.65)
            EKGMatrix = np.zeros((len(peaks)-2,PrePeak+PostPeak))
            for j in range(1,len(peaks)-1):
                if peaks[j]+PostPeak < len(stream["TimeDomain"]["Filtered"][i]) and peaks[j]-PrePeak > 0:
                    EKGMatrix[j-1,:] = stream["TimeDomain"]["Filtered"][i][peaks[j]-PrePeak:peaks[j]+PostPeak]

            EKGTemplate = np.mean(EKGMatrix,axis=0)
            EKGTemplate = EKGTemplate / (np.max(EKGTemplate)-np.min(EKGTemplate))

            def EKGTemplateFunc(xdata, amplitude, offset):
                return EKGTemplate * amplitude + offset

            for j in range(len(peaks)):
                if peaks[j]-PrePeak < 0:
                    pass
                elif peaks[j]+PostPeak >= len(stream["TimeDomain"]["Filtered"][i]) :
                    pass
                else:
                    sliceSelection = np.arange(peaks[j]-PrePeak,peaks[j]+PostPeak)
                    params, covmat = optimize.curve_fit(EKGTemplateFunc, sliceSelection, stream["TimeDomain"]["Filtered"][i][sliceSelection])
                    stream["TimeDomain"]["Filtered"][i][sliceSelection] = stream["TimeDomain"]["Filtered"][i][sliceSelection] - EKGTemplateFunc(sliceSelection, *params)

        # Wavelet Computation
        stream["TimeDomain"]["Wavelet"].append(SPU.waveletTimeFrequency(stream["TimeDomain"]["Filtered"][i], freq=np.arange(0.5,100.5,0.5), ma=int(stream["TimeDomain"]["SamplingRate"]/2), fs=stream["TimeDomain"]["SamplingRate"]))
        stream["TimeDomain"]["Wavelet"][i]["Missing"] = stream["TimeDomain"]["Missing"][:,i][::int(stream["TimeDomain"]["SamplingRate"]/2)]
        stream["TimeDomain"]["Wavelet"][i]["Power"] = stream["TimeDomain"]["Wavelet"][i]["Power"][:,::int(stream["TimeDomain"]["SamplingRate"]/2)]
        stream["TimeDomain"]["Wavelet"][i]["Time"] = stream["TimeDomain"]["Wavelet"][i]["Time"][::int(stream["TimeDomain"]["SamplingRate"]/2)]
        stream["TimeDomain"]["Wavelet"][i]["Type"] = "Wavelet"
        del(stream["TimeDomain"]["Wavelet"][i]["logPower"])

        # SFFT Computation
        stream["TimeDomain"]["Spectrogram"].append(SPU.defaultSpectrogram(stream["TimeDomain"]["Filtered"][i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=stream["TimeDomain"]["SamplingRate"]))
        stream["TimeDomain"]["Spectrogram"][i]["Type"] = "Spectrogram"
        stream["TimeDomain"]["Spectrogram"][i]["Time"] += 0 # TODO Check later
        
        TimeArray = np.arange(len(stream["TimeDomain"]["Filtered"][i])) / stream["TimeDomain"]["SamplingRate"]
        stream["TimeDomain"]["Spectrogram"][i]["Missing"] = np.zeros(stream["TimeDomain"]["Spectrogram"][i]["Time"].shape, dtype=bool)
        for j in range(len(stream["TimeDomain"]["Spectrogram"][i]["Missing"])):
            if np.any(stream["TimeDomain"]["Missing"][rangeSelection(TimeArray, [stream["TimeDomain"]["Spectrogram"][i]["Time"][j]-2, stream["TimeDomain"]["Spectrogram"][i]["Time"][j]+2]), i]):
                stream["TimeDomain"]["Spectrogram"][i]["Missing"][j] = True
        del(stream["TimeDomain"]["Spectrogram"][i]["logPower"])

    return stream

def queryRealtimeStreamRecording(analysis, cardiacFilter=False, refresh=False):
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

    allRecordings = models.NeuralActivityRecording.objects.filter(recording_id__in=analysis.recording_list)
    PowerRecording = None
    TimeRecording = None
    for recording in allRecordings:
        if recording.recording_type == "BrainSenseStreamPowerDomain":
            PowerRecording = recording
        elif recording.recording_type == "BrainSenseStreamTimeDomain":
            TimeRecording = recording
    
    Device = models.PerceptDevice.objects.filter(deidentified_id=TimeRecording.device_deidentified_id).first()
    if Device:
        leads = Device.device_lead_configurations
    else:
        leads = {}
        
    BrainSenseData = dict()
    BrainSenseData["Info"] = dict({"Leads": leads})
    if PowerRecording:
        BrainSenseData["Info"].update(PowerRecording.recording_info)
        BrainSenseData["PowerDomain"] = Database.loadSourceDataPointer(PowerRecording.recording_datapointer)
    
    if TimeRecording:
        BrainSenseData["Info"].update(TimeRecording.recording_info)
        BrainSenseData["TimeDomain"] = Database.loadSourceDataPointer(TimeRecording.recording_datapointer)
    
    if not "CardiacFilter" in TimeRecording.recording_info:
        TimeRecording.recording_info["CardiacFilter"] = cardiacFilter
        TimeRecording.save()

    if not "Spectrogram" in BrainSenseData["TimeDomain"].keys() or (refresh or not TimeRecording.recording_info["CardiacFilter"] == cardiacFilter):
        TimeRecording.recording_info["CardiacFilter"] = cardiacFilter
        BrainSenseData = processRealtimeStreams(BrainSenseData, cardiacFilter=cardiacFilter)
        Database.saveSourceFiles(BrainSenseData["TimeDomain"], "BrainSenseStreamTimeDomain", "Raw", TimeRecording.recording_id, TimeRecording.device_deidentified_id)
        TimeRecording.save()
    
    if "Alignment" in PowerRecording.recording_info.keys():
        BrainSenseData["PowerDomain"]["StartTime"] += PowerRecording.recording_info["Alignment"]/1000
    
    BrainSenseData["Timestamp"] = analysis.analysis_date.timestamp()
    BrainSenseData["Info"].update(PowerRecording.recording_info)
    BrainSenseData["Info"].update(TimeRecording.recording_info)
    BrainSenseData["Info"]["Device"] = "Percept PC"

    RecordingID = analysis.deidentified_id
    
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

    recordings = models.NeuralActivityRecording.objects.filter(recording_id__in=recordingIds, recording_type="BrainSenseStream").all()
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

                cIndex = 0
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

def processRealtimeStreamRenderingData(stream, options=dict(), centerFrequencies=[0,0], stimulationReference="Ipsilateral"):
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
    
    stream["PowerDomain"]["Stimulation"] = processRealtimeStreamStimulationAmplitude(stream["PowerDomain"])
    stream["PowerDomain"]["PowerBand"] = processRealtimeStreamPowerBand(stream["PowerDomain"])

    data = dict()
    data["Channels"] = stream["TimeDomain"]["ChannelNames"]
    data["Stimulation"] = stream["PowerDomain"]["Stimulation"]
    data["PowerBand"] = stream["PowerDomain"]["PowerBand"]
    data["Info"] = stream["Info"]
    data["Timestamp"] = stream["TimeDomain"]["StartTime"]
    data["PowerTimestamp"] = stream["PowerDomain"]["StartTime"]
    data["Annotations"] = stream["Annotations"]

    if len(centerFrequencies) < len(stream["TimeDomain"]["ChannelNames"]):
        centerFrequencies.append(0)
    
    data["Stream"] = list()
    for counter in range(len(data["Channels"])):
        data["Stream"].append(dict())
        data["Stream"][counter]["RawData"] = stream["TimeDomain"]["Filtered"][counter]
        data["Stream"][counter]["Time"] = np.arange(len(data["Stream"][counter]["RawData"]))/stream["TimeDomain"]["SamplingRate"]

        if options["SpectrogramMethod"]["value"] == "Spectrogram":
            data["Stream"][counter]["Spectrogram"] = copy.deepcopy(stream["TimeDomain"]["Spectrogram"][counter])
            data["Stream"][counter]["Spectrogram"]["Power"][data["Stream"][counter]["Spectrogram"]["Power"] == 0] = 1e-10
            data["Stream"][counter]["Spectrogram"]["Power"] = np.log10(data["Stream"][counter]["Spectrogram"]["Power"])*10
            data["Stream"][counter]["Spectrogram"]["ColorRange"] = [-20,20]

        elif options["SpectrogramMethod"]["value"]  == "Wavelet":
            data["Stream"][counter]["Spectrogram"] = copy.deepcopy(stream["TimeDomain"]["Wavelet"][counter])
            data["Stream"][counter]["Spectrogram"]["Power"][data["Stream"][counter]["Spectrogram"]["Power"] == 0] = 1e-10
            data["Stream"][counter]["Spectrogram"]["Power"] = np.log10(data["Stream"][counter]["Spectrogram"]["Power"])*10
            data["Stream"][counter]["Spectrogram"]["ColorRange"] = [-10,20]

        if options["PSDMethod"]["value"] == "Time-Frequency Analysis":
            data["Stream"][counter]["StimPSD"] = processRealtimeStreamStimulationPSD(stream, data["Channels"][counter], method=options["SpectrogramMethod"]["value"], stim_label=stimulationReference, centerFrequency=centerFrequencies[counter])
        else:
            data["Stream"][counter]["StimPSD"] = processRealtimeStreamStimulationPSD(stream, data["Channels"][counter], method=options["PSDMethod"]["value"], stim_label=stimulationReference, centerFrequency=centerFrequencies[counter])
        counter += 1

    return data

def processRealtimeStreamStimulationAmplitude(stream):
    """ Process BrainSense Streaming Data to extract data segment at different stimulation amplitude.

    Args:
      stream: processed BrainSense PowerDomain structure (see processRealtimeStreams function)

    Returns:
      Returns list of stimulation series.
    """

    StimulationSeries = list()
    StimulationChannelIndexes = [i for i in range(len(stream["ChannelNames"])) if stream["ChannelNames"][i].endswith("Stimulation")]
    for StimulationSide in StimulationChannelIndexes:
        Stimulation = np.around(stream["Data"][:,StimulationSide],2)
        TimeArray = np.arange(len(Stimulation)) / stream["SamplingRate"]
        indexOfChanges = np.where(np.abs(np.diff(Stimulation)) > 0)[0]+1
        if len(indexOfChanges) == 0:
            indexOfChanges = np.insert(indexOfChanges,0,0)
        elif indexOfChanges[0] < 0:
            indexOfChanges[0] = 0
        else:
            indexOfChanges = np.insert(indexOfChanges,0,0)
        indexOfChanges = np.insert(indexOfChanges,len(indexOfChanges),len(Stimulation)-1)
        ChannelName = stream["ChannelNames"][StimulationSide].replace(" Stimulation","")
        channels, hemisphere = Percept.reformatChannelName(ChannelName)
        StimulationSeries.append({"Name": ChannelName, "Hemisphere": hemisphere, "LegendName": f"E{channels[0]:02}-E{channels[1]:02}", "Time": TimeArray[indexOfChanges], "Amplitude": np.around(stream["Data"][indexOfChanges,StimulationSide],2)})
    return StimulationSeries

def processRealtimeStreamPowerBand(stream):
    """ Extract Onboard Power-band recording.

    Additional filtering is done by performing zscore normalization. Outliers are removed. 

    Args:
      stream: processed BrainSense PowerDomain structure (see processRealtimeStreams function)

    Returns:
      Returns list of stimulation series.
    """
    
    PowerSensing = list()
    PowerIndexes = [i for i in range(len(stream["ChannelNames"])) if stream["ChannelNames"][i].endswith("Power")]
    for StimulationSide in PowerIndexes:
        Power = stream["Data"][:,StimulationSide]
        TimeArray = np.arange(len(Power)) / stream["SamplingRate"]
        selectedData = np.abs(stats.zscore(Power)) < 3
        ChannelName = stream["ChannelNames"][StimulationSide].replace(" Power","")
        channels, hemisphere = Percept.reformatChannelName(ChannelName)
        PowerSensing.append({"Name": ChannelName, "Hemisphere": hemisphere, "LegendName": f"E{channels[0]:02}-E{channels[1]:02}<br>Sense {stream['Descriptor']['Therapy'][hemisphere]['FrequencyInHertz']}Hz", "Time": TimeArray[selectedData], "Power": Power[selectedData]})
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
        for Stimulation in stream["PowerDomain"]["Stimulation"]:
            if Stimulation["Name"] == channel:
                StimulationSeries = Stimulation
    else:
        for Stimulation in stream["PowerDomain"]["Stimulation"]:
            if not Stimulation["Name"] == channel:
                StimulationSeries = Stimulation

    if not "StimulationSeries" in locals():
        raise Exception("Data not available")
    
    TimeArray = np.arange(stream["TimeDomain"]["Data"].shape[0])/stream["TimeDomain"]["SamplingRate"]
    TimeShift = stream["TimeDomain"]["StartTime"] - stream["PowerDomain"]["StartTime"]
    DataIndex = [i for i in range(len(stream["TimeDomain"]["ChannelNames"])) if stream["TimeDomain"]["ChannelNames"][i] == channel][0]
    
    cIndex = 0
    StimulationEpochs = list()
    for i in range(1,len(StimulationSeries["Time"])):
        cIndex += 1 

        if method == "Welch":
            timeSelection = rangeSelection(TimeArray+TimeShift,[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            timeSelection = np.bitwise_and(timeSelection, stream["TimeDomain"]["Missing"][:,DataIndex] == 0)
            if np.sum(timeSelection) < 250 * 5:
                continue
            StimulationEpoch = stream["TimeDomain"]["Filtered"][DataIndex][timeSelection]
            fxx, pxx = signal.welch(StimulationEpoch, fs=stream["TimeDomain"]["SamplingRate"], nperseg=250 * 1, noverlap=250 * 0.5, nfft=250 * 2, scaling="density")
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i-1], "Frequency": fxx, "PSD": pxx})
            timeSelection = rangeSelection(stream["TimeDomain"]["Spectrogram"][DataIndex]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])

        elif method == "Spectrogram":
            timeSelection = rangeSelection(stream["TimeDomain"]["Spectrogram"][DataIndex]["Time"]+TimeShift,[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            timeSelection = np.bitwise_and(timeSelection, stream["TimeDomain"]["Spectrogram"][DataIndex]["Missing"] == 0)
            if np.sum(timeSelection) < 2 * 5:
                continue
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i-1], "Frequency": stream["TimeDomain"]["Spectrogram"][DataIndex]["Frequency"], "PSD": np.mean(stream["TimeDomain"]["Spectrogram"][DataIndex]["Power"][:,timeSelection],axis=1)})

        elif method == "Wavelet":
            timeSelection = rangeSelection(stream["TimeDomain"]["Wavelet"][DataIndex]["Time"]+TimeShift,[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            if np.sum(timeSelection) < 2 * 5:
                continue
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i-1], "Frequency": stream["TimeDomain"]["Wavelet"][DataIndex]["Frequency"], "PSD": np.mean(stream["TimeDomain"]["Wavelet"][DataIndex]["Power"][:,timeSelection],axis=1)})

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

        if method == "Welch":
            StimulationEpochs[i]["SpectralFeatures"] = StimulationEpochs[i]["PSD"].reshape((len(StimulationEpochs[i]["PSD"]),1))
        elif method == "Spectrogram":
            timeSelection = np.bitwise_and(StimulationEpochs[i]["TimeSelection"], stream["TimeDomain"]["Spectrogram"][DataIndex]["Missing"] == 0)
            StimulationEpochs[i]["SpectralFeatures"] = stream["TimeDomain"]["Spectrogram"][DataIndex]["Power"][:,timeSelection]
        elif method == "Wavelet":
            timeSelection = np.bitwise_and(StimulationEpochs[i]["TimeSelection"], stream["TimeDomain"]["Wavelet"][DataIndex]["Missing"] == 0)
            StimulationEpochs[i]["SpectralFeatures"] = stream["TimeDomain"]["Wavelet"][DataIndex]["Power"][:,timeSelection]

        StimulationEpochs[i]["SpectralFeatures"] = np.mean(StimulationEpochs[i]["SpectralFeatures"][frequencySelection,:],axis=0)
        del(StimulationEpochs[i]["TimeSelection"])

    return StimulationEpochs
