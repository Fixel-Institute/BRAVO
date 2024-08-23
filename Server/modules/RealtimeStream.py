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
from modules.Percept import BrainSenseStream
from modules.Summit import StreamingData

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

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
        if device.device_type == "Summit RC+S": 
            allAnalysis = models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=device.deidentified_id, analysis_name="SummitRealtimeStreaming").order_by("-analysis_date").all()
            if len(allAnalysis) > 0:
                leads = device.device_lead_configurations

            for analysis in allAnalysis:
                for recordingId in analysis.recording_list:
                    if not recordingId in authority["Permission"] and authority["Level"] == 2:
                        continue

                data = dict()
                data["Timestamp"] = analysis.analysis_date.timestamp()

                if data["Timestamp"] in includedRecording:
                    continue

                data["AnalysisID"] = str(analysis.deidentified_id)
                data["AnalysisLabel"] = analysis.analysis_label
                data["RecordingIDs"] = analysis.recording_list

                DeviceName = device.device_name
                if DeviceName == "":
                    DeviceName = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)
                data["DeviceName"] = DeviceName
                data["DeviceID"] = device.deidentified_id
                data["DeviceLocation"] = device.device_location
                data["Channels"] = list()
                data["ContactTypes"] = list()

                if not ("SummitLfp" in analysis.recording_type and "SummitAdaptive" in analysis.recording_type):
                    continue 

                allRecordings = models.NeuralActivityRecording.objects.filter(recording_id__in=analysis.recording_list)
                if len(allRecordings) == 0:
                    analysis.delete()
                    continue 

                for recording in allRecordings:
                    if recording.recording_type == "SummitLfp":
                        TimeRecording = recording
                    elif recording.recording_type == "SummitAdaptive":
                        PowerRecording = recording

                if TimeRecording.recording_duration == 0:
                    RawData = Database.loadSourceDataPointer(TimeRecording.recording_datapointer)
                    TimeRecording.recording_duration = RawData["Duration"]
                    TimeRecording.save()

                data["Duration"] = TimeRecording.recording_duration
                if data["Duration"] < 5:
                    continue
                
                for i in range(len(TimeRecording.recording_info["Channel"])):
                    hemisphere = TimeRecording.recording_info["Channel"][i].split(" ")[0]
                    for lead in leads:
                        if lead["TargetLocation"].startswith(hemisphere):
                            data["Channels"].append({"Hemisphere": lead["TargetLocation"], "CustomName": lead["CustomName"], "Contacts": TimeRecording.recording_info["Channel"][i].replace(hemisphere + " ", ""), "Type": lead["ElectrodeType"]})

                BrainSenseData.append(data)
                includedRecording.append(data["Timestamp"])
        else:
            allAnalysis = models.CombinedRecordingAnalysis.objects.filter(device_deidentified_id=device.deidentified_id, analysis_name="DefaultBrainSenseStreaming").order_by("-analysis_date").all()
            if len(allAnalysis) > 0:
                leads = device.device_lead_configurations

            for analysis in allAnalysis:
                for recordingId in analysis.recording_list:
                    if not recordingId in authority["Permission"] and authority["Level"] == 2:
                        continue

                data = dict()
                data["Timestamp"] = analysis.analysis_date.timestamp()

                if data["Timestamp"] in includedRecording:
                    continue

                data["AnalysisID"] = str(analysis.deidentified_id)
                data["AnalysisLabel"] = analysis.analysis_label
                data["RecordingIDs"] = analysis.recording_list

                DeviceName = device.device_name
                if DeviceName == "":
                    DeviceName = str(device.deidentified_id) if not (user.is_admin or user.is_clinician) else device.getDeviceSerialNumber(key)
                data["DeviceName"] = DeviceName
                data["DeviceID"] = device.deidentified_id
                data["DeviceLocation"] = device.device_location
                data["Channels"] = list()
                data["ContactTypes"] = list()

                allRecordings = models.NeuralActivityRecording.objects.filter(recording_id__in=analysis.recording_list)
                for recording in allRecordings:
                    if recording.recording_type == "BrainSenseStreamPowerDomain":
                        PowerRecording = recording
                    elif recording.recording_type == "BrainSenseStreamTimeDomain":
                        TimeRecording = recording

                if len(allRecordings) == 0:
                    analysis.delete()
                    continue 

                RawData = Database.loadSourceDataPointer(PowerRecording.recording_datapointer)
                if not "Therapy" in PowerRecording.recording_info:
                    PowerRecording.recording_info["Therapy"] = RawData["Descriptor"]["Therapy"]
                    PowerRecording.save()
                
                data["Therapy"] = PowerRecording.recording_info["Therapy"]
                data["Duration"] = RawData["Duration"]

                if RawData["Duration"] < 5:
                    continue
                
                Channels = TimeRecording.recording_info["Channel"]
                if not "ContactType" in PowerRecording.recording_info:
                    PowerRecording.recording_info["ContactType"] = ["Ring" for channel in Channels]
                    PowerRecording.save()
                if not len(PowerRecording.recording_info["ContactType"]) == len(Channels):
                    PowerRecording.recording_info["ContactType"] = ["Ring" for channel in Channels]
                    PowerRecording.save()
                
                data["ContactType"] = PowerRecording.recording_info["ContactType"]
                for channel in Channels:
                    contacts, hemisphere = Percept.reformatChannelName(channel)
                    for lead in leads:
                        if lead["TargetLocation"].startswith(hemisphere):
                            data["Channels"].append({"Hemisphere": lead["TargetLocation"], "CustomName": lead["CustomName"], "Contacts": contacts, "Type": lead["ElectrodeType"]})
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
    
    analysis = models.CombinedRecordingAnalysis.objects.filter(deidentified_id=recordingId).first()
    if not analysis == None:
        if authority["Level"] == 2:
            for recordingId in analysis.recording_list:
                if not recordingId in authority["Permission"] and authority["Level"] == 2:
                    return BrainSenseData, RecordingID
        
        if "BrainSenseRecording" in analysis.recording_type:
            BrainSenseData, RecordingID = BrainSenseStream.queryRealtimeStreamRecording(analysis, cardiacFilter, refresh)
        
        elif "SummitLfp" in analysis.recording_type or "SummitAdaptive" in analysis.recording_type:
            BrainSenseData, RecordingID = StreamingData.queryRealtimeStreamRecording(analysis, cardiacFilter, refresh)
    
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
    
    if stream["Info"]["Device"] == "Summit RC+S":
        stream["PowerDomain"]["Stimulation"] = StreamingData.processRealtimeStreamStimulationAmplitude(stream["PowerDomain"])
        stream["PowerDomain"]["PowerBand"] = StreamingData.processRealtimeStreamPowerBand(stream["PowerDomain"])
    else:
        stream["PowerDomain"]["Stimulation"] = BrainSenseStream.processRealtimeStreamStimulationAmplitude(stream["PowerDomain"])
        stream["PowerDomain"]["PowerBand"] = BrainSenseStream.processRealtimeStreamPowerBand(stream["PowerDomain"])

    data = dict()
    data["Channels"] = stream["TimeDomain"]["ChannelNames"]
    data["Stimulation"] = stream["PowerDomain"]["Stimulation"]
    data["PowerBand"] = stream["PowerDomain"]["PowerBand"]
    data["Info"] = stream["Info"]
    data["Timestamp"] = stream["TimeDomain"]["StartTime"]
    data["PowerTimestamp"] = stream["PowerDomain"]["StartTime"]
    data["Annotations"] = stream["Annotations"]

    while len(centerFrequencies) < len(stream["TimeDomain"]["ChannelNames"]):
        centerFrequencies.append(0)

    for i in range(len(data["PowerBand"])):
        for lead in data["Info"]["Leads"]:
            if lead["TargetLocation"].startswith(data["PowerBand"][i]["Hemisphere"]):
                if "CustomName" in lead.keys():
                    data["PowerBand"][i]["LegendName"] = lead["CustomName"] + " " + data["PowerBand"][i]["LegendName"]
                else:
                    data["PowerBand"][i]["LegendName"] = lead["TargetLocation"] + " " + data["PowerBand"][i]["LegendName"]

    for i in range(len(data["Stimulation"])):
        for lead in data["Info"]["Leads"]:
            if lead["TargetLocation"].startswith(data["Stimulation"][i]["Hemisphere"]):
                if "CustomName" in lead.keys():
                    data["Stimulation"][i]["LegendName"] = lead["CustomName"] + " " + data["Stimulation"][i]["LegendName"]
                else:
                    data["Stimulation"][i]["LegendName"] = lead["TargetLocation"] + " " + data["Stimulation"][i]["LegendName"]
        
    data["Stream"] = list()
    for counter in range(len(data["Channels"])):
        data["Stream"].append(dict())
        data["Stream"][counter]["RawData"] = stream["TimeDomain"]["Data"][:,counter]
        data["Stream"][counter]["Filtered"] = stream["TimeDomain"]["Filtered"][counter]
        data["Stream"][counter]["Time"] = np.arange(len(data["Stream"][counter]["RawData"]))/stream["TimeDomain"]["SamplingRate"]

        if options["SpectrogramMethod"]["value"] == "Spectrogram":
            data["Stream"][counter]["Spectrogram"] = copy.deepcopy(stream["TimeDomain"]["Spectrogram"][counter])
            data["Stream"][counter]["Spectrogram"]["Power"][data["Stream"][counter]["Spectrogram"]["Power"] == 0] = 1e-10
            data["Stream"][counter]["Spectrogram"]["Power"] = np.log10(data["Stream"][counter]["Spectrogram"]["Power"])*10
            data["Stream"][counter]["Spectrogram"]["ColorRange"] = [-20,20]
            #MedianPower = np.median(data["Stream"][counter]["Spectrogram"]["Power"])
            #MaxScale = np.max(np.abs(data["Stream"][counter]["Spectrogram"]["Power"]-MedianPower))
            #data["Stream"][counter]["Spectrogram"]["ColorRange"] = [MedianPower-MaxScale,MedianPower+MaxScale]

        elif options["SpectrogramMethod"]["value"]  == "Wavelet":
            data["Stream"][counter]["Spectrogram"] = copy.deepcopy(stream["TimeDomain"]["Wavelet"][counter])
            data["Stream"][counter]["Spectrogram"]["Power"][data["Stream"][counter]["Spectrogram"]["Power"] == 0] = 1e-10
            data["Stream"][counter]["Spectrogram"]["Power"] = np.log10(data["Stream"][counter]["Spectrogram"]["Power"])*10
            data["Stream"][counter]["Spectrogram"]["ColorRange"] = [-10,20]
            #MedianPower = np.median(data["Stream"][counter]["Spectrogram"]["Power"])
            #MaxScale = np.max(np.abs(data["Stream"][counter]["Spectrogram"]["Power"]-MedianPower))
            #data["Stream"][counter]["Spectrogram"]["ColorRange"] = [MedianPower-MaxScale,MedianPower+MaxScale]

        if stream["Info"]["Device"] == "Summit RC+S":
            if options["PSDMethod"]["value"] == "Time-Frequency Analysis":
                data["Stream"][counter]["StimPSD"] = StreamingData.processRealtimeStreamStimulationPSD(stream, data["Channels"][counter], method=options["SpectrogramMethod"]["value"], stim_label=stimulationReference, centerFrequency=centerFrequencies[counter])
            else:
                data["Stream"][counter]["StimPSD"] = StreamingData.processRealtimeStreamStimulationPSD(stream, data["Channels"][counter], method=options["PSDMethod"]["value"], stim_label=stimulationReference, centerFrequency=centerFrequencies[counter])
        else:
            if options["PSDMethod"]["value"] == "Time-Frequency Analysis":
                data["Stream"][counter]["StimPSD"] = BrainSenseStream.processRealtimeStreamStimulationPSD(stream, data["Channels"][counter], method=options["SpectrogramMethod"]["value"], stim_label=stimulationReference, centerFrequency=centerFrequencies[counter])
            else:
                data["Stream"][counter]["StimPSD"] = BrainSenseStream.processRealtimeStreamStimulationPSD(stream, data["Channels"][counter], method=options["PSDMethod"]["value"], stim_label=stimulationReference, centerFrequency=centerFrequencies[counter])

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
        StimulationSeries.append({"Name": ChannelName, "Hemisphere": hemisphere, "Time": TimeArray[indexOfChanges], "Amplitude": np.around(stream["Data"][indexOfChanges,StimulationSide],2)})
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
        PowerSensing.append({"Name": ChannelName, "Time": TimeArray[selectedData], "Power": Power[selectedData]})
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
    DataIndex = [i for i in range(len(stream["TimeDomain"]["ChannelNames"])) if stream["TimeDomain"]["ChannelNames"][i] == channel][0]
    
    cIndex = 0
    StimulationEpochs = list()
    for i in range(1,len(StimulationSeries["Time"])):
        cIndex += 1 

        if method == "Welch":
            timeSelection = rangeSelection(TimeArray,[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            timeSelection = np.bitwise_and(timeSelection, stream["TimeDomain"]["Missing"][:,DataIndex] == 0)
            if np.sum(timeSelection) < 250 * 5:
                continue
            StimulationEpoch = stream["TimeDomain"]["Filtered"][DataIndex][timeSelection]
            fxx, pxx = signal.welch(StimulationEpoch, fs=stream["TimeDomain"]["SamplingRate"], nperseg=250 * 1, noverlap=250 * 0.5, nfft=250 * 2, scaling="density")
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i-1], "Frequency": fxx, "PSD": pxx})
            timeSelection = rangeSelection(stream["TimeDomain"]["Spectrogram"][DataIndex]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])

        elif method == "Spectrogram":
            timeSelection = rangeSelection(stream["TimeDomain"]["Spectrogram"][DataIndex]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            timeSelection = np.bitwise_and(timeSelection, stream["TimeDomain"]["Spectrogram"][DataIndex]["Missing"] == 0)
            if np.sum(timeSelection) < 2 * 5:
                continue
            StimulationEpochs.append({"Stimulation": StimulationSeries["Amplitude"][i-1], "Frequency": stream["TimeDomain"]["Spectrogram"][DataIndex]["Frequency"], "PSD": np.mean(stream["TimeDomain"]["Spectrogram"][DataIndex]["Power"][:,timeSelection],axis=1)})

        elif method == "Wavelet":
            timeSelection = rangeSelection(stream["TimeDomain"]["Wavelet"][DataIndex]["Time"],[StimulationSeries["Time"][i-1]+2,StimulationSeries["Time"][i]-2])
            if np.sum(timeSelection) < 250 * 5:
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
        timeSelection = np.bitwise_and(StimulationEpochs[i]["TimeSelection"], stream["TimeDomain"]["Spectrogram"][DataIndex]["Missing"] == 0)
        
        if method == "Wavelet":
            timeSelection = np.bitwise_and(timeSelection, stream["TimeDomain"]["Missing"][:,DataIndex] == 0)
            StimulationEpochs[i]["SpectralFeatures"] = stream["TimeDomain"]["Wavelet"][DataIndex]["Power"][:,timeSelection]
        else:
            timeSelection = np.bitwise_and(timeSelection, stream["TimeDomain"]["Spectrogram"][DataIndex]["Missing"] == 0)
            StimulationEpochs[i]["SpectralFeatures"] = stream["TimeDomain"]["Spectrogram"][DataIndex]["Power"][:,timeSelection]

        StimulationEpochs[i]["SpectralFeatures"] = np.mean(StimulationEpochs[i]["SpectralFeatures"][frequencySelection,:],axis=0)
        del(StimulationEpochs[i]["TimeSelection"])

    return StimulationEpochs

def processAnnotationAnalysis(data):
    EventOnsetSpectrum = {}
    EventPSDs = {}
    if "Annotations" in data.keys():
        for j in range(len(data["Annotations"])):
            if data["Annotations"][j]["Duration"] > 0:
                if not data["Annotations"][j]["Name"] in EventPSDs.keys():
                    EventPSDs[data["Annotations"][j]["Name"]] = []

                EventStartTime = data["Annotations"][j]["Time"] - data["Timestamp"]
                for k in range(len(data["Stream"])):
                    ChannelFound = -1
                    for l in range(len(EventPSDs[data["Annotations"][j]["Name"]])):
                        if EventPSDs[data["Annotations"][j]["Name"]][l]["Channel"] == data["Channels"][k]:
                            ChannelFound = l
                            break

                    if not ChannelFound >= 0:
                        EventPSDs[data["Annotations"][j]["Name"]].append({
                            "Channel": data["Channels"][k],
                            "Count": 0,
                            "MeanPower": [],
                            "StdPower": [],
                            "Frequency": []
                        })
                        ChannelFound = len(EventPSDs[data["Annotations"][j]["Name"]]) - 1
                    
                    TimeSelection = rangeSelection(data["Stream"][k]["Spectrogram"]["Time"], [EventStartTime, EventStartTime+data["Annotations"][j]["Duration"]])
                    PSDs = data["Stream"][k]["Spectrogram"]["Power"][:, TimeSelection]
                    EventPSDs[data["Annotations"][j]["Name"]][ChannelFound]["Count"] += 1
                    EventPSDs[data["Annotations"][j]["Name"]][ChannelFound]["MeanPower"].append(np.mean(PSDs, axis=1))
                    EventPSDs[data["Annotations"][j]["Name"]][ChannelFound]["Frequency"] = data["Stream"][k]["Spectrogram"]["Frequency"]

            else:
                for k in range(len(data["Channels"])):
                    key = data["Channels"][k] + " " + data["Annotations"][j]["Name"]
                    
                    if not key in EventOnsetSpectrum.keys():
                        EventOnsetSpectrum[key] = {
                            "Count": 0,
                            "Time": [],
                            "Frequency": [],
                            "Spectrum": []
                        }

                    EventStartTime = data["Annotations"][j]["Time"] - data["Timestamp"]
                    TimeSelection = rangeSelection(data["Stream"][k]["Spectrogram"]["Time"], [EventStartTime-5, EventStartTime+5])
                    EventOnsetSpectrum[key]["Frequency"] = data["Stream"][k]["Spectrogram"]["Frequency"]
                    EventOnsetSpectrum[key]["Time"] = data["Stream"][k]["Spectrogram"]["Time"][TimeSelection] - EventStartTime

                    PSDs = data["Stream"][k]["Spectrogram"]["Power"][:, TimeSelection]
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

    data["EventPSDs"] = EventPSDs
    data["EventOnsetSpectrum"] = EventOnsetSpectrum
    return data