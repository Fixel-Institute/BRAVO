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
Query Imaging Models Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import HttpResponse

from Backend import models

from modules import Database, ImageDatabase
from utility.PythonUtility import uniqueList
import json
import numpy as np
import nibabel as nib

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class QueryImageModelDirectory(RestViews.APIView):
    """ Query all Image models store in the patient's imaging folder.

    This route will provide user with all model descriptor related to a specific patient, assuming 
    there are imaging models in the patient's imaging folder.

    **POST**: ``/api/queryImageDirectory``

    Args:
      id (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.

    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains ``descriptor``, a dictionary that describe initial rendered objects and their parameters, and
      ``availableModels``, an array of dictionary with field {file, type, mode}. 
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [AllowAny]
    def post(self, request):
        if not "authToken" in request.data:
            return Response(status=403, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        mobileUser = models.MobileUser.objects.filter(active_token=request.data["authToken"]).first()
        if not mobileUser:
            return Response(status=401)

        associatedPatient = models.Patient.objects.filter(deidentified_id=mobileUser.linked_patient_id).first()
        if not associatedPatient:
            return Response(status=401)

        data = ImageDatabase.extractAvailableModels(str(mobileUser.linked_patient_id), {
          "Level": 1,
          "Permission": [0,0]
        })
        return Response(status=200, data=data)

class QueryImageModel(RestViews.APIView):
    """ Query all Image models store in the patient's imaging folder.

    This route will provide user with all model descriptor related to a specific patient, assuming 
    there are imaging models in the patient's imaging folder.

    **POST**: ``/api/queryImageModel``

    Args:
      Directory (uuid): Patient Unique Identifier as provided from ``QueryPatientList`` route.
      FileMode (string): "single" or "multiple", define whether the API should return individual file or pagination for multiple requests.
      FileType (string): "stl", "tracts", or "electrode", define what kind of model the server should retrieve. This defines the decoder function.
      FileName (string): filename of the model.
      
    Returns:
      Response Code 200 if success or 400 if error. 
      Response Body contains an octet-stream (binary buffer) for "stl" and "electrode", or array of points for tracts.
    """

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [AllowAny]
    def post(self, request):
        if not "authToken" in request.data:
            return Response(status=403, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

        mobileUser = models.MobileUser.objects.filter(active_token=request.data["authToken"]).first()
        if not mobileUser:
            return Response(status=401)

        associatedPatient = models.Patient.objects.filter(deidentified_id=mobileUser.linked_patient_id).first()
        if not associatedPatient:
            return Response(status=401)
          
        PatientID = str(mobileUser.linked_patient_id)

        if request.data["FileMode"] == "single":
            if request.data["FileType"] == "stl":
                file_data = ImageDatabase.stlReader(PatientID, request.data["FileName"])
                if not file_data:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                return HttpResponse(bytes(file_data), status=200, headers={
                    "Content-Type": "application/octet-stream"
                })

            elif request.data["FileType"] == "tracts":
                tracts = ImageDatabase.tractReader(PatientID, request.data["FileName"])
                if not tracts:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                return Response(status=200, data={
                    "points": tracts
                })
            
            elif request.data["FileType"] == "points":
                tracts = ImageDatabase.pointsReader(PatientID, request.data["FileName"])
                if not tracts:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                return Response(status=200, data={
                    "points": tracts
                })
            
            elif request.data["FileType"] == "electrode":
                file_data = ImageDatabase.stlReader("Electrodes/" + request.data["ElectrodeName"], request.data["FileName"])
                if not file_data:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                return HttpResponse(bytes(file_data), status=200, headers={
                    "Content-Type": "application/octet-stream"
                })

            elif request.data["FileType"] == "volume":
                file_data = ImageDatabase.niftiLoader(PatientID, request.data["FileName"])
                if len(file_data) == 0:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                return HttpResponse(bytes(file_data), status=200, headers={
                    "Content-Type": "application/octet-stream"
                })

        elif request.data["FileMode"] == "multiple":
            if request.data["FileType"] == "electrode":
                pages = ImageDatabase.electrodeReader(request.data["FileName"])
                return Response(status=200, data={"pages": pages, "color": "0x000000"})
            
            elif request.data["FileType"] == "volume":
                headers = ImageDatabase.niftiInfo(PatientID, request.data["FileName"])
                return Response(status=200, data={"headers": headers})
