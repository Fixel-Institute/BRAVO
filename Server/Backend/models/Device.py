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
Device Models (Recording Systems)
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from uuid import uuid4

from neomodel import StructuredNode, StringProperty, ArrayProperty, FloatProperty, IntegerProperty, Relationship
from .HelperFunctions import encryptMessage, decryptMessage

class BaseDevice(StructuredNode):
    uid = StringProperty(unique_index=True, default=uuid4)
    name = StringProperty(max_length=512)
    type = StringProperty(max_length=128)

    electrodes = Relationship("Electrode", "CONNECTED_ELECTRODE")
    recordings = Relationship(".Recording.Recording", "DATA_RECORDED")
    source_files = Relationship(".SourceFile.SourceFile", "HAS_SOURCEFILE")

    def setDeviceName(self, name):
        self.name = encryptMessage(name)

    def getDeviceName(self):
        return decryptMessage(self.name)
    
    def purge(self):
        for electrode in self.electrodes:
            electrode.purge()
        for recording in self.recordings:
            recording.purge()
        for file in self.source_files:
            file.purge()
        self.delete()

class DBSDevice(BaseDevice):
    implanted_location = StringProperty()
    implanted_date = FloatProperty()
    estimated_eol = FloatProperty()

    device_bloodline = StringProperty()

class Electrode(StructuredNode):
    type = StringProperty()
    name = StringProperty()
    channel_count = IntegerProperty()
    channel_names = ArrayProperty(StringProperty())
    channel_mapping = StringProperty() #This should be a path to the mapping file, if available
    channel_coordinates = ArrayProperty(StringProperty()) # It is in reality XYZ coordinates or trajectory, but will be encoded into String for simplicity
    implanted_date = FloatProperty()

    def purge(self):
        self.delete()

class DBSElectrode(Electrode):
    custom_name = StringProperty()