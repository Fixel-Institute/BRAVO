import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())

from datetime import datetime, date, timedelta
import pickle, joblib
import dateutil, pytz
import numpy as np
import pandas as pd

from Backend import models

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

def retrieveProcessingSettings(config=dict()):
    options = {
        "RealtimeStream": {
            "SpectrogramMethod": {
                "name": "Time-Frequency Analysis Algorithm",
                "description": "",
                "options": ["Welch","Spectrogram","Wavelet"],
                "value": "Spectrogram"
            },
            "PSDMethod": {
                "name": "Stimulation Epoch Power Spectrum Algorithm",
                "description": "",
                "options": ["Welch","Time-Frequency Analysis"],
                "value": "Welch"
            },
            "NormalizedPSD": {
                "name": "Normalize Stimulation Epoch Power Spectrum",
                "description": "",
                "options": ["true", "false"],
                "value": "false"
            },
        }
    }

    for key in config.keys():
        if type(config[key]) == dict:
            for subkey in config[key].keys():
                if type(config[key][subkey]) == dict and subkey in options[key].keys():
                    if config[key][subkey]["name"] == options[key][subkey]["name"] and config[key][subkey]["description"] == options[key][subkey]["description"] and config[key][subkey]["options"] == options[key][subkey]["options"]:
                        options[key][subkey]["value"] = config[key][subkey]["value"]
    return options

def extractUserInfo(user):
    userInfo = dict()
    userInfo["Name"] = user.user_name
    userInfo["Email"] = user.email
    userInfo["Institute"] = user.institute
    userInfo["Clinician"] = user.is_clinician
    userInfo["Admin"] = user.is_admin
    return userInfo

def extractInstituteInfo():
    allInstitutes = models.Institute.objects.all()
    return [{"value": institute.name, "label": institute.name} for institute in allInstitutes]

def getDirectorySize(path):
    total = 0
    if not os.path.exists(path):
        return total 
        
    with os.scandir(path) as it:
        for entry in it:
            if entry.is_file():
                total += entry.stat().st_size
            elif entry.is_dir():
                total += getDirectorySize(entry.path)
    return total

def getDatabaseInfo(user):
    if user.is_admin or user.is_clinician:
        Patients = models.Patient.objects.filter(institute=user.institute).all()
    else:
        Patients = models.Patient.objects.filter(institute=user.email).all()

    DatabaseSize = 0
    for patient in Patients:
        for device in patient.device_deidentified_id:
            DatabaseSize += getDirectorySize(DATABASE_PATH + "recordings" + os.path.sep + str(device))

    if DatabaseSize > 1024*1024*1024:
        return {"patients": len(Patients), "totalStorage": f"{DatabaseSize/1024/1024/1024:.2f} GBytes"}
    else:
        return {"patients": len(Patients), "totalStorage": f"{DatabaseSize/1024/1024:.2f} MBytes"}

def getAllResearchUsers():
    ResearchUserList = list()
    users = models.PlatformUser.objects.filter(is_clinician=0, is_admin=0).all()
    for user in users:
        ResearchUserList.append({"Username": user.email, "FirstName": user.first_name, "LastName": user.last_name, "ID": user.unique_user_id})
    return ResearchUserList

def AuthorizeResearchAccess(user, researcher_id, patient_id, permission):
    if permission:
        if not models.DeidentifiedPatientID.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id).exists():
            identified_patient = models.Patient.objects.get(deidentified_id=patient_id)
            patient = models.Patient(first_name="Deidentified", last_name=patient_id, birth_date=datetime.now(tz=pytz.utc), diagnosis="", medical_record_number="", institute=researcher_id)
            patient.save()
            models.DeidentifiedPatientID(researcher_id=researcher_id, authorized_patient_id=patient_id, deidentified_id=patient.deidentified_id).save()
    else:
        if models.DeidentifiedPatientID.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id).exists():
            DeidentifiedID = models.DeidentifiedPatientID.objects.get(researcher_id=researcher_id, authorized_patient_id=patient_id)
            if models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id).exists():
                models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id).all().delete()
            models.Patient.objects.filter(institute=researcher_id, deidentified_id=DeidentifiedID.deidentified_id).all().delete()
            models.DeidentifiedPatientID.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id).all().delete()

