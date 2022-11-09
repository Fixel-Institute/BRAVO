import os, sys, pathlib

RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())
sys.path.append(os.environ.get("PYTHON_UTILITY"))

from datetime import datetime, date, timedelta
import pickle, joblib
import dateutil, pytz
import numpy as np
import pandas as pd
from cryptography.fernet import Fernet
import hashlib

from Backend import models
from modules import Database
from modules.Percept import Therapy, BrainSenseSurvey, BrainSenseStream, IndefiniteStream, BrainSenseEvent, ChronicBrainSense
from decoder import Percept

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

def retrievePatientInformation(PatientInformation, Institute, lookupTable=None, encoder=None):
    if not encoder:
        encoder = Fernet(key)
        
    FirstName = encoder.encrypt(PatientInformation["PatientFirstName"].encode('utf_8')).decode("utf-8")
    LastName = encoder.encrypt(PatientInformation["PatientLastName"].encode('utf_8')).decode("utf-8")
    Diagnosis = PatientInformation["Diagnosis"].replace("DiagnosisTypeDef.","")
    MRN = encoder.encrypt(PatientInformation["PatientId"].encode('utf_8')).decode("utf-8")

    hashfield = hashlib.sha256((PatientInformation["PatientFirstName"] + " " + PatientInformation["PatientLastName"]).encode("utf-8")).hexdigest()

    try:
        PatientDateOfBirth = datetime.fromisoformat(PatientInformation["PatientDateOfBirth"][:-1]+"+00:00")
    except:
        PatientDateOfBirth = datetime.fromtimestamp(0)

    newPatient = False
    try:
        patient = models.Patient.objects.get(patient_identifier_hashfield=hashfield, birth_date=PatientDateOfBirth, diagnosis=Diagnosis, institute=Institute)
    except:
        patient = models.Patient(first_name=FirstName, last_name=LastName, patient_identifier_hashfield=hashfield, birth_date=PatientDateOfBirth, diagnosis=Diagnosis, medical_record_number=MRN, institute=Institute)
        patient.save()
        newPatient = True

    return patient, newPatient

