import numpy as np 
from scipy import signal, stats
import utility.SignalProcessingUtility as SPU

#result = sio.loadmat("/mnt/d/BRAVOStorage/recordings/da633069-4449-4a54-88c4-6efeab560751/AnalysisOutput_Raw_d6da1ccc-6b12-4904-91ef-ad036c6ab46b.mat", simplify_cells=True)["ProcessedData"]

def ExtractEventPeriod(result):
    pass

def ExtractAlignedDataOverview(result, eventPeriod=[]):
    Accelerometer = None
    for recording in result:
        if recording["DataType"] == "Accelerometer":
            Accelerometer = recording
        if type(recording["ChannelNames"]) == str:
            recording["ChannelNames"] = [recording["ChannelNames"]]
        else:
            ChannelNames = []
            for name in recording["ChannelNames"]:
                if not name in ChannelNames:
                    ChannelNames.append(name)
            ChannelNames = [name.strip() for name in ChannelNames]
            recording["ChannelNames"] = ChannelNames
    
    AvailableSensors = []
    for name in Accelerometer["ChannelNames"]:
        if not name[:-2] in AvailableSensors:
            AvailableSensors.append(name[:-2])

    AvailableDataChannel = []
    for recording in result:
        if recording["DataType"] == "Signal":
            for name in recording["ChannelNames"]:
                if not name in AvailableDataChannel:
                    AvailableDataChannel.append(name)

    # Filter
    [b,a] = signal.butter(5, np.array([1,20])*2/Accelerometer["SamplingRate"], "bandpass")

    AccelerometerSpectrogram = {}
    if len(eventPeriod) > 0:
        TimePeriodSelection = np.zeros(Accelerometer["Time"].shape, dtype=bool)
        for event in eventPeriod:
            TimePeriodSelection[(Accelerometer["Time"] > event["EventTime"]) & (Accelerometer["Time"] < event["EventTime"]+event["EventDuration"])] = True
    else:
        TimePeriodSelection = np.ones(Accelerometer["Time"].shape, dtype=bool)

    if np.sum(TimePeriodSelection) < 500:
        return None
    
    for i in range(len(AvailableSensors)):
        ChannelSelection = np.array([name.startswith(AvailableSensors[i]) for name in Accelerometer["ChannelNames"]])
        rawSignal = SPU.rssq(Accelerometer["Data"][:,ChannelSelection])[TimePeriodSelection]
        Spectrum = SPU.defaultSpectrogram(signal.filtfilt(b,a,rawSignal), fs=Accelerometer["SamplingRate"])
        AccelerometerSpectrogram[AvailableSensors[i]] = {
            "MeanPower": np.mean(Spectrum["Power"], axis=1),
            "StdPower": SPU.stderr(Spectrum["Power"], axis=1)*2,
        }
        AccelerometerSpectrogram["Frequency"] = Spectrum["Frequency"]

    return {"AccelerometerSpectrogram": AccelerometerSpectrogram, "SensorChannels": AvailableSensors, "DataChannels": AvailableDataChannel}

def findIndex(array, value):
    index = np.argmin(np.abs(array-value))
    closeness = array[index] - value
    return index, closeness

