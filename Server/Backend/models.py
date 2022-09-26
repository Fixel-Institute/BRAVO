from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, User
from django.utils import timezone
import uuid
import json
import datetime
from cryptography.fernet import Fernet

def PerceptRecordingDefaultAuthorization():
    nullDateTime = 0
    nowDateTime = datetime.datetime.utcnow().timestamp()
    Authorization = {
        "TherapyHistory": [nullDateTime, nowDateTime],
        "BrainSenseSurvey": [nullDateTime, nowDateTime],
        "BrainSenseStream": [nullDateTime, nowDateTime],
        "IndefiniteStream": [nullDateTime, nowDateTime],
        "ChronicLFPs": [nullDateTime, nowDateTime]
    }
    return Authorization

# Create your models here.
class PlatformUserManager(BaseUserManager):
    def create_user(self, email, user_name, institute, password=None):
        if not email:
            raise ValueError("Email must exist")
        user = self.model(email=self.normalize_email(email), user_name=user_name, institute=institute)
        user.set_password(password)
        user.save()
        return user

class PlatformUser(AbstractBaseUser):
    email = models.EmailField(verbose_name="Email Address", max_length=255, unique=True)
    user_name = models.CharField(max_length=512, default="")
    institute = models.CharField(max_length=255, default="Independent")
    unique_user_id = models.UUIDField(default=uuid.uuid1, unique=True, editable=False)

    register_date = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["user_name", "institute"]

    objects = PlatformUserManager()

    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_clinician = models.BooleanField(default=False)

    def __str__(self):
        return self.name + " (" + self.email + ")"
    
    def has_module_perms(self, app_label):
        return True

    def has_perm(self, perm, obj=None):
        return True

    @property
    def is_staff(self):
        return self.is_admin

class Institute(models.Model):
    name = models.CharField(default="", max_length=100, unique=True)

    def __str__(self):
        return self.name

class Patient(models.Model):
    first_name = models.CharField(default="", max_length=255)
    last_name = models.CharField(default="", max_length=255)
    diagnosis = models.CharField(default="", max_length=255)
    institute = models.CharField(default="", max_length=255)
    medical_record_number = models.CharField(default="", max_length=255)

    research_study_id = models.JSONField(default=list, null=True)
    patient_identifier_hashfield = models.CharField(default="", max_length=255)

    birth_date = models.DateTimeField(default=timezone.now)
    device_deidentified_id = models.JSONField(default=list, null=True)

    deidentified_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)

    def __str__(self):
        return str(self.deidentified_id)

    def getPatientFirstName(self, key):
        secureEncoder = Fernet(key)
        return secureEncoder.decrypt(self.first_name.encode("utf-8")).decode("utf-8")

    def setPatientFirstName(self, first_name, key):
        secureEncoder = Fernet(key)
        self.first_name = secureEncoder.encrypt(first_name.encode('utf_8')).decode("utf-8")

    def getPatientLastName(self, key):
        secureEncoder = Fernet(key)
        return secureEncoder.decrypt(self.last_name.encode("utf-8")).decode("utf-8")

    def setPatientLastName(self, last_name, key):
        secureEncoder = Fernet(key)
        self.last_name = secureEncoder.encrypt(last_name.encode('utf_8')).decode("utf-8")

    def getPatientMRN(self, key):
        secureEncoder = Fernet(key)
        return secureEncoder.decrypt(self.medical_record_number.encode("utf-8")).decode("utf-8")

    def setPatientMRN(self, mrn, key):
        secureEncoder = Fernet(key)
        self.medical_record_number = secureEncoder.encrypt(mrn.encode("utf-8")).decode("utf-8")

    def addDevice(self, deviceID):
        if not deviceID in self.device_deidentified_id:
            self.device_deidentified_id.append(deviceID)
            self.save()

    def removeDevice(self, deviceID):
        if deviceID in self.device_deidentified_id:
            self.device_deidentified_id.remove(deviceID)
            self.save()

class DeidentifiedPatientID(models.Model):
    researcher_id = models.UUIDField(default=uuid.uuid1)
    authorized_patient_id = models.UUIDField(default=uuid.uuid4)
    deidentified_id = models.UUIDField(default=uuid.uuid4)
    authorized_time_range = models.JSONField(default=PerceptRecordingDefaultAuthorization, null=True)

    def __str__(self):
        return str(self.study_id) + " " + str(self.deidentified_id) + " is accessible by " + str(self.researcher_id)

class ResearchAuthorizedAccess(models.Model):
    researcher_id = models.UUIDField(default=uuid.uuid1)
    authorized_patient_id = models.UUIDField(default=uuid.uuid4)
    authorized_recording_type = models.CharField(default="", max_length=255)
    authorized_recording_id = models.UUIDField(default=uuid.uuid4)
    can_edit = models.BooleanField(default=False)

    def __str__(self):
        return str(self.authorized_patient_id) + " is accessible by " + str(self.researcher_id)

