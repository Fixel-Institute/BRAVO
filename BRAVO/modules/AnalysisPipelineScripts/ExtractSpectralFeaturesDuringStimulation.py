from Server import models

import os, sys
from pathlib import Path
import datetime, pytz
import numpy as np
from scipy import stats, signal
import pickle
import subprocess

from modules import DataAnalysis, Database, DataCurator
from modules.HelperFunctions import utc_offset_to_timezone

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

AnalysisScriptType = "ExtractSpectralFeaturesDuringStimulation"
AnalysisMethodVersion = "1.1.0"

def checkHistory(items, newItem):
    for item in items:
        if item["ParticipantId"] == newItem["ParticipantId"] and item["Date"] == newItem["Date"] and item["Contact"] == newItem["Contact"] and item["TherapyParameters"] == newItem["TherapyParameters"]:
            return True
    return False

def ExtractTherapyLevelPSDs(Analysis):
    for therapy in Analysis["Therapy"]:
        for k in range(len(therapy["TherapySeries"])):
            therapy["TherapySeries"][k]["Spectrum"] = {}
            therapy["TherapySeries"][k]["Frequency"] = []
            for i in range(len(Analysis["Signal"])):
                for j in range(len(Analysis["Signal"][i]["SignalSeries"]["ChannelNames"])):
                    Time = np.array(Analysis["Signal"][i]["SignalSeries"]["Spectrum"][j]["Time"]) + Analysis["Signal"][i]["SignalSeries"]["StartTime"]
                    TimeSelection = Time > therapy["TherapySeries"][k]["Time"]+3
                    if k < len(therapy["TherapySeries"])-1:
                        TimeSelection = TimeSelection & (Time < therapy["TherapySeries"][k+1]["Time"]-3)
                    therapy["TherapySeries"][k]["Spectrum"][Analysis["Signal"][i]["SignalSeries"]["ChannelNames"][j]] = np.array(Analysis["Signal"][i]["SignalSeries"]["Spectrum"][j]["Power"])[:,TimeSelection]
                    therapy["TherapySeries"][k]["Frequency"] = np.array(Analysis["Signal"][i]["SignalSeries"]["Spectrum"][j]["Frequency"])
    return Analysis["Therapy"]

def MovingAverageFilter(signal, window_size):
    window = np.ones(window_size) / window_size
    return np.convolve(signal, window, mode='same')

def ExtractAperiodicComponents(Frequency, Power):
    FrequencySelection = ((Frequency > 55) & (Frequency < 90)) | ((Frequency > 30) & (Frequency < 40)) 
    YData = np.log10(Power[FrequencySelection])
    XData = np.log10(Frequency[FrequencySelection])
    coe = np.polyfit(XData, YData, 1)
    AperiodicBaseline = np.polyval(coe, np.log10(Frequency))
    for j in range(len(AperiodicBaseline)):
        if np.isnan(AperiodicBaseline[-j-1]):
            AperiodicBaseline[-j-1] = AperiodicBaseline[-j]
    AperiodicBaseline = np.power(10,AperiodicBaseline)
    return AperiodicBaseline

def FindPeaks(signal):
    peaks = []
    for i in range(1, len(signal)-1):
        if signal[i] > signal[i-1] and signal[i] > signal[i+1]:
            peaks.append(i)
    return peaks

