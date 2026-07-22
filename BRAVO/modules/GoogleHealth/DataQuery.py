import os, sys
import datetime 
import json
import traceback
import requests
import numpy as np

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from modules import Database
from Server import models

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

GoogleHealth_CLIENT_ID = os.environ["GoogleHealth_CLIENT_ID"]
GoogleHealth_CLIENT_SECRET = os.environ["GoogleHealth_CLIENT_SECRET"]
GoogleHealth_CLIENT_REDIRECT_URI = os.environ["GoogleHealth_CLIENT_REDIRECT_URI"]

def retrieveToken(code):
    try:
        response = requests.post("https://oauth2.googleapis.com/token", headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }, data={
            "code": code,
            "client_id": GoogleHealth_CLIENT_ID,
            "client_secret": GoogleHealth_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "redirect_uri": GoogleHealth_CLIENT_REDIRECT_URI,
        })
        data = response.json()
        if "access_token" in data.keys() and "refresh_token" in data.keys():
            return data

    except Exception as e:
        print(traceback.format_exc())

    return None

def refreshToken(token):
    try:
        response = requests.post("https://oauth2.googleapis.com/token", headers={
            "Content-Type": "application/x-www-form-urlencoded"
        }, data={
            "client_id": GoogleHealth_CLIENT_ID,
            "client_secret": GoogleHealth_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": token["refresh_token"]
        })
        data = response.json()
        if "access_token" in data.keys():
            token["access_token"] = data["access_token"]
        if "refresh_token" in data.keys():
            token["refresh_token"] = data["refresh_token"]
        return token 

    except Exception as e:
        print(traceback.format_exc())

    return None

def loadGoogleHealthData(Participant):
    Data = {}
    source = models.SourceFile.find(owner=Participant, type="GoogleHealthSource")
    if source:
        Data = Database.loadSourceFile(source.pointer, source.hashed)
    return Data

def saveGoogleHealthData(Participant, data):
    if not models.SourceFile.include(type="GoogleHealthSource", owner=Participant):
        source = models.SourceFile(name="GoogleHealthSource", type="GoogleHealthSource", owner=Participant)
        source.save()
        source.pointer = DATABASE_PATH + "recordings" + os.path.sep + Participant.uid + os.path.sep + source.uid + ".bdat"
    else:
        source = models.SourceFile.find(owner=Participant, type="GoogleHealthSource")

    source.hashed = Database.saveSourceFile(data, source.pointer)
    source.save()

def deleteGoogleHealthData(Participant):
    source = models.SourceFile.find(owner=Participant, type="GoogleHealthSource")
    if source:
        source.delete()
        
def getDate(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")

def getTime(timestamp):
    return datetime.datetime.fromtimestamp(timestamp).strftime("%H:%M")

def calculateDateKey(period):
    keys = []
    for day in np.arange(period[0], period[1]+1, 3600*24):
        keys.append(getDate(day))
    return keys

def createPlaceholderRecording(date):
    DateTimeObj = datetime.datetime.fromisoformat(date)
    Metadata = {
        "QueryTime": date,
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

def getStepList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/steps",
        filter=f"steps.interval.start_time >= \"{start_time}\" AND steps.interval.start_time < \"{end_time}\""
    )
    
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)

    return all_data

def getSleepList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/sleep",
        filter=f"sleep.interval.end_time >= \"{start_time}\" AND sleep.interval.end_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)

    return all_data

