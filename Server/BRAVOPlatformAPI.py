#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
Python Package to Access BRAVO REST APIs
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
@date: Thu Sep 16 12:05:09 2021
"""

import pandas as pd
import requests
from datetime import datetime
import json

class BRAVOPlatformRequest:
    def __init__(self, username, password, server="http://localhost:3001"):
        self.__Username = username
        self.__Password = password
        self.__Server = server
        self.__RefreshCode = ""
        
        form = {"Email": username, "Password": password, "Persistent": True}
        headers = {"Content-Type": "application/json"}
        response = requests.post(self.__Server + "/api/authenticate", json.dumps(form), headers=headers)
        if response.status_code == 200:
            payload = response.json()
            self.__RefreshCode = payload["refresh"]
            self.__Headers = {"Content-Type": "application/json", "Authorization": f"Bearer {payload['access']}"} 
        else:
            print(response.content)
            raise Exception(f"Network Error: {response.status_code}")
    
    def refreshAuthToken(self):
        form = {"refresh": self.__RefreshCode}
        headers = {"Content-Type": "application/json"}
        response = requests.post(self.__Server + "/api/authRefresh", json.dumps(form), headers=headers)
        if response.status_code == 200:
            payload = response.json()
            self.__Headers = {"Content-Type": "application/json", "Authorization": f"Bearer {payload['access']}"} 
        else:
            print(response.content)
            raise Exception(f"Network Error: {response.status_code}")
    
    def RequestPatientList(self):
        response = requests.post(self.__Server + "/api/queryPatients", headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestPatientList()
            else:
                raise Exception(f"Network Error: {response.status_code}")
            
    def RequestPatientInfo(self, PatientID):
        form = {"id": PatientID}
        response = requests.post(self.__Server + "/api/queryPatientInfo", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestPatientInfo(PatientID)
            else:
                raise Exception(f"Network Error: {response.status_code}")
    
    def RequestPatientTagUpdate(self, PatientID, PatientObj):
        form = {"updatePatientInfo": PatientID,
                "FirstName": PatientObj["FirstName"],
                "LastName": PatientObj["LastName"],
                "Diagnosis": PatientObj["Diagnosis"],
                "MRN": PatientObj["MRN"],
                "Tags": PatientObj["Tags"]}
        response = requests.post(self.__Server + "/api/updatePatientInformation", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            return True
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestPatientTagUpdate(PatientID, PatientObj)
            else:
                raise Exception(f"Network Error: {response.status_code}")
        
    def RequestImpedanceMeasurement(self, PatientID):
        
        return 
            
    def RequestBrainSenseSurveys(self, PatientID):
        form = {"id": PatientID}
        response = requests.post(self.__Server + "/api/queryBrainSenseSurveys", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestBrainSenseSurveys(PatientID)
            else:
                raise Exception(f"Network Error: {response.status_code}")
        
    def RequestBrainSenseSurveysRaw(self, PatientID):
        form = {"id": PatientID, "requestRaw": True}
        response = requests.post(self.__Server + "/api/queryBrainSenseSurveys", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestBrainSenseSurveysRaw(PatientID)
            else:
                raise Exception(f"Network Error: {response.status_code}")
        
    def RequestBrainSenseStreamList(self, PatientID):
        form = {"id": PatientID, "requestOverview": True}
        response = requests.post(self.__Server + "/api/queryBrainSenseStreaming", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestBrainSenseStreamList(PatientID)
            else:
                raise Exception(f"Network Error: {response.status_code}")
        
    def RequestBrainSenseStream(self, PatientID, RecordingID):
        form = {"id": PatientID, "recordingId": RecordingID, "requestData": True}
        response = requests.post(self.__Server + "/api/queryBrainSenseStreaming", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        elif response.status_code == 401:
            self.refreshAuthToken()
            return self.RequestBrainSenseStream(PatientID, RecordingID)
        else:
            raise Exception(f"Network Error: {response.status_code}")
        
    def RequestIndefiniteStreamList(self, PatientID):
        form = {"id": PatientID, "requestOverview": True}
        response = requests.post(self.__Server + "/api/queryIndefiniteStreaming", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        elif response.status_code == 401:
            self.refreshAuthToken()
            return self.RequestIndefiniteStreamList(PatientID)
        else:
            raise Exception(f"Network Error: {response.status_code}")
        
    def RequestIndefiniteStream(self, PatientID, Timestamps, Devices):
        form = {"id": PatientID, "timestamps": Timestamps, "devices": Devices, "requestData": True}
        response = requests.post(self.__Server + "/api/queryIndefiniteStreaming", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        elif response.status_code == 401:
            self.refreshAuthToken()
            return self.RequestIndefiniteStream(PatientID, Timestamps, Devices)
        else:
            raise Exception(f"Network Error: {response.status_code}")
        
    def RequestBrainSenseStimulationPSD(self, DeviceID, Timestamp, ChannelID):
        # TODO 
        return 
        
    def RequestTherapyConfigurations(self, PatientID):
        form = {"id": PatientID}
        response = requests.post(self.__Server + "/api/queryTherapyHistory", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        elif response.status_code == 401:
            self.refreshAuthToken()
            return self.RequestTherapyConfigurations(PatientID)
        else:
            raise Exception(f"Network Error: {response.status_code}")
    
    def RequestChronicLFP(self, PatientID):
        form = {"id": PatientID, "requestData": True, "timezoneOffset": 3600*5, "normalizeCircadianRhythm": False}
        response = requests.post(self.__Server + "/api/queryChronicBrainSense", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestChronicLFP(PatientID)
            else:
                raise Exception(f"Network Error: {response.status_code}")
        
    def RequestPatientEvents(self, PatientID):
        form = {"id": PatientID}
        response = requests.post(self.__Server + "/api/queryPatientEvents", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestPatientEvents(PatientID)
            else:
                raise Exception(f"Network Error: {response.status_code}")
        
    def RequestPredictionModelOverview(self, PatientID):
        form = {"id": PatientID, "requestOverview": True}
        response = requests.post(self.__Server + "/api/queryPredictionModel", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestPatientEvents(PatientID)
            else:
                raise Exception(f"Network Error: {response.status_code}")
        
    def RequestPredictionModel(self, PatientID, RecordingID):
        form = {"id": PatientID, "recordingId": RecordingID, "updatePredictionModels": True}
        response = requests.post(self.__Server + "/api/queryPredictionModel", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            elif response.status_code == 401:
                self.refreshAuthToken()
                return self.RequestPatientEvents(PatientID)
            raise Exception(f"Network Error: {response.status_code}")
