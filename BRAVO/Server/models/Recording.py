""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under Open Source GPL-3.0 License

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
SQL Table Definitions
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os
from django.db import models
from django.db.models.signals import pre_delete
from django.dispatch import receiver
import json
import datetime

from modules.Database import deleteSourceFile
from modules.HelperFunctions import current_time, get_or_none, uuid4_hex

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class Recording(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, unique=True, primary_key=True)
    name = models.CharField(max_length=128, default="")
    type = models.CharField(max_length=128, default="")
    date = models.FloatField(default=current_time)
    adjusted_alignment = models.FloatField(default=0)
    fs_scaling_factor = models.FloatField(default=1)
    
    pointer = models.CharField(max_length=1024, default="")
    hashed = models.CharField(max_length=64, default="")
    metadata = models.JSONField(default=dict)
    
    source = models.ForeignKey('SourceFile', models.CASCADE)
    original = models.ForeignKey('Recording', models.CASCADE, null=True)

    def create(recording, type):
        return Recording(name=recording.name, type=type, date=current_time(), source=recording.source, original=recording)

    def include(*args, **kwargs):
        return Recording.objects.select_related("source").filter(**kwargs).exists()

    def find(*args, **kwargs):
        return Recording.objects.select_related("source").filter(**kwargs).first()

    def find_all(*args, **kwargs):
        return Recording.objects.select_related("source").filter(**kwargs).all()

    def get_info(self):
        return {
            "Id": self.uid,
            "SourceId": self.source.uid,
            "Name": self.name,
            "Type": self.type,
            "Date": self.date,
            "Alignment": self.adjusted_alignment,
            "SamplingRateScaling": self.fs_scaling_factor,
            "Metadata": self.metadata,
            "Device": self.source.metadata["Device"] if "Device" in self.source.metadata.keys() else "",
            "Timezone": self.source.metadata["Timezone"] if "Timezone" in self.source.metadata.keys() else "",
        }

class RecordingRel(models.Model):
    analysis = models.ForeignKey("Analysis", on_delete=models.CASCADE)
    recording = models.ForeignKey("Recording", on_delete=models.CASCADE)
    time_shift = models.FloatField(default=0)
    data_type = models.CharField(max_length=128, default="")

    def find(*args, **kwargs):
        return RecordingRel.objects.prefetch_related("analysis", "analysis").filter(**kwargs).first()

    def get_info(self):
        return {
            "Analysis": self.analysis.uid,
            "Recording": self.recording.uid,
            "TimeShift": self.time_shift,
            "DataType": self.data_type
        }
    
class Analysis(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, unique=True, primary_key=True)
    name = models.CharField(max_length=128, default="")
    type = models.CharField(max_length=128, default="")
    date = models.FloatField(default=current_time)
    
    metadata = models.JSONField(default=dict)

    recordings = models.ManyToManyField("Recording", through="RecordingRel")

    def create(*args, **kwargs):
        analysis = Analysis.objects.create(**kwargs)
        analysis.save()
        return analysis

    def include(*args, **kwargs):
        return Analysis.objects.prefetch_related("recordings").filter(**kwargs).exists()

    def find(*args, **kwargs):
        return Analysis.objects.prefetch_related("recordings").filter(**kwargs).first()

    def find_all(*args, **kwargs):
        return Analysis.objects.prefetch_related("recordings").filter(**kwargs).all()

    def add_recording(self, recording):
        self.recordings.add(recording)

    def get_info(self):
        rels = [rel.get_info() for rel in RecordingRel.objects.prefetch_related("analysis", "recording").filter(analysis=self).all()]
        if len(rels) == 0 and not self.type == "CustomizedAnalysis":
            self.delete()
            return None
        
        return {
            "Id": self.uid,
            "Name": self.name,
            "Type": self.type,
            "Date": self.date,
            "Metadata": self.metadata,
            "DataId": [rel["Recording"] for rel in rels],
            "DataShift": [rel["TimeShift"] for rel in rels],
            "DataType": [rel["DataType"] for rel in rels]
        }


@receiver(pre_delete, sender=Recording)
def on_recording_delete(sender, instance, **kwargs):
    if len(instance.pointer) > 0:
        get_or_none(deleteSourceFile)(instance.pointer)
        get_or_none(os.remove)(instance.pointer + ".lock")
        
        