def AuthorizeRecordingAccess(user, researcher_id, patient_id, recording_id="", recording_type="", permission=True):
    if recording_id == "":
        if permission:
            if recording_type == "TherapyHistory":
                if not models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type=recording_type).exists():
                    models.ResearchAuthorizedAccess(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type=recording_type).save()
            elif recording_type == "ChronicLFPs":
                if not models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type=recording_type).exists():
                    models.ResearchAuthorizedAccess(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type=recording_type).save()
            else:
                DeidentifiedPatientID = models.DeidentifiedPatientID.objects.get(researcher_id=researcher_id, authorized_patient_id=patient_id)
                TimeRange = [datetime.fromtimestamp(timestamp) for timestamp in DeidentifiedPatientID.authorized_time_range[recording_type]]
                AvailableDevices = models.PerceptDevice.objects.filter(patient_deidentified_id=patient_id, authority_level="Clinic", authority_user=user.institute).all()
                for device in AvailableDevices:
                    AvailableRecordings = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id, recording_type=recording_type, recording_date__gte=TimeRange[0], recording_date__lte=TimeRange[1]).order_by("-recording_date").all()
                    for recording in AvailableRecordings:
                        if not models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type=recording_type, authorized_recording_id=recording.recording_id).exists():
                            models.ResearchAuthorizedAccess(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type=recording_type, authorized_recording_id=recording.recording_id).save()
        else:
            if models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type=recording_type).exists():
                models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type=recording_type).all().delete()
    else:
        if permission:
            if not models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_id=recording_id).exists():
                models.ResearchAuthorizedAccess(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_id=recording_id).save()
        else:
            if models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_id=recording_id).exists():
                models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_id=recording_id).all().delete()

def extractPatientTableRow(user, patient):
    key = os.environ.get('ENCRYPTION_KEY')

    info = dict()
    info["FirstName"] = patient.getPatientFirstName(key)
    info["LastName"] = patient.getPatientLastName(key)
    info["Diagnosis"] = patient.diagnosis
    info["MRN"] = patient.getPatientMRN(key)
    info["DOB"] = patient.birth_date
    info["Institute"] = patient.institute
    info["DaysSinceImplant"] = []
    lastTimestamp = datetime.fromtimestamp(0, tz=pytz.utc)

    deviceIDs = patient.device_deidentified_id
    for id in deviceIDs:
        device = models.PerceptDevice.objects.filter(deidentified_id=id).first()
        if device == None:
            patient.device_deidentified_id.remove(id)
            patient.save()
            continue

        if not (user.is_admin or user.is_clinician):
            device = models.PerceptDevice.objects.filter(deidentified_id=id).first()
            if device.device_name == "":
                device.device_name = id

        daysSinceImplant = np.round((datetime.now(tz=pytz.utc) - device.implant_date).total_seconds() / (3600*24))
        if device.device_name == "":
            deviceName = device.getDeviceSerialNumber(key)
        else:
            deviceName = device.device_name
        
        info["DaysSinceImplant"].append({"Name": deviceName, "Days": daysSinceImplant})
        if device.device_last_seen > lastTimestamp:
            lastTimestamp = device.device_last_seen

    info["LastSeen"] = lastTimestamp.timestamp()
    info["ID"] = str(patient.deidentified_id)
    return info

