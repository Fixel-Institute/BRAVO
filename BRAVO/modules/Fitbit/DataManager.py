import os
import datetime
import numpy as np

from Server import models
from modules import Database
from modules.Fitbit import DataQuery

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

def loadFitbitData(Participant):
    Data = {}
    source = models.SourceFile.find(owner=Participant, type="FitbitWebAPISource")
    if source:
        Data = Database.loadSourceFile(source.pointer, source.hashed)
    return Data

def saveFitbitData(Participant, data):
    if not models.SourceFile.include(type="FitbitWebAPISource", owner=Participant):
        source = models.SourceFile(name="FitbitWebAPISource", type="FitbitWebAPISource", owner=Participant)
        source.save()
        source.pointer = DATABASE_PATH + "recordings" + os.path.sep + Participant.uid + os.path.sep + source.uid + ".bdat"
    else:
        source = models.SourceFile.find(owner=Participant, type="FitbitWebAPISource")

    source.hashed = Database.saveSourceFile(data, source.pointer)
    source.save()

def deleteFitbitData(Participant):
    source = models.SourceFile.find(owner=Participant, type="FitbitWebAPISource")
    if source:
        source.delete()
        
def calculateDateKey(period):
    keys = []
    for day in np.arange(period[0], period[1]+1, 3600*24):
        keys.append(DataQuery.fitbitDate(day))
    return keys

def formatFitbitData(data, type):
    Data = {"Time": [], "Data": [], "DateLabel": []}
    if not type in data.keys():
        return Data

    if type == "active-zone-minutes":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Value = {}
            for key in data[type][i]["value"].keys():
                Value[key] = float(data[type][i]["value"][key])
            Data["Data"].append(Value)
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "distance":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "Distance": float(data[type][i]["value"])
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "elevation":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "Elevation": float(data[type][i]["value"])
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "floors":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "Floor": float(data[type][i]["value"])
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "minutesSedentary":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "MinutesSedentary": float(data[type][i]["value"])
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "minutesLightlyActive":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "MinutesLightlyActive": float(data[type][i]["value"])
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "minutesFairlyActive":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "MinutesFairlyActive": float(data[type][i]["value"])
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "minutesVeryActive":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "MinutesVeryActive": float(data[type][i]["value"])
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "steps":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "Steps": float(data[type][i]["value"])
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "heart-rate":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Value = {}
            for j in data[type][i]["value"]["heartRateZones"]:
                Value[j["name"]] = [float(j["min"]), (float(j["min"])+float(j["max"]))/2 , float(j["max"])]
            Data["Data"].append(Value)
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "heart-rate-variability":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "DailyHeartRateVariability": float(data[type][i]["value"]["dailyRmssd"]),
                "DeepHeartRateVariability": float(data[type][i]["value"]["deepRmssd"]),
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "oxygen-saturation":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "OxygenSaturation": [float(data[type][i]["value"]["min"]), float(data[type][i]["value"]["avg"]) , float(data[type][i]["value"]["max"])]
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "skin-temperature":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Value = {}
            for j in data[type][i]["value"].keys():
                Value[j] = float(data[type][i]["value"][j])
            Value["SkinTemperatureLogType"] = data[type][i]["logType"]
            Data["Data"].append(Value)
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "core-temperature":
        # TODO: Not available on the watches we purchased. 
        pass
    
    elif type == "breathing-rate":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "BreathingRate": float(data[type][i]["value"]["breathingRate"]),
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    elif type == "sleep":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateOfSleep"] + "T00:00:00+00:00").timestamp())
            Data["Data"].append({
                "SleepDuration": float(data[type][i]["duration"]),
                "SleepTotalSleepMinutes": float(data[type][i]["minutesAsleep"]),
                "SleepTotalTimeInBed": float(data[type][i]["timeInBed"]),
                "SleepStartTime": datetime.datetime.fromisoformat(data[type][i]["startTime"]),
                "SleepEndTime": datetime.datetime.fromisoformat(data[type][i]["endTime"]),
                "SleepDuration": float(data[type][i]["duration"]),
            })
            Data["Unstructured"] = data[type][i]
            Data["DateLabel"].append(data[type][i]["dateOfSleep"])
    
    elif type == "cardioscore":
        for i in range(len(data[type])):
            Data["Time"].append(datetime.datetime.fromisoformat(data[type][i]["dateTime"] + "T00:00:00+00:00"))
            Vo2Max = data[type][i]["value"]["vo2Max"].split("-")
            Data["Data"].append({
                "MaximalOxygenConsumption": [float(Vo2Max[0]), (float(Vo2Max[0])+float(Vo2Max[1]))/2 , float(Vo2Max[1])],
            })
            Data["DateLabel"].append(data[type][i]["dateTime"])

    else:
        print(type)

    return Data

