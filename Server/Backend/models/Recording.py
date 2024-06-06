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
Recording Model
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import datetime, pytz
from uuid import uuid4
import json

from neomodel import StructuredNode, StringProperty, FloatProperty, JSONProperty, ArrayProperty, Relationship, StructuredRel
from modules import Database

class Visit(StructuredNode):
    date = FloatProperty()
    name = StringProperty()

    recordings = Relationship("Recording", "CONTAIN_RECORDING")

    def purge(self):
        for recording in self.recordings:
            recording.purge()
        self.delete()

class Annotation(StructuredNode):
    date = FloatProperty()
    name = StringProperty()
    duration = FloatProperty()

class Recording(StructuredNode):
    uid = StringProperty(unique_index=True, default=uuid4)
    type = StringProperty(max_length=128)
    date = FloatProperty()
    data_pointer = StringProperty()
    devices = Relationship(".Device.BaseDevice", "RECORDED_WITH")
    labels = ArrayProperty(StringProperty())
    
    annotations = Relationship("Annotation", "HAS_ANNOTATION")

    def purge(self):
        Database.deleteSourceDataPointer(self.data_pointer)
        self.delete()

class TimeSeriesRecording(Recording):
    channel_names = ArrayProperty(StringProperty())
    sampling_rate = FloatProperty()
    duration = FloatProperty()

class InMemoryRecording(Recording):
    in_memory_storage = JSONProperty()

    def purge(self):
        self.delete()

class ImagingRecording(Recording):
    image_modality = StringProperty()

class RecordingRel(StructuredRel):
    time_shift = FloatProperty(default=0)
    data_type = ArrayProperty(StringProperty())
    
class CombinedAnalysis(StructuredNode):
    uid = StringProperty(unique_index=True, default=uuid4)
    type = StringProperty()
    date = FloatProperty()
    name = StringProperty()
    status = StringProperty()

    recordings = Relationship("Recording", "FOR_RECORDING", model=RecordingRel)

    def purge(self):
        self.delete()