def ExtractAvailableDates(participant):
    RecordingCollections = []

    Data = DataAnalysis.queryAvailableAnalyses(participant["Id"], "TimeSeriesAnalysis")
    Dates = {}
    for i in range(len(Data["Recordings"])):
        if Data["Recordings"][i]["Timezone"] == "":
            Data["Recordings"][i]["Timezone"] = "UTC-04:00"
        RecordingDate = datetime.datetime.fromtimestamp(Data["Recordings"][i]["Date"]).astimezone(utc_offset_to_timezone(Data["Recordings"][i]["Timezone"])).strftime("%Y-%m-%d")
        Data["Recordings"][i]["LocalDate"] = RecordingDate
        if "Therapy" in Data["Recordings"][i].keys():
            for j in range(len(Data["Recordings"][i]["Therapy"])):
                TherapyParameter = str(Data["Recordings"][i]["Therapy"][j]["Frequency"]) + "Hz " + str(Data["Recordings"][i]["Therapy"][j]["Pulsewidth"]) + "uSec"

                if not Data["Recordings"][i]["Therapy"][j]["Contact"] in Dates.keys():
                    Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]] = {}
                
                if not TherapyParameter in Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]].keys():
                    Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter] = {}
                    
                if not RecordingDate in Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter].keys():
                    Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter][RecordingDate] = []
                
                if not "UniqueAmplitudes" in Data["Recordings"][i]["Therapy"][j].keys():
                    Data["Recordings"][i]["Therapy"][j]["UniqueAmplitudes"] = []
                Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter][RecordingDate].extend(Data["Recordings"][i]["Therapy"][j]["UniqueAmplitudes"])

    for contact in Dates.keys():
        for therapyParam in Dates[contact].keys():
            for date in Dates[contact][therapyParam].keys():
                Dates[contact][therapyParam][date] = np.unique(Dates[contact][therapyParam][date])
                if len(Dates[contact][therapyParam][date]) > 3 and 0 in Dates[contact][therapyParam][date]:
                    Recordings = []
                    for i in range(len(Data["Recordings"])):
                        if "Therapy" in Data["Recordings"][i].keys():
                            if Data["Recordings"][i]["LocalDate"] == date:
                                for j in range(len(Data["Recordings"][i]["Therapy"])):
                                    if Data["Recordings"][i]["Therapy"][j]["Contact"] == contact:
                                        TherapyParameter = str(Data["Recordings"][i]["Therapy"][j]["Frequency"]) + "Hz " + str(Data["Recordings"][i]["Therapy"][j]["Pulsewidth"]) + "uSec"
                                        if TherapyParameter == therapyParam:
                                            Recordings.append({
                                                "TimeSeries": Data["Recordings"][i]["Id"],
                                                "Therapy": Data["Recordings"][i]["Therapy"][j]["Id"]
                                            })

                    collection = {
                        "ParticipantId": participant["Id"],
                        "Diagnosis": participant["Diagnosis"],
                        "Contact": contact,
                        "Date": date,
                        "TherapyParameters": therapyParam,
                        "UniqueAmplitudes": Dates[contact][therapyParam][date],
                        "Recordings": Recordings
                    }
                    if not checkHistory(RecordingCollections, collection):
                        RecordingCollections.append(collection)
                        
    return RecordingCollections

def FTGDetection(Frequency, NormalizedPSDs, Amplitude, CenterFreq=0):
    GammaStats = {
        "FTGFrequency": 0,
            "BaselineFTGPower": 0.0,
            "FTGThreshold": 0.0,
            "FTGCorrelation": 0.0,
            "InitialFTGDetection": {
                "Power": 0.0, "Amplitude": 0.0
            },
            "MaximumFTGPower": {
            "Power": 0.0, "Amplitude": 0.0
            },
            "LastSignificantFTGPower": {
            "Power": 0.0, "Amplitude": 0.0
            }
    }

    GammaSelection = (Frequency > 55) & (Frequency < 95)
    MaskedPeaks = np.zeros(len(Frequency), dtype=bool)
    for j in range(NormalizedPSDs.shape[0]):
        residuals = NormalizedPSDs[j,GammaSelection]
        MaskedPeaks[GammaSelection] |= stats.zscore(residuals) > 2
    MaskedPeaks = np.convolve(MaskedPeaks, np.ones(3, dtype=bool), mode="same") > 0

    MeanPSD = np.max(NormalizedPSDs, axis=0)
    MaskStart = np.where(np.diff(np.array(MaskedPeaks, dtype=float)) == 1)[0]
    MaskEnd = np.where(np.diff(np.array(MaskedPeaks, dtype=float)) == -1)[0]
    PeakIndexes = []
    for j in range(len(MaskStart)):
        if (Frequency[MaskStart[j]] + Frequency[MaskEnd[j]]) / 2 > 50 and (Frequency[MaskStart[j]] + Frequency[MaskEnd[j]]) / 2 < 95:
            PeakIndexes.append(np.argmax(MeanPSD[MaskStart[j]:MaskEnd[j]]) + MaskStart[j])

    # Find FTG
    PeaknessThreshold = 0.2 # db
    for i in range(len(PeakIndexes)):
        GammaPeakSelection = (Frequency >= Frequency[PeakIndexes[i]] - 2.5) & (Frequency <= Frequency[PeakIndexes[i]] + 2.5)
        FTGFrequency = Frequency[PeakIndexes[i]]

        GammaPower = np.max(NormalizedPSDs[:,GammaPeakSelection],axis=1)
        r, p = stats.spearmanr(Amplitude, GammaPower)
        MaxGamma = np.max(GammaPower)
        if MaxGamma == GammaPower[0]:
            continue

        AmpIndex = np.argmax(GammaPower)
        Peakness = GammaPower[AmpIndex] - np.mean(NormalizedPSDs[AmpIndex,GammaSelection & ~GammaPeakSelection])

        BaselineGamma = np.mean(GammaPower[Amplitude < 0.5])
        FTGThreshold = (np.max(GammaPower) - BaselineGamma) * 0.5

        ReferenceData = NormalizedPSDs[:, GammaSelection & ~GammaPeakSelection]
        ReferenceData -= np.mean(ReferenceData, axis=0)
        Threshold = np.std(ReferenceData) * 5

        ReferenceFrequency = Frequency[GammaSelection & ~GammaPeakSelection]
        InterpFrequency = Frequency[GammaPeakSelection]
        Threshold = np.interp(InterpFrequency, ReferenceFrequency, np.mean(ReferenceData, axis=0) + Threshold)
        Threshold = np.mean(Threshold)

        #print(f"Peakness: {Peakness:.2f}, Threshold: {FTGThreshold:.2f}")
        #print(f"FTG Candidate: {FTGFrequency:.1f}Hz, Correlation: {r:.2f}, Max Gamma: {MaxGamma:.2f}, Threshold for Significance: {Threshold:.2f}")
        if FTGThreshold > GammaStats["FTGThreshold"] and MaxGamma > Threshold and Peakness > PeaknessThreshold:
            GammaStats["FTGFrequency"] = FTGFrequency
            GammaStats["FTGThreshold"] = FTGThreshold
            GammaStats["FTGCorrelation"] = r
            GammaStats["BaselineFTGPower"] = BaselineGamma
            PeaknessThreshold = Peakness

            IndexOfReduction = np.where(GammaPower > BaselineGamma + FTGThreshold)[0][0]
            GammaStats["InitialFTGDetection"] = {
                "Power": GammaPower[IndexOfReduction],
                "Amplitude": Amplitude[IndexOfReduction]
            }

            GammaStats["MaximumFTGPower"] = {
                "Power": np.max(GammaPower),
                "Amplitude": Amplitude[np.argmax(GammaPower)]
            }

            IndexOfReduction = np.where(GammaPower > BaselineGamma + FTGThreshold)[0][-1]
            GammaStats["LastSignificantFTGPower"] = {
                "Power": GammaPower[IndexOfReduction],
                "Amplitude": Amplitude[IndexOfReduction]
            }
            
    return GammaStats