def extractPatientInfo(user, patientUniqueID):
    key = os.environ.get('ENCRYPTION_KEY')
    patient = models.Patient.objects.get(deidentified_id=patientUniqueID)

    info = dict()
    info["FirstName"] = patient.getPatientFirstName(key)
    info["LastName"] = patient.getPatientLastName(key)
    if user.is_clinician:
        info["Name"] = info["FirstName"] + " " + info["LastName"]
    else:
        info["Name"] = info["FirstName"] + " (" + info["LastName"] + ")"

    info["Diagnosis"] = patient.diagnosis
    info["MRN"] = patient.getPatientMRN(key)
    info["DOB"] = patient.birth_date
    info["Institute"] = patient.institute

    info["Devices"] = list()
    deviceIDs = patient.device_deidentified_id

    for id in deviceIDs:
        deviceInfo = dict()
        device = models.PerceptDevice.objects.get(deidentified_id=id)

        deviceInfo["ID"] = id
        deviceInfo["Location"] = device.device_location
        if device.device_name == "":
            if not (user.is_admin or user.is_clinician):
                deviceInfo["DeviceName"] = id
            else:
                deviceInfo["DeviceName"] = device.getDeviceSerialNumber(key)
        else:
            deviceInfo["DeviceName"] = device.device_name

        deviceInfo["DeviceType"] = device.device_type
        deviceInfo["ImplantDate"] = device.implant_date.timestamp()
        deviceInfo["LastSeenDate"] = device.device_last_seen.timestamp()
        deviceInfo["EOLDate"] = device.device_eol_date.timestamp()
        deviceInfo["Leads"] = device.device_lead_configurations
        info["Devices"].append(deviceInfo)

    return info

def getPerceptDevices(user, patientUniqueID, authority):
    availableDevices = None
    if authority["Level"] == 1:
        if user.is_clinician or user.is_admin:
            availableDevices = models.PerceptDevice.objects.filter(patient_deidentified_id=patientUniqueID, authority_level="Clinic", authority_user=user.institute).all()
        else:
            availableDevices = models.PerceptDevice.objects.filter(patient_deidentified_id=patientUniqueID, authority_level="Research", authority_user=user.email).all()
    elif authority["Level"] == 2:
        availableDevices = models.PerceptDevice.objects.filter(patient_deidentified_id=patientUniqueID).all()
        for device in availableDevices:
            device.serial_number = str(device.deidentified_id)

    return availableDevices

def extractAccess(user, patient_id):
    if not (user.is_clinician or user.is_admin):
        if models.DeidentifiedPatientID.objects.filter(researcher_id=user.unique_user_id, deidentified_id=patient_id):
            deidentified = models.DeidentifiedPatientID.objects.filter(researcher_id=user.unique_user_id, deidentified_id=patient_id).first()
            return deidentified
            #return models.Patient.objects.filter(deidentified_id=deidentified.authorized_patient_id).first()
        elif models.Patient.objects.filter(deidentified_id=patient_id).exists():
            return models.Patient.objects.filter(deidentified_id=patient_id).first()
        else:
            return 0
    else:
        return models.Patient.objects.filter(deidentified_id=patient_id).first()

def verifyAccess(user, patient_id):
    if not (user.is_clinician or user.is_admin):
        if models.DeidentifiedPatientID.objects.filter(researcher_id=user.unique_user_id, deidentified_id=patient_id):
            return 2
        elif models.Patient.objects.filter(deidentified_id=patient_id).exists():
            return 1
        else:
            return 0
    else:
        patient = models.Patient.objects.filter(deidentified_id=patient_id).first()
        if patient:
            return 1
        else:
            return 0

def verifyPermission(user, patient_id, authority, access_type):
    if authority["Level"] == 1:
        return [0, 0]

    if access_type == "TherapyHistory" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type="TherapyHistory").exists():
        DeidentifiedPatientID = models.DeidentifiedPatientID.objects.get(researcher_id=user.unique_user_id, authorized_patient_id=patient_id)
        TimeRange = DeidentifiedPatientID.authorized_time_range
        return TimeRange[access_type]

    elif access_type == "BrainSenseSurvey" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).exists():
        recording_ids = models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).all().values("authorized_recording_id")
        recording_ids = [id["authorized_recording_id"] for id in recording_ids]
        return recording_ids

    elif access_type == "BrainSenseStream" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).exists():
        recording_ids = models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).all().values("authorized_recording_id")
        recording_ids = [id["authorized_recording_id"] for id in recording_ids]
        return recording_ids

    elif access_type == "IndefiniteStream" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).exists():
        recording_ids = models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).all().values("authorized_recording_id")
        recording_ids = [id["authorized_recording_id"] for id in recording_ids]
        return recording_ids

    elif access_type == "ChronicLFPs" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type="ChronicLFPs").exists():
        DeidentifiedPatientID = models.DeidentifiedPatientID.objects.get(researcher_id=user.unique_user_id, authorized_patient_id=patient_id)
        TimeRange = DeidentifiedPatientID.authorized_time_range
        return TimeRange[access_type]

    return None

