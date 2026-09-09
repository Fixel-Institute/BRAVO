import numpy as np
import pandas as pd
from io import BytesIO

def decodeMDATv2(rawBytes):
    packets = []
    startIndex = 0
    while startIndex < len(rawBytes):
        header = rawBytes[startIndex : startIndex + 4]
        if not header == b'PFF\x00':
            raise Exception("ReadMDAT Format Error: Header Error")
        
        Time = np.frombuffer(rawBytes[startIndex + 4 : startIndex + 12], dtype="<i8")[0]
        dataLengths = np.frombuffer(rawBytes[startIndex + 12 : startIndex + 20], dtype="<i4")
        Trigger = rawBytes[startIndex + 20 : startIndex + 20 + dataLengths[0]].decode("utf-8")
        if Trigger == "TriggerText":
            Data = rawBytes[startIndex + 20 + dataLengths[0] : startIndex + 20 + dataLengths[0] + dataLengths[1]].decode("utf-8")
        else:
            Data = np.frombuffer(rawBytes[startIndex + 20 + dataLengths[0] : startIndex + 20 + dataLengths[0] + dataLengths[1]], dtype="<f8")
            
        packets.append({
            "Time": Time,
            "Type": Trigger,
            "Data": Data
        })

        startIndex += 20 + dataLengths[0] + dataLengths[1]

    RecordingId = 0
    DelsysRecording = []
    for i in range(len(packets)):
        if packets[i]["Type"] == "TriggerText":
            if packets[i]["Data"] == "Delsys Started":
                RecordingId += 1

    Channels = []
    for i in range(len(packets)):
        if packets[i]["Type"].endswith(" SamplingRate"):
            ChannelName = packets[i]["Type"].replace(" SamplingRate","")
            Channels.append(ChannelName)
    Channels = sorted(Channels)

    Delsys = []
    for n in range(len(Channels)):
        totalSize = 0
        startTime = 0
        fs = -1
        for i in range(len(packets)):
            if packets[i]["Type"] == "TriggerText":
                if packets[i]["Data"] == "Delsys Started":
                    startTime = packets[i]["Time"]
            elif packets[i]["Type"] == Channels[n] + " SamplingRate":
                fs = packets[i]["Data"]
            elif packets[i]["Type"] == Channels[n]:
                totalSize += len(packets[i]["Data"])

        Signal = np.zeros(totalSize)
        totalSize = 0
        for i in range(len(packets)):
            if packets[i]["Type"] == Channels[n]:
                Signal[totalSize:totalSize + len(packets[i]["Data"])] = packets[i]["Data"]
                totalSize += len(packets[i]["Data"])
        
        Delsys.append({
            "Name": Channels[n],
            "Data": Signal,
            "SamplingRate": fs,
            "StartTime": startTime
        })

    SamplingRates = np.unique([Delsys[i]["SamplingRate"] for i in range(len(Delsys))])

    SensorDataList = []
    for fs in SamplingRates:
        RecordingDurations = [len(Delsys[i]["Data"]) for i in range(len(Delsys)) if Delsys[i]["SamplingRate"] == fs]
        MinRecordingDuration = np.min(RecordingDurations)

        Data = {"ChannelNames": []}
        Data["Time"] = np.arange(MinRecordingDuration) / fs
        Data["Data"] = []
        for i in range(len(Delsys)):
            if Delsys[i]["SamplingRate"] == fs:
                Data["Data"].append(Delsys[i]["Data"][:MinRecordingDuration])
                Data["ChannelNames"].append(Delsys[i]["Name"])
        Data["Data"] = np.array(Data["Data"]).T
        Data["SamplingRate"] = fs
        Data["StartTime"] = Delsys[i]["StartTime"] / 1000
        Data["Missing"] = np.zeros(Data["Data"].shape)
        Data["Duration"] = MinRecordingDuration / fs
        SensorDataList.append(Data)
    
    return SensorDataList

