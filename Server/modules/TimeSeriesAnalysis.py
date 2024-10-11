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
Python Module for Time-series Analysis
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())

import json
import uuid
import numpy as np
import copy
from shutil import copyfile, rmtree
from datetime import datetime, date, timedelta
import dateutil, pytz
import pickle
import pandas as pd

from scipy import signal, stats, optimize, interpolate
from specparam import SpectralModel

from decoder import Percept
from utility import SignalProcessingUtility as SPU
from utility.PythonUtility import rangeSelection

from Backend import models
from modules import Database
from modules.Percept import BrainSenseStream

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

TimeSeriesLabels = ["BrainSenseTimeDomain", "BrainSenseSurvey"]

def queryAvailableAnalysis(experiment, analysis_type):
    availableAnalyses = []
    for analysis in experiment.analyses:
        availableAnalyses.append({
            "uid": analysis.uid,
            "type": analysis.type,
            "name": analysis.name,
            "status": analysis.status,
            "date": analysis.date,
            "recordings": [recording.uid for recording in analysis.recordings],
            "time_shift": [analysis.recordings.relationship(recording).time_shift for recording in analysis.recordings]
        })
    
    availableRecordings = []
    for source_file in experiment.source_files:
        if len(source_file.device) > 0:
            deviceInfo = source_file.device.get().getInfo()
            for recording in source_file.recordings:
                if type(recording) == models.TimeSeriesRecording:
                    availableRecordings.append({
                        "date": recording.date, "duration": recording.duration, 
                        "type": recording.type, "uid": recording.uid, "labels": recording.labels if recording.labels else [],
                        "channels": recording.channel_names, "device": deviceInfo,
                    })
    
    for i in range(len(availableAnalyses)):
        availableAnalyses[i]["duration"] = 0
        for j in availableRecordings: 
            if j["uid"] in availableAnalyses[i]["recordings"]:
                availableAnalyses[i]["duration"] += j["duration"]

    return {"analyses": availableAnalyses, "recordings": sorted(availableRecordings, key=lambda item: item["date"])}

def queryAnalysisResult(analysis, config):
    Recordings = []
    if analysis.type == "DefaultBrainSenseStreaming":
        Recordings = BrainSenseStream.queryTherapeuticAnalysis(analysis, config)

    for recording in Recordings:
        if recording["Type"] == "RawSignal":
            recording["Recording"] = processTimeDomainStreaming(recording["Recording"], recording["Data"], config)
            recording["Type"] = "Signal"
    
    Result = {}
    for recording in Recordings:
        if recording["Type"] == "Signal":
            Result["Signal"] = recording
        elif recording["Type"] == "Therapy":
            Result["Therapy"] = recording

    return Result

def processTimeDomainStreaming(recording, data, config):
    if config["TimeSeriesRecording"]["StandardFilter"]["value"] == "Butterworth 1-100Hz":
        [b,a] = signal.butter(5, np.array([1,100])*2/data["SamplingRate"], 'bp', output='ba')
        data["Data"] = signal.filtfilt(b, a, data["Data"], axis=0)

    if config["TimeSeriesRecording"]["NotchFilter"]["value"] == "Notch 55-65Hz":
        [b,a] = signal.butter(5, np.array([55,65])*2/data["SamplingRate"], 'bandstop', output='ba')
        data["Data"] = signal.filtfilt(b, a, data["Data"], axis=0)
    elif config["TimeSeriesRecording"]["NotchFilter"]["value"] == "Notch 45-55Hz":
        [b,a] = signal.butter(5, np.array([45,55])*2/data["SamplingRate"], 'bandstop', output='ba')
        data["Data"] = signal.filtfilt(b, a, data["Data"], axis=0)

    for i in range(len(data["ChannelNames"])):
        if config["TimeSeriesRecording"]["WienerFilter"]["value"] == "Use Wiener Filter":
            data["Data"][:,i] -= signal.wiener(data["Data"][:,i], mysize=int(data["SamplingRate"] / 2))

    if config["TimeSeriesRecording"]["CardiacFilter"]["value"] == "Use Adaptive Template Matching":
        data = handleCardiacFilter(recording, data, {
            "StandardFilter": config["TimeSeriesRecording"]["StandardFilter"]["value"],
            "NotchFilter": config["TimeSeriesRecording"]["NotchFilter"]["value"],
            "WienerFilter": config["TimeSeriesRecording"]["WienerFilter"]["value"],
            "CardiacFilter": config["TimeSeriesRecording"]["CardiacFilter"]["value"]
        })
        
    data = handleTimeFrequencyAnalysis(recording, data, {
        "StandardFilter": config["TimeSeriesRecording"]["StandardFilter"]["value"],
        "NotchFilter": config["TimeSeriesRecording"]["NotchFilter"]["value"],
        "WienerFilter": config["TimeSeriesRecording"]["WienerFilter"]["value"],
        "CardiacFilter": config["TimeSeriesRecording"]["CardiacFilter"]["value"],
        "SpectrogramMethod": config["TimeSeriesRecording"]["SpectrogramMethod"]["value"],
        "BaselineCorrection": config["TimeSeriesRecording"]["BaselineCorrection"]["value"],
        "Normalization": config["TimeSeriesRecording"]["Normalization"]["value"]
    })

    return data

