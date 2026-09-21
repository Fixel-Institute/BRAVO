#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BRAVO.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


def processInput(argv):
    if len(argv) > 1:
        if argv[1] == "create_template":
            # Build paths inside the project like this: BASE_DIR / 'subdir'.
            BASE_DIR = Path(__file__).resolve().parent
            with open(BASE_DIR / "Server/templates/index.html", "w+") as fileout:
                with open(BASE_DIR / "../Client/build/index.html", "r+") as filein:
                    for line in filein:
                        text = line
                        text = text.replace('</head><body>', '</head>{% csrf_token %}<body>')
                        text = text.replace('<!doctype html>', '{% load static %}<!doctype html>')
                        fileout.write(text)

            return True
        
        elif argv[1] == "make_staticfile":
            # Build paths inside the project like this: BASE_DIR / 'subdir'.
            BASE_DIR = Path(__file__).resolve().parent
            with open(BASE_DIR / "Server/templates/index.html", "w+") as fileout:
                with open(BASE_DIR / "../Client/build/index.html", "r+") as filein:
                    for line in filein:
                        text = line
                        text = text.replace('<!doctype html>', '{% load static %}<!doctype html>')
                        text = text.replace('</head><body>', '</head>{% csrf_token %}<body>')
                        text = text.replace('"/static/', '\"{% static \'')
                        text = text.replace('.js"', '.js\' %}\"')
                        text = text.replace('.png"', '.png\' %}\"')
                        text = text.replace('.json"', '.json\' %}\"')
                        text = text.replace('.css" rel=', '.css\' %}\" rel=')
                        fileout.write(text)

            return True
        
        elif argv[1] == "DeleteChronicNeuralActivityCache":
            from BRAVO import wsgi
            from Server import models
            from modules import Database
            from modules import DataCurator

            participants = models.Participant.find_all()
            for i in range(len(participants)):
                participant = participants[i]
                print(f"Start Processing Participant {i}/{len(participants)}")
                if models.Recording.find(type="MedtronicChronicNeuralActivity", source__owner=participant):
                    models.Recording.find(type="MedtronicChronicNeuralActivity", source__owner=participant).delete()
                Database.deleteCachedResult(participant.uid, url="/queryChronicNeuralActivity")
            return True 
                    
        elif argv[1] == "RefreshPerceptSessions":
            from BRAVO import wsgi
            from Server import models
            from modules import Database
            from modules import DataCurator

            participants = models.Participant.find_all()
            for i in range(len(participants)):
                participant = participants[i]
                print(f"Start Processing Participant {i}/{len(participants)}")
                session_files = models.SourceFile.find_all(owner=participant, metadata__contains={"UploadType": "MedtronicJSON"})
                for session in session_files:
                    StartFiles = models.Recording.objects.filter(source=session).count()
                    device = models.DBSDevice.find(uid=session.metadata["Device"])
                    DataCurator.MedtronicPerceptJSONDecoder(session, device=device, person=participant)
                    EndFiles = models.Recording.objects.filter(source=session).count()
                    if EndFiles > StartFiles:
                        print(f"Participant {participant.uid} - {participant.name} - {StartFiles} -> {EndFiles}")
            return True 
                    
        elif argv[1] == "ClearErrorCachedFiles":
            from BRAVO import wsgi
            from Server import models
            models.SourceFile.objects.filter(owner=None).delete()
            return True 

        elif argv[1] == "MigrateDataStorage":
            from BRAVO import wsgi
            from Server import models

            OldStoragePath = argv[2]
            DATASERVER_PATH = os.environ.get('DATASERVER_PATH')
            
            source_files = models.SourceFile.find_all()
            for i in range(len(source_files)):
                source_file = source_files[i]
                print(f"Processing source file {i}/{len(source_files)}")
                source_file.pointer = source_file.pointer.replace(OldStoragePath, DATASERVER_PATH).replace("\\", os.path.sep).replace("/", os.path.sep)
                source_file.save()

            source_files = models.Recording.find_all()
            for i in range(len(source_files)):
                source_file = source_files[i]
                print(f"Processing recording file {i}/{len(source_files)}")
                source_file.pointer = source_file.pointer.replace(OldStoragePath, DATASERVER_PATH).replace("\\", os.path.sep).replace("/", os.path.sep)
                source_file.save()
        
            return True
        
        elif argv[1] == "CleanUpDevices":
            from BRAVO import wsgi
            from Server import models
            from modules import Database
            participants = models.Participant.find_all()

            def matchElectrodes(old, new):
                if not len(old) == len(new):
                    return False
                
                for lead in new:
                    lead_exist = False
                    for electrode in old:
                        if electrode["Type"] == lead["Type"]:
                            if electrode["Target"] == lead["Target"]:
                                lead_exist = True
                    
                    if not lead_exist:
                        return False

                return True

            for participant in participants:
                while True:
                    Merged = False
                    devices = models.DBSDevice.find_all(owner=participant)
                    for i in range(len(devices)):
                        Electrodes = [electrode.get_info() for electrode in devices[i].electrodes.all()]
                        for j in range(i+1, len(devices)):
                            if devices[i].serial_number == devices[j].serial_number:
                                Electrodes_Compare = [electrode.get_info() for electrode in devices[j].electrodes.all()]
                                if matchElectrodes(Electrodes, Electrodes_Compare):
                                    Merged = True
                                    Database.assignSourceFile(devices[j].uid, devices[i].uid)

                        if Merged:
                            break

                    if not Merged:
                        break
            
            return True

        elif argv[1] == "SetupBRAVO":
            import socket
            import json
            from cryptography import fernet

            BASE_DIR = Path(__file__).resolve().parent
            if os.path.exists(os.path.join(BASE_DIR, '.env')):
                print("Environment Variable Exist, cannot perform fresh installation.")
                return True
        
            config = dict()
            databasePath = input("Please enter the full path to the desired folder as database storage [Default: $SCRIPT_DIR/BRAVO/BRAVOStorage/]: ")
            if not databasePath == "":
                config["DATASERVER_PATH"] = databasePath
            else:
                config["DATASERVER_PATH"] = os.path.join(BASE_DIR, 'BRAVOStorage')
            if not config["DATASERVER_PATH"].endswith(os.path.sep):
                config["DATASERVER_PATH"] += os.path.sep
            os.makedirs(config["DATASERVER_PATH"], exist_ok=True)

            config["DATASERVER_ENCRYPTION"] = fernet.Fernet.generate_key().decode("utf-8")
            config["DATASERVER_HASHKEY"] = "BRAVOServerHashkey"
            config["DJANGO_SECRET_KEY"] = "django-insecure-" + fernet.Fernet.generate_key().decode("utf-8")

            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                localAddress = s.getsockname()[0]
                s.close()
            except:
                localAddress = "127.0.1.1"

            serverAddress = input(f"Please enter the public IP address if available [Default: Local Address {localAddress}]: ")
            if not serverAddress == "":
                config["SERVER_HOST"] = serverAddress
                config["SERVER_ADDRESS"] = "https://" + serverAddress
            else:
                config["SERVER_HOST"] = localAddress
                config["SERVER_ADDRESS"] = "http://" + localAddress + ":27286"

            config["DJANGO_MODE"] = "DEBUG"
        
            config["FIBIT_CLIENT_SECRET"] = ""
            config["FIBIT_CLIENT_ID"] = ""
            
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
                    content = re.split(r"[\s]?=[\s]?", line)
                
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
            subprocess.run(["sudo","mysql", "-uroot", "-e", f"CREATE USER '{userName}'@'{hostName}' IDENTIFIED BY '{dbPassword}'"])
            subprocess.run(["sudo","mysql", "-uroot", "-e", f"GRANT ALL PRIVILEGES ON {databaseName}.* TO '{userName}'@'{hostName}'"])
            subprocess.run(["sudo","mysql", "-uroot", "-e", f"FLUSH PRIVILEGES"])

            return True

if __name__ == '__main__':
    if not processInput(sys.argv):
        main()
