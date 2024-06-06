""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2024 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Common Database Processing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())

from datetime import datetime, date, timedelta
import pickle, blosc
import dateutil, pytz
import numpy as np
import pandas as pd
from cryptography.fernet import Fernet
import scipy.io as sio
import json

from Backend import models

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

def retrieveProcessingSettings(config=dict()):
    options = {
        "TimeSeriesRecording": {
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
        },
        "PowerSpectralDensity": {
            "PSDMethod": {
                "name": "Power Spectrum Estimation Algorithm",
                "description": "",
                "options": ["Estimated Medtronic PSD","Short-time Fourier Transform"],
                "value": "Short-time Fourier Transform"
            },
            "MonopolarEstimation": {
                "name": "Monopolar Estimation Algorithm",
                "description": "",
                "options": ["No Estimation", "DETEC Algorithm (Strelow et. al., 2022)"],
                "value": "No Estimation"
            },
        }
    }

    if not "ProcessingSettings" in config.keys():
        return options, True
    
    if not type(config["ProcessingSettings"]) == dict:
        return options, True

    for key in config["ProcessingSettings"].keys():
        if type(config["ProcessingSettings"][key]) == dict:
            for subkey in config["ProcessingSettings"][key].keys():
                if type(config["ProcessingSettings"][key][subkey]) == dict and subkey in options[key].keys():
                    if config["ProcessingSettings"][key][subkey]["name"] == options[key][subkey]["name"] and config["ProcessingSettings"][key][subkey]["description"] == options[key][subkey]["description"] and config["ProcessingSettings"][key][subkey]["options"] == options[key][subkey]["options"]:
                        options[key][subkey]["value"] = config["ProcessingSettings"][key][subkey]["value"]
    
    return options, not (options==config["ProcessingSettings"])

def extractUserInfo(user):
    userInfo = dict()
    userInfo["Name"] = user.user_name
    userInfo["Email"] = user.email
    userInfo["Clinician"] = False
    userInfo["Admin"] = False
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

def extractPatientTableRow(user, patient, deidentifiedId=None):
    key = os.environ.get('ENCRYPTION_KEY')

    if deidentifiedId:
        info = extractPatientTableRow(user, deidentifiedId)
    else:
        info = dict()
        info["FirstName"] = patient.getPatientFirstName(key)
        info["LastName"] = patient.getPatientLastName(key)
        info["Diagnosis"] = patient.diagnosis
        info["MRN"] = patient.getPatientMRN(key)
        info["DOB"] = patient.birth_date.timestamp()
        info["Institute"] = patient.institute
        info["Tags"] = patient.tags
        info["DaysSinceImplant"] = []
        info["ID"] = str(patient.deidentified_id)
        info["LastChange"] = patient.last_change.timestamp()

    lastTimestamp = datetime.fromtimestamp(0, tz=pytz.utc)
    deviceIDs = patient.device_deidentified_id
    for id in deviceIDs:
        device = models.PerceptDevice.objects.filter(deidentified_id=id).first()
        if device == None:
            patient.device_deidentified_id.remove(id)
            patient.save()
            continue

        if not (user.is_admin or user.is_clinician):
            daysSinceImplant = np.round((datetime.now(tz=pytz.utc) - device.implant_date).total_seconds() / (3600*24)) - 15
        else:
            daysSinceImplant = np.round((datetime.now(tz=pytz.utc) - device.implant_date).total_seconds() / (3600*24))
            
        if device.device_name == "":
            if not (user.is_admin or user.is_clinician):
                deviceName = str(device.deidentified_id)
            else:
                deviceName = device.getDeviceSerialNumber(key)
        else:
            deviceName = device.device_name

        info["DaysSinceImplant"].append({"Name": deviceName, "Days": daysSinceImplant})
        if device.device_last_seen > lastTimestamp:
            lastTimestamp = device.device_last_seen

    info["LastSeen"] = lastTimestamp.timestamp()
    return info

