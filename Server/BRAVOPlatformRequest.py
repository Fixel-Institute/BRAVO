
import requests
import json
import os
import pickle as pkl
import datetime

class BRAVOPlatformRequest:
    def __init__(self, api_key, server="http://localhost"):
        self.__Server = server
        self.__request = requests.Session()
        self.__API_Key = api_key
    
        self.__ActiveStudy = None
        self.__ActiveParticipant = None
        self.__ActiveEvent = None

        self.DatabaseOverview = None

    def query(self, url, data=None, files=None, content_type="application/json"):
        if not content_type:
            Headers = {"X-Secure-API-Key": self.__API_Key}
        else:
            Headers = {"Content-Type": content_type, "X-Secure-API-Key": self.__API_Key}

        if data:
            return self.__request.post(self.__Server + url,
                                       json.dumps(data) if content_type else data,
                                       headers=Headers)
        elif files:
            return self.__request.post(self.__Server + url,
                                       files=files,
                                       headers=Headers)
        else:
            return self.__request.post(self.__Server + url,
                                       headers=Headers)
    
    def QueryStudyParticipants(self):
        response = self.query("/api/queryStudyParticipant")
        if response.status_code == 200:
            payload = response.json()
            self.DatabaseOverview = payload
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")
    
    def SetActiveStudy(self, name):
        for study in self.DatabaseOverview["studies"]:
            if study["name"] == name:
                self.__ActiveStudy = study["uid"]
                self.__ActiveEvent = None
                return study

    def SetActiveParticipant(self, name):
        for participant in self.DatabaseOverview["participants"][self.__ActiveStudy]:
            if participant["name"] == name:
                self.__ActiveParticipant = participant["uid"]
                self.__ActiveEvent = None
                return participant
    
    def GetParticipantInfo(self):
        response = self.query("/api/queryParticipantInformation", { "participant_uid": self.__ActiveParticipant })
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def CreateStudyParticipant(self, study, name, dob=None, sex=None, diagnosis=None, disease_start_time=None):
        data = {"name": name, "study": study, "dob": dob, "sex": sex, 
                "diagnosis": diagnosis, "disease_start_time": disease_start_time}
        
        response = self.query("/api/createStudyParticipant", data)
        if response.status_code == 200:
            payload = response.json()
            self.__ActiveParticipant = payload["uid"]
            self.__ActiveStudy = payload["study"]
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")
    
    def SetActiveEvent(self, uid):
        self.__ActiveEvent = uid
    
    def CreateParticipantEvent(self, event_name, event_type, date=None):
        data = {"participant_uid": self.__ActiveParticipant, "study": self.__ActiveStudy, "event_name": event_name, "event_type": event_type}
        if date:
            data["date"] = date
        
        response = self.query("/api/createParticipantEvent", data)
        if response.status_code == 200:
            payload = response.json()
            self.__ActiveEvent = payload["event_uid"]
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")
    
    def UploadData(self, data_type, files, metadata):
        form = {"study": (None, self.__ActiveStudy), 
                "participant": (None, self.__ActiveParticipant), 
                "data_type": (None, data_type), 
                "metadata": (None, json.dumps(metadata))}
        
        if type(files) == list:
            for i in range(len(files)):
                form["file" + str(i)] = files[i]
        else:
            form["file"] = files

        if self.__ActiveEvent:
            form["event"] = (None, self.__ActiveEvent)
        
        response = self.query("/api/uploadData", files=form)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")
            
    def RetrieveDataList(self, event=None):
        data = {"participant": self.__ActiveParticipant, "study": self.__ActiveStudy, "event": event if event else self.__ActiveEvent}
        response = self.query("/api/retrieveDataList", data)
        if response.status_code == 200:
            payload = response.json()
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")

    def RetrieveData(self, recording_uid):
        data = {"participant": self.__ActiveParticipant, "study": self.__ActiveStudy, "recording_uid": recording_uid}
        response = self.query("/api/retrieveData", data)
        if response.status_code == 200:
            payload = response
            return payload
        else:
            if response.status_code == 400:
                raise Exception(f"Network Error: {response.json()}")
            else:
                raise Exception(f"Network Error: {response.status_code}")
