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

from modules.HelperFunctions import current_time, get_token, get_or_none, uuid4_hex

class Therapy(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, primary_key=True)
    name = models.CharField(max_length=128, default="")
    type = models.CharField(max_length=128, default="")

    date = models.FloatField(default=current_time)
    source = models.ForeignKey("SourceFile", models.CASCADE)

    def include(*args, **kwargs):
        return Therapy.objects.select_related("source").filter(**kwargs).exists()
    
    def find_all(*args, **kwargs):
        return Therapy.objects.select_related("source").filter(**kwargs).order_by("date").all()
    
    def get_info(self):
        if self.type in ["Pre-visit Therapy", "Post-visit Therapy"]:
            Therapy = ElectricalTherapy.find(therapy=self)
        else:
            Therapy = None
        
        if Therapy:
            return Therapy.get_info()

    def purge(self):
        self.delete()

class Medication(models.Model):
    therapy = models.ForeignKey("Therapy", models.CASCADE)

    medication = models.CharField(max_length=128, default="")
    dosage = models.FloatField(default=0)
    dosage_unit = models.CharField(max_length=128, default="")
    frequency = models.CharField(max_length=128, default="")

class ElectricalTherapy(models.Model):
    therapy = models.ForeignKey("Therapy", models.CASCADE)

    group_type = models.CharField(max_length=128, default="")
    group_name = models.CharField(max_length=128, default="")
    group_id = models.CharField(max_length=128, default="")
    stimulation_type = models.CharField(max_length=128, default="")
    label = models.CharField(max_length=128, default="")
    
    stimulation_settings = models.ManyToManyField("ElectricalStimulation", related_name="has_setting")
    adaptive_settings = models.ManyToManyField("AdaptiveTherapy", related_name="has_adaptive")

    def include(*args, **kwargs):
        return ElectricalTherapy.objects.select_related("therapy").filter(**kwargs).prefetch_related("stimulation_settings", "adaptive_settings").exists()
    
    def find(*args, **kwargs):
        return ElectricalTherapy.objects.select_related("therapy").filter(**kwargs).prefetch_related("stimulation_settings", "adaptive_settings").first()
    
    def find_all(*args, **kwargs):
        return ElectricalTherapy.objects.select_related("therapy").filter(**kwargs).prefetch_related("stimulation_settings", "adaptive_settings").all()
    
    def get_info(self):
        return {
            "Id": self.therapy.uid,
            "SourceId": self.therapy.source.uid,
            "Name": self.therapy.name,
            "Type": self.therapy.type,
            "Date": self.therapy.date,
            "Label": self.label,
            "Timezone": self.therapy.source.metadata["Timezone"],
            "GroupId": self.group_id,
            "GroupName": self.group_name,
            "GroupType": self.group_type,
            "StimulationType": self.stimulation_type,
            "StimulationSettings": [i.get_info() for i in self.stimulation_settings.all()],
            "AdaptiveSettings": [i.get_info() for i in self.adaptive_settings.all()] 
        }

class ElectricalStimulation(models.Model):
    group = models.ForeignKey("ElectricalTherapy", models.CASCADE)

    electrode = models.ForeignKey("Electrode", models.CASCADE)
    contact = models.JSONField(default=list)
    return_contact = models.JSONField(default=list)
    amplitude = models.FloatField(default=0)
    amplitude_fraction = models.JSONField(default=list)
    amplitude_unit = models.CharField(max_length=128, default="mA")
    pulsewidth = models.FloatField(default=90)
    pulsewidth_unit = models.CharField(max_length=128, default="uS")
    frequency = models.FloatField(default=125)
    cycling = models.FloatField(default=1)
    cycling_period = models.FloatField(default=0)

    #waveform = StringProperty() # This needs to be implemented as a method later, typical options being passive or active, cathode/anode etc.

    def get_info(self):
        Electrode = self.electrode.get_info()

        Info = {
            "StimulationType": self.group.stimulation_type,
            "Electrode": Electrode,
            "Contact": self.contact,
            "ReturnContact": self.return_contact,
            "Amplitude": self.amplitude,
            "FractionalAmplitudes": self.amplitude_fraction,
            "AmplitudeUnit": self.amplitude_unit,
            "Pulsewidth": self.pulsewidth,
            "PulsewidthUnit": self.pulsewidth_unit,
            "Frequency": self.frequency,
            "Cycling": self.cycling,
            "CyclingPeriod": self.cycling_period
        }

        ValidContactName = True
        for i in self.contact:
            if i >= len(Electrode["ChannelNames"]):
                ValidContactName = False

        if ValidContactName:
            Info["Contact"] = [Electrode["ChannelNames"][i] for i in self.contact]
            
        ValidContactName = True
        for i in self.return_contact:
            if i >= len(Electrode["ChannelNames"]):
                ValidContactName = False

        if ValidContactName:
            Info["ReturnContact"] = [Electrode["ChannelNames"][i] if i >= 0 else "CAN" for i in self.return_contact]
            
        return Info
    
class AdaptiveTherapy(models.Model):
    group = models.ForeignKey("ElectricalTherapy", models.CASCADE)

    sensing_type = models.CharField(max_length=128, default="Unknown")
    sensing = models.JSONField(default=dict)
    adaptive_type = models.CharField(max_length=128, default="Unknown")
    adaptive = models.JSONField(default=dict)

    def get_info(self):
        return {
            "RecordingConfiguration": {
                "Type": self.sensing_type,
                "Config": self.sensing
            },
            "StimulationConfiguration": {
                "Type": self.adaptive_type,
                "Config": self.adaptive
            }
        }