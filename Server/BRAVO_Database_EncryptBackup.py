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
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys
from decoder import Percept
import pickle as pkl 

from cryptography.fernet import Fernet
import hashlib
import base64
import datetime, pytz

# Setup Password in Environment to avoid leaks
#os.environ["DecryptionPassword"] = ""
BRAVO_Database_DIR = ""
Files = os.listdir(BRAVO_Database_DIR + os.path.sep + "Raw")

if not os.path.exists(BRAVO_Database_DIR + os.path.sep + "PatientLibrary.pkl"):
    with open(BRAVO_Database_DIR + os.path.sep + "PatientLibrary.pkl", "wb+") as file:
        pkl.dump({"ExistingDevices": {}, 
                  "ExistingPatients": {},
                  "ExistingFiles": {},
                  "EncryptionDictionary": {"Name": {}, "Device": {}}}, file)

def changeTimeString(string, shift):
    return datetime.datetime.fromtimestamp(Percept.getTimestamp(string) + shift, tz=pytz.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def replaceJSONTimestamp(item, shift):
    if type(item) == dict:
        currentKeys = list(item.keys())
        for key in currentKeys:
            item[key] = replaceJSONTimestamp(item[key], shift)
        
            if key.endswith("Z"):
                try:
                    newTimeKey = changeTimeString(key, shift)
                    item[newTimeKey] = item[key]
                    del(item[key])
                except:
                    continue 
                
    elif type(item) == list:
        for i in range(len(item)):
            item[i] = replaceJSONTimestamp(item[i], shift)
    elif type(item) == str:
        if item.endswith("Z"):
            try:
                return changeTimeString(item, shift)
            except Exception as e:
                pass
    
    return item

def checkFiles(file1, file2):
    with open(file1, "rb") as file:
        File1Content = file.read()
    with open(file2, "rb") as file:
        File2Content = file.read()
    return File1Content == File2Content


with open(BRAVO_Database_DIR + os.path.sep + "PatientLibrary.pkl", "rb") as file:
    pklRead = pkl.load(file)
EncryptionDictionary = pklRead["EncryptionDictionary"]
ExistingDevices = pklRead["ExistingDevices"]
ExistingPatients = pklRead["ExistingPatients"]
ExistingFiles = pklRead["ExistingFiles"]

for i in range(len(Files)):
    if not os.path.exists(BRAVO_Database_DIR + os.path.sep + "Encrypted" + os.path.sep + Files[i]):
        JSON = Percept.decodeJSON(BRAVO_Database_DIR + os.path.sep + "Raw" + os.path.sep + Files[i])
        Name = JSON["PatientInformation"]["Final"]["PatientFirstName"].strip() + " " + JSON["PatientInformation"]["Final"]["PatientLastName"].strip()
        if "," in Name:
            Name = Name.split(",")[1].strip() + " " + Name.split(",")[0].strip()
        Name = ''.join([i for i in Name if not i.isdigit()])
        if Name.startswith(" "):
            Name = Name.strip()
        Name = Name.title()
        
        DeviceID = JSON["DeviceInformation"]["Final"]["NeurostimulatorSerialNumber"]
        
        if DeviceID in ExistingDevices.keys():
            with open(BRAVO_Database_DIR + os.path.sep + "Raw" + os.path.sep + Files[i], "rb") as file:
                NewMD5 = hashlib.md5(file.read()).hexdigest()
            for File in ExistingDevices[DeviceID]:
                if ExistingFiles[File] == NewMD5:
                    print("SAME MD5")
                    if checkFiles(BRAVO_Database_DIR + os.path.sep + "Raw" + os.path.sep + File, 
                                  BRAVO_Database_DIR + os.path.sep + "Raw" + os.path.sep + Files[i]):
                        os.remove(BRAVO_Database_DIR + os.path.sep + "Raw" + os.path.sep + Files[i])
                        break
                                
        if not os.path.exists(BRAVO_Database_DIR + os.path.sep + "Raw" + os.path.sep + Files[i]):
            continue 
        
        if not DeviceID in ExistingDevices.keys():
            ExistingDevices[DeviceID] = []
            if not Name in ExistingPatients.keys():
                ExistingPatients[Name] = []
            ExistingPatients[Name].append(DeviceID)
                
        ExistingDevices[DeviceID].append(Files[i])
    print(f"{i}/{len(Files)}")

hashedName = hashlib.sha256(os.environ["DecryptionPassword"].encode("utf-8")).hexdigest()[::2]
shiftTime = int.from_bytes(base64.b64encode(hashedName.encode("utf-8"))[8:13], "little") / 1000
encoder = Fernet(base64.b64encode(hashedName.encode("utf-8")))
for Name in ExistingPatients.keys():
    if not Name in EncryptionDictionary["Name"].keys():
        EncryptionDictionary["Name"][Name] = encoder.encrypt(Name.encode("utf-8")).decode("utf-8")
    for Device in ExistingPatients[Name]:
        if not Device in EncryptionDictionary["Device"].keys():
            EncryptionDictionary["Device"][Device] = encoder.encrypt(Device.encode("utf-8")).decode("utf-8")
        
        for File in ExistingDevices[Device]:
            if not os.path.exists(BRAVO_Database_DIR + os.path.sep + "Encrypted" + os.path.sep + File):
                JSON = Percept.decodeJSON(BRAVO_Database_DIR + os.path.sep + "Raw" + os.path.sep + File)
                JSON = replaceJSONTimestamp(JSON, -round(shiftTime))
                for key in ["Initial","Final"]:
                    JSON["PatientInformation"][key]["PatientFirstName"] = EncryptionDictionary["Name"][Name]
                    JSON["PatientInformation"][key]["PatientLastName"] = ""
                    JSON["PatientInformation"][key]["PatientId"] = ""
                    JSON["PatientInformation"][key]["ClinicianNotes"] = ""
                    
                    JSON["DeviceInformation"][key]["NeurostimulatorSerialNumber"] = EncryptionDictionary["Device"][Device]
                    JSON["DeviceInformation"][key]["DeviceName"] = ""
                    
                    with open(BRAVO_Database_DIR + os.path.sep + "Encrypted" + os.path.sep + File, "w+") as file:
                        json.dump(JSON, file)
    

with open(BRAVO_Database_DIR + os.path.sep + "PatientLibrary.pkl", "wb+") as file:
    pkl.dump({"ExistingDevices": ExistingDevices, "ExistingPatients": ExistingPatients, 
              "EncryptionDictionary": EncryptionDictionary, "ExistingFiles": ExistingFiles}, file)