def extractPatientInfo(user, patientUniqueID, deidentifiedId=None):
    key = os.environ.get('ENCRYPTION_KEY')

    patient = models.Patient.objects.get(deidentified_id=patientUniqueID)

    if deidentifiedId:
        info = extractPatientInfo(user, deidentifiedId)
    else:
        info = dict()
        info["FirstName"] = patient.getPatientFirstName(key)
        info["LastName"] = patient.getPatientLastName(key)
        if (user.is_admin or user.is_clinician):
            info["Name"] = info["FirstName"] + " " + info["LastName"]
        else:
            info["Name"] = info["FirstName"] + " (" + info["LastName"] + ")"

        info["Diagnosis"] = patient.diagnosis
        info["MRN"] = patient.getPatientMRN(key)
        info["DOB"] = patient.birth_date
        info["Institute"] = patient.institute
        info["Gender"] = patient.getPatientGender(key)

        info["Devices"] = list()
        info["Tags"] = patient.tags

    availableDevices = getPerceptDevices(user, patientUniqueID, {
        "Level": 2 if deidentifiedId else 1,
    })

    if info["Gender"] == "":
        fileSize = 0
        sessionPath = ""
        for device in availableDevices:
            availableSessions = models.PerceptSession.objects.filter(device_deidentified_id=device.deidentified_id).all()
            for session in availableSessions:
                if os.path.exists(DATABASE_PATH + session.session_file_path):
                    if os.path.getsize(DATABASE_PATH + session.session_file_path) < fileSize or fileSize == 0:
                        fileSize = os.path.getsize(DATABASE_PATH + session.session_file_path)
                        sessionPath = DATABASE_PATH + session.session_file_path

        if sessionPath != "":
            JSON = Percept.decodeEncryptedJSON(sessionPath, key)
            info["Gender"] = JSON["PatientInformation"]["Final"]["PatientGender"].replace("PatientGenderDef.","")
            patient.setPatientGender(info["Gender"], key)
            patient.save()
            
    for device in availableDevices:
        deviceInfo = dict()
        deviceInfo["ID"] = device.deidentified_id
        deviceInfo["Location"] = device.device_location
        if device.device_name == "":
            if not (user.is_admin or user.is_clinician):
                deviceInfo["DeviceName"] = device.deidentified_id
            else:
                deviceInfo["DeviceName"] = device.getDeviceSerialNumber(key)
        else:
            deviceInfo["DeviceName"] = device.device_name

        deviceInfo["DeviceType"] = device.device_type
        if not (user.is_admin or user.is_clinician):
            deviceInfo["ImplantDate"] = device.implant_date.timestamp()+15*3600*24
        else:
            deviceInfo["ImplantDate"] = device.implant_date.timestamp()

        deviceInfo["LastSeenDate"] = device.device_last_seen.timestamp()
        deviceInfo["EOLDate"] = device.device_eol_date.timestamp()
        deviceInfo["Leads"] = device.device_lead_configurations
        info["Devices"].append(deviceInfo)

    return info

def extractTags(typeName, institute):
    allTags = models.SearchTags.objects.filter(tag_type=typeName, institute=institute).all()
    return [tag.tag_name for tag in allTags]

