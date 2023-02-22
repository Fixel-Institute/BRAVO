#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
@author: Jackson Cagle, University of Florida, ©2021
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
        
        form = {"Email": username, "Password": password}
        headers = {"Content-Type": "application/json"}
        response = requests.post(self.__Server + "/api/authenticate", json.dumps(form), headers=headers)
        if response.status_code == 200:
            payload = response.json()
            self.__Headers = {"Content-Type": "application/json", "Authorization": f"Token {payload['token']}"} 
        else:
            print(response.content)
            raise Exception(f"Network Error: {response.status_code}")
    
    def RequestPatientList(self):
        response = requests.post(self.__Server + "/api/queryPatients", headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            raise Exception(f"Network Error: {response.status_code}")
            
    def RequestPatientInfo(self, PatientID):
        form = {"id": PatientID}
        response = requests.post(self.__Server + "/api/queryPatientInfo", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            raise Exception(f"Network Error: {response.status_code}")
            
    def RequestImpedanceMeasurement(self, PatientID):
        # Not Implemented in V2.0
        return 
            
    def RequestBrainSenseSurveys(self, PatientID):
        form = {"id": PatientID}
        response = requests.post(self.__Server + "/api/queryBrainSenseSurveys", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            raise Exception(f"Network Error: {response.status_code}")
        
    def RequestBrainSenseStreamList(self, PatientID):
        form = {"id": PatientID, "requestOverview": True}
        response = requests.post(self.__Server + "/api/queryBrainSenseStreaming", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            raise Exception(f"Network Error: {response.status_code}")
        
    def RequestBrainSenseStream(self, PatientID, RecordingID):
        form = {"id": PatientID, "recordingId": RecordingID, "requestData": True}
        response = requests.post(self.__Server + "/api/queryBrainSenseStreaming", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            raise Exception(f"Network Error: {response.status_code}")
        
    def RequestIndefiniteStreamList(self, PatientID):
        form = {"id": PatientID, "requestOverview": True}
        response = requests.post(self.__Server + "/api/queryIndefiniteStreaming", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            raise Exception(f"Network Error: {response.status_code}")
        
    def RequestIndefiniteStream(self, PatientID, Timestamps, Devices):
        form = {"id": PatientID, "timestamps": Timestamps, "devices": Devices, "requestData": True}
        response = requests.post(self.__Server + "/api/queryIndefiniteStreaming", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
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
        else:
            raise Exception(f"Network Error: {response.status_code}")
    
    def RequestChronicLFP(self, PatientID):
        form = {"id": PatientID, "requestData": True, "timezoneOffset": 3600*5}
        response = requests.post(self.__Server + "/api/queryChronicBrainSense", json.dumps(form), headers=self.__Headers)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            raise Exception(f"Network Error: {response.status_code}")
        
    def RequestPredictionModelOverview(self, PatientID):
        # TODO 
        return 
        
    def RequestPredictionModel(self, PatientID, Timestamp, ChannelID):
        # TODO 
        return 