def decodeMDATv3(rawBytes):
    packets = []
    startIndex = 0
    while startIndex < len(rawBytes):
        header = rawBytes[startIndex : startIndex + 4]
        if not header == b'PFF\x00':
            raise Exception("ReadMDAT Format Error: Header Error")
        
        Time = np.frombuffer(rawBytes[startIndex + 4 : startIndex + 12], dtype="<i8")[0]
        dataLengths = np.frombuffer(rawBytes[startIndex + 12 : startIndex + 20], dtype="<i4")
        Trigger = rawBytes[startIndex + 20 : startIndex + 20 + dataLengths[0]].decode("utf-8")
        if Trigger == "TriggerText":
            Data = rawBytes[startIndex + 20 + dataLengths[0] : startIndex + 20 + dataLengths[0] + dataLengths[1]].decode("utf-8")
        elif Trigger == "Delsys_ChannelIDs":
            Data = rawBytes[startIndex + 20 + dataLengths[0] : startIndex + 20 + dataLengths[0] + dataLengths[1]].decode("utf-8")
        else:
            Data = np.frombuffer(rawBytes[startIndex + 20 + dataLengths[0] : startIndex + 20 + dataLengths[0] + dataLengths[1]], dtype="<f8")
            
        packets.append({
            "Time": Time,
            "Type": Trigger,
            "Data": Data
        })

        startIndex += 20 + dataLengths[0] + dataLengths[1]

    RecordingId = 0
    DelsysRecording = []
    for i in range(len(packets)):
        if packets[i]["Type"] == "TriggerText":
            if packets[i]["Data"] == "Delsys Started":
                RecordingId += 1

    ChannelInfos = {}
    LastSeenChannel = ""
    for i in range(len(packets)):
        if packets[i]["Type"] == "Delsys_ChannelIDs":
            ChannelInfos[packets[i]["Data"]] = {"SamplingRate": -1}
            LastSeenChannel = packets[i]["Data"]
        elif packets[i]["Type"] == "Delsys_SamplingRate":
            if LastSeenChannel != "":
                ChannelInfos[LastSeenChannel]["SamplingRate"] = packets[i]["Data"][0]
                LastSeenChannel = ""
            else:
                raise Exception("ReadMDAT Format Error: SamplingRate without preceding ChannelID")

    Delsys = []
    Channels = list(ChannelInfos.keys())
    for n in range(len(Channels)):
        totalSize = 0
        startTime = 0
        fs = -1
        for i in range(len(packets)):
            if packets[i]["Type"] == "Delsys_DataPacket|" + Channels[n]:
                if startTime == 0: 
                    startTime = packets[i]["Time"]
                totalSize += len(packets[i]["Data"])

        Signal = np.zeros(totalSize)
        totalSize = 0
        for i in range(len(packets)):
            if packets[i]["Type"] == "Delsys_DataPacket|" + Channels[n]:
                Signal[totalSize:totalSize + len(packets[i]["Data"])] = packets[i]["Data"]
                totalSize += len(packets[i]["Data"])
        
        Delsys.append({
            "Name": Channels[n],
            "Data": Signal,
            "SamplingRate": ChannelInfos[Channels[n]]["SamplingRate"],
            "StartTime": startTime
        })

    SamplingRates = np.unique([Delsys[i]["SamplingRate"] for i in range(len(Delsys))])

    SensorDataList = []
    for fs in SamplingRates:
        RecordingDurations = [len(Delsys[i]["Data"]) for i in range(len(Delsys)) if Delsys[i]["SamplingRate"] == fs]
        MinRecordingDuration = np.min(RecordingDurations)

        Data = {"ChannelNames": []}
        Data["Time"] = np.arange(MinRecordingDuration) / fs
        Data["Data"] = []
        for i in range(len(Delsys)):
            if Delsys[i]["SamplingRate"] == fs:
                Data["Data"].append(Delsys[i]["Data"][:MinRecordingDuration])
                Data["ChannelNames"].append(Delsys[i]["Name"])
        Data["Data"] = np.array(Data["Data"]).T
        Data["SamplingRate"] = fs
        Data["StartTime"] = Delsys[i]["StartTime"] / 1000
        Data["Missing"] = np.zeros(Data["Data"].shape)
        Data["Duration"] = MinRecordingDuration / fs
        SensorDataList.append(Data)
    
    return SensorDataList
