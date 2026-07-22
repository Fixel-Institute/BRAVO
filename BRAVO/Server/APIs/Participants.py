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
Database Participant APIs
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from django.contrib.auth import authenticate, login, logout

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.http import HttpResponse, FileResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings

from modules.HelperFunctions import sanitize_input, get_or_none, get_token
from modules import Database, DataAnalysis
from modules.DataCurator import ExportBRAVOStructure
from Server import models

def queryParticipantFunc(user):
    AllParticipants = []
    AllParticipantInfos = []
    
    if "ActiveStudy" in user.configuration.keys():
        study = models.Study.find(uid=user.configuration["ActiveStudy"])
        if not study:
            user.configuration["ActiveStudy"] = ""
        else:
            rel = models.StudyRel.find(member=user, study=study)
            if rel:
                deidentified = True
                if rel.permission["Position"] == "Admin" or "PHIAllowed" in rel.permission.keys():
                    deidentified = False

                AllParticipants = study.participants.all()
                for i in range(len(AllParticipants)):
                    ParticipantInfo = AllParticipants[i].get_info()
                    ParticipantInfo["DBSDevices"] = Database.extractParticipantDevices(AllParticipants[i])
                    if deidentified:
                        ParticipantInfo["Name"] = ParticipantInfo["Id"]
                        ParticipantInfo["MRN"] = ""
                        ParticipantInfo["DOB"] = 0
                            
                    AllParticipantInfos.append(ParticipantInfo)

    else:
        institute = user.institute
        if institute:
            AllParticipants = models.Participant.from_institute(institute)
            for i in range(len(AllParticipants)):
                ParticipantInfo = AllParticipants[i].get_info()
                ParticipantInfo["DBSDevices"] = Database.extractParticipantDevices(AllParticipants[i])
                AllParticipantInfos.append(ParticipantInfo)

    return AllParticipantInfos

