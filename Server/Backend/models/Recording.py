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

import datetime, pytz, os
from uuid import uuid4
import json

from neomodel import StructuredNode, StructuredRel, StringProperty, FloatProperty, JSONProperty, ArrayProperty, Relationship, RelationshipTo, RelationshipFrom, StructuredRel
from modules import Database

class Annotation(StructuredNode):
    date = FloatProperty()
    name = StringProperty()
    duration = FloatProperty()

class Processed(StructuredRel):
    type = StringProperty(default="Analysis")
    metadata = JSONProperty()
    version = StringProperty(default="Version.1")

class Recording(StructuredNode):
    uid = StringProperty(default=uuid4)
    type = StringProperty(max_length=128)
    date = FloatProperty()
    data_pointer = StringProperty()
    hashed = StringProperty()
    
    labels = ArrayProperty(StringProperty())
    
    source_file = RelationshipFrom(".SourceFile.SourceFile", "SOURCE_OF_RECORDING")
    processed = Relationship("Recording","HAS_PROCESSED_DATA", model=Processed)

    def purge(self):
        if self.data_pointer:
            try: 
                os.remove(DATABASE_PATH + "recordings" + os.path.sep + self.data_pointer)
            except:
                pass
        
        for processed in self.processed:
            processed.purge()
        
        self.delete()

class TimeSeriesRecording(Recording):
    channel_names = ArrayProperty(StringProperty())
    sampling_rate = FloatProperty()
    duration = FloatProperty()

class TimeFrequencyAnalysis(TimeSeriesRecording):
    method = StringProperty(default="STFT")
    frequency_resolution = FloatProperty()
    frequency_range = ArrayProperty(FloatProperty())
    color_range = ArrayProperty(FloatProperty())
    
class InMemoryRecording(Recording):
    in_memory_storage = JSONProperty()

class ImagingRecording(Recording):
    image_modality = StringProperty()

class RecordingRel(StructuredRel):
    time_shift = FloatProperty(default=0)
    data_type = StringProperty()
    
class CombinedAnalysis(StructuredNode):
    uid = StringProperty(default=uuid4)
    type = StringProperty()
    date = FloatProperty()
    name = StringProperty()
    status = StringProperty()

    recordings = Relationship("Recording", "FOR_RECORDING", model=RecordingRel)