def ExtractSpectrogramData(result, sensorName, channelName, eventPeriod=[]):
    Accelerometer = None
    for recording in result:
        if recording["DataType"] == "Accelerometer":
            Accelerometer = recording
        if type(recording["ChannelNames"]) == str:
            recording["ChannelNames"] = [recording["ChannelNames"]]
        else:
            ChannelNames = []
            for name in recording["ChannelNames"]:
                if not name in ChannelNames:
                    ChannelNames.append(name)
            ChannelNames = [name.strip() for name in ChannelNames]
            recording["ChannelNames"] = ChannelNames
    
    # Filter
    [b,a] = signal.butter(5, np.array([1,20])*2/Accelerometer["SamplingRate"], "bandpass")

    ChannelSelection = np.array([name.startswith(sensorName) for name in Accelerometer["ChannelNames"]])
    rawSignal = SPU.rssq(Accelerometer["Data"][:,ChannelSelection])
    SensorSpectrum = SPU.defaultSpectrogram(signal.filtfilt(b,a,rawSignal), fs=Accelerometer["SamplingRate"])
    SensorSpectrum["Power"] = SensorSpectrum["logPower"]
    del SensorSpectrum["logPower"]
    SensorSpectrum["Time"] += Accelerometer["StartTime"]

    MotionFrequencySelection = SensorSpectrum["Frequency"] < 30
    SensorSpectrum["Power"] = SensorSpectrum["Power"][MotionFrequencySelection, :]
    SensorSpectrum["Frequency"] = SensorSpectrum["Frequency"][MotionFrequencySelection]

    # Neural Recordings
    NeuralData = []
    for recording in result:
        if recording["DataType"] == "Signal":
            if len(recording["Data"]) < recording["SamplingRate"]*5:
                continue

            if np.ndim(recording["Data"]) == 1:
                recording["Data"] = np.reshape(recording["Data"], (len(recording["Data"]), 1))
            for i in range(len(recording["ChannelNames"])):
                if recording["ChannelNames"][i] == channelName:
                    Spectrum = SPU.defaultSpectrogram(recording["Data"][:,i], fs=recording["SamplingRate"])
                    Spectrum["Power"] = Spectrum["logPower"]
                    del Spectrum["logPower"]
                    Spectrum["Time"] += recording["StartTime"]
                    NeuralData.append(Spectrum)

    NeuralData = {"Power": np.concatenate([NeuralData[i]["Power"] for i in range(len(NeuralData))], axis=1),
                  "Time": np.concatenate([NeuralData[i]["Time"] for i in range(len(NeuralData))], axis=0),
                  "DataFrequency": NeuralData[0]["Frequency"]}
    NeuralData["SensorFrequency"] = SensorSpectrum["Frequency"]
    NeuralData["SensorPower"] = np.zeros((len(SensorSpectrum["Frequency"]), len(NeuralData["Time"])))
    NeuralData["Missing"] = np.zeros((len(NeuralData["Time"])), dtype=bool)
    
    if len(eventPeriod) > 0:
        NeuralData["Missing"] = np.ones(NeuralData["Time"].shape, dtype=bool)
        for event in eventPeriod:
            NeuralData["Missing"][(NeuralData["Time"] > event["EventTime"]) & (NeuralData["Time"] < event["EventTime"]+event["EventDuration"])] = False
    else:
        NeuralData["Missing"] = np.zeros((len(NeuralData["Time"])), dtype=bool)
    
    for i in range(len(NeuralData["Missing"])):
        index, closeness = findIndex(SensorSpectrum["Time"], NeuralData["Time"][i])
        if closeness < 1 and not np.any(np.isinf(NeuralData["Power"][:,i])):
            NeuralData["SensorPower"][:,i] = SensorSpectrum["Power"][:,index]
        else:
            NeuralData["Missing"][i] = True
    
    NeuralData["CorrelationMatrix"] = np.zeros((len(NeuralData["SensorFrequency"]), len(NeuralData["DataFrequency"])))
    for i in range(len(NeuralData["SensorFrequency"])):
        for j in range(len(NeuralData["DataFrequency"])):
            NeuralData["CorrelationMatrix"][i,j] = stats.pearsonr(NeuralData["SensorPower"][i,~NeuralData["Missing"]], NeuralData["Power"][j,~NeuralData["Missing"]]).statistic
            NeuralData["CorrelationMatrix"][i,j] *= NeuralData["CorrelationMatrix"][i,j]

    NeuralData["Power"] = NeuralData["Power"][:,~NeuralData["Missing"]]
    NeuralData["SensorPower"] = NeuralData["SensorPower"][:,~NeuralData["Missing"]]

    return NeuralData