def extractPatientList(user):
    PatientInfo = list()
    if user.is_admin or user.is_clinician:
        patients = models.Patient.objects.filter(institute=user.institute).all()
        for patient in patients:
            info = extractPatientTableRow(user, patient)
            PatientInfo.append(info)

    else:
        patients = models.Patient.objects.filter(institute=user.email).all()
        for patient in patients:
            info = extractPatientTableRow(user, patient)
            PatientInfo.append(info)
        
        DeidentifiedPatientID = models.DeidentifiedPatientID.objects.filter(researcher_id=user.unique_user_id).all()
        for deidentified_patient in DeidentifiedPatientID:
            patient = models.Patient.objects.filter(deidentified_id=deidentified_patient.deidentified_id, institute=user.unique_user_id).first()
            info = extractPatientTableRow(user, patient)
            PatientInfo.append(info)

    PatientInfo = sorted(PatientInfo, key=lambda patient: patient["LastName"]+", "+patient["FirstName"])
    return PatientInfo

def extractAuthorizedAccessList(researcher_id):
    AuthorizedList = list()
    DeidentifiedPatientID = models.DeidentifiedPatientID.objects.filter(researcher_id=researcher_id).all()
    for patient in DeidentifiedPatientID:
        AuthorizedList.append({"ID": patient.authorized_patient_id})
    return AuthorizedList

def extractAvailableRecordingList(user, researcher_id, patient_id):
    key = os.environ.get('ENCRYPTION_KEY')

    RecordingList = dict()
    try:
        DeidentifiedPatientID = models.DeidentifiedPatientID.objects.get(researcher_id=researcher_id, authorized_patient_id=patient_id)
        RecordingList["TimeRange"] = DeidentifiedPatientID.authorized_time_range
    except:
        RecordingList["TimeRange"] = models.PerceptRecordingDefaultAuthorization()

    RecordingList["Recordings"] = list()
    RecordingInfo = {"Device": "", "ID": "", "Type": "TherapyHistory",
                    "Date": RecordingList["TimeRange"]["TherapyHistory"][1],
                    "Authorized": models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type="TherapyHistory").exists()}
    RecordingList["Recordings"].append(RecordingInfo)

    RecordingInfo = {"Device": "", "ID": "", "Type": "ChronicLFPs",
                    "Date": RecordingList["TimeRange"]["ChronicLFPs"][1],
                    "Authorized": models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_type="ChronicLFPs").exists()}
    RecordingList["Recordings"].append(RecordingInfo)

    AvailableDevices = models.PerceptDevice.objects.filter(patient_deidentified_id=patient_id, authority_level="Clinic", authority_user=user.institute).all()
    for device in AvailableDevices:
        AvailableRecordings = models.BrainSenseRecording.objects.filter(device_deidentified_id=device.deidentified_id).order_by("-recording_date").all()
        for recording in AvailableRecordings:
            if recording.recording_type == "ChronicLFPs":
                continue
            RecordingInfo = {"Device": device.getDeviceSerialNumber(key), "ID": recording.recording_id, "Type": recording.recording_type,
                            "Date": recording.recording_date.timestamp(),
                            "Authorized": models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_id=recording.recording_id).exists()}

            if not RecordingInfo in RecordingList["Recordings"]:
                RecordingList["Recordings"].append(RecordingInfo)

    return RecordingList

def saveSourceFiles(datastruct, datatype, info, id, device_id):
    try:
        os.mkdir(DATABASE_PATH + "recordings" + os.path.sep + str(device_id))
    except Exception:
        pass

    filename = str(device_id) + os.path.sep + datatype + "_" + info + "_" + str(id) + ".pkl"
    with open(DATABASE_PATH + "recordings" + os.path.sep + filename, "wb+") as file:
        pickle.dump(datastruct, file)
    return filename

def loadSourceDataPointer(filename):
    with open(DATABASE_PATH + "recordings" + os.path.sep + filename, "rb") as file:
        datastruct = pickle.load(file)
    return datastruct