def filterDataByDateKeys(data, datekey):
    FilteredData = {"Time": [], "Data": [], "DateLabel": []}
    for i in range(len(data["DateLabel"])):
        if data["DateLabel"][i] in datekey:
            FilteredData["Time"].append(data["Time"][i])
            FilteredData["Data"].append(data["Data"][i])
            FilteredData["DateLabel"].append(data["DateLabel"][i])
    return FilteredData

def createPlaceholderRecording(date):
    DateTimeObj = datetime.datetime.fromisoformat(DataQuery.fitbitDate(date) + "T00:00:00+00:00")
    Metadata = {
        "QueryTime": DataQuery.fitbitDate(date),
        "Timezone": DateTimeObj.tzname(),
        "DayLabel": "",
        "DailySummaryTimestamp": DateTimeObj.timestamp(),
        "Score": -1,
        "ScoreContributors": {},
        "NoData": True
    }
    Descriptor = {}

    Recording = dict()
    Recording["SamplingRate"] = -1
    Recording["ChannelNames"] = []
    Recording["Time"] = np.zeros(0)
    Recording["Data"] = np.zeros((0,1))
    Recording["Missing"] = np.zeros((0,1))
    Recording["StartTime"] = DateTimeObj.timestamp()
    Recording["Duration"] = 0
    Recording["Descriptor"] = Descriptor
    Recording["Metadata"] = Metadata
    return Recording

def hasData(listItems, date):
    for i in range(len(listItems)):
        if "Metadata" in listItems[i].keys():
            if listItems[i]["Metadata"]["QueryTime"] == date:
                return True
    return False

def getOffsetString(offset):
    if offset >= 0:
        return f"+{int(offset/3600):02d}:{int((offset%3600)/60):02d}"
    else:
        return f"-{int(abs(offset)/3600):02d}:{int((abs(offset)%3600)/60):02d}"

