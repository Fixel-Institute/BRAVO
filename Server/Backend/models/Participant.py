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
Participant Model
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from uuid import uuid4
import datetime, pytz

from neomodel import StructuredNode, StringProperty, FloatProperty, Relationship, db
from .HelperFunctions import encryptMessage, decryptMessage

class Participant(StructuredNode):
    uid = StringProperty(unique_index=True, default=uuid4)
    name = StringProperty(max_length=512)
    date_of_birth = FloatProperty()
    sex = StringProperty()
    
    studies = Relationship("Study", "OF_STUDY")
    tags = Relationship("Tag", "HAS_TAG")

    therapies = Relationship(".Therapy.Therapy", "HAS_THERAPY")
    events = Relationship(".Event.BaseEvent", "HAS_EVENT")
    devices = Relationship(".Device.BaseDevice", "HAS_DEVICE")
    visits = Relationship(".Recording.Visit", "HAS_VISIT")
    analyses = Relationship(".Recording.CombinedAnalysis", "HAS_ANALYSIS")

    def setName(self, name):
        self.name = encryptMessage(name)

    def getName(self):
        return decryptMessage(self.name)

    def setDateOfBirth(self, dob):
        self.date_of_birth = dob
    
    def getDateOfBirth(self):
        return datetime.datetime.fromtimestamp(self.date_of_birth, tz=pytz.utc)
    
    def retrieveRecording(self, recording_uid):
        uid = f"'{self.uid}'"
        results, _ = db.cypher_query(f"MATCH (a:SourceFile {{uid: '{recording_uid}'}})-[:UPLOADED_FOR]->(:Participant {{uid: {uid}}}) RETURN a", resolve_objects=True)
        return [row[0] for row in results]

    def purge(self):
        for therapy in self.therapies:
            therapy.purge()
        for event in self.events:
            event.purge()
        for visit in self.visits:
            visit.purge()
        for device in self.devices:
            device.purge()
        for analysis in self.analyses:
            analysis.purge()
        self.delete()
    
class Patient(Participant):
    diagnosis = StringProperty()
    disease_start_time = FloatProperty()

    def setDiseaseStartTime(self, start_time):
        self.date_of_birth = start_time
    
    def getDiseaseStartTime(self):
        return datetime.datetime.fromtimestamp(self.disease_start_time, tz=pytz.utc)

class Tag(StructuredNode):
    name = StringProperty()
    participants = Relationship("Participant", "OF_PARTICIPANT")

class Study(StructuredNode):
    uid = StringProperty(unique_index=True, default=uuid4)
    name = StringProperty()
    managers = Relationship(".User.PlatformUser", "MANAGE_BY")
    participants = Relationship("Participant", "HAS_PARTICIPANT")

    def checkPermission(self, user_id):
        approved_managers = [manager.user_id for manager in self.managers]
        return user_id in approved_managers