def ProcessCollection(collection, userConfig):
    SensingChannel = "Unknown"
    if collection["Contact"].endswith("E01-E02"):
        SensingChannel = collection["Contact"].replace("E01-E02","E00-E03")
    elif collection["Contact"].endswith("E02"):
        SensingChannel = collection["Contact"].replace("E02","E01-E03")
    elif collection["Contact"].endswith("E01"):
        SensingChannel = collection["Contact"].replace("E01","E00-E02")

    UniqueTherapyAmplitudes = {}
    for recording in collection["Recordings"]:
        try:
            Analysis = DataAnalysis.processTimeseriesAnalysis(collection["ParticipantId"], recording["TimeSeries"], userConfig)
            Analysis["Therapy"] = DataAnalysis.processTimeseriesAnalysis(collection["ParticipantId"], recording["Therapy"], userConfig)["Therapy"]
        except Exception as e:
            print(f"Error processing recording {recording['TimeSeries']}: {e}")
            continue

        TherapyPSDs = ExtractTherapyLevelPSDs(Analysis)
        
        for amp in collection["UniqueAmplitudes"]:
            for therapy in TherapyPSDs:
                for k in range(len(therapy["TherapySeries"])):
                    for chan in therapy["TherapySeries"][k]["TherapyOverview"].keys():
                        if chan.endswith(SensingChannel):
                            if therapy["TherapySeries"][k]["TherapyOverview"][chan]["Amplitude"] == amp:
                                PSDFrequency = therapy["TherapySeries"][k]["Frequency"]
                                if chan in therapy["TherapySeries"][k]["Spectrum"].keys():
                                    if not amp in UniqueTherapyAmplitudes.keys():
                                        UniqueTherapyAmplitudes[amp] = therapy["TherapySeries"][k]["Spectrum"][chan]
                                    else:
                                        UniqueTherapyAmplitudes[amp] = np.concatenate((UniqueTherapyAmplitudes[amp], therapy["TherapySeries"][k]["Spectrum"][chan]), axis=1)

    GammaFrequency = float(collection["TherapyParameters"].split("Hz ")[0]) / 2
    GammaSelection = (PSDFrequency < GammaFrequency+5) & (PSDFrequency > GammaFrequency-5)

    AllPSDs = []
    for amp in sorted(collection["UniqueAmplitudes"]):
        if amp in UniqueTherapyAmplitudes.keys():
            if UniqueTherapyAmplitudes[amp].shape[1] > 3:
                AllPSDs.append(np.nanmedian(UniqueTherapyAmplitudes[amp],axis=1))
    
    if len(AllPSDs) > 1:
        AllPSDs = np.mean(np.array(AllPSDs),axis=0)
        MaxPowerIndex = np.argmax(AllPSDs[GammaSelection])
        GammaFrequency = PSDFrequency[GammaSelection][MaxPowerIndex]
        GammaSelection = (PSDFrequency < GammaFrequency+2) & (PSDFrequency > GammaFrequency-2)
    
    collection["PSDs"] = []
    for amp in sorted(collection["UniqueAmplitudes"]):
        if amp in UniqueTherapyAmplitudes.keys():
            if UniqueTherapyAmplitudes[amp].shape[1] > 3:
                PSDInfo = {
                    "PowerSpectrum": np.nanmedian(UniqueTherapyAmplitudes[amp],axis=1),
                    "StdPower": np.nanstd(UniqueTherapyAmplitudes[amp],axis=1) / np.sqrt(UniqueTherapyAmplitudes[amp].shape[1]),
                    "Amplitudes": amp, 
                    "Frequency": PSDFrequency
                }
                PSDInfo["AperiodicComponent"] = ExtractAperiodicComponents(PSDFrequency, MovingAverageFilter(PSDInfo["PowerSpectrum"],5))
                        
                GammaPower = PSDInfo["PowerSpectrum"][GammaSelection]
                GammaFluctuation = np.nanmedian(UniqueTherapyAmplitudes[amp][((PSDFrequency < 90) & (PSDFrequency > 60)) & (~GammaSelection), :],axis=1)

                if np.all(np.isnan(GammaFluctuation)) or np.all(np.isnan(GammaPower)) : 
                    continue 

                if stats.sem(GammaPower) > 1e5 or stats.sem(GammaFluctuation) > 1e5:
                    continue

                GammaFluctuation = signal.detrend(GammaFluctuation[~np.isnan(GammaFluctuation)])
                collection["PSDs"].append(PSDInfo)

    collection["FTGStats"] = {"FirstAppearance": 0, "MaxGamma": [-99,-99], "LastAppearance": 0, "GammaFrequency": GammaFrequency}
    if len(collection["PSDs"]) > 1:
        PSDLists = np.array([collection["PSDs"][i]["PowerSpectrum"] for i in range(0, len(collection["PSDs"]))])
        PeakIndex = np.argmax(np.max(PSDLists, axis=0))

        FrequencyOfInterest = (PSDFrequency > 3) & (PSDFrequency < 98)
        MeanPSD = MovingAverageFilter(np.mean(PSDLists, axis=0), 5)
        MaskedPeaks = np.zeros(len(PSDFrequency), dtype=bool)
        while True:
            x = np.log10(PSDFrequency[FrequencyOfInterest & ~MaskedPeaks])
            y = np.log10(MeanPSD[FrequencyOfInterest & ~MaskedPeaks])
            coe = np.polyfit(x, y, 1)
            residual = y - np.polyval(coe, x)
            MaskedPeak = stats.zscore(residual) > 2
            MaskedPeak = np.convolve(MaskedPeak, np.ones(3, dtype=bool), mode="same") > 0
            MaskedPeaks[FrequencyOfInterest & ~MaskedPeaks] = MaskedPeak
            if np.sum(MaskedPeak) == 0:
                break

        AperiodicPower = np.zeros(len(PSDFrequency))
        AperiodicPower[PSDFrequency > 0] = np.power(10, np.polyval(coe, np.log10(PSDFrequency[PSDFrequency > 0])));
        AperiodicPower[PSDFrequency == 0] = AperiodicPower[PSDFrequency > 0][0]

        NormalizedPSDs = np.zeros(PSDLists.shape)
        for j in range(PSDLists.shape[0]):
            scale = np.median(PSDLists[j,FrequencyOfInterest] / AperiodicPower[FrequencyOfInterest])
            NormalizedPSDs[j,:] = PSDLists[j,:] / AperiodicPower / scale

        Amplitude = np.array([collection["PSDs"][i]["Amplitudes"] for i in range(len(collection["PSDs"]))])
        GammaStats = FTGDetection(PSDFrequency, np.log10(NormalizedPSDs), Amplitude)
        if GammaStats["MaximumFTGPower"]["Power"] > 0.8:
            collection["FTGStats"]["FirstAppearance"] = GammaStats["InitialFTGDetection"]["Amplitude"]
            collection["FTGStats"]["MaxGamma"] = [GammaStats["MaximumFTGPower"]["Power"], GammaStats["MaximumFTGPower"]["Power"]]
            collection["FTGStats"]["LastAppearance"] = GammaStats["LastSignificantFTGPower"]["Amplitude"]
            collection["FTGStats"]["GammaFrequency"] = GammaStats["FTGFrequency"]
        
    # Calculate the Stimulation-induced Power Increase
    collection["StimulationCorrelation"] = {"MeanSlope": 0, "PercentSignificant": 0, "MeanCorrelation": 0}
    if len(collection["PSDs"]) > 1:
        Amplitude = [psd["Amplitudes"] for psd in collection["PSDs"]]
        PowerSpectrum = np.array([psd["PowerSpectrum"] for psd in collection["PSDs"]])

        Correlations = []
        for i in range(len(PSDFrequency)):
            if PSDFrequency[i] < 55 or PSDFrequency[i] > 90:
                continue

            # Calculate the correlation between amplitude and power spectrum
            corr = stats.pearsonr(Amplitude, PowerSpectrum[:,i])
            Correlations.append({
                "Frequency": PSDFrequency[i],
                "Correlation": corr[0],
                "Slope": corr[0] * np.std(Amplitude) / np.std(PowerSpectrum[:,i]),
                "PValue": corr[1]
            })
        
        collection["StimulationCorrelation"]["MeanSlope"] = np.mean([corr["Slope"] for corr in Correlations])
        collection["StimulationCorrelation"]["MeanCorrelation"] = np.mean([corr["Correlation"] for corr in Correlations])
        collection["StimulationCorrelation"]["PercentSignificant"] = np.sum([corr["PValue"] < 0.05 for corr in Correlations]) / len(Correlations) * 100

    # Calculate the Stimulation-induced Beta Changes
    collection["BetaStats"] = {"BetaFrequency": 0, "BaselineBetaPower": -99, 
                                "MaxCorrelation": 0, 
                                "BetaThreshold": {
                                    "Amplitude": 0, "Power": 0, "Threshold": 0
                                },
                                "MinBeta": {
                                    "Amplitude": -1, "Power": 99
                                }, 
                                "LastBeta": {
                                    "Amplitude": -1, "Power": 99
                                }}
    if len(collection["PSDs"]) > 1:
        Amplitude = [psd["Amplitudes"] for psd in collection["PSDs"]]
        PowerSpectrum = np.array([psd["PowerSpectrum"] for psd in collection["PSDs"]])
        SmoothedPSDs = np.array([MovingAverageFilter(psd["PowerSpectrum"],5) for psd in collection["PSDs"]])
        StimulationInducedPSDs = np.log10(SmoothedPSDs / SmoothedPSDs[0,:])

        PeakIndexes = FindPeaks(SmoothedPSDs[0,:])
        BetaPeaks = [idx for idx in PeakIndexes if PSDFrequency[idx] >= 12 and PSDFrequency[idx] <=30]
        
        Correlations = []
        for i in range(len(BetaPeaks)):
            # Calculate the correlation between amplitude and power spectrum
            BetaBand = (PSDFrequency > PSDFrequency[BetaPeaks[i]] - 2.5) & (PSDFrequency < PSDFrequency[BetaPeaks[i]] + 2.5)
            corr = stats.pearsonr(Amplitude, np.mean(StimulationInducedPSDs[:,BetaBand], axis=1))
            Correlations.append({
                "Frequency": PSDFrequency[BetaPeaks[i]],
                "Correlation": corr[0],
                "MaxPeak": np.mean(SmoothedPSDs[0,:][BetaBand]),
                "Slope": corr[0] * np.std(Amplitude) / np.std(StimulationInducedPSDs[:,BetaPeaks[i]]),
                "PValue": corr[1]
            })
        
        # Identify Beta Frequency by Max Correlation/PValue within Beta Band
        for i in range(len(Correlations)):
            if Correlations[i]["PValue"] < 0.05 and Correlations[i]["MaxPeak"] > collection["BetaStats"]["BaselineBetaPower"]:
                collection["BetaStats"]["MaxCorrelation"] = Correlations[i]["Correlation"]
                collection["BetaStats"]["BaselineBetaPower"] = Correlations[i]["MaxPeak"]
                collection["BetaStats"]["BetaFrequency"] = Correlations[i]["Frequency"]
        
        if collection["BetaStats"]["MaxCorrelation"] < 0:
            BetaBand = (PSDFrequency > collection["BetaStats"]["BetaFrequency"] - 2.5) & (PSDFrequency < collection["BetaStats"]["BetaFrequency"] + 2.5)
            BetaPowers = np.mean(SmoothedPSDs[:,BetaBand], axis=1)

            for i in range(len(BetaPowers)):
                if BetaPowers[i] < collection["BetaStats"]["MinBeta"]["Power"]:
                    collection["BetaStats"]["MinBeta"] = {"Amplitude": collection["PSDs"][i]["Amplitudes"], "Power": BetaPowers[i]}
            
            BetaReduction = collection["BetaStats"]["MinBeta"]["Power"] - collection["BetaStats"]["BaselineBetaPower"]
            collection["BetaStats"]["BetaThreshold"]["Threshold"] = BetaReduction * 0.5
            
            for i in range(len(BetaPowers)):
                if BetaPowers[i] < collection["BetaStats"]["BetaThreshold"]["Threshold"] + collection["BetaStats"]["BaselineBetaPower"]:
                    collection["BetaStats"]["BetaThreshold"]["Amplitude"] = collection["PSDs"][i]["Amplitudes"]
                    collection["BetaStats"]["BetaThreshold"]["Power"] = BetaPowers[i]
                    break 
            
            collection["BetaStats"]["LastBeta"] = {"Amplitude": collection["PSDs"][-1]["Amplitudes"], "Power": BetaPowers[-1]}

    return collection