def handleCardiacFilter(recording, data, config):
    FoundProcessed = False
    for processed in recording.processed:
        ProcessedModel = recording.processed.relationship(processed)
        if ProcessedModel.type == "CardiacFiltered":
            if Database.checkConfiguration(ProcessedModel.metadata, config):
                FoundProcessed = processed
    
    if FoundProcessed:
        return Database.loadSourceDataPointer(FoundProcessed.data_pointer, FoundProcessed.hashed)
    
    Window = int(data["SamplingRate"] / 2)
    for i in range(len(data["ChannelNames"])):
        KurtosisIndex = range(0, len(data["Data"][:,i])-Window)
        ExpectedKurtosis = np.zeros((len(KurtosisIndex)))
        for j in range(len(KurtosisIndex)):
            zScore = stats.zscore(data["Data"][:,i][KurtosisIndex[j]:KurtosisIndex[j]+Window])
            ExpectedKurtosis[j] = np.mean(np.power(zScore, 4))

        [b,a] = signal.butter(3, np.array([0.5, 2])*2/data["SamplingRate"], "bandpass")
        ExpectedKurtosis = signal.filtfilt(b,a,ExpectedKurtosis)
        Peaks, _ = signal.find_peaks(ExpectedKurtosis, distance=125)
        Peaks += int(Window/2)

        CardiacEpochs = []
        SearchWindow = int(data["SamplingRate"] * 0.4)
        for j in range(len(Peaks)):
            if ExpectedKurtosis[Peaks[j]-int(Window/2)] < 1.2:
                continue

            ShiftPeak = 0
            if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(data["Data"][:,i]):
                continue 
            findPeak = np.argmax(data["Data"][:,i][Peaks[j]-SearchWindow:Peaks[j]+SearchWindow])
            ShiftPeak = SearchWindow-findPeak
            if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(data["Data"][:,i]):
                continue 
            CardiacEpochs.append(data["Data"][:,i][Peaks[j]-SearchWindow-ShiftPeak:Peaks[j]+SearchWindow-ShiftPeak])

        EKGTemplate = np.mean(np.array(CardiacEpochs), axis=0)
        EKGTemplate = EKGTemplate / (np.max(EKGTemplate)-np.min(EKGTemplate))

        def EKGTemplateFunc(xdata, amplitude, offset):
            return EKGTemplate * amplitude + offset

        CardiacFiltered = copy.deepcopy(data["Data"][:,i])
        for j in range(len(Peaks)):
            ShiftPeak = 0
            if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(data["Data"][:,i]):
                continue 

            findPeak = np.argmax(data["Data"][:,i][Peaks[j]-SearchWindow:Peaks[j]+SearchWindow])
            ShiftPeak = SearchWindow-findPeak
            if Peaks[j]-SearchWindow-ShiftPeak < 0 or Peaks[j]+SearchWindow-ShiftPeak >= len(data["Data"][:,i]):
                continue
            
            sliceSelection = np.arange(Peaks[j]-SearchWindow-ShiftPeak, Peaks[j]+SearchWindow-ShiftPeak)
            Original = data["Data"][:,i][sliceSelection]
            params, covmat = optimize.curve_fit(EKGTemplateFunc, sliceSelection, Original)
            CardiacFiltered[sliceSelection] = Original - EKGTemplateFunc(sliceSelection, *params)
        data["Data"][:,i] = CardiacFiltered

    processed = models.TimeSeriesRecording(type="ProcessedTimeSeries", date=models.current_time(), 
                                            sampling_rate=data["SamplingRate"], duration=data["Duration"]).save()
    
    filename, hashed = Database.saveSourceFiles(data, "ProcessedTimeSeries", processed.uid, os.path.dirname(recording.data_pointer).split("/")[-1])
    processed.channel_names = data["ChannelNames"]
    processed.data_pointer = filename
    processed.hashed = hashed
    processed.save()

    recording.processed.connect(processed, {
        "type": "CardiacFiltered", "metadata": config
    })

    return data

