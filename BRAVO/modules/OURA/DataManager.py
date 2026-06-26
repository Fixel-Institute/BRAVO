import requests
import os, sys
import datetime
import numpy as np

from Server import models
from modules import Database

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class OuraRingAPI:
    def __init__(self, token, refresh_token=""):
        self.refresh_token = refresh_token
        self.token = token
        self.server = "https://api.ouraring.com"
        self.attempts = 0

    def query(self, endpoint, params):
        response = requests.get(f"{self.server}/{endpoint}",
                                headers={"Authorization": f"Bearer {self.token}"},
                                params=params)
        if self.attempts > 3:
            raise Exception("Too many failed attempts to query Oura API. Please check your token.")
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 401:
            print("Token expired or invalid. Attempting to refresh token...")
            self.refreshToken(refresh_token=self.refresh_token)
            self.attempts += 1
            return self.query(endpoint, params)
        
        self.attempts = 0
        print(response.status_code)
        raise Exception(response.text)
    
    def refreshToken(self, auth_code="", refresh_token=""):
        token_url = "https://api.ouraring.com/oauth/token"
        if auth_code:
            token_data = {
                "grant_type": "authorization_code",
                "code": auth_code,
                "client_id": os.environ["OURA_CLIENT_ID"],
                "client_secret": os.environ["OURA_CLIENT_SECRET"],
                "redirect_uri": os.environ["OURA_CLIENT_REDIRECT_URI"]
            }
        elif refresh_token:
            token_data = {
                "grant_type": "refresh_token",
                "refresh_token": refresh_token,
                "client_id": os.environ["OURA_CLIENT_ID"],
                "client_secret": os.environ["OURA_CLIENT_SECRET"],
            }

        response = requests.post(token_url, data=token_data, headers={"Content-Type": "application/x-www-form-urlencoded"})
        if response.status_code != 200:
            print("Failed to refresh token. Please check your credentials and try again.")
            print(response.json())
            return False
        
        tokens = response.json()
        access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        self.token = access_token
        return True

    def verifyToken(self):
        result = self.query("v2/usercollection/personal_info", {})
        return result

    def getDailyActivity(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        result = self.query("v2/usercollection/daily_activity", params)

        Recordings = []
        for item in result["data"]:
            DateTimeObj = datetime.datetime.fromisoformat(item["timestamp"])
            if len(item["class_5_min"]) < 288:
                continue

            ClassLabelUpSampled = np.zeros(5*len(item["class_5_min"]))
            for i in range(len(item["class_5_min"])):
                ClassLabelUpSampled[i*5:(i+1)*5] = np.ones(5) * int(item["class_5_min"][i])

            Metadata = {
                "Timezone": DateTimeObj.tzname(),
                "DayLabel": item["day"],
                "DailySummaryTimestamp": DateTimeObj.timestamp(),
                "Score": item["score"],
                "ScoreContributors": item["contributors"],
            }

            Descriptor = {
                "ActiveCalories": item["active_calories"],
                "AverageMETMinutes": item["average_met_minutes"],
                "HighActivityMETMinutes": item["high_activity_met_minutes"],
                "MediumActivityMETMinutes": item["medium_activity_met_minutes"],
                "LowActivityMETMinutes": item["low_activity_met_minutes"],
                "SedentaryActivityMETMinutes": item["sedentary_met_minutes"],
                "HighActivityTime": item["high_activity_time"],
                "MediumActivityTime": item["medium_activity_time"],
                "LowActivityTime": item["low_activity_time"],
                "SedentaryActivityTime": item["sedentary_time"],
                "RestingTime": item["resting_time"],
                "InactivityAlert": item["inactivity_alerts"],
                "MetersToTarget": item["meters_to_target"],
                "TargetMets": item["target_meters"],
                "TotalCalories": item["total_calories"],
                "Steps": item["steps"],
                "NonWearTime": item["non_wear_time"],
                "EquivalentWalkingDistance": item["equivalent_walking_distance"],
            }

            Recording = dict()
            Recording["SamplingRate"] = 1 / item["met"]["interval"]
            Recording["ChannelNames"] = ["Class Label", "Metabolic Equivalent of Task"]
            Recording["Data"] = np.array([ClassLabelUpSampled, item["met"]["items"]]).T
            Recording["Missing"] = np.zeros((len(ClassLabelUpSampled), 2))
            Recording["StartTime"] = datetime.datetime.fromisoformat(item["met"]["timestamp"]).timestamp()
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            Recording["Descriptor"] = Descriptor
            Recording["Metadata"] = Metadata
            Recordings.append(Recording)

        return Recordings

    def getDailyReadiness(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        result = self.query("v2/usercollection/daily_readiness", params)
        
        Recordings = []
        for item in result["data"]:
            DateTimeObj = datetime.datetime.fromisoformat(item["timestamp"])
            Metadata = {
                "Timezone": DateTimeObj.tzname(),
                "DayLabel": item["day"],
                "DailySummaryTimestamp": DateTimeObj.timestamp(),
                "Score": item["score"],
                "ScoreContributors": item["contributors"],
            }

            Descriptor = {
                "TemperatureDeviation": item["temperature_deviation"],
                "TemperatureTrendDeviation": item["temperature_trend_deviation"],
            }

            Recording = dict()
            Recording["SamplingRate"] = -1
            Recording["ChannelNames"] = []
            Recording["Data"] = np.zeros(0)
            Recording["Missing"] = np.zeros(0)
            Recording["StartTime"] = DateTimeObj.timestamp()
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            Recording["Descriptor"] = Descriptor
            Recording["Metadata"] = Metadata
            Recordings.append(Recording)

        return Recordings

    def getDailyResilience(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        # Not getting this data from testing user. Currently not immplented
        return self.query("v2/usercollection/daily_resilience", params)

    def getDailySleep(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        result = self.query("v2/usercollection/daily_sleep", params)
    
        Recordings = []
        for item in result["data"]:
            DateTimeObj = datetime.datetime.fromisoformat(item["timestamp"])
            Metadata = {
                "Timezone": DateTimeObj.tzname(),
                "DayLabel": item["day"],
                "DailySummaryTimestamp": DateTimeObj.timestamp(),
                "Score": item["score"],
                "ScoreContributors": item["contributors"],
            }

            Descriptor = {}

            Recording = dict()
            Recording["SamplingRate"] = -1
            Recording["ChannelNames"] = []
            Recording["Data"] = np.zeros(0)
            Recording["Missing"] = np.zeros(0)
            Recording["StartTime"] = DateTimeObj.timestamp()
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            Recording["Descriptor"] = Descriptor
            Recording["Metadata"] = Metadata
            Recordings.append(Recording)

        return Recordings

    def getDailySpo2(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        result = self.query("v2/usercollection/daily_spo2", params)
    
        Recordings = []
        for item in result["data"]:
            if not item["spo2_percentage"]:
                continue
            DateTimeObj = datetime.datetime.fromisoformat(item["day"] + "T00:00:00+00:00")
            Metadata = {
                "Timezone": DateTimeObj.tzname(),
                "DayLabel": item["day"],
                "DailySummaryTimestamp": DateTimeObj.timestamp(),
                "Score": -1,  # Oura does not provide a score for daily SPO2
                "ScoreContributors": {},
            }

            Descriptor = {
                "Spo2": item["spo2_percentage"]["average"],
                "BreathingDisturbance": item["breathing_disturbance_index"]
            }

            Recording = dict()
            Recording["SamplingRate"] = -1
            Recording["ChannelNames"] = []
            Recording["Data"] = np.zeros(0)
            Recording["Missing"] = np.zeros(0)
            Recording["StartTime"] = DateTimeObj.timestamp()
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            Recording["Descriptor"] = Descriptor
            Recording["Metadata"] = Metadata
            Recordings.append(Recording)

        return Recordings

    def getDailyCardiovascularAge(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        result = self.query("v2/usercollection/daily_cardiovascular_age", params)
    
        Recordings = []
        for item in result["data"]:
            DateTimeObj = datetime.datetime.fromisoformat(item["day"] + "T00:00:00+00:00")
            Metadata = {
                "Timezone": DateTimeObj.tzname(),
                "DayLabel": item["day"],
                "DailySummaryTimestamp": DateTimeObj.timestamp(),
                "Score": -1,  # Oura does not provide a score for daily cardiovascular age
                "ScoreContributors": {},
            }

            Descriptor = {
                "VascularAge": item["vascular_age"],
            }

            Recording = dict()
            Recording["SamplingRate"] = -1
            Recording["ChannelNames"] = []
            Recording["Data"] = np.zeros(0)
            Recording["Missing"] = np.zeros(0)
            Recording["StartTime"] = DateTimeObj.timestamp()
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            Recording["Descriptor"] = Descriptor
            Recording["Metadata"] = Metadata
            Recordings.append(Recording)

        return Recordings

    def getDailyStress(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        result = self.query("v2/usercollection/daily_stress", params)

        Recordings = []
        for item in result["data"]:
            DateTimeObj = datetime.datetime.fromisoformat(item["day"] + "T00:00:00+00:00")
            Metadata = {
                "Timezone": DateTimeObj.tzname(),
                "DayLabel": item["day"],
                "DailySummaryTimestamp": DateTimeObj.timestamp(),
                "Score": -1,  # Oura does not provide a score for daily cardiovascular age
                "ScoreContributors": {},
            }

            Descriptor = {
                "StressHigh": item["stress_high"],
                "RecoveryHigh": item["recovery_high"],
                "Summary": item["day_summary"],
            }

            Recording = dict()
            Recording["SamplingRate"] = -1
            Recording["ChannelNames"] = []
            Recording["Data"] = np.zeros(0)
            Recording["Missing"] = np.zeros(0)
            Recording["StartTime"] = DateTimeObj.timestamp()
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            Recording["Descriptor"] = Descriptor
            Recording["Metadata"] = Metadata
            Recordings.append(Recording)

        return Recordings

    def getUserCustomTags(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        # Not getting this data from testing user. Currently not implemented
        return self.query("v2/usercollection/enhanced_tag", params)

    def getRestModePeriods(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        # Not getting this data from testing user. Currently not implemented
        return self.query("v2/usercollection/rest_mode_period", params)

    def getHeartRate(self, start_date, end_date):
        params = {
            "start_datetime": start_date + "T00:00:00+00:00",
            "end_datetime": end_date + "T23:59:59+00:00"
        }
        result = self.query("v2/usercollection/heartrate", params)

        DateTimeObj = datetime.datetime.fromisoformat(start_date + "T00:00:00+00:00")
        Metadata = {
            "Timezone": DateTimeObj.tzname(),
            "DayLabel": start_date,
            "DailySummaryTimestamp": DateTimeObj.timestamp(),
            "Score": -1,
            "ScoreContributors": {},
        }

        KnownStates = ["awake", "rest", "workout"]
        for item in result["data"]:
            if not item["source"] in KnownStates:
                KnownStates.append(item["source"])
        
        Descriptor = {
            "StateLabels": KnownStates
        }

        if len(result["data"]) == 0:
            return []

        Recording = dict()
        Recording["SamplingRate"] = -1
        Recording["ChannelNames"] = ["Heart Rate", "Heart Rate State"]
        Recording["Time"] = [datetime.datetime.fromisoformat(result["data"][i]["timestamp"]).timestamp() for i in range(len(result["data"]))]
        Recording["Data"] = np.zeros((len(result["data"]), 2))
        Recording["Missing"] = np.zeros((len(result["data"]), 2))
        for i in range(len(result["data"])):
            Recording["Data"][i,0] = result["data"][i]["bpm"]
            Recording["Data"][i,1] = KnownStates.index(result["data"][i]["source"])
        Recording["StartTime"] = Recording["Time"][0]
        Recording["Duration"] = Recording["Time"][-1] - Recording["Time"][0]
        Recording["Descriptor"] = Descriptor
        Recording["Metadata"] = Metadata
        
        return [Recording]

    def getSleep(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        result = self.query("v2/usercollection/sleep", params)

        Recordings = []
        for item in result["data"]:
            DateTimeObj = datetime.datetime.fromisoformat(item["heart_rate"]["timestamp"])
            Metadata = {
                "Timezone": DateTimeObj.tzname(),
                "DayLabel": item["day"],
                "DailySummaryTimestamp": DateTimeObj.timestamp(),
                "Score": -1,
                "ScoreContributors": {},
            }

            Descriptor = {
                "AverageBreath": item["average_breath"],
                "AverageHeartRate": item["average_heart_rate"],
                "AverageHRV": item["average_hrv"],
                "AwakeTime": item["awake_time"],
                "TimeInBed": item["time_in_bed"],
                "TotalSleepDuration": item["total_sleep_duration"],
                "DeepSleepDuration": item["deep_sleep_duration"],
                "LightSleepDuration": item["light_sleep_duration"],
                "RemSleepDuration": item["rem_sleep_duration"],
                "RestlessPeriods": item["restless_periods"],
                "Efficiency": item["efficiency"],
                "Latency": item["latency"],
                "BedtimeStart": datetime.datetime.fromisoformat(item["bedtime_start"]).timestamp(),
                "BedtimeEnd": datetime.datetime.fromisoformat(item["bedtime_end"]).timestamp(),
            }

            item["movement_30_sec"] = np.array([int(i) for i in item["movement_30_sec"]])

            Recording = dict()
            Recording["SamplingRate"] = 1 / 300
            Recording["ChannelNames"] = ["Heart Rate", "Heart Rate Variability", "Sleep Phase", "Average Movement"]
            Recording["Data"] = np.zeros((len(item["heart_rate"]["items"]), 4))
            for i in range(len(item["heart_rate"]["items"])):
                Recording["Data"][i, 0] = item["heart_rate"]["items"][i] if item["heart_rate"]["items"][i] else -1
                Recording["Data"][i, 1] = item["hrv"]["items"][i] if item["hrv"]["items"][i] else -1
                Recording["Data"][i, 2] = int(item["sleep_phase_5_min"][i]) if i < len(item["sleep_phase_5_min"])-1 else -1
                Recording["Data"][i, 3] = np.mean(item["movement_30_sec"][i*10:i*10+10]) if i*10+10 < len(item["movement_30_sec"]) else np.mean(item["movement_30_sec"][i*10:])

            Recording["Missing"] = np.zeros(Recording["Data"].shape)
            for i in range(Recording["Data"].shape[0]):
                if Recording["Data"][i, 0] < 0:
                    Recording["Missing"][i, 0] = 1
                if Recording["Data"][i, 1] < 0:
                    Recording["Missing"][i, 1] = 1

            Recording["StartTime"] = DateTimeObj.timestamp()
            Recording["Duration"] = Recording["Data"].shape[0] / Recording["SamplingRate"]
            Recording["Descriptor"] = Descriptor
            Recording["Metadata"] = Metadata
            Recordings.append(Recording)
        
        return Recordings

    def getSleepRecommendation(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        # Not getting this data from testing user. Currently not implemented
        return self.query("v2/usercollection/sleep_time", params)

    def getVO2Max(self, start_date, end_date):
        params = {
            "start_date": start_date,
            "end_date": end_date
        }
        # Not getting this data from testing user. Currently not implemented
        return self.query("v2/usercollection/vO2_max", params)

def loadOuraRingData(Participant):
    Data = {}
    source = models.SourceFile.find(owner=Participant, type="OuraRingAPISource")
    if source:
        Data = Database.loadSourceFile(source.pointer, source.hashed)
    return Data

def saveOuraRingData(Participant, data):
    if not models.SourceFile.include(type="OuraRingAPISource", owner=Participant):
        source = models.SourceFile(name="OuraRingAPISource", type="OuraRingAPISource", owner=Participant)
        source.save()
        source.pointer = DATABASE_PATH + "recordings" + os.path.sep + Participant.uid + os.path.sep + source.uid + ".bdat"
    else:
        source = models.SourceFile.find(owner=Participant, type="OuraRingAPISource")

    source.hashed = Database.saveSourceFile(data, source.pointer)
    source.save()

def OuraRingDate(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

def OuraRingTime(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M")

def deleteOuraRingData(Participant):
    source = models.SourceFile.find(owner=Participant, type="OuraRingAPISource")
    if source:
        source.delete()

def refreshOuraRingData(device):
    Participant = device.owner
    Data = loadOuraRingData(Participant)

    requester = OuraRingAPI(device.auth["token"], device.auth["refresh_token"])
    try:
        Data["DailyActivity"] = []
        Data["DailyReadiness"] = []
        Data["DailyCardiovascularAge"] = []
        Data["DailySpo2"] = []
        Data["DailyStress"] = []
        Data["HeartRate"] = []
        Data["Sleep"] = []

        for date in device.date_periods:
            Data["DailyActivity"].extend(requester.getDailyActivity(OuraRingDate(date[0]), OuraRingDate(date[1])))
            Data["DailyReadiness"].extend(requester.getDailyReadiness(OuraRingDate(date[0]), OuraRingDate(date[1])))
            Data["DailyCardiovascularAge"].extend(requester.getDailyCardiovascularAge(OuraRingDate(date[0]), OuraRingDate(date[1])))
            Data["DailySpo2"].extend(requester.getDailySpo2(OuraRingDate(date[0]), OuraRingDate(date[1])))
            Data["DailyStress"].extend(requester.getDailyStress(OuraRingDate(date[0]), OuraRingDate(date[1])))
            Data["HeartRate"].extend(requester.getHeartRate(OuraRingDate(date[0]), OuraRingDate(date[1])))
            Data["Sleep"].extend(requester.getSleep(OuraRingDate(date[0]), OuraRingDate(date[1])))
    except Exception as e:
        print(e)
        if requester.refresh_token != device.auth["refresh_token"]:
            device.auth["refresh_token"] = requester.refresh_token
            device.save()
        raise e
    
    if requester.refresh_token != device.auth["refresh_token"]:
        device.auth["refresh_token"] = requester.refresh_token
        device.save()
    saveOuraRingData(Participant, Data)