def HandleRefreshAnalysis():
    Participants = [participant.get_info() for participant in models.Participant.find_all()]
    source_file = models.SourceFile.find(type=AnalysisScriptType, metadata={
        "User": "Admin",
        "Version": AnalysisMethodVersion
    })
    if not source_file:
        source_file = models.SourceFile.create(type=AnalysisScriptType, metadata={
            "User": "Admin",
            "Version": AnalysisMethodVersion
        })
        source_file.name = AnalysisScriptType
        source_file.pointer = DATABASE_PATH + "cache" + os.path.sep + source_file.name + ".bpkl"
        hashed = Database.saveSourceFile([], source_file.pointer)
        source_file.hashed = hashed
        source_file.save()

    if not "Version" in source_file.metadata:
        source_file.metadata["Version"] = AnalysisMethodVersion
        source_file.save()

    # Reset Collections
    RecordingCollections = []

    for participant in Participants:
        try:
            Data = DataAnalysis.queryAvailableAnalyses(participant["Id"], "TimeSeriesAnalysis")
        except Exception as e:
            print(f"Error occurred while querying available analyses for participant {participant['Id']}: {e}")
            continue
        Dates = {}
        for i in range(len(Data["Recordings"])):
            if Data["Recordings"][i]["Timezone"] == "":
                Data["Recordings"][i]["Timezone"] = "UTC-04:00"
            RecordingDate = datetime.datetime.fromtimestamp(Data["Recordings"][i]["Date"]).astimezone(utc_offset_to_timezone(Data["Recordings"][i]["Timezone"])).strftime("%Y-%m-%d")
            Data["Recordings"][i]["LocalDate"] = RecordingDate
            if "Therapy" in Data["Recordings"][i].keys():
                for j in range(len(Data["Recordings"][i]["Therapy"])):
                    TherapyParameter = str(Data["Recordings"][i]["Therapy"][j]["Frequency"]) + "Hz " + str(Data["Recordings"][i]["Therapy"][j]["Pulsewidth"]) + "uSec"

                    if not Data["Recordings"][i]["Therapy"][j]["Contact"] in Dates.keys():
                        Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]] = {}
                    
                    if not TherapyParameter in Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]].keys():
                        Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter] = {}
                        
                    if not RecordingDate in Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter].keys():
                        Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter][RecordingDate] = []
                    
                    if not "UniqueAmplitudes" in Data["Recordings"][i]["Therapy"][j].keys():
                        Data["Recordings"][i]["Therapy"][j]["UniqueAmplitudes"] = []
                        
                    Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter][RecordingDate].extend(Data["Recordings"][i]["Therapy"][j]["UniqueAmplitudes"])

        for contact in Dates.keys():
            for therapyParam in Dates[contact].keys():
                for date in Dates[contact][therapyParam].keys():
                    Dates[contact][therapyParam][date] = np.unique(Dates[contact][therapyParam][date])
                    if len(Dates[contact][therapyParam][date]) > 3 and 0 in Dates[contact][therapyParam][date]:
                        Recordings = []
                        for i in range(len(Data["Recordings"])):
                            if "Therapy" in Data["Recordings"][i].keys():
                                if Data["Recordings"][i]["LocalDate"] == date:
                                    for j in range(len(Data["Recordings"][i]["Therapy"])):
                                        if Data["Recordings"][i]["Therapy"][j]["Contact"] == contact:
                                            TherapyParameter = str(Data["Recordings"][i]["Therapy"][j]["Frequency"]) + "Hz " + str(Data["Recordings"][i]["Therapy"][j]["Pulsewidth"]) + "uSec"
                                            if TherapyParameter == therapyParam:
                                                Recordings.append({
                                                    "TimeSeries": Data["Recordings"][i]["Id"],
                                                    "Therapy": Data["Recordings"][i]["Therapy"][j]["Id"]
                                                })

                        collection = {
                            "ParticipantId": participant["Id"],
                            "Diagnosis": participant["Diagnosis"],
                            "Contact": contact,
                            "Date": date,
                            "TherapyParameters": therapyParam,
                            "UniqueAmplitudes": Dates[contact][therapyParam][date],
                            "Recordings": Recordings
                        }
                        if not checkHistory(RecordingCollections, collection):
                            RecordingCollections.append(collection)

    userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": {
        "TimeSeriesRecording": {
            "StandardFilter": {
                "value": "Butterworth 1-100Hz"
            },
            "CardiacFilter": {
                "value": "No Filter"
            },
            "SpectrogramMethod": {
                "value": "Welch's Periodogram"
            }
        }
    }})
    userConfig["APIAccess"] = True

    for collection in RecordingCollections:
        print(collection["ParticipantId"] + " " + collection["Contact"])
        collection = ProcessCollection(collection, userConfig)
        
    hashed = Database.saveSourceFile(RecordingCollections, source_file.pointer)
    source_file.metadata["Version"] = AnalysisMethodVersion
    source_file.hashed = hashed
    source_file.save()