def getPerceptDevices(user, patientUniqueID, authority):
    availableDevices = None
    if authority["Level"] == 1:
        if (user.is_admin or user.is_clinician):
            availableDevices = models.PerceptDevice.objects.filter(patient_deidentified_id=patientUniqueID, authority_level="Clinic", authority_user=user.institute).all()
        else:
            availableDevices = models.PerceptDevice.objects.filter(patient_deidentified_id=patientUniqueID, authority_level="Research", authority_user=user.email).all()
    elif authority["Level"] == 2:
        availableDevices = models.PerceptDevice.objects.filter(patient_deidentified_id=patientUniqueID).all()
        for device in availableDevices:
            device.serial_number = str(device.deidentified_id)

    if availableDevices:
        for device in availableDevices:
            for configuration in device.device_lead_configurations:
                if not "CustomName" in configuration.keys():
                    configuration["CustomName"] = configuration["TargetLocation"]

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
        elif models.Patient.objects.filter(deidentified_id=patient_id, institute=user.institute).exists():
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
    
    # If given all access
    if access_type == "TherapyHistory" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type="TherapyHistory").exists():
        DeidentifiedPatientID = models.DeidentifiedPatientID.objects.get(researcher_id=user.unique_user_id, authorized_patient_id=patient_id)
        TimeRange = DeidentifiedPatientID.authorized_time_range
        return TimeRange[access_type]

    elif access_type == "BrainSenseSurvey" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).exists():
        recording_ids = models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).all().values("authorized_recording_id")
        recording_ids = [id["authorized_recording_id"] for id in recording_ids]
        return recording_ids

    elif access_type == "BrainSenseStream":
        recording_ids = []
        for subaccess_type in ["BrainSenseStreamTimeDomain", "BrainSenseStreamPowerDomain"]:
            if models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=subaccess_type).exists():
                recording_ids_obj = models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=subaccess_type).all().values("authorized_recording_id")
                recording_ids.extend([str(id["authorized_recording_id"]) for id in recording_ids_obj])
        if len(recording_ids) == 0:
            return None
        return recording_ids

    elif access_type == "IndefiniteStream" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).exists():
        recording_ids = models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).all().values("authorized_recording_id")
        recording_ids = [id["authorized_recording_id"] for id in recording_ids]
        return recording_ids

    elif access_type == "ChronicLFPs" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type="ChronicLFPs").exists():
        DeidentifiedPatientID = models.DeidentifiedPatientID.objects.get(researcher_id=user.unique_user_id, authorized_patient_id=patient_id)
        TimeRange = DeidentifiedPatientID.authorized_time_range
        return TimeRange[access_type]

    # TODO: Imaging Pipeline for Research Authorization. 
    elif access_type == "Imaging" and models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type="Imaging").exists():
        recording_ids = models.ResearchAuthorizedAccess.objects.filter(researcher_id=user.unique_user_id, authorized_patient_id=patient_id, authorized_recording_type=access_type).all().values("authorized_recording_id")
        recording_ids = [id["authorized_recording_id"] for id in recording_ids]
        return recording_ids

    return None

def extractPatientList(user):
    PatientInfo = list()
    patients = models.Patient.objects.filter(institute=user.institute).all()
    for patient in patients:
        info = extractPatientTableRow(user, patient)
        PatientInfo.append(info)

    DeidentifiedPatientID = models.DeidentifiedPatientID.objects.filter(researcher_id=user.unique_user_id).all()
    for deidentified_patient in DeidentifiedPatientID:
        patient = models.Patient.objects.filter(deidentified_id=deidentified_patient.deidentified_id, institute=user.unique_user_id).first()
        info = extractPatientTableRow(user, models.Patient.objects.filter(deidentified_id=deidentified_patient.authorized_patient_id).first(), deidentifiedId=patient)
        PatientInfo.append(info)

    PatientInfo = sorted(PatientInfo, key=lambda patient: patient["LastName"]+", "+patient["FirstName"])
    return PatientInfo

