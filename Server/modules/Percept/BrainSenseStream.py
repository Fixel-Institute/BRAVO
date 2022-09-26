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

key = os.environ.get('ENCRYPTION_KEY')

def saveRealtimeStreams(deviceID, StreamingTD, StreamingPower, sourceFile):
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
        stream["Wavelet"][channel]["Power"] = stream["Wavelet"][channel]["Power"][:,::int(250/2)]
        stream["Wavelet"][channel]["Time"] = stream["Wavelet"][channel]["Time"][::int(250/2)]
        stream["Wavelet"][channel]["Type"] = "Wavelet"
        del(stream["Wavelet"][channel]["logPower"])

        # SFFT Computation
        stream["Spectrogram"][channel] = SPU.defaultSpectrogram(stream["Filtered"][channel], window=1.0, overlap=0.5, frequency_resolution=0.5, fs=250)
        stream["Spectrogram"][channel]["Type"] = "Spectrogram"
        stream["Spectrogram"][channel]["Time"] += stream["Time"][0]
        del(stream["Spectrogram"][channel]["logPower"])

    return stream

def queryRealtimeStreamOverview(user, patientUniqueID, authority):
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

            if data["Duration"] < 30:
                continue

            data["RecordingID"] = recording.recording_id
            data["DeviceName"] = device.getDeviceSerialNumber(key)
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
                        data["Channels"].append({"Hemisphere": lead["TargetLocation"], "Contacts": contacts})
                        if lead["ElectrodeType"].startswith("SenSight"):
                            data["ContactTypes"].append(["Ring","Segment A","Segment B","Segment C","Segment AB","Segment BC","Segment AC"])
                        else:
                            data["ContactTypes"].append(["Ring"])

            BrainSenseData.append(data)
            includedRecording.append(data["Timestamp"])
    return BrainSenseData

def queryRealtimeStreamRecording(user, recordingId, authority, cardiacFilter=False, refresh=False):
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

        if not "Spectrogram" in BrainSenseData.keys() or (refresh and (not recording.recording_info["CardiacFilter"] == cardiacFilter)):
            recording.recording_info["CardiacFilter"] = cardiacFilter
            BrainSenseData = processRealtimeStreams(BrainSenseData, cardiacFilter=cardiacFilter)
            Database.saveSourceFiles(BrainSenseData,recording.recording_type,info,recording.recording_id, recording.device_deidentified_id)
            recording.save()

        BrainSenseData["Timestamp"] = recording.recording_date.timestamp();
        BrainSenseData["Info"] = recording.recording_info;
        RecordingID = recording.recording_id
    return BrainSenseData, RecordingID

def queryRealtimeStreamData(user, device, timestamp, authority, cardiacFilter=False, refresh=False):
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

def processRealtimeStreamRenderingData(stream, options=dict()):
    stream["Stimulation"] = processRealtimeStreamStimulationAmplitude(stream)
    stream["PowerBand"] = processRealtimeStreamPowerBand(stream)
    data = dict()
    data["Channels"] = stream["Channels"]
    data["Stimulation"] = stream["Stimulation"]
    data["PowerBand"] = stream["PowerBand"]
    data["Info"] = stream["Info"]
    data["Timestamp"] = stream["Timestamp"]
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
            data[channel]["StimPSD"] = processRealtimeStreamStimulationPSD(stream, channel, method=options["SpectrogramMethod"]["value"], stim_label="Ipsilateral")
        else:
            data[channel]["StimPSD"] = processRealtimeStreamStimulationPSD(stream, channel, method=options["PSDMethod"]["value"], stim_label="Ipsilateral")
    return data

def processRealtimeStreamStimulationAmplitude(stream):
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

    cIndex = 0;
    StimulationEpochs = list()
    for i in range(1,len(StimulationSeries["Time"])):
        StimulationDuration = StimulationSeries["Time"][i] - StimulationSeries["Time"][i-1]
        if StimulationDuration < 7:
            continue
        cIndex += 1

        if method == "Welch":
            timeSelection = rangeSelection(stream["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            StimulationEpoch = stream["Filtered"][channel][timeSelection]
            fxx, pxx = signal.welch(StimulationEpoch, fs=250, nperseg=250 * 1, noverlap=250 * 0.5, nfft=250 * 2, scaling="density")
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i], "Frequency": fxx, "PSD": pxx})
            timeSelection = rangeSelection(stream["Spectrogram"][channel]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])

        elif method == "Spectrogram":
            timeSelection = rangeSelection(stream["Spectrogram"][channel]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i], "Frequency": stream["Spectrogram"][channel]["Frequency"], "PSD": np.mean(stream["Spectrogram"][channel]["Power"][:,timeSelection],axis=1)})

        elif method == "Wavelet":
            timeSelection = rangeSelection(stream["Wavelet"][channel]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
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
            StimulationEpochs[i]["SpectralFeatures"] = stream["Wavelet"][channel]["Power"][:,timeSelection]
        else:
            StimulationEpochs[i]["SpectralFeatures"] = stream["Spectrogram"][channel]["Power"][:,timeSelection]

        StimulationEpochs[i]["SpectralFeatures"] = np.mean(StimulationEpochs[i]["SpectralFeatures"][frequencySelection,:],axis=0)
        del(StimulationEpochs[i]["TimeSelection"])

    return StimulationEpochs