class PerceptDevice(models.Model):
    serial_number = models.CharField(default="", max_length=512)
    device_name = models.CharField(default="", max_length=32)
    device_type = models.CharField(default="Percept PC", max_length=32)
    deidentified_id = models.UUIDField(default=uuid.uuid4, editable=False)
    patient_deidentified_id = models.UUIDField(default=uuid.uuid4)
    implant_date = models.DateTimeField(default=timezone.now)

    device_identifier_hashfield = models.CharField(default="", max_length=255)

    device_location = models.CharField(default="", max_length=32)
    device_lead_configurations = models.JSONField(default=list, null=True)
    device_last_seen = models.DateTimeField(default=timezone.now)
    device_eol_date = models.DateTimeField(default=timezone.now)

    authority_level = models.CharField(default="Research", max_length=32)
    authority_user = models.CharField(default="", max_length=255)

    def __str__(self):
        return str(self.deidentified_id)

    def getDeviceSerialNumber(self, key):
        try:
            secureEncoder = Fernet(key)
            serialNumber = secureEncoder.decrypt(self.serial_number.encode("utf-8")).decode("utf-8")
        except Exception as e:
            serialNumber = str(self.deidentified_id)
        
        return serialNumber

class PerceptSession(models.Model):
    deidentified_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    device_deidentified_id = models.UUIDField(default=uuid.uuid4)
    session_file_path = models.CharField(default="", max_length=256)
    session_source_filename = models.CharField(default="", max_length=256)

    def __str__(self):
        return str(self.deidentified_id)

class TherapyHistory(models.Model):
    history_log_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    device_deidentified_id = models.UUIDField(default=uuid.uuid4)

    therapy_date = models.DateTimeField(default=timezone.now)
    group_name = models.CharField(default="", max_length=32)
    group_id = models.CharField(default="", max_length=32)
    active_group = models.BooleanField(default=False)

    therapy_type = models.CharField(default="", max_length=64)
    therapy_details = models.JSONField(default=dict, null=True)

    source_file = models.CharField(default="", max_length=256)

    def __str__(self):
        return str(self.device_deidentified_id) + " " + str(self.therapy_date)

    def extractTherapy(self):
        return self.therapy_details

class PredictionModel(models.Model):
    recording_id = models.UUIDField(default=uuid.uuid4)
    recording_channel = models.CharField(default="", max_length=64)
    recording_contact_type = models.CharField(default="", max_length=64)
    model_details = models.JSONField(default=dict, null=True)

class TherapyChangeLog(models.Model):
    device_deidentified_id = models.UUIDField(default=uuid.uuid4)

    date_of_change = models.DateTimeField(default=timezone.now)
    previous_group = models.CharField(default="", max_length=32)
    new_group = models.CharField(default="", max_length=32)

    source_file = models.CharField(default="", max_length=256)

    def __str__(self):
        return str(self.device_deidentified_id) + " " + str(self.date_of_change)

class ChronicSensingLFP(models.Model):
    uniqueIdentificationKey = models.CharField(default="", max_length=128, unique=True)
    device_deidentified_id = models.UUIDField(default=uuid.uuid4)
    hemisphere = models.CharField(default="", max_length=32)

    timestamp = models.DateTimeField(default=timezone.now)
    amplitude = models.FloatField(default=0)
    power = models.FloatField(default=0)

    source_file = models.CharField(default="", max_length=256)

    class Meta:
        ordering = ['-timestamp']

class PatientCustomEvents(models.Model):
    deidentified_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    device_deidentified_id = models.UUIDField(default=uuid.uuid4)

    event_name = models.CharField(default="", max_length=32)
    event_time = models.DateTimeField(default=timezone.now)
    sensing_exist = models.BooleanField(default=False)
    brainsense_psd = models.JSONField(default=list, null=True)

    class Meta:
        ordering = ['-event_time']

class BrainSenseRecording(models.Model):
    recording_id = models.UUIDField(default=uuid.uuid4, unique=True)
    device_deidentified_id = models.UUIDField(default=uuid.uuid4)
    recording_type = models.CharField(default="", max_length=32)
    recording_date = models.DateTimeField(default=timezone.now)
    recording_info = models.JSONField(default=dict, null=True)
    recording_duration = models.FloatField(default=0)

    recording_datapointer = models.CharField(default="", max_length=256)

    source_file = models.CharField(default="", max_length=256)

    class Meta:
        ordering = ['recording_date']

    def __str__(self):
        return str(self.device_deidentified_id) + " " + self.recording_type + " " + str(self.recording_id)

class UserConfigurations(models.Model):
    user_id = models.UUIDField(default=uuid.uuid1, editable=False)
    configuration = models.JSONField(default=dict, null=True)

class ExternalRecording(models.Model):
    recording_id = models.UUIDField(default=uuid.uuid4, unique=True)
    patient_deidentified_id = models.UUIDField(default=uuid.uuid4)
    recording_type = models.CharField(default="", max_length=32)
    recording_date = models.DateTimeField(default=timezone.now)
    recording_duration = models.FloatField(default=0)

    recording_datapointer = models.CharField(default="", max_length=256)

    class Meta:
        ordering = ['recording_date']

    def __str__(self):
        return str(self.patient_deidentified_id) + " " + self.recording_type + " " + str(self.recording_id)

class ExternalSensorPairing(models.Model):
    patient_deidentified_id = models.UUIDField(default=uuid.uuid4)
    device_mac = models.CharField(default="", max_length=64)
    pairing_date = models.DateTimeField(default=timezone.now)
    pairing_code = models.CharField(default="", max_length=10)
    pairing_password = models.CharField(default="", max_length=64)
    paired = models.BooleanField(default=False)