def refreshFitbitData(device):
    Participant = device.owner
    Data = loadFitbitData(Participant)

    for key in Data.keys():
        Data[key] = [recording for recording in Data[key] if "StartTime" in recording.keys() and len(recording["Time"]) > 0]
    
    AcceptedDates = []
    for date in device.date_periods:
        AcceptedDates.extend(calculateDateKey(date))

    DateToQuery = []
    for date in AcceptedDates:
        QueryTimestamp = datetime.datetime.fromisoformat(date + "T00:00:00" + getOffsetString(device.auth["timezoneOffset"]/1000)).timestamp()
        if QueryTimestamp > datetime.datetime.now().timestamp()-24*3600:
            continue
        DateToQuery.append(QueryTimestamp)
    DateToQuery = sorted(DateToQuery)
    
    try:
        for date in DateToQuery:
            for resource in ["activities/heart", "activities/active-zone-minutes", "activities/calories", "activities/distance", "activities/elevation", "activities/floors", "activities/steps", "hrv", "spo2"]:
                if not (resource+"-intraday") in Data.keys():
                    Data[resource+"-intraday"] = []

                if hasData(Data[resource+"-intraday"], DataQuery.fitbitDate(date)):
                    continue
                
                result = DataQuery.getIntradayActivityTimeseries(device, resource, date)
                if resource == "activities/active-zone-minutes":
                    if len(result[resource.replace("/","-") + "-intraday"]) == 0:
                        Recording = createPlaceholderRecording(date)
                        Data[resource+"-intraday"].append(Recording)
                        continue

                    for n in range(len(result[resource.replace("/","-") + "-intraday"])):
                        DateTimeObj = datetime.datetime.fromisoformat(result[resource.replace("/","-") + "-intraday"][n]["dateTime"] + "T00:00:00" + getOffsetString(device.auth["timezoneOffset"]/1000))
                        Metadata = {
                            "QueryTime": DataQuery.fitbitDate(date),
                            "Timezone": DateTimeObj.tzname(),
                            "DayLabel": result[resource.replace("/","-") + "-intraday"][n]["dateTime"],
                            "DailySummaryTimestamp": DateTimeObj.timestamp(),
                            "Score": -1,
                            "ScoreContributors": {},
                        }

                        Descriptor = {}

                        Recording = dict()
                        Recording["SamplingRate"] = -1
                        Recording["ChannelNames"] = ["activeZoneMinutes"]
                        Recording["Time"] = np.zeros(len(result[resource.replace("/","-") + "-intraday"][n]["minutes"]))
                        Recording["Data"] = np.zeros((len(result[resource.replace("/","-") + "-intraday"][n]["minutes"]), len(Recording["ChannelNames"])))
                        for i in range(len(result[resource.replace("/","-") + "-intraday"][n]["minutes"])):
                            Recording["Time"][i] = datetime.datetime.fromisoformat(result[resource.replace("/","-") + "-intraday"][n]["minutes"][i]["minute"].replace(".000", getOffsetString(device.auth["timezoneOffset"]/1000))).timestamp()
                            for j in range(len(Recording["ChannelNames"])):
                                Recording["Data"][i,j] = result[resource.replace("/","-") + "-intraday"][n]["minutes"][i]["value"][Recording["ChannelNames"][j]]

                        Recording["Missing"] = np.zeros((len(result[resource.replace("/","-") + "-intraday"][n]["minutes"]), len(Recording["ChannelNames"])))
                        Recording["StartTime"] = DateTimeObj.timestamp()
                        if len(Recording["Time"]) > 0:
                            Recording["Duration"] = Recording["Time"][-1] - Recording["Time"][0]
                        else:
                            Recording["Duration"] = 0
                        Recording["Descriptor"] = Descriptor
                        Recording["Metadata"] = Metadata
                        Data[resource+"-intraday"].append(Recording)

                elif resource.startswith("activities"):
                    DateTimeObj = datetime.datetime.fromisoformat(result[resource.replace("/","-")][0]["dateTime"] + "T00:00:00" + getOffsetString(device.auth["timezoneOffset"]/1000))
                    Metadata = {
                        "QueryTime": DataQuery.fitbitDate(date),
                        "Timezone": DateTimeObj.tzname(),
                        "DayLabel": result[resource.replace("/","-")][0]["dateTime"],
                        "DailySummaryTimestamp": DateTimeObj.timestamp(),
                        "Score": result[resource.replace("/","-")][0]["value"],
                        "ScoreContributors": {},
                    }

                    Descriptor = {}

                    Recording = dict()
                    Recording["SamplingRate"] = -1
                    Recording["ChannelNames"] = [resource]
                    Recording["Time"] = np.zeros(len(result[resource.replace("/","-") + "-intraday"]["dataset"]))
                    Recording["Data"] = np.zeros((len(result[resource.replace("/","-") + "-intraday"]["dataset"]), 1))
                    for i in range(len(result[resource.replace("/","-") + "-intraday"]["dataset"])):
                        Recording["Time"][i] = datetime.datetime.fromisoformat(Metadata["DayLabel"] + "T" + result[resource.replace("/","-") + "-intraday"]["dataset"][i]["time"] + getOffsetString(device.auth["timezoneOffset"]/1000)).timestamp()
                        Recording["Data"][i,0] = result[resource.replace("/","-") + "-intraday"]["dataset"][i]["value"]

                    Recording["Missing"] = np.zeros((len(result[resource.replace("/","-") + "-intraday"]["dataset"]), 2))
                    Recording["StartTime"] = DateTimeObj.timestamp()
                    if len(Recording["Time"]) > 0:
                        Recording["Duration"] = Recording["Time"][-1] - Recording["Time"][0]
                    else:
                        Recording["Duration"] = 0
                    Recording["Descriptor"] = Descriptor
                    Recording["Metadata"] = Metadata
                    Data[resource+"-intraday"].append(Recording)

                elif resource == "hrv":
                    if len(result[resource]) == 0:
                        Recording = createPlaceholderRecording(date)
                        Data[resource+"-intraday"].append(Recording)
                        continue

                    for n in range(len(result[resource])):
                        DateTimeObj = datetime.datetime.fromisoformat(result[resource][n]["dateTime"] + "T00:00:00" + getOffsetString(device.auth["timezoneOffset"]/1000))
                        Metadata = {
                            "QueryTime": DataQuery.fitbitDate(date),
                            "Timezone": DateTimeObj.tzname(),
                            "DayLabel": result[resource][n]["dateTime"],
                            "DailySummaryTimestamp": DateTimeObj.timestamp(),
                            "Score": -1,
                            "ScoreContributors": {},
                        }

                        Descriptor = {}

                        Recording = dict()
                        Recording["SamplingRate"] = -1
                        Recording["ChannelNames"] = ["rmssd", "coverage", "hf", "lf"]
                        Recording["Time"] = np.zeros(len(result[resource][n]["minutes"]))
                        Recording["Data"] = np.zeros((len(result[resource][n]["minutes"]), 4))
                        for i in range(len(result[resource][n]["minutes"])):
                            Recording["Time"][i] = datetime.datetime.fromisoformat(result[resource][n]["minutes"][i]["minute"].replace(".000", getOffsetString(device.auth["timezoneOffset"]/1000))).timestamp()
                            for j in range(len(Recording["ChannelNames"])):
                                Recording["Data"][i,j] = result[resource][n]["minutes"][i]["value"][Recording["ChannelNames"][j]]

                        Recording["Missing"] = np.zeros((len(result[resource][n]["minutes"]), 4))
                        Recording["StartTime"] = DateTimeObj.timestamp()
                        if len(Recording["Time"]) > 0:
                            Recording["Duration"] = Recording["Time"][-1] - Recording["Time"][0]
                        else:
                            Recording["Duration"] = 0
                        Recording["Descriptor"] = Descriptor
                        Recording["Metadata"] = Metadata
                        Data[resource+"-intraday"].append(Recording)

                elif resource == "spo2":
                    if len(result) == 0:
                        Recording = createPlaceholderRecording(date)
                        Data[resource+"-intraday"].append(Recording)
                        continue

                    for n in range(len(result)):
                        DateTimeObj = datetime.datetime.fromisoformat(result[n]["dateTime"] + "T00:00:00" + getOffsetString(device.auth["timezoneOffset"]/1000))
                        Metadata = {
                            "QueryTime": DataQuery.fitbitDate(date),
                            "Timezone": DateTimeObj.tzname(),
                            "DayLabel": result[n]["dateTime"],
                            "DailySummaryTimestamp": DateTimeObj.timestamp(),
                            "Score": -1,
                            "ScoreContributors": {},
                        }

                        Descriptor = {}

                        Recording = dict()
                        Recording["SamplingRate"] = -1
                        Recording["ChannelNames"] = ["spo2"]
                        Recording["Time"] = np.zeros(len(result[n]["minutes"]))
                        Recording["Data"] = np.zeros((len(result[n]["minutes"]), 1))
                        for i in range(len(result[n]["minutes"])):
                            Recording["Time"][i] = datetime.datetime.fromisoformat(result[n]["minutes"][i]["minute"].replace(".000", getOffsetString(device.auth["timezoneOffset"]/1000))).timestamp()
                            Recording["Data"][i,0] = result[n]["minutes"][i]["value"]

                        Recording["Missing"] = np.zeros((len(result[n]["minutes"]), 1))
                        Recording["StartTime"] = DateTimeObj.timestamp()
                        if len(Recording["Time"]) > 0:
                            Recording["Duration"] = Recording["Time"][-1] - Recording["Time"][0]
                        else:
                            Recording["Duration"] = 0
                        Recording["Descriptor"] = Descriptor
                        Recording["Metadata"] = Metadata
                        Data[resource+"-intraday"].append(Recording)

            for key in DataQuery.FitbitDataTypes.keys():
                if not key in Data.keys():
                    Data[key] = []

                if hasData(Data[key], DataQuery.fitbitDate(date)):
                    continue

                result = DataQuery.queryFitbitData(device, key, int(date), int(date))
                if len(result) == 0:
                    Recording = createPlaceholderRecording(date)
                    Data[key].append(Recording)
                    continue
                
                if key in ["active-zone-minutes", "heart-rate-variability", "oxygen-saturation", "skin-temperature", "core-temperature", "breathing-rate"]:
                    for n in range(len(result)):
                        DateTimeObj = datetime.datetime.fromisoformat(result[n]["dateTime"] + "T00:00:00" + getOffsetString(device.auth["timezoneOffset"]/1000))
                        Metadata = {
                            "QueryTime": DataQuery.fitbitDate(date),
                            "Timezone": DateTimeObj.tzname(),
                            "DayLabel": result[n]["dateTime"],
                            "DailySummaryTimestamp": DateTimeObj.timestamp(),
                            "Score": -1,
                            "ScoreContributors": {},
                        }

                        Descriptor = {}

                        Recording = dict()
                        Recording["SamplingRate"] = -1
                        Recording["ChannelNames"] = [a for a in result[n]["value"].keys()]
                        Recording["Time"] = np.zeros(1)
                        Recording["Data"] = np.zeros((1, len(Recording["ChannelNames"])))
                        
                        Recording["Time"][0] = DateTimeObj.timestamp()
                        for i in range(len(Recording["ChannelNames"])):
                            Recording["Data"][0,i] = result[n]["value"][Recording["ChannelNames"][i]]

                        Recording["Missing"] = np.zeros((1, len(Recording["ChannelNames"])))
                        Recording["StartTime"] = DateTimeObj.timestamp()
                        Recording["Duration"] = 0
                        Recording["Descriptor"] = Descriptor
                        Recording["Metadata"] = Metadata
                        Data[key].append(Recording)
                
                elif key in ["heart-rate"]:
                    for n in range(len(result)):
                        DateTimeObj = datetime.datetime.fromisoformat(result[n]["dateTime"] + "T00:00:00" + getOffsetString(device.auth["timezoneOffset"]/1000))
                        Metadata = {
                            "QueryTime": DataQuery.fitbitDate(date),
                            "Timezone": DateTimeObj.tzname(),
                            "DayLabel": result[n]["dateTime"],
                            "DailySummaryTimestamp": DateTimeObj.timestamp(),
                            "Score": -1,
                            "ScoreContributors": {},
                        }

                        Descriptor = {}

                        Recording = dict()
                        Recording["SamplingRate"] = -1
                        Recording["ChannelNames"] = [zone["name"] for zone in result[n]["value"]["heartRateZones"]]
                        Recording["Time"] = np.zeros(1)
                        Recording["Data"] = np.zeros((1, len(Recording["ChannelNames"])))
                        
                        Recording["Time"][0] = DateTimeObj.timestamp()
                        for i in range(len(Recording["ChannelNames"])):
                            for j in range(len(result[n]["value"]["heartRateZones"])):
                                if Recording["ChannelNames"][i] == result[n]["value"]["heartRateZones"][j]["name"]:
                                    Recording["Data"][0,i] = result[n]["value"]["heartRateZones"][j]["minutes"]
                                    break
                        Recording["Missing"] = np.zeros((1, len(Recording["ChannelNames"])))
                        Recording["StartTime"] = DateTimeObj.timestamp()
                        Recording["Duration"] = 0
                        Recording["Descriptor"] = Descriptor
                        Recording["Metadata"] = Metadata
                        Data[key].append(Recording)

                elif key in ["sleep"]:
                    for n in range(len(result)):
                        DateTimeObj = datetime.datetime.fromisoformat(result[0]["startTime"].replace(".000", getOffsetString(device.auth["timezoneOffset"]/1000)))
                        Metadata = {
                            "QueryTime": DataQuery.fitbitDate(date),
                            "Timezone": DateTimeObj.tzname(),
                            "DayLabel": result[0]["dateOfSleep"],
                            "DailySummaryTimestamp": DateTimeObj.timestamp(),
                            "Score": -1,
                            "ScoreContributors": {},
                            "SleepStages": {
                                "asleep": 1,
                                "restless": 2,
                                "awake": 3,
                                "deep": 4,
                                "light": 5,
                                "rem": 6, 
                                "wake": 7
                            }
                        }

                        Descriptor = {
                            "Duration": result[n]["duration"],
                            "Efficiency": result[n]["efficiency"],
                            "MinutesAfterWakeup": result[n]["minutesAfterWakeup"],
                            "MinutesAsleep": result[n]["minutesAsleep"],
                            "MinutesAwake": result[n]["minutesAwake"],
                            "MinutesToFallAsleep": result[n]["minutesToFallAsleep"],
                            "TimeInBed": result[n]["timeInBed"],
                        }

                        Recording = dict()
                        Recording["SamplingRate"] = -1
                        Recording["ChannelNames"] = ["SleepStage"]
                        Recording["Time"] = np.zeros(len(result[n]["levels"]["data"]))
                        Recording["Duration"] = np.zeros(len(result[n]["levels"]["data"]))
                        Recording["Data"] = np.zeros((len(result[n]["levels"]["data"]), len(Recording["ChannelNames"])))

                        for i in range(len(result[n]["levels"]["data"])):
                            Recording["Time"][i] = datetime.datetime.fromisoformat(result[n]["levels"]["data"][i]["dateTime"].replace(".000", "") + getOffsetString(device.auth["timezoneOffset"]/1000)).timestamp()
                            Recording["Duration"][i] = result[n]["levels"]["data"][i]["seconds"]
                            Recording["Data"][i,0] = float(Metadata["SleepStages"][result[n]["levels"]["data"][i]["level"]])

                        Recording["Missing"] = np.zeros(Recording["Data"].shape)
                        Recording["StartTime"] = DateTimeObj.timestamp()
                        Recording["Descriptor"] = Descriptor
                        Recording["Metadata"] = Metadata
                        Data[key].append(Recording)

                elif key in ["cardioscore"]:
                    for n in range(len(result)):
                        DateTimeObj = datetime.datetime.fromisoformat(result[n]["dateTime"] + "T00:00:00" + getOffsetString(device.auth["timezoneOffset"]/1000))
                        Metadata = {
                            "QueryTime": DataQuery.fitbitDate(date),
                            "Timezone": DateTimeObj.tzname(),
                            "DayLabel": result[n]["dateTime"],
                            "DailySummaryTimestamp": DateTimeObj.timestamp(),
                            "Score": -1,
                            "ScoreContributors": {},
                        }

                        Descriptor = {}

                        Recording = dict()
                        Recording["SamplingRate"] = -1
                        Recording["ChannelNames"] = ["vo2MaxRange0", "vo2MaxRange1"]
                        Recording["Time"] = np.zeros(1)
                        Recording["Data"] = np.zeros((1, len(Recording["ChannelNames"])))
                        
                        Recording["Time"][0] = DateTimeObj.timestamp()
                        Recording["Data"][0,0] = float(result[n]["value"]["vo2Max"].split("-")[0])
                        Recording["Data"][0,1] = float(result[n]["value"]["vo2Max"].split("-")[1])

                        Recording["Missing"] = np.zeros((1, len(Recording["ChannelNames"])))
                        Recording["StartTime"] = DateTimeObj.timestamp()
                        Recording["Duration"] = 0
                        Recording["Descriptor"] = Descriptor
                        Recording["Metadata"] = Metadata
                        Data[key].append(Recording)

                elif key in ["distance", "elevation", "floors", "minutesSedentary", "minutesLightlyActive", "minutesFairlyActive", "minutesVeryActive", "steps"]:
                    for n in range(len(result)):
                        DateTimeObj = datetime.datetime.fromisoformat(result[n]["dateTime"] + "T00:00:00" + getOffsetString(device.auth["timezoneOffset"]/1000))
                        Metadata = {
                            "QueryTime": DataQuery.fitbitDate(date),
                            "Timezone": DateTimeObj.tzname(),
                            "DayLabel": result[n]["dateTime"],
                            "DailySummaryTimestamp": DateTimeObj.timestamp(),
                            "Score": -1,
                            "ScoreContributors": {},
                        }

                        Descriptor = {}

                        Recording = dict()
                        Recording["SamplingRate"] = -1
                        Recording["ChannelNames"] = [key]
                        Recording["Time"] = np.zeros(1)
                        Recording["Data"] = np.zeros((1, len(Recording["ChannelNames"])))
                        
                        Recording["Time"][0] = DateTimeObj.timestamp()
                        Recording["Data"][0,0] = float(result[n]["value"])
                        Recording["Missing"] = np.zeros((1, len(Recording["ChannelNames"])))
                        Recording["StartTime"] = DateTimeObj.timestamp()
                        Recording["Duration"] = 0
                        Recording["Descriptor"] = Descriptor
                        Recording["Metadata"] = Metadata
                        Data[key].append(Recording)

    except Exception as e:
        print(f"Error refreshing Fitbit data: {e}")
        
    finally:
        saveFitbitData(Participant, Data)