def processPerceptJSON(user, filename, rawBytes, device_deidentified_id="", lookupTable=None, process=True):
    secureEncoder = Fernet(key)
    with open(DATABASE_PATH + "cache" + os.path.sep + filename, "wb+") as file:
        file.write(secureEncoder.encrypt(rawBytes))

    try:
        JSON = Percept.decodeEncryptedJSON(DATABASE_PATH + "cache" + os.path.sep + filename, key)
    except:
        return "JSON Format Error: " + filename, None, None

    if not process:
        os.remove(DATABASE_PATH + "cache" + os.path.sep + filename)
        return "Success", None, JSON

    if JSON["DeviceInformation"]["Final"]["NeurostimulatorSerialNumber"] != "":
        DeviceSerialNumber = secureEncoder.encrypt(JSON["DeviceInformation"]["Final"]["NeurostimulatorSerialNumber"].encode("utf-8")).decode("utf-8")
    else:
        DeviceSerialNumber = "Unknown"
    deviceHashfield = hashlib.sha256(JSON["DeviceInformation"]["Final"]["NeurostimulatorSerialNumber"].encode("utf-8")).hexdigest()

    try:
        Data = Percept.extractPerceptJSON(JSON)
    except:
        return "Decoding Error: " + filename, None, None

    SessionDate = datetime.fromtimestamp(Percept.estimateSessionDateTime(JSON),tz=pytz.utc)
    if user.is_clinician or user.is_admin:
        deviceID = models.PerceptDevice.objects.filter(device_identifier_hashfield=deviceHashfield, authority_level="Clinic", authority_user=user.institute).first()
    elif lookupTable:
        deviceID = models.PerceptDevice.objects.filter(device_identifier_hashfield=deviceHashfield, authority_level="Research", authority_user=user.email).first()
    else:
        deviceID = models.PerceptDevice.objects.filter(deidentified_id=device_deidentified_id, authority_level="Research", authority_user=user.email).first()
        if deviceID == None:
            return "Device ID Error: " + filename, None, None

    newPatient = None
    if deviceID == None:
        PatientInformation = JSON["PatientInformation"]["Final"]
        
        
        patient, isNewPatient = retrievePatientInformation(PatientInformation, user.institute, encoder=secureEncoder)
        if isNewPatient:
            newPatient = patient
            patient.institute = user.institute
            patient.save()

        DeviceInformation = JSON["DeviceInformation"]["Final"]
        DeviceType = DeviceInformation["Neurostimulator"]
        NeurostimulatorLocation = DeviceInformation["NeurostimulatorLocation"].replace("InsLocation.","")
        ImplantDate = datetime.fromisoformat(DeviceInformation["ImplantDate"][:-1]+"+00:00")
        LeadConfigurations = list()

        LeadInformation = JSON["LeadConfiguration"]["Final"]
        for lead in LeadInformation:
            LeadConfiguration = dict()
            LeadConfiguration["TargetLocation"] = lead["Hemisphere"].replace("HemisphereLocationDef.","") + " "
            if lead["LeadLocation"] == "LeadLocationDef.Vim":
                LeadConfiguration["TargetLocation"] += "VIM"
            elif lead["LeadLocation"] == "LeadLocationDef.Stn":
                LeadConfiguration["TargetLocation"] += "STN"
            elif lead["LeadLocation"] == "LeadLocationDef.Gpi":
                LeadConfiguration["TargetLocation"] += "GPi"
            else:
                LeadConfiguration["TargetLocation"] += lead["LeadLocation"].replace("LeadLocationDef.","")

            if lead["ElectrodeNumber"] == "InsPort.ZERO_THREE":
                LeadConfiguration["ElectrodeNumber"] = "E00-E03"
            elif lead["ElectrodeNumber"] == "InsPort.ZERO_SEVEN":
                LeadConfiguration["ElectrodeNumber"] = "E00-E07"
            elif lead["ElectrodeNumber"] == "InsPort.EIGHT_ELEVEN":
                LeadConfiguration["ElectrodeNumber"] = "E08-E11"
            elif lead["ElectrodeNumber"] == "InsPort.EIGHT_FIFTEEN":
                LeadConfiguration["ElectrodeNumber"] = "E08-E15"
            if lead["Model"] == "LeadModelDef.LEAD_B33015":
                LeadConfiguration["ElectrodeType"] = "SenSight B33015"
            elif lead["Model"] == "LeadModelDef.LEAD_B33005":
                LeadConfiguration["ElectrodeType"] = "SenSight B33005"
            elif lead["Model"] == "LeadModelDef.LEAD_3387":
                LeadConfiguration["ElectrodeType"] = "Medtronic 3387"
            elif lead["Model"] == "LeadModelDef.LEAD_3389":
                LeadConfiguration["ElectrodeType"] = "Medtronic 3389"
            elif lead["Model"] == "LeadModelDef.LEAD_OTHER":
                LeadConfiguration["ElectrodeType"] = "Unknown Lead"
            else:
                LeadConfiguration["ElectrodeType"] = lead["Model"]

            LeadConfigurations.append(LeadConfiguration)

        if user.is_clinician or user.is_admin:
            deviceID = models.PerceptDevice(patient_deidentified_id=patient.deidentified_id, authority_level="Clinic", authority_user=user.institute, serial_number=DeviceSerialNumber, device_type=DeviceType, implant_date=ImplantDate, device_location=NeurostimulatorLocation, device_lead_configurations=LeadConfigurations, device_last_seen=datetime.fromtimestamp(0, tz=pytz.utc))
        else:
            deviceID = models.PerceptDevice(patient_deidentified_id=patient.deidentified_id, authority_level="Research", authority_user=user.email, serial_number=DeviceSerialNumber, device_type=DeviceType, implant_date=ImplantDate, device_location=NeurostimulatorLocation, device_lead_configurations=LeadConfigurations, device_last_seen=datetime.fromtimestamp(0, tz=pytz.utc))

        SessionDate = datetime.fromtimestamp(Percept.estimateSessionDateTime(JSON),tz=pytz.utc)
        if "EstimatedBatteryLifeMonths" in JSON["BatteryInformation"].keys():
            deviceID.device_eol_date = SessionDate + timedelta(days=30*JSON["BatteryInformation"]["EstimatedBatteryLifeMonths"])
        else:
            deviceID.device_eol_date = datetime.fromtimestamp(0, tz=pytz.utc)
        deviceID.device_identifier_hashfield=deviceHashfield
        deviceID.save()

        patient.addDevice(str(deviceID.deidentified_id))
    else:
        patient = models.Patient.objects.filter(deidentified_id=deviceID.patient_deidentified_id).first()

    DeviceInformation = JSON["DeviceInformation"]["Final"]
    NeurostimulatorLocation = DeviceInformation["NeurostimulatorLocation"].replace("InsLocation.","")
    ImplantDate = datetime.fromisoformat(DeviceInformation["ImplantDate"][:-1]+"+00:00")
    deviceID.implant_date = ImplantDate
    deviceID.device_location = NeurostimulatorLocation

    if SessionDate >= deviceID.device_last_seen:
        deviceID.device_last_seen = SessionDate
        if "EstimatedBatteryLifeMonths" in JSON["BatteryInformation"].keys():
            deviceID.device_eol_date = SessionDate + timedelta(days=30*JSON["BatteryInformation"]["EstimatedBatteryLifeMonths"])
        else:
            deviceID.device_eol_date = datetime.fromtimestamp(0, tz=pytz.utc)

        LeadConfigurations = list()
        LeadInformation = JSON["LeadConfiguration"]["Final"]
        for lead in LeadInformation:
            LeadConfiguration = dict()
            LeadConfiguration["TargetLocation"] = lead["Hemisphere"].replace("HemisphereLocationDef.","") + " "
            if lead["LeadLocation"] == "LeadLocationDef.Vim":
                LeadConfiguration["TargetLocation"] += "VIM"
            elif lead["LeadLocation"] == "LeadLocationDef.Stn":
                LeadConfiguration["TargetLocation"] += "STN"
            elif lead["LeadLocation"] == "LeadLocationDef.Gpi":
                LeadConfiguration["TargetLocation"] += "GPi"
            else:
                LeadConfiguration["TargetLocation"] += lead["LeadLocation"].replace("LeadLocationDef.","")

            if lead["ElectrodeNumber"] == "InsPort.ZERO_THREE":
                LeadConfiguration["ElectrodeNumber"] = "E00-E03"
            elif lead["ElectrodeNumber"] == "InsPort.ZERO_SEVEN":
                LeadConfiguration["ElectrodeNumber"] = "E00-E07"
            elif lead["ElectrodeNumber"] == "InsPort.EIGHT_ELEVEN":
                LeadConfiguration["ElectrodeNumber"] = "E08-E11"
            elif lead["ElectrodeNumber"] == "InsPort.EIGHT_FIFTEEN":
                LeadConfiguration["ElectrodeNumber"] = "E08-E15"
            if lead["Model"] == "LeadModelDef.LEAD_B33015":
                LeadConfiguration["ElectrodeType"] = "SenSight B33015"
            elif lead["Model"] == "LeadModelDef.LEAD_B33005":
                LeadConfiguration["ElectrodeType"] = "SenSight B33005"
            elif lead["Model"] == "LeadModelDef.LEAD_3387":
                LeadConfiguration["ElectrodeType"] = "Medtronic 3387"
            elif lead["Model"] == "LeadModelDef.LEAD_3389":
                LeadConfiguration["ElectrodeType"] = "Medtronic 3389"
            else:
                LeadConfiguration["ElectrodeType"] = lead["Model"]

            LeadConfigurations.append(LeadConfiguration)
        deviceID.device_lead_configurations = LeadConfigurations

    deviceID.save()
    session = models.PerceptSession(device_deidentified_id=deviceID.deidentified_id, session_source_filename=filename)
    session.session_file_path = DATABASE_PATH + "sessions" + os.path.sep + str(session.device_deidentified_id)+"_"+str(session.deidentified_id)+".json"
    sessionUUID = str(session.deidentified_id)

    # Process Therapy History
    NewDataFound = False
    if Therapy.saveTherapySettings(deviceID.deidentified_id, Data["StimulationGroups"], SessionDate, "Post-visit Therapy", sessionUUID):
        NewDataFound = True

    if Therapy.saveTherapySettings(deviceID.deidentified_id, Data["PreviousGroups"], SessionDate, "Pre-visit Therapy", sessionUUID):
        NewDataFound = True

    if "TherapyHistory" in Data.keys():
        for i in range(len(Data["TherapyHistory"])):
            SessionDate = datetime.fromtimestamp(Percept.getTimestamp(Data["TherapyHistory"][i]["DateTime"]),tz=pytz.utc)
            if Therapy.saveTherapySettings(deviceID.deidentified_id, Data["TherapyHistory"][i]["Therapy"], SessionDate, "Past Therapy", sessionUUID):
                NewDataFound = True

    if "TherapyChangeHistory" in Data.keys():
        logToSave = list()
        for therapyChange in Data["TherapyChangeHistory"]:
            TherapyObject = models.TherapyChangeLog.objects.filter(device_deidentified_id=deviceID.deidentified_id, date_of_change=therapyChange["DateTime"].astimezone(pytz.utc)).first()
            if TherapyObject == None:
                logToSave.append(models.TherapyChangeLog(device_deidentified_id=deviceID.deidentified_id, date_of_change=therapyChange["DateTime"].astimezone(pytz.utc),
                                    previous_group=therapyChange["OldGroupId"], new_group=therapyChange["NewGroupId"], source_file=sessionUUID))
                NewDataFound = True
        if len(logToSave) > 0:
            models.TherapyChangeLog.objects.bulk_create(logToSave, ignore_conflicts=True)

    # Process BrainSense Survey
    if "MontagesTD" in Data.keys():
        if BrainSenseSurvey.saveBrainSenseSurvey(deviceID.deidentified_id, Data["MontagesTD"], sessionUUID):
            NewDataFound = True
    if "BaselineTD" in Data.keys():
        if BrainSenseSurvey.saveBrainSenseSurvey(deviceID.deidentified_id, Data["BaselineTD"], sessionUUID):
            NewDataFound = True

    # Process Montage Streams
    if "IndefiniteStream" in Data.keys():
        if IndefiniteStream.saveMontageStreams(deviceID.deidentified_id, Data["IndefiniteStream"], sessionUUID):
            NewDataFound = True

    # Process Realtime Streams
    if "StreamingTD" in Data.keys() and "StreamingPower" in Data.keys():
        if BrainSenseStream.saveRealtimeStreams(deviceID.deidentified_id, Data["StreamingTD"], Data["StreamingPower"], sessionUUID):
            NewDataFound = True

    # Stiore Chronic LFPs
    if "LFPTrends" in Data.keys():
        if ChronicBrainSense.saveChronicLFP(deviceID.deidentified_id, Data["LFPTrends"], sessionUUID):
            NewDataFound = True

    if "LFPEvents" in Data.keys():
        if BrainSenseEvent.saveBrainSenseEvents(deviceID.deidentified_id, JSON["DiagnosticData"]["LfpFrequencySnapshotEvents"], sessionUUID):
            NewDataFound = True

    if NewDataFound:
        os.rename(DATABASE_PATH + "cache" + os.path.sep + filename, session.session_file_path)
        session.save()
    else:
        os.remove(DATABASE_PATH + "cache" + os.path.sep + filename)

    JSON["PatientID"] = str(patient.deidentified_id)
    return "Success", newPatient, JSON