class QueryParticipants(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        AllParticipants = []
        AllParticipantInfos = []

        if "ActiveStudy" in request.user.configuration.keys():
            study = models.Study.find(uid=request.user.configuration["ActiveStudy"])
            if not study:
                request.user.configuration["ActiveStudy"] = ""
            else:
                rel = models.StudyRel.find(member=request.user, study=study)
                if rel:
                    deidentified = True
                    if rel.permission["Position"] == "Admin" or "PHIAllowed" in rel.permission.keys():
                        deidentified = False

                    AllParticipants = study.participants.all()
                    for i in range(len(AllParticipants)):
                        ParticipantInfo = AllParticipants[i].get_info()
                        ParticipantInfo["DBSDevices"] = Database.extractParticipantDevices(AllParticipants[i])
                        if deidentified:
                            ParticipantInfo["Name"] = ParticipantInfo["Id"]
                            ParticipantInfo["MRN"] = ""
                            ParticipantInfo["DOB"] = 0
                                
                        AllParticipantInfos.append(ParticipantInfo)

        else:
            institute = request.user.institute
            if institute:
                AllParticipants = models.Participant.from_institute(institute)
                for i in range(len(AllParticipants)):
                    ParticipantInfo = AllParticipants[i].get_info()
                    ParticipantInfo["DBSDevices"] = Database.extractParticipantDevices(AllParticipants[i])
                    AllParticipantInfos.append(ParticipantInfo)

        return Response(status=200, data=AllParticipantInfos)

class QueryParticipantInformation(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                            study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)

        ParticipantInfo = Database.extractParticipantInformation(request.data["ParticipantId"], deidentified=Permissions["Deidentified"])
        return Response(status=200, data=ParticipantInfo)

class ExportParticipant(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def get(self, request):
        ParticipantId = self.request.query_params.get('ParticipantId')
        Deidentified = self.request.query_params.get('Deidentified')
        Permissions = Database.checkAccessPermission(request.user, ParticipantId, 
                            study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        Participant = models.Participant.find(uid=ParticipantId)
        filePath = ExportBRAVOStructure(Participant, deidentified=Permissions["Deidentified"] or Deidentified=="True")
        fid = open(filePath, "rb")
        filename = ParticipantId + ".bdat"
        response = FileResponse(fid, as_attachment=True, filename=filename)
        return response

class UpdateParticipantInformation(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId"], accepted_keys=["ParticipantId", "MergeWith", "Name", "MRN", "DOB", "Sex", "Diagnosis", "DiagnosisStartTime", "Tags"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                            study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        
        Participant = models.Participant.find(uid=request.data["ParticipantId"])
        if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Edit"):
            if "Tags" in request.data.keys():
                Participant.tags.clear()
                for tag_name in request.data["Tags"]:
                    tag, _ = models.Tag.find_or_create(name=tag_name, owner=request.user)
                    Participant.tags.add(tag)
                Participant.save()
                ParticipantInfo = Database.extractParticipantInformation(request.data["ParticipantId"], deidentified=Permissions["Deidentified"])
                return Response(status=200, data=ParticipantInfo)
            return Response(status=403)
        
        if "MergeWith" in request.data.keys():
            if not Database.checkManagePermission(request.user, request.data["MergeWith"], "Delete"):
                return Response(status=403)

            TargetParticipant = models.Participant.find(uid=request.data["MergeWith"])
            try:
                Database.mergeParticipants(source=Participant, target=TargetParticipant)
            except Exception as e:
                return Response(status=400, data={"message": str(e)})
            return Response(status=200)

        if "Name" in request.data.keys():
            Participant.name = request.data["Name"]
        if "MRN" in request.data.keys():
            Participant.mrn = request.data["MRN"]
        if "DOB" in request.data.keys():
            Participant.date_of_birth = request.data["DOB"]
        if "Sex" in request.data.keys():
            Participant.sex = request.data["Sex"]
        if "Diagnosis" in request.data.keys():
            Participant.diagnosis = request.data["Diagnosis"]
        if "Tags" in request.data.keys():
            Participant.tags.clear()
            for tag_name in request.data["Tags"]:
                tag, _ = models.Tag.find_or_create(name=tag_name, owner=request.user)
                Participant.tags.add(tag)

        Participant.save()
        ParticipantInfo = Database.extractParticipantInformation(request.data["ParticipantId"])
        return Response(status=200, data=ParticipantInfo)

class DeleteParticipantInformation(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId"], accepted_keys=["ParticipantId"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Delete"):
            return Response(status=403)
        
        Participant = models.Participant.find(uid=request.data["ParticipantId"])
        Participant.delete()
        return Response(status=200)

class ManageParticipantDevice(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Edit"):
            return Response(status=403)
        
        Participant = models.Participant.find(uid=request.data["ParticipantId"])

        if not "DeviceId" in request.data.keys():
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "DeviceType", "ManufacturerDeviceType", "SerialNumber"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if request.data["DeviceType"] == "DBSDevice":
                device = models.DBSDevice.find(serial_number=request.data["SerialNumber"], type=request.data["ManufacturerDeviceType"], owner=Participant)
                if not device:
                    device = models.DBSDevice.create(request.data["SerialNumber"], request.data["ManufacturerDeviceType"])
                    device.owner = Participant
                    device.save()
                return Response(status=200, data=device.get_info())
            
        return Response(status=400, data={"message": "Malformed Input"})
        
class UpdateDeviceInformation(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "DeviceId"], accepted_keys=["ParticipantId", "DeviceId", "Name", "Electrodes"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Edit"):
            return Response(status=403)
        
        Participant = models.Participant.find(uid=request.data["ParticipantId"])
        DBSDevice = models.DBSDevice.find(owner=Participant, uid=request.data["DeviceId"])
        if not DBSDevice:
            return Response(status=403)
        
        if "Name" in request.data.keys():
            DBSDevice.name = request.data["Name"]
        if "Electrodes" in request.data.keys():
            for electrode in request.data["Electrodes"]:
                lead = DBSDevice.electrodes.filter(uid=electrode["Id"]).first() # NOTE: SQL-Specific QuerySet
                lead.custom_name = electrode["CustomName"]
                lead.save()

        DBSDevice.save()
        ParticipantInfo = Database.extractParticipantInformation(request.data["ParticipantId"])
        return Response(status=200, data=ParticipantInfo)

class DeleteDeviceInformation(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "DeviceId"], accepted_keys=["ParticipantId", "DeviceId"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Delete"):
            return Response(status=403)
        
        Participant = models.Participant.find(uid=request.data["ParticipantId"])
        DBSDevice = models.DBSDevice.find(owner=Participant, uid=request.data["DeviceId"])
        if not DBSDevice:
            return Response(status=403)
        
        models.SourceFile.find_all(owner=Participant, metadata__Device=DBSDevice.uid).delete()
        DBSDevice.delete()
        ParticipantInfo = Database.extractParticipantInformation(request.data["ParticipantId"])
        return Response(status=200, data=ParticipantInfo)

class CreateParticipantInformation(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["Name"], accepted_keys=["Name", "MRN", "DOB", "Sex", "Diagnosis", "DiseaseStartTime"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        person, person_created = models.Participant.find_or_create(request.data["Name"], "", request.user.institute.uid)
        if person_created:
            if "DOB" in request.data.keys():
                person.date_of_birth = request.data["DOB"]
            if "Sex" in request.data.keys():
                person.sex = request.data["Sex"]
            if "MRN" in request.data.keys():
                person.mrn = request.data["MRN"]
            if "Diagnosis" in request.data.keys():
                person.diagnosis = request.data["Diagnosis"]
            if "DiseaseStartTime" in request.data.keys():
                person.disease_start_time = request.data["DiseaseStartTime"]
            person.institute = request.user.institute
            person.save()
        else:
            return Response(status=400, data={"message": "Participant Name Used"})
        
        return Response(status=200, data=person.get_info())

class StudyHandler(RestViews.APIView):

    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})

        if request.data["RequestType"] == "GetStudies":
            studies = models.Study.find_all(members=request.user)
            Studies = []
            for study in studies:
                Studies.append(study.get_info(request.user))
                
            return Response(status=200, data=Studies)

        elif request.data["RequestType"] == "CreateStudy":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "StudyName"]):
                return Response(status=400, data={"message": "Malformed Input"})

            study = models.Study.create(request.data["StudyName"])
            rel = models.StudyRel.create(study=study, member=request.user, permission={
                "Position": "Admin"
            })
            rel.save()
            
            return Response(status=200, data=study.get_info(request.user))

        elif request.data["RequestType"] == "ResetStudyCode":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "StudyId"]):
                return Response(status=400, data={"message": "Malformed Input"})

            study = models.Study.find(uid=request.data["StudyId"])
            if not study:
                return Response(status=400, data={"message": "Incorrect Study Id"})
            
            if not models.StudyRel.find(member=request.user, study=study, permission__Position="Admin"):
                return Response(status=403)
            
            study.invite_code = get_token(64)
            study.save()
            return Response(status=200, data=study.invite_code)

        elif request.data["RequestType"] == "JoinStudy":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "StudyId"]):
                return Response(status=400, data={"message": "Malformed Input"})

            study = models.Study.find(invite_code=request.data["StudyId"])
            if not study:
                return Response(status=400, data={"message": "Incorrect Invitation Code"})
            
            rel = models.StudyRel.create(study=study, member=request.user, permission={
                "Position": "Member"
            })
            rel.save()
            
            return Response(status=200, data=study.get_info(request.user))

        elif request.data["RequestType"] == "RemoveMember":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "StudyId", "Member"]):
                return Response(status=400, data={"message": "Malformed Input"})

            study = models.Study.find(uid=request.data["StudyId"])
            if not study:
                return Response(status=400, data={"message": "Incorrect Study Id"})
            
            if not models.StudyRel.find(member=request.user, study=study, permission__Position="Admin"):
                return Response(status=403)
            
            tagetUser = models.PlatformUser.find(email=request.data["Member"])
            study.members.remove(tagetUser)

            return Response(status=200)

        elif request.data["RequestType"] == "LeaveStudy":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "StudyId"]):
                return Response(status=400, data={"message": "Malformed Input"})

            study = models.Study.find(uid=request.data["StudyId"])
            if not study:
                return Response(status=400, data={"message": "Incorrect Study Id"})
            
            study.members.remove(request.user)
            if study.members.count() == 0:
                study.delete()
            return Response(status=200)

        elif request.data["RequestType"] == "RequestRecordingList":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "ParticipantId"]):
                return Response(status=400, data={"message": "Malformed Input"})

            if not Database.checkManagePermission(request.user, request.data["ParticipantId"]):
                return Response(status=403)
            
            Overview = DataAnalysis.queryAllRecordings(request.data["ParticipantId"])
            return Response(status=200, data=Overview)
        
        elif request.data["RequestType"] == "EditStudyAccessPermission":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "ParticipantId", "StudyId", "Permissions"]):
                return Response(status=400, data={"message": "Malformed Input"})

            study = models.Study.find(uid=request.data["StudyId"])
            if not study:
                return Response(status=400, data={"message": "Incorrect Study Id"})
            
            if not models.StudyRel.find(member=request.user, study=study, permission__Position="Admin"):
                return Response(status=403)
            
            if not study.participants.filter(uid=request.data["ParticipantId"]).exists():
                return Response(status=403)

            if not Database.checkManagePermission(request.user, request.data["ParticipantId"]):
                return Response(status=403)
            
            Participant = models.Participant.find(uid=request.data["ParticipantId"])
            rel = models.StudyDataRel.find(study=study, participant=Participant)
            if len(request.data["Permissions"]["Recordings"]) == 0 and len(request.data["Permissions"]["Surveys"]) == 0:
                rel.permission = {}
            else:
                rel.permission["Recordings"] = request.data["Permissions"]["Recordings"]
                rel.permission["Surveys"] = request.data["Permissions"]["Surveys"]
            rel.save()

            return Response(status=200)

        elif request.data["RequestType"] == "AddParticipant":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "StudyId", "ParticipantId"]):
                return Response(status=400, data={"message": "Malformed Input"})

            study = models.Study.find(uid=request.data["StudyId"])
            if not study:
                return Response(status=400, data={"message": "Incorrect Study Id"})
            
            if not Database.checkManagePermission(request.user, request.data["ParticipantId"]):
                return Response(status=403)
            
            Participant = models.Participant.find(uid=request.data["ParticipantId"])
            study.participants.add(Participant)
            return Response(status=200)

        elif request.data["RequestType"] == "RemoveParticipant":
            if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "StudyId", "ParticipantId"]):
                return Response(status=400, data={"message": "Malformed Input"})

            study = models.Study.find(uid=request.data["StudyId"])
            if not study:
                return Response(status=400, data={"message": "Incorrect Study Id"})
            
            if not Database.checkManagePermission(request.user, request.data["ParticipantId"]):
                return Response(status=403)
            
            Participant = models.Participant.find(uid=request.data["ParticipantId"])
            study.participants.remove(Participant)
            return Response(status=200)
        
        return Response(status=400, data={"message": "Malformed Input"})

class CheckAccessPermission(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        
        if Permissions:
            return Response(status=200)
        
        return Response(status=403)