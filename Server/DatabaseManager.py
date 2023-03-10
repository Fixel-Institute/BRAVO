import os, sys
from datetime import datetime
import pytz

import uuid
import json

from BRAVO import asgi
from Backend import models
from modules.Percept import Sessions

from decoder import Percept

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

def processInput(argv):
  if len(argv) > 1:
    if argv[1] == "Clean":
      if argv[2] == "All":
        Patients = models.Patient.objects.all()
        for patient in Patients:
          for device_id in patient.device_deidentified_id:
            device = models.PerceptDevice.objects.filter(deidentified_id=device_id).first()
            Sessions.deleteDevice(device.deidentified_id)
            patient.removeDevice(device_id)
            device.delete()
          patient.delete()
        return True

    elif argv[1] == "MigrateFromV1":

      OLD_DATABASE_PATH = argv[2]

      import shutil
      from MySQLdb import _mysql
      connector = _mysql.connect(user='DjangoServer', password='AdminPassword',
                              host='localhost',
                              database='PerceptServer')
      
      # Platform User 
      connector.query("""
      SELECT * FROM PerceptDashboard_platformuser;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        user = models.PlatformUser(
          email=result[i]["email"].decode("utf-8"),
          user_name=result[i]["first_name"].decode("utf-8") + " " + result[i]["last_name"].decode("utf-8"),
          password=result[i]["password"].decode("utf-8"),
          institute=result[i]["institute"].decode("utf-8"),
          unique_user_id=uuid.UUID(result[i]["uniqueUserID"].decode("utf-8")),
          register_date=datetime.fromisoformat(result[i]["register_date"].decode("utf-8")).astimezone(tz=pytz.utc),
          is_active=result[i]["is_active"].decode("utf-8") == "1",
          is_admin=result[i]["is_admin"].decode("utf-8") == "1",
          is_clinician=result[i]["is_clinician"].decode("utf-8") == "1"
        )
        batchResult.append(user)
      models.PlatformUser.objects.bulk_create(batchResult)
      
      # Institute
      connector.query("""
      SELECT * FROM PerceptDashboard_institute;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        institute = models.Institute(
          name=result[i]["name"].decode("utf-8"),
        )
        batchResult.append(institute)
      models.Institute.objects.bulk_create(batchResult)
      
      # Patient
      connector.query("""
      SELECT * FROM PerceptDashboard_patient;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        patient = models.Patient(
          first_name=result[i]["first_name"].decode("utf-8"),
          last_name=result[i]["last_name"].decode("utf-8"),
          diagnosis=result[i]["diagnosis"].decode("utf-8"),
          institute=result[i]["institute"].decode("utf-8"),
          medical_record_number=result[i]["medical_record_number"].decode("utf-8"),
          research_study_id=json.loads(result[i]["research_study_id"].decode("utf-8")),
          patient_identifier_hashfield=result[i]["patient_identifier_hashfield"].decode("utf-8"),
          birth_date=datetime.fromisoformat(result[i]["birth_date"].decode("utf-8")).astimezone(tz=pytz.utc),
          device_deidentified_id=json.loads(result[i]["device_deidentified_id"].decode("utf-8")),
          deidentified_id=uuid.UUID(result[i]["deidentified_id"].decode("utf-8")),
        )
        batchResult.append(patient)
      models.Patient.objects.bulk_create(batchResult)
      
      # Deidentified Patient
      connector.query("""
      SELECT * FROM PerceptDashboard_deidentifiedpatientid;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        patient = models.DeidentifiedPatientID(
          researcher_id=uuid.UUID(result[i]["researcher_id"].decode("utf-8")),
          authorized_patient_id=uuid.UUID(result[i]["authorized_patient_id"].decode("utf-8")),
          deidentified_id=uuid.UUID(result[i]["deidentified_id"].decode("utf-8")),
          authorized_time_range=json.loads(result[i]["authorized_time_range"].decode("utf-8")),
        )
        batchResult.append(patient)
      models.DeidentifiedPatientID.objects.bulk_create(batchResult)
      
      # Research Authorized Access
      connector.query("""
      SELECT * FROM PerceptDashboard_researchauthorizedaccess;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        patient = models.ResearchAuthorizedAccess(
          researcher_id=uuid.UUID(result[i]["researcher_id"].decode("utf-8")),
          authorized_patient_id=uuid.UUID(result[i]["authorized_patient_id"].decode("utf-8")),
          authorized_recording_type=result[i]["authorized_recording_type"].decode("utf-8"),
          authorized_recording_id=uuid.UUID(result[i]["authorized_recording_id"].decode("utf-8")),
          can_edit=result[i]["can_edit"].decode("utf-8") == "1",
        )
        batchResult.append(patient)
      models.ResearchAuthorizedAccess.objects.bulk_create(batchResult)
      
      # Percept Device
      connector.query("""
      SELECT * FROM PerceptDashboard_perceptdevice;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        device = models.PerceptDevice(
          serial_number=result[i]["serial_number"].decode("utf-8"),
          device_name=result[i]["device_name"].decode("utf-8"),
          device_type=result[i]["device_type"].decode("utf-8"),
          deidentified_id=uuid.UUID(result[i]["deidentified_id"].decode("utf-8")),
          patient_deidentified_id=uuid.UUID(result[i]["patient_deidentified_id"].decode("utf-8")),
          implant_date=datetime.fromisoformat(result[i]["implant_date"].decode("utf-8")).astimezone(tz=pytz.utc),
          device_identifier_hashfield=result[i]["device_identifier_hashfield"].decode("utf-8"),
          device_location=result[i]["device_location"].decode("utf-8"),
          device_lead_configurations=json.loads(result[i]["device_lead_configurations"].decode("utf-8")),
          device_eol_date=datetime.fromisoformat(result[i]["device_eol_date"].decode("utf-8")).astimezone(tz=pytz.utc),
          device_last_seen=datetime.fromisoformat(result[i]["device_last_seen"].decode("utf-8")).astimezone(tz=pytz.utc),
          authority_level=result[i]["authority_level"].decode("utf-8"),
          authority_user=result[i]["authority_user"].decode("utf-8"),
        )
        batchResult.append(device)
      models.PerceptDevice.objects.bulk_create(batchResult)
      
      # Percept Session
      connector.query("""
      SELECT * FROM PerceptDashboard_perceptsession;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        oldPath = result[i]["session_file_path"].decode("utf-8")
        newPath = DATABASE_PATH + "sessions/" + oldPath.split("/")[-1]
        shutil.copyfile(oldPath, newPath)

        session = models.PerceptSession(
          deidentified_id=uuid.UUID(result[i]["deidentified_id"].decode("utf-8")),
          device_deidentified_id=uuid.UUID(result[i]["device_deidentified_id"].decode("utf-8")),
          session_file_path=newPath,
          session_source_filename=result[i]["session_source_filename"].decode("utf-8"),
        )
        batchResult.append(session)
      models.PerceptSession.objects.bulk_create(batchResult)
      
      # Therapy History
      connector.query("""
      SELECT * FROM PerceptDashboard_therapyhistory;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        history = models.TherapyHistory(
          history_log_id=uuid.UUID(result[i]["history_log_id"].decode("utf-8")),
          device_deidentified_id=uuid.UUID(result[i]["device_deidentified_id"].decode("utf-8")),
          therapy_date=datetime.fromisoformat(result[i]["therapy_date"].decode("utf-8")).astimezone(tz=pytz.utc),
          group_name=result[i]["group_name"].decode("utf-8"),
          group_id=result[i]["group_id"].decode("utf-8"),
          active_group=result[i]["active_group"].decode("utf-8") == "1",
          therapy_type=result[i]["therapy_type"].decode("utf-8"),
          therapy_details=json.loads(result[i]["therapy_details"].decode("utf-8")),
          source_file=result[i]["source_file"].decode("utf-8"),
        )
        batchResult.append(history)
      models.TherapyHistory.objects.bulk_create(batchResult)
      
      # Therapy Change Log
      connector.query("""
      SELECT * FROM PerceptDashboard_therapychangelog;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        history = models.TherapyChangeLog(
          device_deidentified_id=uuid.UUID(result[i]["device_deidentified_id"].decode("utf-8")),
          date_of_change=datetime.fromisoformat(result[i]["date_of_change"].decode("utf-8")).astimezone(tz=pytz.utc),
          previous_group=result[i]["previous_group"].decode("utf-8"),
          new_group=result[i]["new_group"].decode("utf-8"),
          source_file=result[i]["source_file"].decode("utf-8"),
        )
        batchResult.append(history)
      models.TherapyChangeLog.objects.bulk_create(batchResult)
      
      # Patient Custom Events
      connector.query("""
      SELECT * FROM PerceptDashboard_patientcustomevents;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        event = models.PatientCustomEvents(
          deidentified_id=uuid.UUID(result[i]["deidentified_id"].decode("utf-8")),
          device_deidentified_id=uuid.UUID(result[i]["device_deidentified_id"].decode("utf-8")),
          event_name=result[i]["event_name"].decode("utf-8"),
          event_time=datetime.fromisoformat(result[i]["event_time"].decode("utf-8")).astimezone(tz=pytz.utc),
          sensing_exist=result[i]["sensing_exist"].decode("utf-8") == "1",
          brainsense_psd=json.loads(result[i]["brainsense_psd"].decode("utf-8")),
        )
        batchResult.append(event)
      models.PatientCustomEvents.objects.bulk_create(batchResult)
      
      # BrainSense Recording
      connector.query("""
      SELECT * FROM PerceptDashboard_brainsenserecording;
      """)
      result = connector.store_result()
      result = result.fetch_row(maxrows=0, how=1)

      batchResult = []
      for i in range(len(result)):
        deviceId = uuid.UUID(result[i]["device_deidentified_id"].decode("utf-8"))
        recording = models.BrainSenseRecording(
          recording_id=uuid.UUID(result[i]["recording_id"].decode("utf-8")),
          device_deidentified_id=deviceId,
          recording_type=result[i]["recording_type"].decode("utf-8"),
          recording_date=datetime.fromisoformat(result[i]["recording_date"].decode("utf-8")).astimezone(tz=pytz.utc),
          recording_info=json.loads(result[i]["recording_info"].decode("utf-8")),
          recording_duration=float(result[i]["recording_duration"].decode("utf-8")),
          recording_datapointer=str(deviceId) + "/" + result[i]["recording_datapointer"].decode("utf-8"),
          source_file=result[i]["source_file"].decode("utf-8"),
        )

        try:
            os.mkdir(DATABASE_PATH + "recordings" + os.path.sep + str(recording.device_deidentified_id))
        except Exception:
            pass

        oldPath = OLD_DATABASE_PATH + "recordings/" + result[i]["recording_datapointer"].decode("utf-8")
        newPath = DATABASE_PATH + "recordings/" + recording.recording_datapointer
        shutil.copyfile(oldPath, newPath)

        batchResult.append(recording)
      models.BrainSenseRecording.objects.bulk_create(batchResult)
      
      connector.close()

      return True

    elif argv[1] == "Merge":
      if argv[2] == "Patient":
        PatientID = argv[3]
        PatientID2 = argv[4]
        SourcePatient = models.Patient.objects.filter(deidentified_id=PatientID).first()
        MergePatient = models.Patient.objects.filter(deidentified_id=PatientID2).first()

        if MergePatient and SourcePatient:
          for device_id in SourcePatient.device_deidentified_id:
            device = models.PerceptDevice.objects.filter(deidentified_id=device_id).first()
            device.patient_deidentified_id = MergePatient.deidentified_id
            device.save()
            MergePatient.addDevice(str(device.deidentified_id))

        SourcePatient.delete()
        return True
      
      else: 
        PatientID = argv[2]
        SourcePatient = models.Patient.objects.filter(deidentified_id=PatientID).first()
        for device_id in SourcePatient.device_deidentified_id:
          device = models.PerceptDevice.objects.filter(deidentified_id=device_id).first()
          device.patient_deidentified_id = SourcePatient.deidentified_id
          device.save()
          print(device)
        
        return True

    elif argv[1] == "Refresh":
      if argv[2] == "TherapyHistory":
        if argv[3] == "All":
          SessionFiles = models.PerceptSession.objects.all()
        else:
          SessionFiles = models.PerceptSession.objects.filter(device_deidentified_id=argv[3]).all()

        for sessionFile in SessionFiles:
          try:
            JSON = Percept.decodeEncryptedJSON(sessionFile.session_file_path, key)
          except:
            print(sessionFile.session_file_path)
            continue
          
          TherapySettings = Percept.extractTherapySettings(JSON)
          
          TherapyHistories = models.TherapyHistory.objects.filter(source_file=str(sessionFile.deidentified_id)).all()
          for therapy in TherapyHistories:
            if therapy.therapy_type == "Past Therapy":
              for newTherapy in TherapySettings["TherapyHistory"]:
                if therapy.therapy_date == datetime.fromisoformat(newTherapy["DateTime"]+"+00:00"):
                  for group in newTherapy["Therapy"]:
                    if group["GroupId"] == therapy.group_id:
                      therapy.therapy_details = group
                      therapy.save()
            elif therapy.therapy_type == "Pre-visit Therapy":
              for newTherapy in TherapySettings["PreviousGroups"]:
                if newTherapy["GroupId"] == therapy.group_id:
                  therapy.therapy_details = newTherapy
                  therapy.save()
            elif therapy.therapy_type == "Post-visit Therapy":
              for newTherapy in TherapySettings["StimulationGroups"]:
                if newTherapy["GroupId"] == therapy.group_id:
                  therapy.therapy_details = newTherapy
                  therapy.save()
        
      elif argv[2] == "Sessions":
        if argv[3] == "All":
          SessionFiles = models.PerceptSession.objects.all()
        else:
          SessionFiles = models.PerceptSession.objects.filter(device_deidentified_id=argv[3]).all()

        for sessionFile in SessionFiles:
          try:
            JSON = Percept.decodeEncryptedJSON(sessionFile.session_file_path, key)
          except:
            print(sessionFile.session_file_path)
            continue
          
          LeadConfigurations = []
          LeadInformation = JSON["LeadConfiguration"]["Final"]
          for lead in LeadInformation:
              LeadConfiguration = dict()
              LeadConfiguration["TargetLocation"] = lead["Hemisphere"].replace("HemisphereLocationDef.","") + " "
              if lead["LeadLocation"] == "LeadLocationDef.Vim":
                  LeadConfiguration["TargetLocation"] += "VIM"
              elif lead["LeadLocation"] == "LeadLocationDef.Stn":
                  LeadConfiguration["TargetLocation"] += "STN"
              elif lead["LeadLocation"] == "LeadLocationDef.Gpi":
                  LeadConfiguration["TargetLocation"] += "GPi"
              else:
                  LeadConfiguration["TargetLocation"] += lead["LeadLocation"].replace("LeadLocationDef.","")

              if lead["ElectrodeNumber"] == "InsPort.ZERO_THREE":
                  LeadConfiguration["ElectrodeNumber"] = "E00-E03"
              elif lead["ElectrodeNumber"] == "InsPort.ZERO_SEVEN":
                  LeadConfiguration["ElectrodeNumber"] = "E00-E07"
              elif lead["ElectrodeNumber"] == "InsPort.EIGHT_ELEVEN":
                  LeadConfiguration["ElectrodeNumber"] = "E08-E11"
              elif lead["ElectrodeNumber"] == "InsPort.EIGHT_FIFTEEN":
                  LeadConfiguration["ElectrodeNumber"] = "E08-E15"
              if lead["Model"] == "LeadModelDef.LEAD_B33015":
                  LeadConfiguration["ElectrodeType"] = "SenSight B33015"
              elif lead["Model"] == "LeadModelDef.LEAD_B33005":
                  LeadConfiguration["ElectrodeType"] = "SenSight B33005"
              elif lead["Model"] == "LeadModelDef.LEAD_3387":
                  LeadConfiguration["ElectrodeType"] = "Medtronic 3387"
              elif lead["Model"] == "LeadModelDef.LEAD_3389":
                  LeadConfiguration["ElectrodeType"] = "Medtronic 3389"
              elif lead["Model"] == "LeadModelDef.LEAD_OTHER":
                  LeadConfiguration["ElectrodeType"] = "Unknown Lead"
              else:
                  LeadConfiguration["ElectrodeType"] = lead["Model"]

              LeadConfigurations.append(LeadConfiguration)

          SessionDate = datetime.fromtimestamp(Percept.estimateSessionDateTime(JSON),tz=pytz.utc)
          sessionFile.session_date = SessionDate
          sessionFile.save()
        
          deviceObj = models.PerceptDevice.objects.filter(deidentified_id=sessionFile.device_deidentified_id).first()
          if len(deviceObj.device_lead_configurations) < len(LeadConfigurations):
            deviceObj.device_lead_configurations = LeadConfigurations
            deviceObj.save()

      elif argv[2] == "Impedance":
        if argv[3] == "All":
          SessionFiles = models.PerceptSession.objects.all()
        else:
          SessionFiles = models.PerceptSession.objects.filter(device_deidentified_id=argv[3]).all()

        for sessionFile in SessionFiles:
          try:
            JSON = Percept.decodeEncryptedJSON(sessionFile.session_file_path, key)
          except:
            print(sessionFile.session_file_path)
            continue

          Data = Percept.extractPatientInformation(JSON)
          if "Impedance" in Data.keys():
            models.ImpedanceHistory(impedance_record=Data["Impedance"], device_deidentified_id=sessionFile.device_deidentified_id, session_date=sessionFile.session_date).save()
          
      return True