def processSessionFile(JSON):
    SessionDate = datetime.fromtimestamp(Percept.estimateSessionDateTime(JSON),tz=pytz.utc).timestamp()

    Overview = {}
    Overview["Overall"] = Percept.extractPatientInformation(JSON, {})
    Overview["Therapy"] = Percept.extractTherapySettings(JSON, {})
    Overview["Overall"]["SessionDate"] = datetime.fromtimestamp(SessionDate).strftime("%Y/%m/%d")

    lastMeasuredTimestamp = 0
    if "TherapyHistory" in Overview["Therapy"].keys():
        for i in range(len(Overview["Therapy"]["TherapyHistory"])):
            HistoryDate = datetime.fromisoformat(Overview["Therapy"]["TherapyHistory"][i]["DateTime"][:-1]+"+00:00").timestamp()
            if SessionDate-HistoryDate > 24*3600:
                lastMeasuredTimestamp = HistoryDate
                break

    if lastMeasuredTimestamp == 0:
        lastMeasuredTimestamp = datetime.fromisoformat(Overview["Overall"]["DeviceInformation"]["ImplantDate"][:-1]+"+00:00").timestamp()

    if "TherapyChangeHistory" in Overview["Therapy"].keys():
        if SessionDate > Overview["Therapy"]["TherapyChangeHistory"][-1]["DateTime"].timestamp():
            Overview["Therapy"]["TherapyChangeHistory"].append({"DateTime": datetime.fromtimestamp(SessionDate), "OldGroupId": Overview["Therapy"]["TherapyChangeHistory"][-1]["NewGroupId"], "NewGroupId": Overview["Therapy"]["TherapyChangeHistory"][-1]["NewGroupId"]})
    else:
        Overview["Therapy"]["TherapyChangeHistory"] = [{"DateTime": datetime.fromtimestamp(SessionDate), "OldGroupId": "GroupIdDef.GROUP_A", "NewGroupId": "GroupIdDef.GROUP_A"}]

    TherapyDutyPercent = dict()
    for i in range(len(Overview["Therapy"]["TherapyChangeHistory"])):
        if lastMeasuredTimestamp < SessionDate:
            if i > 0:
                if Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"] == Overview["Therapy"]["TherapyChangeHistory"][i-1]["NewGroupId"]:
                    Overview["Therapy"]["TherapyChangeHistory"][i]["DateTime"] = Overview["Therapy"]["TherapyChangeHistory"][i]["DateTime"].timestamp()
                    DateOfChange = Overview["Therapy"]["TherapyChangeHistory"][i]["DateTime"]
                    if DateOfChange > lastMeasuredTimestamp:
                        if not Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"] in TherapyDutyPercent.keys():
                            TherapyDutyPercent[Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"]] = 0
                        if DateOfChange > SessionDate:
                            TherapyDutyPercent[Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"]] += (SessionDate-lastMeasuredTimestamp)
                            lastMeasuredTimestamp = SessionDate
                        else:
                            TherapyDutyPercent[Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"]] += (DateOfChange-lastMeasuredTimestamp)
                            lastMeasuredTimestamp = DateOfChange
                else:
                    Overview["Therapy"]["TherapyChangeHistory"][i]["DateTime"] = Overview["Therapy"]["TherapyChangeHistory"][i]["DateTime"].timestamp()
                    DateOfChange = Overview["Therapy"]["TherapyChangeHistory"][i]["DateTime"]
                    if DateOfChange > lastMeasuredTimestamp:
                        if not Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"] in TherapyDutyPercent.keys():
                            TherapyDutyPercent[Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"]] = 0
                        if DateOfChange > SessionDate:
                            TherapyDutyPercent[Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"]] += (SessionDate-lastMeasuredTimestamp)
                            lastMeasuredTimestamp = SessionDate
                        else:
                            TherapyDutyPercent[Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"]] += (DateOfChange-lastMeasuredTimestamp)
                            lastMeasuredTimestamp = DateOfChange
            else:
                Overview["Therapy"]["TherapyChangeHistory"][i]["DateTime"] = Overview["Therapy"]["TherapyChangeHistory"][i]["DateTime"].timestamp()
                DateOfChange = Overview["Therapy"]["TherapyChangeHistory"][i]["DateTime"]
                if DateOfChange > lastMeasuredTimestamp:
                    if not Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"] in TherapyDutyPercent.keys():
                        TherapyDutyPercent[Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"]] = 0
                    if DateOfChange > SessionDate:
                        TherapyDutyPercent[Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"]] += (SessionDate-lastMeasuredTimestamp)
                        lastMeasuredTimestamp = SessionDate
                    else:
                        TherapyDutyPercent[Overview["Therapy"]["TherapyChangeHistory"][i]["OldGroupId"]] += (DateOfChange-lastMeasuredTimestamp)
                        lastMeasuredTimestamp = DateOfChange

    totalHours = np.sum([TherapyDutyPercent[key] for key in TherapyDutyPercent.keys()])
    for i in range(len(Overview["Therapy"]["PreviousGroups"])):
        if Overview["Therapy"]["PreviousGroups"][i]["GroupId"] in TherapyDutyPercent.keys():
            DutyPercent = TherapyDutyPercent[Overview["Therapy"]["PreviousGroups"][i]["GroupId"]] / totalHours
            Overview["Therapy"]["PreviousGroups"][i]["DutyPercent"] = f"({DutyPercent*100:.2f}%)"
        else:
            Overview["Therapy"]["PreviousGroups"][i]["DutyPercent"] = "(0%)"

    if "Impedance" in Overview["Overall"].keys():
        del(Overview["Overall"]["Impedance"])

    return Overview

def viewSession(user, patient_id, session_id, authority):
    availableDevices = Database.getPerceptDevices(user, patient_id, authority)
    for device in availableDevices:
        if models.PerceptSession.objects.filter(device_deidentified_id=device.deidentified_id, deidentified_id=str(session_id)).exists():
            session = models.PerceptSession.objects.filter(deidentified_id=session_id).first()
            JSON = Percept.decodeJSON(session.session_file_path)
            Overview = processSessionFile(JSON)

            if not user.is_clinician:
                Overview["Overall"]["PatientInformation"]["PatientFirstName"] = "Deidentified FirstName"
                Overview["Overall"]["PatientInformation"]["PatientLastName"] = "Deidentified LastName"
                Overview["Overall"]["PatientInformation"]["Diagnosis"] = "Unknown"
                Overview["Overall"]["PatientInformation"]["PatientId"] = "Unknown"
                Overview["Overall"]["PatientInformation"]["PatientDateOfBirth"] = "Unknown"
                Overview["Overall"]["DeviceInformation"]["NeurostimulatorSerialNumber"] = "Unknown"
            return Overview
    return {}

def queryAvailableSessionFiles(user, patient_id, authority):
    availableDevices = Database.getPerceptDevices(user, patient_id, authority)

    sessions = list()
    for device in availableDevices:
        availableSessions = models.PerceptSession.objects.filter(device_deidentified_id=device.deidentified_id).all()
        for session in availableSessions:
            sessionInfo = dict()
            if not device.device_name == "":
                sessionInfo["DeviceName"] = device.device_name
            else:
                sessionInfo["DeviceName"] = device.serial_number
            sessionInfo["SessionFilename"] = session.session_source_filename
            sessionInfo["SessionID"] = session.deidentified_id

            sessionInfo["AvailableRecording"] = ""
            sessionInfo["AvailableRecording"] += "Realtime Streaming Data: " + str(models.BrainSenseRecording.objects.filter(source_file=session.deidentified_id, recording_type="BrainSenseStream").count()) + "<br>"
            sessionInfo["AvailableRecording"] += "Indefinite Streaming Data: " + str(models.BrainSenseRecording.objects.filter(source_file=session.deidentified_id, recording_type="IndefiniteStream").count()) + "<br>"
            sessionInfo["AvailableRecording"] += "BrainSense Survey Count: " + str(models.BrainSenseRecording.objects.filter(source_file=session.deidentified_id, recording_type="BrainSenseSurvey").count()) + "<br>"
            sessionInfo["AvailableRecording"] += "Therapy History Info: " + str(models.TherapyHistory.objects.filter(source_file=session.deidentified_id).count()) + "<br>"
            sessionInfo["AvailableRecording"] += "# of Therapy History Changed: " + str(models.TherapyChangeLog.objects.filter(source_file=session.deidentified_id).count()) + "<br>"
            sessionInfo["AvailableRecording"] += "# of Chronic Recording Info: " + str(models.ChronicSensingLFP.objects.filter(source_file=session.deidentified_id).count()) + "<br>"
            sessions.append(sessionInfo)
    return sessions

def deleteDevice(device_id):
    recordings = models.BrainSenseRecording.objects.filter(device_deidentified_id=device_id).all()
    for recording in recordings:
        try:
            os.remove(DATABASE_PATH + "recordings" + os.path.sep + recording.recording_datapointer)
        except:
            pass
    recordings.delete()

    Sessions = models.PerceptSession.objects.filter(device_deidentified_id=device_id).all()
    for session in Sessions:
        models.TherapyHistory.objects.filter(source_file=str(session.deidentified_id)).delete()
        models.TherapyChangeLog.objects.filter(source_file=str(session.deidentified_id)).delete()
        models.ChronicSensingLFP.objects.filter(source_file=str(session.deidentified_id)).delete()
        try:
            os.remove(session.session_file_path)
        except:
            pass
    Sessions.delete()

def deleteSessions(user, patient_id, session_ids, authority):
    availableDevices = Database.getPerceptDevices(user, patient_id, authority)

    for i in range(len(session_ids)):
        for device in availableDevices:
            if models.PerceptSession.objects.filter(device_deidentified_id=device.deidentified_id, deidentified_id=str(session_ids[i])).exists():
                models.TherapyHistory.objects.filter(source_file=str(session_ids[i])).delete()
                models.TherapyChangeLog.objects.filter(source_file=str(session_ids[i])).delete()
                models.ChronicSensingLFP.objects.filter(source_file=str(session_ids[i])).delete()
                recordings = models.BrainSenseRecording.objects.filter(source_file=str(session_ids[i])).all()
                for recording in recordings:
                    try:
                        os.remove(DATABASE_PATH + "recordings" + os.path.sep + recording.recording_datapointer)
                    except:
                        pass
                recordings.delete()
                session = models.PerceptSession.objects.filter(deidentified_id=session_ids[i]).first()
                try:
                    os.remove(session.session_file_path)
                except:
                    pass
                session.delete()