def ProcessParticipant(participantId):
    RecordingCollections = []
    Data = DataAnalysis.queryAvailableAnalyses(participantId, "TimeSeriesAnalysis")
    Dates = {}
    for i in range(len(Data["Recordings"])):
        if Data["Recordings"][i]["Timezone"] == "":
            Data["Recordings"][i]["Timezone"] = "UTC-04:00"
        RecordingDate = datetime.datetime.fromtimestamp(Data["Recordings"][i]["Date"]).astimezone(utc_offset_to_timezone(Data["Recordings"][i]["Timezone"])).strftime("%Y-%m-%d")
        Data["Recordings"][i]["LocalDate"] = RecordingDate
        if "Therapy" in Data["Recordings"][i].keys():
            for j in range(len(Data["Recordings"][i]["Therapy"])):
                TherapyParameter = str(Data["Recordings"][i]["Therapy"][j]["Frequency"]) + "Hz " + str(Data["Recordings"][i]["Therapy"][j]["Pulsewidth"]) + "uSec"

                if not Data["Recordings"][i]["Therapy"][j]["Contact"] in Dates.keys():
                    Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]] = {}
                
                if not TherapyParameter in Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]].keys():
                    Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter] = {}
                    
                if not RecordingDate in Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter].keys():
                    Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter][RecordingDate] = []
                
                Dates[Data["Recordings"][i]["Therapy"][j]["Contact"]][TherapyParameter][RecordingDate].extend(Data["Recordings"][i]["Therapy"][j]["UniqueAmplitudes"])

    for contact in Dates.keys():
        for therapyParam in Dates[contact].keys():
            for date in Dates[contact][therapyParam].keys():
                Dates[contact][therapyParam][date] = np.unique(Dates[contact][therapyParam][date])
                if len(Dates[contact][therapyParam][date]) > 3 and 0 in Dates[contact][therapyParam][date]:
                    Recordings = []
                    for i in range(len(Data["Recordings"])):
                        if "Therapy" in Data["Recordings"][i].keys():
                            if Data["Recordings"][i]["LocalDate"] == date:
                                for j in range(len(Data["Recordings"][i]["Therapy"])):
                                    if Data["Recordings"][i]["Therapy"][j]["Contact"] == contact:
                                        TherapyParameter = str(Data["Recordings"][i]["Therapy"][j]["Frequency"]) + "Hz " + str(Data["Recordings"][i]["Therapy"][j]["Pulsewidth"]) + "uSec"
                                        if TherapyParameter == therapyParam:
                                            Recordings.append({
                                                "TimeSeries": Data["Recordings"][i]["Id"],
                                                "Therapy": Data["Recordings"][i]["Therapy"][j]["Id"]
                                            })

                    collection = {
                        "ParticipantId": participantId,
                        "Contact": contact,
                        "Date": date,
                        "TherapyParameters": therapyParam,
                        "UniqueAmplitudes": Dates[contact][therapyParam][date],
                        "Recordings": Recordings
                    }
                    
                    RecordingCollections.append(collection)
    
    userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": {
        "TimeSeriesRecording": {
            "StandardFilter": {
                "value": "Butterworth 1-100Hz"
            },
            "CardiacFilter": {
                "value": "No Filter"
            },
            "SpectrogramMethod": {
                "value": "Welch's Periodogram"
            }
        }
    }})
    userConfig["APIAccess"] = True
    for collection in RecordingCollections:
        collection = ProcessCollection(collection, userConfig)
    
    return RecordingCollections

