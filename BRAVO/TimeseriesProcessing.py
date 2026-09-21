import os, sys
import time
import pywt
import numpy as np
from scipy import signal
from scipy.ndimage import uniform_filter1d

from BRAVO import wsgi
from Server import models

from modules import DataAnalysis, Database
from modules.utility import SignalProcessingUtility as SPU


# Default Configs
DefaultConfig = {
    "StandardFilter": "No Filter",
    "NotchFilter": "No Filter",
    "WienerFilter": "No Filter",
    "CardiacFilter": "No Filter",
    "SpectrogramMethod": "Welch's Periodogram",
    "BaselineCorrection": "No Correction",
    "Normalization": "No Normalization",
    "SpectrogramParameters": {
        "Window": 1,
        "Overlap": 0.5,
        "FrequencyResolution": 0.5,
        "FrequencyRange": [0, 100]
    }
}

def handleBurstActivityPreprocessing(data, config, centerFreq=22):
    data["BurstEnvelop"] = []
    if len(data["ChannelNames"]) == 1:
        data["Data"] = data["Data"].reshape(-1,1)
        data["Missing"] = data["Missing"].reshape(-1,1)

    for i in range(len(data["ChannelNames"])):

        f_center = pywt.central_frequency("morl")
        desired_freqs = np.geomspace(1, data["SamplingRate"] / 2, num=100)
        scales = f_center * data["SamplingRate"] / desired_freqs

        coefs, freqs = pywt.cwt(data["Data"][:,i], scales, "morl", sampling_period=1/data["SamplingRate"])
        averaging = int(data["SamplingRate"] * 0.2)
        envelope = np.abs(coefs)
        
        if averaging > 1:
            coefs = uniform_filter1d(envelope, size=averaging, axis=1, mode="nearest")
        else:
            coefs = envelope

        data["BurstEnvelop"].append({
            "Wavelet": coefs,
            "Frequency": freqs, 
            "Method": "Morlet",
            "Config": config
        })
    return data

while True:
    KnownParticipants = models.Participant.find_all()

    for participant in KnownParticipants:
        Recordings = models.Recording.find_all(source__owner=participant, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages", 
                                                                                    "MedtronicBrainSenseTimeDomain", "MedtronicIndefiniteStream", 
                                                                                    "DelsysMDAT", "HPFCSV", "AOMPX", "MATFile", "SynchronizedMDAT"])
        for recording in Recordings:
            # TimeFrequencyAnalysis
            Data = None 
            try:
                if not models.Recording.objects.filter(original=recording, type="TimeFrequencyAnalysis", metadata=DefaultConfig).exists():
                    if not Data:
                        Data = Database.loadSourceFile(recording.pointer, recording.hashed)
                    _ = DataAnalysis.handleTimeFrequencyAnalysis(Data, DefaultConfig, recording=recording)
                    print("Processed TimeFrequencyAnalysis for Recording:", recording.uid)
            except Exception as e:
                print("Error processing TimeFrequencyAnalysis for Recording:", recording.uid, "-", str(e))

        Recordings = models.Recording.find_all(source__owner=participant, type__in=["MedtronicBrainSenseSurvey", "MedtronicBaselineMontages", 
                                                                                    "MedtronicBrainSenseTimeDomain", "MedtronicIndefiniteStream"])
        for recording in Recordings:
            try:
                if not models.Recording.objects.filter(original=recording, type="AperiodicNormalization", metadata=DefaultConfig).exists():
                    tfAnalysis = models.Recording.objects.filter(original=recording, type="TimeFrequencyAnalysis", metadata=DefaultConfig).first()
                    if not tfAnalysis:
                        raise
                    
                    Data = Database.loadSourceFile(tfAnalysis.pointer, tfAnalysis.hashed)
                    _ = DataAnalysis.handleAperiodicTrendExtraction(Data, DefaultConfig, recording=recording)
                    print("Processed AperiodicTrendExtraction for Recording:", recording.uid)
            except Exception as e:
                print("Error processing AperiodicNormalization for Recording:", recording.uid, "-", str(e))

            try:
                if not models.Recording.objects.filter(original=recording, type="BurstActivityPreprocessing", metadata=DefaultConfig).exists():
                    Data = Database.loadSourceFile(recording.pointer, recording.hashed)
                    _ = DataAnalysis.handleBurstActivityPreprocessing(Data, DefaultConfig, recording=recording)
                    print("Processed BurstActivityPreprocessing for Recording:", recording.uid)
            except Exception as e:
                print("Error processing BurstActivityPreprocessing for Recording:", recording.uid, "-", str(e))

    time.sleep(60)