def handleTimeFrequencyAnalysis(recording, data, config):
    FoundProcessed = False
    for processed in recording.processed:
        ProcessedModel = recording.processed.relationship(processed)
        if ProcessedModel.type == "TimeFrequencyAnalysis":
            if Database.checkConfiguration(ProcessedModel.metadata, config):
                FoundProcessed = processed
    
    if FoundProcessed:
        return Database.loadSourceDataPointer(FoundProcessed.data_pointer, FoundProcessed.hashed)
    
    data["Spectrum"] = []
    for i in range(len(data["ChannelNames"])):
        if config["SpectrogramMethod"] == "Welch's Periodogram":
            Spectrum = SPU.welchSpectrogram(data["Data"][:,i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=data["SamplingRate"])

        elif config["SpectrogramMethod"] == "Short-time Fourier Transform":
            Spectrum = SPU.defaultSpectrogram(data["Data"][:,i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=data["SamplingRate"])

        else: # Default Welch's Periodogram
            Spectrum = SPU.welchSpectrogram(data["Data"][:,i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=data["SamplingRate"])

        Spectrum["Missing"] = SPU.calculateMissingLabel(data["Missing"][:,i], window=1.0, overlap=0.5, fs=data["SamplingRate"])
        #Spectrum["Time"] += data["StartTime"] + (Configuration["Descriptor"][recordingId]["TimeShift"]/1000)# TODO Check later
        del Spectrum["logPower"]

        dropMissing = False
        if dropMissing:
            TimeSelection = Spectrum["Missing"] == 0
            Spectrum["Missing"] = Spectrum["Missing"][TimeSelection]
            Spectrum["Time"] = Spectrum["Time"][TimeSelection]
            Spectrum["Power"] = Spectrum["Power"][:, TimeSelection]
            Spectrum["logPower"] = Spectrum["logPower"][:, TimeSelection]
        
        if config["Normalization"] == "1/f PSD Trend Removal":
            meanPSDs = np.nanmean(np.array(Spectrum["Power"]), axis=1)
            WindowRange = [1,data["SamplingRate"]/2 if data["SamplingRate"] < 200 else 100]

            FrequencyWindow = rangeSelection(Spectrum["Frequency"], WindowRange)
            fm = SpectralModel(peak_width_limits=[1,24])
            fm.fit(np.array(Spectrum["Frequency"])[FrequencyWindow], meanPSDs[FrequencyWindow], WindowRange)
            oof = fm.get_model("aperiodic", "linear")
            
            for j in range(Spectrum["Power"].shape[1]):
                Spectrum["Power"][FrequencyWindow,j] = np.array(Spectrum["Power"][FrequencyWindow,j]) / oof

            Spectrum["Power"] = Spectrum["Power"][FrequencyWindow,:]
            Spectrum["Frequency"] = np.array(Spectrum["Frequency"])[FrequencyWindow]
            
        elif config["Normalization"] == "Gamma Band Normalize":
            meanPSDs = np.nanmean(np.array(Spectrum["Power"]), axis=1)
            FrequencyWindow = rangeSelection(Spectrum["Frequency"], [70,90])
            MeanRefPower = np.nanmean(meanPSDs[FrequencyWindow])
            for j in range(Spectrum["Power"].shape[1]):
                Spectrum["Power"][:,j] = np.array(Spectrum["Power"][:,j]) / MeanRefPower
            
        data["Spectrum"].append(Spectrum)
    
    processed = models.TimeFrequencyAnalysis(type="ProcessedTimeFrequencyAnalysis", date=models.current_time(), 
                                            sampling_rate=data["SamplingRate"], duration=data["Duration"]).save()
    
    filename, hashed = Database.saveSourceFiles(data, "ProcessedTimeFrequencyAnalysis", processed.uid, os.path.dirname(recording.data_pointer).split("/")[-1])
    processed.channel_names = data["ChannelNames"]
    processed.data_pointer = filename
    processed.hashed = hashed
    processed.save()

    recording.processed.connect(processed, {
        "type": "TimeFrequencyAnalysis", "metadata": config
    })

    return data

def extractTherapeuticPowerSpectrum(data):
    data["Therapy"]["EffectOfTherapy"] = []
    for channel in range(len(data["Signal"]["Recording"]["ChannelNames"])):
        data["Therapy"]["EffectOfTherapy"].append({
            "ChannelName": data["Signal"]["Recording"]["ChannelNames"][channel],
            "PowerSpectralDensity": [],
            "Frequency": data["Signal"]["Recording"]["Spectrum"][channel]["Frequency"]
        })
        for i in range(len(data["Therapy"]["TherapySeries"])-1):
            TimeSelection = rangeSelection(data["Signal"]["Recording"]["Spectrum"][channel]["Time"] + data["Signal"]["AlignmentOffset"], [
                data["Therapy"]["TherapySeries"][i]["Time"] + data["Therapy"]["AlignmentOffset"] + 2,
                data["Therapy"]["TherapySeries"][i+1]["Time"] + data["Therapy"]["AlignmentOffset"] - 2
            ])
            MissingSelection = data["Signal"]["Recording"]["Spectrum"][channel]["Missing"] == 0

            if np.any(TimeSelection & MissingSelection):
                PSD = np.mean(data["Signal"]["Recording"]["Spectrum"][channel]["Power"][:,TimeSelection & MissingSelection],axis=1)
                print(PSD)
                stdPSD = stats.sem(data["Signal"]["Recording"]["Spectrum"][channel]["Power"][:,TimeSelection & MissingSelection],axis=1)
                data["Therapy"]["EffectOfTherapy"][channel]["PowerSpectralDensity"].append({
                    "Mean": PSD,
                    "StdErr": stdPSD,
                    "Label": "" 
                })
            
    return data

def extractVisualizationChannel(data, channel_name=None):
    data["ChannelNames"] = copy.deepcopy(data["Signal"]["Recording"]["ChannelNames"])
    if not channel_name:
        channel_name = data["Signal"]["Recording"]["ChannelNames"][0]
    del data["Signal"]["Data"]

    ChannelIndex = -1
    for i in range(len(data["Signal"]["Recording"]["ChannelNames"])):
        if data["Signal"]["Recording"]["ChannelNames"][i] == channel_name:
            data["Signal"]["Recording"]["Data"] = data["Signal"]["Recording"]["Data"][:,i].reshape(-1,1)
            data["Signal"]["Recording"]["Spectrum"] = [data["Signal"]["Recording"]["Spectrum"][i]]
            data["Signal"]["Recording"]["ChannelNames"] = [data["Signal"]["Recording"]["ChannelNames"][i]]
            break 
    data["ActiveChannel"] = channel_name
    return data

def queryTimeSeriesRecording(recording, info=False, channel=""):
    Data = Database.loadSourceDataPointer(recording.data_pointer)
    if info:
        return {"ChannelNames": Data["ChannelNames"], "uid": recording.uid}
    
    print(Data.keys())
    if not "Spectrogram" in Data.keys():
        Data["Wavelet"] = list()
        Data["Spectrogram"] = list()
        Data["Filtered"] = list()

        for i in range(len(Data["ChannelNames"])):
            [b,a] = signal.butter(5, np.array([1,100])*2/Data["SamplingRate"], 'bp', output='ba')
            Data["Filtered"].append(signal.filtfilt(b, a, Data["Data"][:,i]))

            Data["Wavelet"].append(SPU.waveletTimeFrequency(Data["Filtered"][i], freq=np.arange(0.5,100.5,0.5), ma=int(Data["SamplingRate"]/2), fs=Data["SamplingRate"]))
            Data["Wavelet"][i]["Missing"] = Data["Missing"][:,i][::int(Data["SamplingRate"]/2)]
            Data["Wavelet"][i]["Power"] = Data["Wavelet"][i]["Power"][:,::int(Data["SamplingRate"]/2)]
            Data["Wavelet"][i]["Time"] = Data["Wavelet"][i]["Time"][::int(Data["SamplingRate"]/2)]
            Data["Wavelet"][i]["Type"] = "Wavelet"
            del(Data["Wavelet"][i]["logPower"])

            # SFFT Computation
            Data["Spectrogram"].append(SPU.defaultSpectrogram(Data["Filtered"][i], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=Data["SamplingRate"]))
            Data["Spectrogram"][i]["Type"] = "Spectrogram"
            Data["Spectrogram"][i]["Time"] += 0 # TODO Check later
            
            TimeArray = np.arange(len(Data["Filtered"][i])) / Data["SamplingRate"]
            Data["Spectrogram"][i]["Missing"] = np.zeros(Data["Spectrogram"][i]["Time"].shape, dtype=bool)
            for j in range(len(Data["Spectrogram"][i]["Missing"])):
                if np.any(Data["Missing"][rangeSelection(TimeArray, [Data["Spectrogram"][i]["Time"][j]-2, Data["Spectrogram"][i]["Time"][j]+2]), i]):
                    Data["Spectrogram"][i]["Missing"][j] = True
            del(Data["Spectrogram"][i]["logPower"])
            
        Database.saveSourceFiles(Data, filename=recording.data_pointer)

    Data["Annotations"] = [{"time": item.date, "name": item.name, "duration": item.duration} for item in recording.annotations]
    if channel == "":
        return Data
    else:
        for i in range(len(Data["ChannelNames"])):
            if Data["ChannelNames"][i] == channel:
                Data = {
                    "StartTime": Data["StartTime"],
                    "SamplingRate": Data["SamplingRate"],
                    "Filtered": Data["Filtered"][i],
                    "Spectrum": Data["Spectrogram"][i]
                }
                Data["Spectrum"]["Power"] = 10*np.log10(Data["Spectrum"]["Power"])
                return Data
            
    return None

def processTimeSeriesAnalysis(analysis):
    data = {"Timeseries": {}, "Spectrograms": {}, "ChannelInfo": {}, "Annotations": {}}
    for recording in analysis.recordings:
        TimeSeriesRecording = None
        rel = analysis.recordings.relationship(recording)
        for i in range(len(recording.channel_names)):
            if rel.data_type[i] != "":
                TimeSeriesRecording = queryTimeSeriesRecording(recording)
                break
        
        if TimeSeriesRecording:
            for i in range(len(recording.channel_names)):
                if rel.data_type[i] != "":
                    if not rel.data_type[i] in data["Timeseries"].keys():
                        data["Timeseries"][rel.data_type[i]] = []
                        data["Spectrograms"][rel.data_type[i]] = []
                        data["ChannelInfo"][rel.data_type[i]] = []
                        data["Annotations"][rel.data_type[i]] = []
                    
                    data["Timeseries"][rel.data_type[i]].append(TimeSeriesRecording["Filtered"][i])
                    
                    TimeSeriesRecording["Spectrogram"][i]["Power"] = 10*np.log10(TimeSeriesRecording["Spectrogram"][i]["Power"])
                    data["Spectrograms"][rel.data_type[i]].append(TimeSeriesRecording["Spectrogram"][i])
                    data["Annotations"][rel.data_type[i]].append(TimeSeriesRecording["Annotations"])
                    
                    data["ChannelInfo"][rel.data_type[i]].append({"ChannelName": recording.channel_names[i], 
                                                                  "SamplingRate": TimeSeriesRecording["SamplingRate"], 
                                                                  "StartTime": TimeSeriesRecording["StartTime"] + rel.time_shift,
                                                                  "RecordingUID": recording.uid})
    data = processAnnotationAnalysis(data)
    return data

def processAnnotationAnalysis(data):
    EventOnsetSpectrum = {}
    EventPSDs = {}
    SpectrumConfig = {}

    for data_type in data["Annotations"]:
        for i in range(len(data["Annotations"][data_type])):
            for annotation in data["Annotations"][data_type][i]:
                if annotation["duration"] > 0:
                    if not annotation["name"] in EventPSDs.keys():
                        EventPSDs[annotation["name"]] = {}
                    if not data["ChannelInfo"][data_type][i]["ChannelName"] in EventPSDs[annotation["name"]].keys():
                        EventPSDs[annotation["name"]][data["ChannelInfo"][data_type][i]["ChannelName"]] = []
                    
                    EventStartTime = annotation["time"] - data["ChannelInfo"][data_type][i]["StartTime"]
                    TimeSelection = rangeSelection(data["Spectrograms"][data_type][i]["Time"], [EventStartTime, EventStartTime+annotation["duration"]])
                    PSDs = data["Spectrograms"][data_type][i]["Power"][:, TimeSelection]
                    EventPSDs[annotation["name"]][data["ChannelInfo"][data_type][i]["ChannelName"]].append(np.mean(PSDs,axis=1))

                else:
                    if not annotation["name"] in EventOnsetSpectrum.keys():
                        EventOnsetSpectrum[annotation["name"]] = {}
                    if not data["ChannelInfo"][data_type][i]["ChannelName"] in EventOnsetSpectrum[annotation["name"]].keys():
                        EventOnsetSpectrum[annotation["name"]][data["ChannelInfo"][data_type][i]["ChannelName"]] = []

                    TimePerPSD = data["Spectrograms"][data_type][i]["Config"]["Window"] - data["Spectrograms"][data_type][i]["Config"]["Overlap"]
                    EventStartTime = annotation["time"] - data["ChannelInfo"][data_type][i]["StartTime"]
                    _, index = findClosest(data["Spectrograms"][data_type][i]["Time"], EventStartTime)
                    PSDs = data["Spectrograms"][data_type][i]["Power"][:, int(index-5/TimePerPSD):int(index+5/TimePerPSD+1)]
                    EventOnsetSpectrum[annotation["name"]][data["ChannelInfo"][data_type][i]["ChannelName"]].append(PSDs)
                
                if not data["ChannelInfo"][data_type][i]["ChannelName"] in SpectrumConfig.keys():
                    SpectrumConfig[data["ChannelInfo"][data_type][i]["ChannelName"]] = {"Frequency": data["Spectrograms"][data_type][i]["Frequency"],
                                                                                        "Time": int(5/TimePerPSD)}
    
    for annotation in EventOnsetSpectrum.keys():
        for channel in EventOnsetSpectrum[annotation].keys():
            EventOnsetSpectrum[annotation][channel] = np.mean(np.array(EventOnsetSpectrum[annotation][channel]), axis=0).tolist()
    
    data["EventPSDs"] = EventPSDs
    data["EventOnsetSpectrum"] = EventOnsetSpectrum
    data["SpectrumConfig"] = SpectrumConfig
    return data

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
    BrainSenseData["Info"].update(PowerRecording.recording_info)
    BrainSenseData["Info"].update(TimeRecording.recording_info)

    BrainSenseData["TimeDomain"] = Database.loadSourceDataPointer(TimeRecording.recording_datapointer)
    BrainSenseData["PowerDomain"] = Database.loadSourceDataPointer(PowerRecording.recording_datapointer)
    
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