def calculateDataDifference(device, data):
    DataTypes = ["active-zone-minutes","distance","elevation","floors","minutesSedentary","minutesLightlyActive","minutesFairlyActive","minutesVeryActive",
        "steps","heart-rate","heart-rate-variability","oxygen-saturation","skin-temperature","core-temperature","breathing-rate","sleep","cardioscore"]

    AcceptedDates = []
    for date in device.date_periods:
        AcceptedDates.extend(calculateDateKey(date))

    if len(data.keys()) == 0:
        DateToQuery = []
        for date in AcceptedDates:
            DateToQuery.append(datetime.datetime.fromisoformat(date + "T00:00:00+00:00").timestamp())

        DateToQuery = sorted(DateToQuery)
        DateBreaks = np.where(np.diff(sorted(DateToQuery)) > 3600*24)[0]
        if len(DateBreaks) == 0:
            Data = DataQuery.queryAllData(device, int(DateToQuery[0]), int(DateToQuery[-1]))
        
        for key in DataTypes:
            Data[key] = formatFitbitData(data, key)
        return Data

    else:
        ExistingData = {}
        for key in DataTypes:
            ExistingData[key] = formatFitbitData(data, key)
            ExistingData[key] = filterDataByDateKeys(ExistingData[key], AcceptedDates)

            DateToQuery = []
            for date in AcceptedDates:
                if not date in ExistingData[key]["DateLabel"]:
                    DateToQuery.append(datetime.datetime.fromisoformat(date + "T00:00:00+00:00").timestamp())

            DateToQuery = sorted(DateToQuery)
            DateBreaks = np.where(np.diff(sorted(DateToQuery)) > 3600*24)[0]

            if len(DateBreaks) == 0:
                pass
            else:
                pass 
            