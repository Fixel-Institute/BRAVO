import os, sys
from datetime import datetime

from BRAVO import asgi
from Backend import models
from modules.Percept import Sessions

from decoder import Percept

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
        
        return True