def extractPatientAccessTable(user):
    PatientInfo = list()
    if (user.is_admin or user.is_clinician):
        researcherIds = {}
        patients = models.Patient.objects.filter(institute=user.institute).all()
    else:
        patients = models.Patient.objects.filter(institute=user.email).all()

    for patient in patients:
        info = extractPatientTableRow(user, patient)
        AuthorizedUsers = []
        if models.DeidentifiedPatientID.objects.filter(authorized_patient_id=info["ID"]).exists():
            AuthorizedUsers = models.DeidentifiedPatientID.objects.filter(authorized_patient_id=info["ID"]).values("researcher_id").all()
            AuthorizedUsers = [str(AuthUser["researcher_id"]) for AuthUser in AuthorizedUsers]
            for userId in AuthorizedUsers:
                if not userId in researcherIds.keys():
                    researcherIds[userId] = models.PlatformUser.objects.filter(unique_user_id=userId).first()
        
        PatientInfo.append({
            "ID": info["ID"],
            "FirstName": info["FirstName"],
            "LastName": info["LastName"],
            "Diagnosis": info["Diagnosis"],
            "Uploader": user.institute if (user.is_admin or user.is_clinician) else user.email,
            "Authorized": [{"Email": researcherIds[userId].email, "ID": userId} for userId in AuthorizedUsers]
        })
    
    DeidentifiedPatientID = models.DeidentifiedPatientID.objects.filter(researcher_id=user.unique_user_id).all()
    for deidentified_patient in DeidentifiedPatientID:
        deidentified = models.Patient.objects.filter(deidentified_id=deidentified_patient.deidentified_id).first()
        patient = extractAccess(user, deidentified_patient.authorized_patient_id)
        if patient == 0:
            AuthorizeResearchAccess(user, user.unique_user_id, deidentified_patient.deidentified_id, False)
            continue

        info = extractPatientTableRow(user, deidentified)
        
        PatientInfo.append({
            "ID": info["ID"],
            "FirstName": info["FirstName"],
            "LastName": info["LastName"],
            "Diagnosis": info["Diagnosis"],
            "Uploader": patient.institute,
            "Authorized": []
        })

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
        AvailableRecordings = models.NeuralActivityRecording.objects.filter(device_deidentified_id=device.deidentified_id).order_by("-recording_date").all()
        for recording in AvailableRecordings:
            if recording.recording_type == "ChronicLFPs":
                continue
            RecordingInfo = {"Device": device.getDeviceSerialNumber(key), "ID": recording.recording_id, "Type": recording.recording_type,
                            "Date": recording.recording_date.timestamp(),
                            "Authorized": models.ResearchAuthorizedAccess.objects.filter(researcher_id=researcher_id, authorized_patient_id=patient_id, authorized_recording_id=recording.recording_id).exists()}

            if not RecordingInfo in RecordingList["Recordings"]:
                RecordingList["Recordings"].append(RecordingInfo)

    return RecordingList

def saveResultMATFiles(datastruct, datatype, info, id, device_id):
    try:
        os.mkdir(DATABASE_PATH + "recordings" + os.path.sep + str(device_id))
    except Exception:
        pass

    filename = str(device_id) + os.path.sep + datatype + "_" + info + "_" + str(id) + ".mat"
    sio.savemat(DATABASE_PATH + "recordings" + os.path.sep + filename, datastruct, long_field_names=True)
    return filename

def loadSourceDataPointer(filename, bytes=False):
    with open(DATABASE_PATH + "recordings" + os.path.sep + filename, "rb") as file:
        if bytes:
            datastruct = file.read()
        else:
            if filename.endswith(".pkl"):
                datastruct = pickle.load(file)
            elif filename.endswith(".bpkl"):
                datastruct = pickle.loads(blosc.decompress(file.read()))
            elif filename.endswith(".mat"):
                datastruct = sio.loadmat(file, simplify_cells=True)["ProcessedData"]
    return datastruct

def deleteSourceDataPointer(filename):
    try:
        os.remove(DATABASE_PATH + "recordings" + os.path.sep + filename)
    except:
        pass

def saveSourceFiles(datastruct, datatype="", uid="", participant_id="", filename=None):
    pData = pickle.dumps(datastruct)
    if filename:
        with open(DATABASE_PATH + "recordings" + os.path.sep + filename, "wb+") as file:
            file.write(blosc.compress(pData))
        return filename
    
    os.makedirs(DATABASE_PATH + "recordings" + os.path.sep + str(participant_id), exist_ok=True)
    filename = str(participant_id) + os.path.sep + datatype + "_" + str(uid) + ".bpkl"
    with open(DATABASE_PATH + "recordings" + os.path.sep + filename, "wb+") as file:
        file.write(blosc.compress(pData))
    return filename
