""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2023 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Database Manager for Django Commandlines
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
@date: Thu Sep 16 12:05:09 2021
"""

import os, sys
from datetime import datetime
import pytz
from pathlib import Path

import pickle, blosc
import uuid
import json

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
key = os.environ.get('ENCRYPTION_KEY')

def processInput(argv):
  if len(argv) > 1:
    if argv[1] == "Clean":
      from BRAVO import asgi
      from Backend import models
      from modules.Percept import Sessions
      from decoder import Percept

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
    
    if argv[1] == "ChangePassword":
      from BRAVO import asgi
      from Backend import models
      from modules.Percept import Sessions

      user = models.PlatformUser.objects.get(email=argv[2])
      user.set_password(argv[3])
      user.save()
      return True

    elif argv[1] == "SetupBRAVO":
      import socket
      from cryptography import fernet
      BASE_DIR = Path(__file__).resolve().parent
      if os.path.exists(os.path.join(BASE_DIR, '.env')):
        print("Environment Variable Exist, cannot perform fresh installation.")
        return True
      
      config = dict()
      databasePath = input("Please enter the full path to the desired folder as database storage [Default: $SCRIPT_DIR/Server/BRAVOStorage/]: ")
      if not databasePath == "":
        config["DATASERVER_PATH"] = databasePath
      else:
        config["DATASERVER_PATH"] = os.path.join(BASE_DIR, 'BRAVOStorage')
      print(config["DATASERVER_PATH"].endswith(os.path.sep))
      if not config["DATASERVER_PATH"].endswith(os.path.sep):
        config["DATASERVER_PATH"] += os.path.sep
      os.makedirs(config["DATASERVER_PATH"], exist_ok=True)

      config["PYTHON_UTILITY"] = os.path.join(BASE_DIR, 'modules' + os.path.sep + "python-scripts")
      config["STATIC_ROOT"] = os.path.join(BASE_DIR, 'static')
      config["ENCRYPTION_KEY"] = fernet.Fernet.generate_key().decode("utf-8")
      config["SECRET_KEY"] = "django-insecure-" + fernet.Fernet.generate_key().decode("utf-8")

      try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        localAddress = s.getsockname()[0]
        s.close()
      except:
        localAddress = "127.0.1.1"

      serverAddress = input(f"Please enter the public IP address if available [Default: Local Address {localAddress}]: ")
      if not serverAddress == "":
        config["SERVER_ADDRESS"] = serverAddress
        config["CLIENT_ADDRESS"] = "https://" + serverAddress
      else:
        config["SERVER_ADDRESS"] = localAddress
        config["CLIENT_ADDRESS"] = "http://" + localAddress

      config["MODE"] = "DEBUG"
      
      with open(os.path.join(BASE_DIR, '.env'), "w+") as file:
        json.dump(config, file)

      import re, subprocess
      with open("mysql.config", "r") as fid:
        info = fid.readlines()
      
      databaseName = "BRAVOServer"
      userName = "BRAVOAdmin"
      hostName = "localhost"
      dbPassword = "AdminPassword"

      for line in info:
        if "=" in line:
          line = line.replace(" ","")
          content = re.split("[\s]?=[\s]?", line)
          
          if len(content) == 2:
            if content[0] == "database":
              databaseName = content[1].replace("\n","")
            elif content[0] == "user":
              userName = content[1].replace("\n","")
            elif content[0] == "host":
              hostName = content[1].replace("\n","")
            elif content[0] == "password":
              dbPassword = content[1].replace("\n","")
          
      subprocess.run(["sudo","mysql", "-uroot", "-e", f"CREATE DATABASE {databaseName}"])
      subprocess.run(["sudo","mysql", "-uroot", "-e", f"CREATE USER '{userName}'@'{hostName}' IDENTIFIED WITH mysql_native_password BY '{dbPassword}'"])
      subprocess.run(["sudo","mysql", "-uroot", "-e", f"GRANT ALL PRIVILEGES ON {databaseName}.* TO '{userName}'@'{hostName}'"])
      subprocess.run(["sudo","mysql", "-uroot", "-e", f"FLUSH PRIVILEGES"])

      return True

    elif argv[1] == "MigrateFromV1":
      from BRAVO import asgi
      from Backend import models
      from modules.Percept import Sessions, Therapy, BrainSenseSurvey, BrainSenseStream, BrainSenseEvent, IndefiniteStream, ChronicBrainSense
      from decoder import Percept
      
      from modules import Database

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
      
      # Reprocess all Session File
      # This is the same as 2.1.x upgrade to 2.2 which will have completely 
      # different data structure and improved extraction code.

      # Require to run ProcessingQueueJob after migration.
      users = models.PlatformUser.objects.all()
      Authority = {"Level": 1}
      for user in users:
        if user.is_admin or user.is_clinician:
          Patients = models.Patient.objects.filter(institute=user.institute).all()
        else:
          Patients = models.Patient.objects.filter(institute=user.email).all()

        for patient in Patients:
          availableDevices = Database.getPerceptDevices(user, patient.deidentified_id, Authority)
          for device in availableDevices:
            availableSessions = models.PerceptSession.objects.filter(device_deidentified_id=device.deidentified_id).all()
            for session in availableSessions:
              try:
                shutil.copyfile(DATABASE_PATH + session.session_file_path,(DATABASE_PATH + session.session_file_path).replace("/sessions/","/cache/"))
                models.ProcessingQueue(owner=user.unique_user_id, type="decodeJSON", state="InProgress", descriptor={
                    "filename": session.session_file_path.split("/")[-1],
                    "device_deidentified_id": str(device.deidentified_id)
                }).save()
                Sessions.deleteSessions(user, patient.deidentified_id, [str(session.deidentified_id)], Authority)

              except Exception as e:
                print(e)

      connector.close()

      return True
    
    elif argv[1] == "MigrateFromV2.1":
      from BRAVO import asgi
      from Backend import models
      from modules.Percept import Sessions, Therapy, BrainSenseSurvey, BrainSenseStream, BrainSenseEvent, IndefiniteStream, ChronicBrainSense
      from decoder import Percept
      import shutil
      
      from modules import Database
      DATABASE_PATH = os.environ.get('DATASERVER_PATH')

      users = models.PlatformUser.objects.all()
      Authority = {"Level": 1}
      for user in users:
        if user.is_admin or user.is_clinician:
          Patients = models.Patient.objects.filter(institute=user.institute).all()
        else:
          Patients = models.Patient.objects.filter(institute=user.email).all()

        for patient in Patients:
          availableDevices = Database.getPerceptDevices(user, patient.deidentified_id, Authority)
          for device in availableDevices:
            availableSessions = models.PerceptSession.objects.filter(device_deidentified_id=device.deidentified_id).all()
            for session in availableSessions:
              try:
                shutil.copyfile(DATABASE_PATH + session.session_file_path,(DATABASE_PATH + session.session_file_path).replace("/sessions/","/cache/"))
                models.ProcessingQueue(owner=user.unique_user_id, type="decodeJSON", state="InProgress", descriptor={
                    "filename": session.session_file_path.split("/")[-1],
                    "device_deidentified_id": str(device.deidentified_id),
                }).save()
                Sessions.deleteSessions(user, patient.deidentified_id, [str(session.deidentified_id)], Authority)

              except Exception as e:
                print(e)
          
      # Cleanup Database
      models.CombinedRecordingAnalysis.objects.all().delete()
      models.TherapyChangeLog.objects.all().delete()
      models.TherapyHistory.objects.all().delete()
      models.ImpedanceHistory.objects.all().delete()
      models.NeuralActivityRecording.objects.all().delete()

      # Run Processing Script
      from ProcessingQueueService import processJSONUploads 
      processJSONUploads()

      # Check for Authorized Access
      users = models.PlatformUser.objects.all()
      Authority = {"Level": 1}
      for user in users:
        if user.is_admin or user.is_clinician:
          Patients = models.Patient.objects.filter(institute=user.institute).all()
        else:
          Patients = models.Patient.objects.filter(institute=user.email).all()

        for patient in Patients:
          AuthorizedUsers = []
          if models.DeidentifiedPatientID.objects.filter(authorized_patient_id=patient.deidentified_id).exists():
            AuthorizedUsers = models.DeidentifiedPatientID.objects.filter(authorized_patient_id=patient.deidentified_id).all()

            for authorizeUser in AuthorizedUsers:
              # First Cleanup Permission
              Database.AuthorizeResearchAccess(user, authorizeUser.researcher_id, patient.deidentified_id, False)

              # Then Add Permission Again due to different structures
              Database.AuthorizeResearchAccess(user, authorizeUser.researcher_id, patient.deidentified_id, True)
              Database.AuthorizeRecordingAccess(user, authorizeUser.researcher_id, patient.deidentified_id, recording_type="TherapyHistory")
              Database.AuthorizeRecordingAccess(user, authorizeUser.researcher_id, patient.deidentified_id, recording_type="BrainSenseSurvey")
              Database.AuthorizeRecordingAccess(user, authorizeUser.researcher_id, patient.deidentified_id, recording_type="BrainSenseStreamTimeDomain")
              Database.AuthorizeRecordingAccess(user, authorizeUser.researcher_id, patient.deidentified_id, recording_type="BrainSenseStreamPowerDomain")
              Database.AuthorizeRecordingAccess(user, authorizeUser.researcher_id, patient.deidentified_id, recording_type="IndefiniteStream")
              Database.AuthorizeRecordingAccess(user, authorizeUser.researcher_id, patient.deidentified_id, recording_type="ChronicLFPs")

      return True

    elif argv[1] == "Merge":
      from BRAVO import asgi
      from Backend import models
      from modules.Percept import Sessions
      from decoder import Percept

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
      from BRAVO import asgi
      from Backend import models
      from modules.Percept import Sessions
      from modules import Database
      from decoder import Percept

      if argv[2] == "TherapyHistory":
        if argv[3] == "All":
          SessionFiles = models.PerceptSession.objects.all()
        else:
          SessionFiles = models.PerceptSession.objects.filter(device_deidentified_id=argv[3]).all()

        for sessionFile in SessionFiles:
          try:
            JSON = Percept.decodeEncryptedJSON(DATABASE_PATH + sessionFile.session_file_path, key)
          except:
            print(sessionFile.session_file_path)
            continue
          
          TherapySettings = Percept.extractTherapySettings(JSON)
          
          TherapyHistories = models.TherapyHistory.objects.filter(source_file=str(sessionFile.deidentified_id)).all()
          for therapy in TherapyHistories:
            if therapy.therapy_type == "Past Therapy":
              for newTherapy in TherapySettings["TherapyHistory"]:
                if therapy.therapy_date == datetime.fromisoformat(newTherapy["DateTime"].replace("Z","+00:00")):
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
          if not sessionFile.session_file_path.startswith("sessions/"):
            sessionFile.session_file_path = "sessions/" + sessionFile.session_file_path.split(os.path.sep)[-1]
          try:
            JSON = Percept.decodeEncryptedJSON(DATABASE_PATH + sessionFile.session_file_path, key)
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
            JSON = Percept.decodeEncryptedJSON(DATABASE_PATH + sessionFile.session_file_path, key)
          except:
            print(sessionFile.session_file_path)
            continue

          Data = Percept.extractPatientInformation(JSON)
          if "Impedance" in Data.keys():
            models.ImpedanceHistory(impedance_record=Data["Impedance"], device_deidentified_id=sessionFile.device_deidentified_id, session_date=sessionFile.session_date).save()
          
      elif argv[2] == "Recordings":
        DATABASE_PATH = os.environ.get('DATASERVER_PATH')

        Recordings = models.ExternalRecording.objects.all()
        for recording in Recordings:
          if recording.recording_datapointer.endswith(".pkl"):
            try:
              datastruct = Database.loadSourceDataPointer(recording.recording_datapointer)
            except:
              continue
            filename = recording.recording_datapointer.replace(".pkl",".bpkl")
            pData = pickle.dumps(datastruct)
            with open(DATABASE_PATH + "recordings" + os.path.sep + filename, "wb+") as file:
              file.write(blosc.compress(pData))
            Database.deleteSourceDataPointer(recording.recording_datapointer)
            recording.recording_datapointer = filename
            recording.save()

        Recordings = models.NeuralActivityRecording.objects.all()
        for recording in Recordings:
          if recording.recording_datapointer.endswith(".pkl"):
            try:
              datastruct = Database.loadSourceDataPointer(recording.recording_datapointer)
            except:
              continue
            filename = recording.recording_datapointer.replace(".pkl",".bpkl")
            pData = pickle.dumps(datastruct)
            with open(DATABASE_PATH + "recordings" + os.path.sep + filename, "wb+") as file:
              file.write(blosc.compress(pData))
            Database.deleteSourceDataPointer(recording.recording_datapointer)
            recording.recording_datapointer = filename
            recording.save()

      return True