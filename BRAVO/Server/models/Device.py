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

from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser
import json
import datetime

from modules.HelperFunctions import current_time, get_token, uuid4_hex, PKCE_code_verifier

def matchDevice(device, leads):
    if not device.electrodes.count() == len(leads):
        return False 

    for lead in leads:
        lead_exist = False
        for electrode in device.electrodes.all():
            if electrode.type == lead["type"]:
                if electrode.target == lead["name"]:
                    lead_exist = True
        
        if not lead_exist:
            return False
    
    return True

class DBSDevice(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, unique=True, primary_key=True)
    name = models.CharField(max_length=128, default="")
    type = models.CharField(max_length=128, default="")
    owner = models.ForeignKey('Participant', models.CASCADE)

    serial_number = models.CharField(max_length=256, default="")
    implanted_location = models.CharField(max_length=128, default="")
    implanted_date = models.FloatField(default=0)
    estimated_eol = models.FloatField(default=0)
    device_bloodline = models.CharField(max_length=128, default="")
    electrodes = models.ManyToManyField("Electrode", related_name="has_dbs_electrode")

    def get_name(self):
        if len(self.name) > 0:
            return self.name
        return self.device_bloodline if len(self.device_bloodline) > 0 else self.serial_number

    def include(*args, **kwargs):
        return DBSDevice.objects.select_related("owner").filter(**kwargs).exists()

    def find(*args, **kwargs):
        return DBSDevice.objects.select_related("owner").filter(**kwargs).first()

    def find_all(*args, **kwargs):
        return DBSDevice.objects.select_related("owner").filter(**kwargs).all()

    def create(serial_number, type):
        device = DBSDevice(serial_number=serial_number, type=type)
        return device
    
    def find_or_create(serial_number, leads, type, institute):
        devices = DBSDevice.objects.select_related("owner").filter(serial_number=serial_number, type=type, owner__institute__pk=institute).all()
        if len(devices) > 0:
            for device in devices:
                if matchDevice(device, leads):
                    return device, False
        
        device = DBSDevice(serial_number=serial_number, type=type)
        return device, True
    
    def get_info(self):
        return {
            "Id": self.uid,
            "Name": self.name if self.name else self.device_bloodline,
            "GenericName": self.get_name(),
            "Type": self.type,
            "Location": self.implanted_location,
            "Date": self.implanted_date,
            "Heritage": self.device_bloodline,
            "Electrodes": [i.get_info() for i in self.electrodes.all()]
        }

class MERDevice(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, unique=True, primary_key=True)
    name = models.CharField(max_length=128, default="")
    type = models.CharField(max_length=128, default="")
    owner = models.ForeignKey('Participant', models.CASCADE)

    electrodes = models.ManyToManyField("Electrode", related_name="has_mer_electrode")

    def include(*args, **kwargs):
        return MERDevice.objects.select_related("owner").filter(**kwargs).exists()

    def find(*args, **kwargs):
        return MERDevice.objects.select_related("owner").filter(**kwargs).first()

    def find_all(*args, **kwargs):
        return MERDevice.objects.select_related("owner").filter(**kwargs).all()

class GoogleHealth(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, unique=True, primary_key=True)
    name = models.CharField(max_length=128, default="")
    type = models.CharField(max_length=128, default="")
    owner = models.ForeignKey('Participant', models.CASCADE)

    auth = models.JSONField(default=dict)
    date_periods = models.JSONField(default=list)

    def include(*args, **kwargs):
        return GoogleHealth.objects.select_related("owner").filter(**kwargs).exists()

    def find(*args, **kwargs):
        return GoogleHealth.objects.select_related("owner").filter(**kwargs).first()

    def find_all(*args, **kwargs):
        return GoogleHealth.objects.select_related("owner").filter(**kwargs).all()

    def create(owner):
        device = GoogleHealth(owner=owner)
        device.save()
        return device

class FitbitDevice(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, unique=True, primary_key=True)
    name = models.CharField(max_length=128, default="")
    type = models.CharField(max_length=128, default="")
    owner = models.ForeignKey('Participant', models.CASCADE)

    pkce = models.CharField(max_length=128, default=PKCE_code_verifier)
    auth = models.JSONField(default=dict)

    date_periods = models.JSONField(default=list)

    def include(*args, **kwargs):
        return FitbitDevice.objects.select_related("owner").filter(**kwargs).exists()

    def find(*args, **kwargs):
        return FitbitDevice.objects.select_related("owner").filter(**kwargs).first()

    def find_all(*args, **kwargs):
        return FitbitDevice.objects.select_related("owner").filter(**kwargs).all()

    def create(owner):
        device = FitbitDevice(owner=owner)
        device.save()
        return device

class OuraRingDevice(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, unique=True, primary_key=True)
    name = models.CharField(max_length=128, default="")
    type = models.CharField(max_length=128, default="")
    owner = models.ForeignKey('Participant', models.CASCADE)

    pkce = models.CharField(max_length=128, default=PKCE_code_verifier)
    auth = models.JSONField(default=dict)

    date_periods = models.JSONField(default=list)

    def include(*args, **kwargs):
        return OuraRingDevice.objects.select_related("owner").filter(**kwargs).exists()

    def find(*args, **kwargs):
        return OuraRingDevice.objects.select_related("owner").filter(**kwargs).first()

    def find_all(*args, **kwargs):
        return OuraRingDevice.objects.select_related("owner").filter(**kwargs).all()

    def create(owner):
        device = OuraRingDevice(owner=owner)
        device.save()
        return device

class Electrode(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, unique=True, primary_key=True)
    type = models.CharField(max_length=128, default="")
    name = models.CharField(max_length=128, default="")
    hemisphere = models.CharField(max_length=128, default="")
    target = models.CharField(max_length=128, default="")
    custom_name = models.CharField(max_length=128, default="")
    owner = models.ForeignKey('Participant', models.CASCADE)

    channel_count = models.IntegerField(default=4)
    channel_names = models.JSONField(default=list)
    channel_mapping = models.CharField(max_length=512, default="") #This should be a path to the mapping file, if available
    channel_coordinates = models.JSONField(default=list) # It is in reality XYZ coordinates or trajectory, but will be encoded into String for simplicity
    implanted_date = models.FloatField(default=0)

    def include(*args, **kwargs):
        return Electrode.objects.select_related("owner").filter(**kwargs).exists()

    def find(*args, **kwargs):
        return Electrode.objects.select_related("owner").filter(**kwargs).first()

    def find_all(*args, **kwargs):
        return Electrode.objects.select_related("owner").filter(**kwargs).all()

    def find_or_create(owner, type, target):
        electrode = Electrode.objects.filter(owner=owner, type=type, target=target).first()
        if electrode:
            return electrode, False
        
        electrode = Electrode(owner=owner, type=type, target=target)
        return electrode, True
    
    def get_info(self):
        return {
            "Id": self.uid,
            "Name": self.name,
            "Type": self.type,
            "Hemisphere": self.hemisphere,
            "Target": self.target,
            "CustomName": self.custom_name,
            "Date": self.implanted_date,
            "ChannelNames": self.channel_names
        }