def QueryAnalysisResultTable(Participants):
    source_file = models.SourceFile.find(type=AnalysisScriptType, metadata={
        "User": "Admin",
        "Version": AnalysisMethodVersion
    })
    if not source_file:
        return {"Participants": Participants, "RecordingCollection": []}

    RecordingCollections = Database.loadSourceFile(source_file.pointer, source_file.hashed)
    ParticipantIds = [participant["Id"] for participant in Participants]

    RecordingCollections = [collection for collection in RecordingCollections if collection["ParticipantId"] in ParticipantIds]
    
    Participants = sorted(Participants, key=lambda x: x["Name"])
    ResultTable = {"Participants": Participants, "RecordingCollection": []}
    for collection in RecordingCollections:
        ResultTable["RecordingCollection"].append({
            "ParticipantId": collection["ParticipantId"],
            "Date": collection["Date"],
            "Contact": collection["Contact"],
            "TherapyParameters": collection["TherapyParameters"],
            "UniqueAmplitudes": collection["UniqueAmplitudes"],
            "FTGStats": collection["FTGStats"],
            "BetaStats": collection["BetaStats"],
            "StimulationCorrelation": collection["StimulationCorrelation"],
        })
        
    return ResultTable

def QueryAnalysisResultPSD(ParticipantId, Contact):
    source_file = models.SourceFile.find(type=AnalysisScriptType, metadata={
        "User": "Admin",
        "Version": AnalysisMethodVersion
    })
    if not source_file:
        return []

    RecordingCollections = Database.loadSourceFile(source_file.pointer, source_file.hashed)
    RecordingCollections = [collection for collection in RecordingCollections if collection["ParticipantId"] == ParticipantId]

    Result = []
    for collection in RecordingCollections:
        if collection["Date"] + " " + collection["Contact"] + " " + collection["TherapyParameters"] == Contact:
            for i in range(len(collection["PSDs"])):
                if not "ExpertLabel" in collection.keys():
                    collection["PSDs"][i]["CenterFrequency"] = []
                else:
                    collection["PSDs"][i]["CenterFrequency"] = collection["ExpertLabel"]
            Result = collection["PSDs"]
            break
    return Result