def getHeartRateList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/heart-rate",
        filter=f"heart_rate.sample_time.physical_time >= \"{start_time}\" AND heart_rate.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getHeartRateVariabilityList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/heart-rate-variability",
        filter=f"heart_rate_variability.sample_time.physical_time >= \"{start_time}\" AND heart_rate_variability.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getExerciseList(service, start_time, end_time):
    print(NotImplementedError("Not Working Yet"))
    return []

    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/exercise",
        filter=f"exercise.interval.start_time >= \"{start_time}\" AND exercise.interval.start_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getWeightList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/weight",
        filter=f"weight.sample_time.physical_time >= \"{start_time}\" AND weight.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getAltitudeList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/altitude",
        filter=f"altitude.interval.start_time >= \"{start_time}\" AND altitude.interval.start_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getDistanceList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/distance",
        filter=f"distance.interval.start_time >= \"{start_time}\" AND distance.interval.start_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getBodyFatList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/body-fat",
        filter=f"body_fat.sample_time.physical_time >= \"{start_time}\" AND body_fat.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getActiveZoneMinutesList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/active-zone-minutes",
        filter=f"active_zone_minutes.interval.start_time >= \"{start_time}\" AND active_zone_minutes.interval.start_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getDailySleepTemperatureDerivationsList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/daily-sleep-temperature-derivations",
        filter=f"daily_sleep_temperature_derivations.date >= \"{start_time.split('T')[0]}\" AND daily_sleep_temperature_derivations.date < \"{end_time.split('T')[0]}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getSedentaryPeriodList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/sedentary-period",
        filter=f"sedentary_period.interval.start_time >= \"{start_time}\" AND sedentary_period.interval.start_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getRunVo2Max(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/run-vo2-max",
        filter=f"run_vo2_max.sample_time.physical_time >= \"{start_time}\" AND run_vo2_max.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getVo2Max(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/vo2-max",
        filter=f"vo2_max.sample_time.physical_time >= \"{start_time}\" AND vo2_max.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getActiveMinutesList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/active-minutes",
        filter=f"active_minutes.interval.start_time >= \"{start_time}\" AND active_minutes.interval.start_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getRespiratoryRateSleepSummaryList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/respiratory-rate-sleep-summary",
        filter=f"respiratory_rate_sleep_summary.sample_time.physical_time >= \"{start_time}\" AND respiratory_rate_sleep_summary.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getDailyRespiratoryRateList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/daily-respiratory-rate",
        filter=f"daily_respiratory_rate.date >= \"{start_time.split('T')[0]}\" AND daily_respiratory_rate.date < \"{end_time.split('T')[0]}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getSwimLengthsList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/swim-lengths-data",
        filter=f"swim_lengths_data.interval.start_time >= \"{start_time}\" AND swim_lengths_data.interval.start_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getCoreBodyTemperatureList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/core-body-temperature",
        filter=f"core_body_temperature.sample_time.physical_time >= \"{start_time}\" AND core_body_temperature.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getActiveEnergyBurnedList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/active-energy-burned",
        filter=f"active_energy_burned.interval.start_time >= \"{start_time}\" AND active_energy_burned.interval.start_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getNutritionLogList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/nutrition-log",
        filter=f"nutrition_log.interval.civil_start_time >= \"{start_time[:-1]}\" AND nutrition_log.interval.civil_start_time < \"{end_time[:-1]}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getBloodGlucoseList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/blood-glucose",
        filter=f"blood_glucose.sample_time.physical_time >= \"{start_time}\" AND blood_glucose.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getOxygenSaturationList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/oxygen-saturation",
        filter=f"oxygen_saturation.sample_time.physical_time >= \"{start_time}\" AND oxygen_saturation.sample_time.physical_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getActivityLevelList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().list(
        parent=f"users/me/dataTypes/activity-level",
        filter=f"activity_level.interval.start_time >= \"{start_time}\" AND activity_level.interval.start_time < \"{end_time}\""
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('dataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def getFloorsList(service, start_time, end_time):
    request = service.users().dataTypes().dataPoints().rollUp(
        parent=f"users/me/dataTypes/floors",
        body={
            "range": {
                "startTime": start_time,
                "endTime": end_time
            },
            "windowSize": "60s"
        }
    )
    all_data = []
    while request is not None:
        response = request.execute()
        data_points = response.get('rollupDataPoints', [])
        if not data_points:
            break
        all_data.extend(data_points)
        request = service.users().dataTypes().dataPoints().list_next(request, response)
    return all_data

def refreshGoogleHealthData(device):
    Participant = device.owner
    Data = loadGoogleHealthData(Participant)
    token = device.auth
    
    for key in Data.keys():
        Data[key] = [recording for recording in Data[key]]
    
    AcceptedDates = []
    for date in device.date_periods:
        AcceptedDates.extend(calculateDateKey(date))

    DateToQuery = []
    for date in AcceptedDates:
        QueryTimestamp = datetime.datetime.fromisoformat(date + "T00:00:00").timestamp()
        if QueryTimestamp > datetime.datetime.now().timestamp()-24*3600:
            continue
        DateToQuery.append(QueryTimestamp)
    DateToQuery = sorted(DateToQuery)
    
    creds = Credentials(
        token=token["access_token"],
        refresh_token=token["refresh_token"],
        client_id=GoogleHealth_CLIENT_ID,
        client_secret=GoogleHealth_CLIENT_SECRET,
        token_uri="https://oauth2.googleapis.com/token"
    )
    service = build('health', 'v4', credentials=creds)

    Data = {}
    for date in DateToQuery:
        for dt in ["steps", "heart-rate", "exercise", "sleep", "floors", "heart-rate-variability", "weight", "altitude", "distance", "body-fat", "active-zone-minutes", "active-energy-burned", "nutrition-log", 
                   "blood-glucose", "oxygen-saturation", "daily-sleep-temperature-derivations", "sedentary-period", "run-vo2-max", "vo2-max", "active-minutes", "respiratory-rate-sleep-summary", 
                   "daily-respiratory-rate", "swim-lengths-data", "core-body-temperature", "active-energy-burned", "nutrition-log", "blood-glucose", "oxygen-saturation"]:
            print(f"Querying {dt} for {getDate(date)}")
            if not dt in Data.keys():
                Data[dt] = []

            start_time = datetime.datetime.fromtimestamp(date).isoformat() + "Z"
            end_time = (datetime.datetime.fromtimestamp(date) + datetime.timedelta(days=1)).isoformat() + "Z"

            if dt == "steps":
                all_data = getStepList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "heart-rate":
                all_data = getHeartRateList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "exercise":
                all_data = getExerciseList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "sleep":
                all_data = getSleepList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "floors":
                all_data = getFloorsList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "heart-rate-variability":
                all_data = getHeartRateVariabilityList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "weight":
                all_data = getWeightList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "altitude":
                all_data = getAltitudeList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "distance":
                all_data = getDistanceList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "body-fat":
                all_data = getBodyFatList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "active-zone-minutes":
                all_data = getActiveZoneMinutesList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "active-energy-burned":
                all_data = getActiveEnergyBurnedList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "nutrition-log":
                all_data = getNutritionLogList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "blood-glucose":
                all_data = getBloodGlucoseList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "oxygen-saturation":
                all_data = getOxygenSaturationList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "daily-sleep-temperature-derivations":
                all_data = getDailySleepTemperatureDerivationsList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "sedentary-period":
                all_data = getSedentaryPeriodList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "run-vo2-max":
                all_data = getRunVo2Max(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "vo2-max":
                all_data = getVo2Max(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "active-minutes":
                all_data = getActiveMinutesList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "respiratory-rate-sleep-summary":
                all_data = getRespiratoryRateSleepSummaryList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "daily-respiratory-rate":
                all_data = getDailyRespiratoryRateList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "swim-lengths-data":
                all_data = getSwimLengthsList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "core-body-temperature":
                all_data = getCoreBodyTemperatureList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "active-energy-burned":
                all_data = getActiveEnergyBurnedList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "nutrition-log":
                all_data = getNutritionLogList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "blood-glucose":
                all_data = getBloodGlucoseList(service, start_time, end_time)
                Data[dt].extend(all_data)
            elif dt == "oxygen-saturation":
                all_data = getOxygenSaturationList(service, start_time, end_time)
                Data[dt].extend(all_data)

    service.close()
    saveGoogleHealthData(Participant, Data)