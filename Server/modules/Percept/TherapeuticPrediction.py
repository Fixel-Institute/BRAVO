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
from sklearn.ensemble import RandomForestClassifier

from scipy import signal, stats, optimize, interpolate

from decoder import Percept
from utility import SignalProcessingUtility as SPU
from utility.PythonUtility import *

from Backend import models
from modules import Database
from modules.Percept import BrainSenseStream

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
key = os.environ.get('ENCRYPTION_KEY')

def processSpectrogram(stream, channel):
    if not "Spectrogram" in stream.keys():
        stream["Spectrogram"] = dict()
    
    for series in stream["Stimulation"]:
        if channel == series["Name"]:
            StimulationSeries = series

    stream["Spectrogram"][channel]["ConstantStimulation"] = np.ones(stream["Spectrogram"][channel]["Time"].shape, dtype=bool)
    stream["Spectrogram"][channel]["logPower"] = 10*np.log10(stream["Spectrogram"][channel]["Power"])
    stream["Spectrogram"][channel]["ConstantStimulation"][np.isinf(stream["Spectrogram"][channel]["logPower"][0,:])] = False
    for t in StimulationSeries["Time"]:
        stream["Spectrogram"][channel]["ConstantStimulation"][rangeSelection(stream["Spectrogram"][channel]["Time"], [t-3, t+3])] = False
        
    stream["Spectrogram"][channel]["Stimulation"] = np.zeros(stream["Spectrogram"][channel]["Time"].shape)
    for t in range(len(stream["Spectrogram"][channel]["Time"])):
        Stim = np.where(StimulationSeries["Time"] < stream["Spectrogram"][channel]["Time"][t])[0]
        if len(Stim) == 0:
            stream["Spectrogram"][channel]["Stimulation"][t] = StimulationSeries["Amplitude"][0]
        else:
            stream["Spectrogram"][channel]["Stimulation"][t] = StimulationSeries["Amplitude"][Stim[-1]+1]
            
    return stream

def extractFrequencyOfInterest(stream, channel):
    if len(np.unique(stream["Spectrogram"][channel]["Stimulation"][stream["Spectrogram"][channel]["ConstantStimulation"]])) > 2:
        ModulationIndex = np.zeros(stream["Spectrogram"][channel]["Frequency"].shape)
        for f in range(len(stream["Spectrogram"][channel]["Frequency"])):
            ModulationIndex[f] = np.var(stream["Spectrogram"][channel]["logPower"][f,:][stream["Spectrogram"][channel]["ConstantStimulation"]])
        
        TargetFrequency = rangeSelection(stream["Spectrogram"][channel]["Frequency"], [5,50])
        maxModulation = np.max(ModulationIndex[TargetFrequency])
        
        CorrelationIndex = np.zeros(stream["Spectrogram"][channel]["Frequency"].shape)
        for f in range(len(stream["Spectrogram"][channel]["Frequency"])):
            CorrelationIndex[f], _ = stats.pearsonr(stream["Spectrogram"][channel]["Stimulation"][stream["Spectrogram"][channel]["ConstantStimulation"]], stream["Spectrogram"][channel]["Power"][f,:][stream["Spectrogram"][channel]["ConstantStimulation"]])
        
        CorrelationIndex = np.power(CorrelationIndex,2)
        maxCorrelation = np.max(CorrelationIndex[TargetFrequency])
        
        CombinedFeature = SPU.smooth(ModulationIndex/maxModulation * CorrelationIndex/maxCorrelation,5)
        maxFeature = np.max(CombinedFeature[TargetFrequency])
        
        TargetFrequency = rangeSelection(stream["Spectrogram"][channel]["Frequency"], [5,50])
        
        GoodnessOfFit = np.mean(CombinedFeature[TargetFrequency]) / np.mean(CombinedFeature[~TargetFrequency])
        return stream["Spectrogram"][channel]["Frequency"][CombinedFeature == maxFeature][0], GoodnessOfFit
    return -1, -1

def extractModelParameters(stream, channel, centerFrequency):
    FrequencyOfInterest = rangeSelection(stream["Spectrogram"][channel]["Frequency"], [centerFrequency - 3, centerFrequency + 3])
    constantStimulation = stream["Spectrogram"][channel]["ConstantStimulation"]
    StimulationAmplitude = stream["Spectrogram"][channel]["Stimulation"][constantStimulation]
    BrainPower = np.mean(stream["Spectrogram"][channel]["logPower"][:,constantStimulation][FrequencyOfInterest], axis=0)
    
    uniqueAmplitude = np.unique(StimulationAmplitude)
    simplifiedYData = []
    for k in range(len(uniqueAmplitude)):
        simplifiedYData.append(np.median(BrainPower[StimulationAmplitude==uniqueAmplitude[k]]))
    
    xdata = np.linspace(np.min(StimulationAmplitude), np.max(StimulationAmplitude), 100)
    if len(uniqueAmplitude) >= 4:
        coe = np.polyfit(uniqueAmplitude, simplifiedYData, 4)
        #coe = np.polyfit(StimulationAmplitude, BrainPower, 4)
    else:
        coe = np.polyfit(StimulationAmplitude, BrainPower, 4)
        
    modeled_signal = np.polyval(coe, xdata)
    correlationCoe, p = stats.pearsonr(xdata, modeled_signal)
    
    return {"OptimalFrequency": 1,
        "ChangesDirection": np.sign(correlationCoe),
        "FittedEffect": correlationCoe*correlationCoe,
        "ChangesInPower": np.percentile(modeled_signal, 85) - np.percentile(modeled_signal, 15),
        "FinalPower": np.percentile(modeled_signal, 5)}, xdata[modeled_signal < np.percentile(modeled_signal, 10)][0], [xdata[0], xdata[-1]]

def extractPredictionFeatures(BrainSenseData, HemisphereInfo, centerFrequency=0):
    for channel in BrainSenseData["Channels"]:
        contacts, hemisphere = Percept.reformatChannelName(channel)
        if HemisphereInfo.startswith(hemisphere):
            BrainSenseData = processSpectrogram(BrainSenseData, channel)

            if centerFrequency == 0:
                centerFrequency, goodnessOfFit = extractFrequencyOfInterest(BrainSenseData, channel)
            else:
                pass
            
            if centerFrequency > 0:
                Features, PredictedAmplitude, AmplitudeRange = extractModelParameters(BrainSenseData, channel, centerFrequency)
            else:
                Features = { "OptimalFrequency": -1, "ChangesDirection": 1, "FittedEffect": 0, "ChangesInPower": 0, "FinalPower": 0 }
                PredictedAmplitude = 0
                AmplitudeRange = [0,0]
            
            Features["Score"] = applyPredictionModel(Features)
            Features["PredictedAmplitude"] = PredictedAmplitude
            Features["AmplitudeRange"] = AmplitudeRange
            return Features

    return dict()

def applyPredictionModel(RecordingFeatures):
    Features = np.array([RecordingFeatures[key] for key in RecordingFeatures.keys()])
    with open(RESOURCES + os.path.sep + "ForestModel.rfc", "rb") as file:
        forest = pickle.load(file)
    Probability = forest.predict_proba(Features.reshape(1,-1))[0][1]
    return Probability