def SetExpertLabel(ParticipantId, Contact, Label):
    source_file = models.SourceFile.find(type=AnalysisScriptType, metadata={
        "User": "Admin",
        "Version": AnalysisMethodVersion
    })
    if not source_file:
        return False

    RecordingCollections = Database.loadSourceFile(source_file.pointer, source_file.hashed)
    for collection in RecordingCollections:
        if collection["ParticipantId"] == ParticipantId and collection["Date"] + " " + collection["Contact"] + " " + collection["TherapyParameters"] == Contact:
            collection["ExpertLabel"] = Label
            break

    hashed = Database.saveSourceFile(RecordingCollections, source_file.pointer)
    source_file.hashed = hashed
    source_file.save()
    return True

def QueryAnalysisResultRaw(Participants, refresh=False):
    source_file = models.SourceFile.find(type=AnalysisScriptType, metadata={
        "User": "Admin",
        "Version": AnalysisMethodVersion
    })
    if not source_file:
        return []

    ParticipantIds = [participant["Id"] for participant in Participants]
    RecordingCollections = Database.loadSourceFile(source_file.pointer, source_file.hashed)
    RecordingCollections = [collection for collection in RecordingCollections if collection["ParticipantId"] in ParticipantIds]

    if refresh:
        userConfig, _ = Database.retrieveProcessingSettings({"ProcessingConfiguration": {
            "TimeSeriesRecording": {
                "StandardFilter": {
                    "value": "Butterworth 1-100Hz"
                },
                "CardiacFilter": {
                    "value": "No Filter"
                },
                "SpectrogramMethod": {
                    "value": "Welch's Periodogram"
                }
            }
        }})
        userConfig["APIAccess"] = True

        for collection in RecordingCollections:
            print(collection["ParticipantId"] + " " + collection["Contact"])
            collection = ProcessCollection(collection, userConfig)
        
    return pickle.dumps(RecordingCollections)

def CommandLineAsyncUpdate():
    script_path = str(Path(__file__).resolve().parent) + "/AnalysisPipeline.py"
    subprocess.Popen([sys.executable, script_path, "ExtractSpectralFeaturesDuringStimulation"], cwd=Path(__file__).resolve().parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return True