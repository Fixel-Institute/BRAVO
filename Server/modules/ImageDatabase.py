import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())

from datetime import datetime, date, timedelta
import pickle, joblib
import dateutil, pytz
import numpy as np
import pandas as pd
import nibabel as nib

from Backend import models

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

def extractAvailableModels(patient_id, authority):
    availableModels = []

    if not authority["Permission"]:
        return availableModels

    if not os.path.exists(DATABASE_PATH + '/imaging/' + patient_id):
        return availableModels
        
    files = os.listdir(DATABASE_PATH + '/imaging/' + patient_id)
    for file in files:
        if file in authority["Permission"] or authority["Level"] == 1:
            if file.endswith(".stl"):
                availableModels.append({
                    "file": file,
                    "type": "stl",
                    "mode": "single"
                })

            elif file.endswith(".pts"):
                if file.replace(".pts",".edge") in files:
                    availableModels.append({
                        "file": file,
                        "type": "points",
                        "mode": "single"
                    })

            elif file.endswith(".tck"):
                availableModels.append({
                    "file": file,
                    "type": "tracts",
                    "mode": "single"
                })

            elif file.endswith(".nii.gz") or file.endswith(".nii"):
                availableModels.append({
                    "file": file,
                    "type": "volume",
                    "mode": "multiple"
                })

    """
    if not request.data["Directory"] == "Electrodes":
        electrodes = os.listdir(BASE_DIR + '/resources/' + "Electrodes")
        for file in electrodes:
            if file.endswith("_contacts.stl"):
                if file.replace("_contacts.stl","_shaft.stl") in electrodes:
                    availableModels.append({
                        "file": file.replace("_contacts.stl", "_ElectrodeModel"),
                        "type": "electrode",
                        "mode": "multiple"
                    })
    """
    return availableModels

def stlReader(directory, filename):
    if not os.path.exists(DATABASE_PATH + '/imaging/' + directory + "/" + filename):
        return False 

    with open(DATABASE_PATH + '/imaging/' + directory + "/" + filename, "rb") as file:
        file_data = bytearray(file.read())
    colorHeader = bytes("COLOR=","ascii")
    colorArray = bytearray(colorHeader)
    
    try:
        color = "#FFFFFF"
        for i in range(3):
            colorArray.append(int("0x" + color[i*2+1:(i+1)*2+1], base=16))
        colorArray.append(255)

    except Exception as e:
        color = "#FFFFFF"
        for i in range(3):
            colorArray.append(int("0x" + color[i*2+1:(i+1)*2+1], base=16))
        colorArray.append(255)
        
    colorFound = False
    lastDataByte = 0
    for i in range(70):
        if file_data[i:i+6] == bytes("COLOR=","ascii"):
            colorFound = True
            lastDataByte = i-1
        
        if not colorFound:
            if file_data[i] != 0x00:
                lastDataByte = i
    
    file_data[lastDataByte + 1 : lastDataByte + len(colorArray) + 1] = colorArray
    return file_data

def tractReader(directory, filename):
    if not os.path.exists(DATABASE_PATH + '/imaging/' + directory + "/" + filename):
        return False 

    extractedTckFile = nib.streamlines.load(DATABASE_PATH + '/imaging/' + directory + "/" + filename)
    tracts = []
    for tract in extractedTckFile.streamlines:
        tracts.append(tract)

    return tracts

def electrodeReader(directory, filename):
    pages = []
    electrodes = os.listdir(BASE_DIR + '/resources/' + "Electrodes")
    for file in electrodes:
        if file.startswith(request.data["FileName"].replace("_ElectrodeModel","")):
            pages.append({
                "filename": file,
                "directory": "Electrodes",
                "type": "electrode",
            })