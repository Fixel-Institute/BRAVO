""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Medical Images Processing Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())

from datetime import datetime, date, timedelta
import pickle, joblib
import json
import dateutil, pytz
import numpy as np
import pandas as pd
import nibabel as nib

from Backend import models

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

def extractAvailableModels(patient_id, authority):
    """ Extract available image models from patient directory

    Args:
      patient_id: UUID4 deidentified id for each unique Patient in SQL Database.
      authority: User permission structure indicating the type of access the user has.

    Returns:
      Dictionary with ``availableModels`` array and ``descriptor`` object. 
    """

    descriptor = {}
    availableModels = []

    if not authority["Permission"]:
        return {"availableModels": availableModels, "descriptor": descriptor}

    if not os.path.exists(DATABASE_PATH + 'imaging/' + patient_id):
        return {"availableModels": availableModels, "descriptor": descriptor}
        
    files = os.listdir(DATABASE_PATH + 'imaging/' + patient_id)
    for file in files:
        if file in authority["Permission"] or authority["Level"] == 1:
            if file == "renderer.json": 
                with open(DATABASE_PATH + 'imaging/' + patient_id + "/" + file) as fid:
                    descriptor = json.load(fid)
                    for key in descriptor.keys():
                        if "electrode" in descriptor[key].keys():
                            availableModels.append({
                                "file": key,
                                "electrodeName": descriptor[key]["electrode"],
                                "targetPt": descriptor[key]["targetPoint"],
                                "entryPt": descriptor[key]["entryPoint"],
                                "type": "electrode",
                                "mode": "multiple"
                            })
                            
            elif file.endswith(".stl"):
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
    return {"availableModels": availableModels, "descriptor": descriptor}

def stlReader(directory, filename, color="#FFFFFF"):
    """ Decode STL files. 

    The color parameter will encode color code to binary STL header. This
    will ensure the STL decoder associate the STL object with a specific color.

    Args:
      directory: UUID4 deidentified id for each unique Patient in SQL Database.
      filename: String of model filename
      color: Hex-encoded color string

    Returns:
      Raw byte array of binary STL file.
    """

    if not os.path.exists(DATABASE_PATH + 'imaging/' + directory + "/" + filename):
        return False 

    with open(DATABASE_PATH + 'imaging/' + directory + "/" + filename, "rb") as file:
        file_data = bytearray(file.read())

    colorHeader = bytes("COLOR=","ascii")
    colorArray = bytearray(colorHeader)
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

def pointsReader(directory, filename):
    """ Decode SCIRun Points/Edges files. 

    Args:
      directory: UUID4 deidentified id for each unique Patient in SQL Database.
      filename: String of model filename

    Returns:
      Point arrays of tracts.
    """

    if not os.path.exists(DATABASE_PATH + 'imaging/' + directory + "/" + filename):
        return False 

    if not os.path.exists(DATABASE_PATH + 'imaging/' + directory + "/" + filename.replace(".pts",".edge")):
        return False 

    pts = np.loadtxt(DATABASE_PATH + 'imaging/' + directory + "/" + filename)
    edges = np.loadtxt(DATABASE_PATH + 'imaging/' + directory + "/" + filename.replace(".pts",".edge"))

    tracts = []
    breakingIndex = np.where(np.diff(edges[:,0]) != 1)[0]
    startIndex = 0
    for i in range(len(breakingIndex)):
        if i > 0:
            startIndex = int(edges[breakingIndex[i-1]+1,0])
        endIndex = int(edges[breakingIndex[i],1]+1)
        tracts.append(pts[startIndex:endIndex])

    return tracts

def tractReader(directory, filename):
    """ Decode Tract files. 

    This is a wrapper for NiBabel library's streamlines class. This function can be used to 
    read MRTRIX3 tck file format.

    Args:
      directory: UUID4 deidentified id for each unique Patient in SQL Database.
      filename: String of model filename

    Returns:
      Point arrays of tracts.
    """

    if not os.path.exists(DATABASE_PATH + 'imaging/' + directory + "/" + filename):
        return False 

    extractedTckFile = nib.streamlines.load(DATABASE_PATH + 'imaging/' + directory + "/" + filename)
    tracts = []
    for tract in extractedTckFile.streamlines:
        tracts.append(tract)

    return tracts

def niftiInfo(directory, filename):
    """ Extract Header information from NifTi file

    Args:
      directory: UUID4 deidentified id for each unique Patient in SQL Database.
      filename: String of model filename

    Returns:
      NifTi headers that describe dimension and size of the volume
    """

    if not os.path.exists(DATABASE_PATH + 'imaging/' + directory + "/" + filename):
        return np.array([]) 

    nii = nib.load(DATABASE_PATH + 'imaging/' + directory + "/" + filename)
    headers = {
        "size": nii.header["dim"][1:4],
        "pixdim": nii.header["pixdim"][1:4],
        "affine": nii.header.get_best_affine().reshape(16)
    }
    return headers

def niftiLoader(directory, filename):
    """ Extract raw byte values from NifTi file

    Args:
      directory: UUID4 deidentified id for each unique Patient in SQL Database.
      filename: String of model filename

    Returns:
      Raw byte array of 3D NifTi matrix.
    """

    if not os.path.exists(DATABASE_PATH + 'imaging/' + directory + "/" + filename):
        return False 

    nii = nib.load(DATABASE_PATH + 'imaging/' + directory + "/" + filename)
    raw_data = nii.get_fdata().astype(np.uint16)
    return raw_data

def electrodeReader(filename):
    """ Extract electrode paginations

    This function will read in all models within Electrode directory to create a 
    multi-STL pagination for frontend to request multiple objects. 

    Args:
      filename: String of model filename

    Returns:
      Array of dictionary for Pagination. Each dictionary defines "filename", "electrode", "directory", and "type" 
    """

    pages = []
    if not os.path.exists(DATABASE_PATH + '/imaging/Electrodes/' + filename):
        return False 

    parts = os.listdir(DATABASE_PATH + 'imaging/Electrodes/' + filename)
    for part in parts:
        pages.append({
            "filename": part,
            "electrode": filename,
            "directory": "Electrodes",
            "type": "electrode",
        })
    
    return pages

