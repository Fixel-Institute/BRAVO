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

from neomodel import StructuredNode, StringProperty, FloatProperty, JSONProperty, Relationship, RelationshipTo, RelationshipFrom, db
from .HelperFunctions import encryptMessage, decryptMessage

class Participant(StructuredNode):
    uid = StringProperty(default=uuid4)
    type = StringProperty(default="Participant")
    name = StringProperty(max_length=512)
    date_of_birth = FloatProperty()
    sex = StringProperty()
    
    diagnosis = StringProperty()
    disease_start_time = FloatProperty()
    
    studies = RelationshipFrom("Study", "HAS_PARTICIPANT")
    tags = RelationshipTo("Tag", "HAS_TAG")
    experiments = RelationshipTo("Experiment", "HAS_EXPERIMENT")

    def setName(self, name):
        self.name = encryptMessage(name)
        
    def getName(self):
        return decryptMessage(self.name)
    
    def getDevices(self, device_uid=None):
        devices = []
        for experiment in self.experiments:
            for source_file in experiment.source_files:
                if len(source_file.device) > 0:
                    device = source_file.device.get()
                    if device.uid == device_uid or not device_uid:
                        devices.append(device)
        return devices
    
    def purge(self):
        for experiment in self.experiments:
            for source_file in experiment.source_files:
                source_file.purge()
            experiment.delete()
        self.delete()
    
class Tag(StructuredNode):
    name = StringProperty()
    participants = RelationshipFrom("Participant", "HAS_TAG")

class Study(StructuredNode):
    uid = StringProperty(default=uuid4)
    name = StringProperty()
    participants = RelationshipTo("Participant", "HAS_PARTICIPANT")

    # User.py
    managers = Relationship(".User.PlatformUser", "MANAGED_BY")

    def checkPermission(self, user_id):
        approved_managers = [manager.user_id for manager in self.managers]
        return user_id in approved_managers

class Experiment(StructuredNode):
    uid = StringProperty(default=uuid4)
    name = StringProperty()
    type = StringProperty()

    metadata = JSONProperty()

    # SourceFile.py
    source_files = RelationshipTo(".SourceFile.SourceFile", "HAS_SOURCE_FILE")
    
    # User.py
    participant = RelationshipFrom("Participant", "HAS_EXPERIMENT")

    # Recording.py
    analyses = Relationship(".Recording.CombinedAnalysis", "HAS_ANALYSIS")
    