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
Data Upload Handler Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os
import json
import traceback
from copy import deepcopy
import pickle
from pathlib import Path
import hmac, hashlib
from io import BytesIO
import datetime
import pandas as pd
import numpy as np
from filelock import Timeout, FileLock

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings

from Server import models
from modules.HelperFunctions import sanitize_input, get_or_none, current_time
from modules import Database, DataCurator, DataAnalysis, ImageDatabase, Therapy

DATABASE_PATH = os.environ.get('DATASERVER_PATH')
HASH_KEY = os.environ.get('DATASERVER_HASHKEY')

class DataUploadHandler(RestViews.APIView):

    parser_classes = [RestParsers.MultiPartParser, RestParsers.FormParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "DataType", "Institute", "Metadata", "File"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        if request.data["Institute"] == "":
            institute = request.user.institute
        else:
            institute = models.Institute.find(name=request.data["Institute"])

        if not institute:
            return Response(status=403)
        
        if not institute.has_permission(request.user, "Upload"):
            return Response(status=403)
        
        if ".." in request.data["File"].name or os.path.sep in request.data["File"].name:
            return Response(status=400, data={"message": "Filename not Supported"})
        
        rawBytes = request.data["File"].read()
        metadata = {**{
            "UploadType": request.data["DataType"],
            "Institute": institute.pk,
            "Uploader": request.user.pk,
            "UniqueHashed": hmac.new(HASH_KEY.encode("utf8"), rawBytes, hashlib.sha256).hexdigest()
        }, **json.loads(request.data["Metadata"])}

        source_file = DataCurator.saveCacheFile(request.data["File"].name, metadata, rawBytes)
        lock = FileLock(DATABASE_PATH + "SourceFileDuplicateCheck.lock")
        with lock.acquire(timeout=60):
            if models.SourceFile.objects.exclude(pk=source_file.pk).filter(metadata__Institute=institute.pk, metadata__UniqueHashed=metadata["UniqueHashed"]).exists():
                print("Duplicate File Found")
                source_file.delete()
                return Response(status=301)
        
        lockFile = source_file.pointer + ".lock"
        if request.data["DataType"] == "DefaultType":
            try:
                if not request.data["ParticipantId"] == "batch-upload":
                    if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Upload"):
                        return Response(status=403)

                    person = models.Participant.find(uid=request.data["ParticipantId"])
                    if not person:
                        return Response(status=400, data={"message": "Participant not found."})
                    
                    if not person.institute.uid == institute.uid:
                        return Response(status=403)
                    source_file.owner = person
                    source_file.save()
                
                if source_file.pointer.endswith(".json"):
                    source_file.metadata = {**source_file.metadata, **{"device_location": "", "automatic_deidentification": False, "infer_from_device": True, "automatic_concatenation": False}}
                    DataCurator.MedtronicPerceptJSONDecoder(source_file, person=source_file.owner)
                elif source_file.pointer.endswith(".mpx"):
                    source_file.metadata = {**source_file.metadata, **{"device_location": "", "infer_from_device": True}}
                    DataCurator.AlphaOmegaMPXDecoder(source_file, person=source_file.owner, name=request.data["File"].name)
                elif source_file.pointer.endswith(".mdat"):
                    DataCurator.UFMDATv3Decoder(source_file, person=source_file.owner)
                elif source_file.pointer.endswith(".mat"):
                    DataCurator.MATFileDecoder(source_file, person=source_file.owner)
                else:
                    raise Exception("File type not supported for Default Upload. Please specify the Data Type for this file.")

            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

        if request.data["DataType"] == "MedtronicJSON":
            try:
                if not request.data["ParticipantId"] == "batch-upload":
                    if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Upload"):
                        return Response(status=403)

                    person = models.Participant.find(uid=request.data["ParticipantId"])
                    if not person:
                        return Response(status=400, data={"message": "Participant not found."})
                    
                    if not person.institute.uid == institute.uid:
                        return Response(status=403)
                    source_file.owner = person
                    source_file.save()
                    
                    DataCurator.MedtronicPerceptJSONDecoder(source_file, person=person)
                else:
                    DataCurator.MedtronicPerceptJSONDecoder(source_file)
                    
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})
            
        elif request.data["DataType"] == "NeuroPacePersystDAT":
            try:
                if not request.data["ParticipantId"] == "batch-upload":
                    if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Upload"):
                        return Response(status=403)

                    person = models.Participant.find(uid=request.data["ParticipantId"])
                    if not person:
                        return Response(status=400, data={"message": "Participant not found."})
                    
                    if not person.institute.uid == institute.uid:
                        return Response(status=403)
                    source_file.owner = person
                    source_file.save()
                    
                    DataCurator.NeuroPacePersystDatDecoder(source_file, person=person)
                else:
                    DataCurator.NeuroPacePersystDatDecoder(source_file)
                    
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})
            
        elif request.data["DataType"] == "BRAVOExportv1":
            try:
                DataCurator.ImportBRAVOExport(source_file)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})
            source_file.delete()
            
        elif request.data["DataType"] == "BRAVOExportv2":
            try:
                participant = DataCurator.ImportBRAVOStructure(source_file)
                participant.institute = request.user.institute
                participant.save()
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})
            source_file.delete()
            
        elif request.data["DataType"] == "AlphaOmegaMPX":
            person = models.Participant.find(uid=request.data["ParticipantId"])
            if not person:
                return Response(status=400, data={"message": "Participant not found."})
            
            if not person.institute.uid == institute.uid:
                return Response(status=403)
            source_file.owner = person
            source_file.save()
            
            try:
                DataCurator.AlphaOmegaMPXDecoder(source_file, person, name=request.data["File"].name)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

        elif request.data["DataType"] == "UFMDAT":
            person = models.Participant.find(uid=request.data["ParticipantId"])
            if not person:
                return Response(status=400, data={"message": "Participant not found."})
            
            if not person.institute.uid == institute.uid:
                return Response(status=403)
            source_file.owner = person
            source_file.save()
            
            try:
                DataCurator.UFMDATDecoder(source_file, person)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

        elif request.data["DataType"] == "BRAVORecordingBinaryStructure":
            person = models.Participant.find(uid=request.data["ParticipantId"])
            if not person:
                return Response(status=400, data={"message": "Participant not found."})
            
            if not person.institute.uid == institute.uid:
                return Response(status=403)
            source_file.owner = person
            source_file.save()
            
            try:
                DataCurator.BRAVORecordingBinaryDecoder(source_file, person)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

        elif request.data["DataType"] == "UFMDATv2":
            person = models.Participant.find(uid=request.data["ParticipantId"])
            if not person:
                return Response(status=400, data={"message": "Participant not found."})
            
            if not person.institute.uid == institute.uid:
                return Response(status=403)
            source_file.owner = person
            source_file.save()
            
            try:
                DataCurator.UFMDATv2Decoder(source_file, person)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

        elif request.data["DataType"] == "UFMDATv3":
            person = models.Participant.find(uid=request.data["ParticipantId"])
            if not person:
                return Response(status=400, data={"message": "Participant not found."})
            
            if not person.institute.uid == institute.uid:
                return Response(status=403)
            source_file.owner = person
            source_file.save()
            
            try:
                DataCurator.UFMDATv3Decoder(source_file, person)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

        elif request.data["DataType"] == "MATFile":
            person = models.Participant.find(uid=request.data["ParticipantId"])
            if not person:
                return Response(status=400, data={"message": "Participant not found."})
            
            if not person.institute.uid == institute.uid:
                return Response(status=403)
            source_file.owner = person
            source_file.save()

            try:
                if "StartTime" in metadata.keys():
                    DataCurator.MATFileDecoder(source_file, person, startTime=metadata["StartTime"])
                else:
                    DataCurator.MATFileDecoder(source_file, person)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

        elif request.data["DataType"] == "HPFCSV":
            person = models.Participant.find(uid=request.data["ParticipantId"])
            if not person:
                return Response(status=400, data={"message": "Participant not found."})
            
            if not person.institute.uid == institute.uid:
                return Response(status=403)
            source_file.owner = person
            source_file.save()

            try:
                if "StartTime" in metadata.keys():
                    DataCurator.HPFCSVDecoder(source_file, person, startTime=metadata["StartTime"])
                else:
                    DataCurator.HPFCSVDecoder(source_file, person)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

        elif request.data["DataType"] == "EventCSV":
            person = models.Participant.find(uid=request.data["ParticipantId"])
            if not person:
                return Response(status=400, data={"message": "Participant not found."})
            
            if not person.institute.uid == institute.uid:
                return Response(status=403)
            source_file.owner = person
            source_file.save()

            try:
                DataCurator.EventCSVDecoder(source_file, person)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

            source_file.delete()
            
        elif request.data["DataType"] == "NeuroImage":
            person = models.Participant.find(uid=request.data["ParticipantId"])
            if not person:
                return Response(status=400, data={"message": "Participant not found."})
            
            if not person.institute.uid == institute.uid:
                return Response(status=403)
            source_file.owner = person
            source_file.save()

            try:
                DataCurator.NeuroImageStorage(source_file, person)
            except Exception as e:
                print(request.data["File"].name)
                print(traceback.format_exc())
                source_file.delete()
                return Response(status=400, data={"message": str(e)})

        get_or_none(os.remove)(lockFile)
        return Response(status=200)

class DataDownloadHandler(RestViews.APIView):

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def get(self, request):
        CacheType = self.request.query_params.get('CacheType')
        if CacheType == "ClearDataUpload":
            models.SourceFile.objects.filter(metadata__Uploader=request.user.pk, owner=None).delete()
            return Response(status=200)

        ParticipantId = self.request.query_params.get('ParticipantId')
        Permissions = Database.checkAccessPermission(request.user, ParticipantId, 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)

        if CacheType == "queryTherapeuticEffectAnalysis":
            AnalysisId = self.request.query_params.get('AnalysisId')
            userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            FilePointer = DataAnalysis.downloadTherapeuticAnalysis(ParticipantId, AnalysisId, userConfig)
            
            with BytesIO() as fp:
                FilePointer.to_csv(fp, index=False)
                filename = "TherapeuticEffectAnalysis_" + ParticipantId + "_" + AnalysisId + ".csv"
                response = HttpResponse( fp.getvalue(), content_type="text/csv" )
                response["Content-Disposition"] = "attachment; filename=" + filename
                return response

        elif CacheType == "queryNeuralActivitySnapshot":
            userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            Snapshots = DataAnalysis.downloadNeuralActivitySnapshot(ParticipantId, userConfig)
            file_data = pickle.dumps(Snapshots)
            
            response = HttpResponse(bytes(file_data), status=200, headers={
                "Content-Type": "application/octet-stream"
            })
            response["Content-Disposition"] = "attachment; filename=NeuralActivitySnapshots_" + ParticipantId + ".pkl"
            return response

        elif CacheType == "queryTimeseriesAnalysis":
            RecordingId = self.request.query_params.get('RecordingId')
            userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            FilePointer = DataAnalysis.downloadTimeseriesAnalysis(ParticipantId, RecordingId, userConfig)
            
            with BytesIO() as fp:
                FilePointer.to_csv(fp, index=False)
                filename = "Timeseries_" + ParticipantId + "_" + RecordingId + ".csv"
                response = HttpResponse( fp.getvalue(), content_type="text/csv" )
                response["Content-Disposition"] = "attachment; filename=" + filename
                return response

        elif CacheType == "queryImageModel":
            RecordingId = self.request.query_params.get('RecordingId')
            file = models.SourceFile.find(uid=RecordingId)
            if not file.owner.uid == ParticipantId:
                return Response(status=403)
            
            file_data = DataCurator.loadCacheFile(file)
            return HttpResponse(bytes(file_data), status=200, headers={
                "Content-Type": "application/octet-stream"
            })
        
        elif CacheType == "queryTherapyHistory":
            Participant = models.Participant.find(uid=ParticipantId)
            TherapyHistory = Therapy.queryTherapyHistory(Participant)
            TherapyHistory["DeviceImpedance"] = Therapy.queryElectrodeImpedances(Participant)

            if self.request.query_params.get('RequestType') == "Raw":
                file_data = json.dumps(TherapyHistory, indent=4)
                return HttpResponse(file_data, status=200, headers={
                    "Content-Type": "application/json"
                })
            
            elif self.request.query_params.get('RequestType') == "TherapyModification":
                TherapyExport = []
                for i in range(len(TherapyHistory["TherapyModification"])):
                    for j in range(len(TherapyHistory["TherapyModification"][i]["History"])):
                        Record = {
                            "Date": datetime.datetime.fromtimestamp(TherapyHistory["TherapyModification"][i]["History"][j]["Date"]).isoformat(),
                            "Type": TherapyHistory["TherapyModification"][i]["History"][j]["Type"],
                            "Device": TherapyHistory["TherapyModification"][i]["Device"]["Name"],
                            "Location": TherapyHistory["TherapyModification"][i]["Device"]["Location"],
                        }
                        Record["Previous State"] = TherapyHistory["TherapyModification"][i]["History"][j]["Previous"]
                        Record["New State"] = TherapyHistory["TherapyModification"][i]["History"][j]["New"]
                        TherapyExport.append(Record)

                with BytesIO() as fp:
                    pd.DataFrame(TherapyExport).to_csv(fp, index=False)
                    filename = "TherapyModification_" + ParticipantId + ".csv"
                    response = HttpResponse( fp.getvalue(), content_type="text/csv" )
                    response["Content-Disposition"] = "attachment; filename=" + filename
                    return response
                
            elif self.request.query_params.get('RequestType') == "TherapyHistory":
                TherapyExport = []
                for i in range(len(TherapyHistory["TherapyConfiguration"])):
                    for j in range(len(TherapyHistory["TherapyConfiguration"][i]["History"])):
                        Record = {
                            "Date": datetime.datetime.fromtimestamp(TherapyHistory["TherapyConfiguration"][i]["History"][j]["Date"]).isoformat(),
                            "Timezone": TherapyHistory["TherapyConfiguration"][i]["History"][j]["Timezone"],
                            "Type": TherapyHistory["TherapyConfiguration"][i]["History"][j]["Type"],
                            "Group": TherapyHistory["TherapyConfiguration"][i]["History"][j]["GroupId"],
                            "StimulationType": TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationType"]
                        }

                        for hemisphere in ["Left", "Right"]:
                            for k in range(len(TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationSettings"])):
                                if TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationSettings"][k]["Electrode"]["Target"].startswith(hemisphere):
                                    if (hemisphere + " Program 1 Target") in Record.keys():
                                        ProgramName = hemisphere + " Program 2"
                                    else:
                                        ProgramName = hemisphere + " Program 1"

                                    Record[ProgramName + " Target"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationSettings"][k]["Electrode"]["CustomName"]
                                    Record[ProgramName + " Electrode"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationSettings"][k]["Electrode"]["Type"]
                                    Record[ProgramName + " Stimulation Contact"] = "+".join(TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationSettings"][k]["Contact"])
                                    Record[ProgramName + " Return Contact"] = "+".join(TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationSettings"][k]["ReturnContact"])
                                    Record[ProgramName + " Frequency"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationSettings"][k]["Frequency"]
                                    Record[ProgramName + " Pulsewidth"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationSettings"][k]["Pulsewidth"]
                                    Record[ProgramName + " Amplitude"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["StimulationSettings"][k]["Amplitude"]

                                    if not TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["RecordingConfiguration"]["Type"] == "Unknown":
                                        Record[ProgramName + " Sense Frequency"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["RecordingConfiguration"]["Config"]["SensingSetup"]["FrequencyInHertz"]
                                        Record[ProgramName + " Sense Average Duration"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["RecordingConfiguration"]["Config"]["SensingSetup"]["AveragingDurationInMilliSeconds"]
                                        Record[ProgramName + " Sense Thresholds"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["RecordingConfiguration"]["Config"]["Thresholds"]["LFPThresholds"]

                                    if not TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["StimulationConfiguration"]["Type"] == "Unknown":
                                        if "Mode" in TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["StimulationConfiguration"]["Config"].keys():
                                            Record[ProgramName + " Adaptive Mode"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["StimulationConfiguration"]["Config"]["Mode"]
                                        else:
                                            Record[ProgramName + " Adaptive Mode"] = "NOT_CONFIGURED"

                                        Record[ProgramName + " Adaptive Onset"] = [
                                            TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["StimulationConfiguration"]["Config"]["UpperThresholdOnsetInMilliSeconds"],
                                            TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["StimulationConfiguration"]["Config"]["LowerThresholdOnsetInMilliSeconds"]
                                        ]
                                        Record[ProgramName + " Adaptive Blanking"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["StimulationConfiguration"]["Config"]["DetectionBlankingDurationInMilliSeconds"]

                                        if "Bypass" in TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["StimulationConfiguration"]["Config"].keys():
                                            Record[ProgramName + " Adaptive Feedback"] = TherapyHistory["TherapyConfiguration"][i]["History"][j]["AdaptiveSettings"][k]["StimulationConfiguration"]["Config"]["Bypass"]
                                        else:
                                            Record[ProgramName + " Adaptive Feedback"] = "Self"

                        TherapyExport.append(Record)

                with BytesIO() as fp:
                    pd.DataFrame(TherapyExport).to_csv(fp, index=False)
                    filename = "TherapyHistory_" + ParticipantId + ".csv"
                    response = HttpResponse( fp.getvalue(), content_type="text/csv" )
                    response["Content-Disposition"] = "attachment; filename=" + filename
                    return response
                
            else:
                return Response(status=403)

        
        elif CacheType == "queryChronicNeuralActivity":
            userConfig, _ = Database.retrieveProcessingSettings(request.user.configuration)
            userConfig["APIAccess"] = hasattr(request.user, "api_access")
            FilePointer = DataAnalysis.downloadChronicNeuralActivity(ParticipantId, userConfig)
            
            with BytesIO() as fp:
                FilePointer.to_csv(fp, index=False)
                filename = "ChronicNeuralActivity_" + ParticipantId + ".csv"
                response = HttpResponse( fp.getvalue(), content_type="text/csv" )
                response["Content-Disposition"] = "attachment; filename=" + filename
                return response

        return Response(status=200)
        
    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "CacheType", "DataId"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)

        if request.data["CacheType"] == "queryImageModel":
            file = models.SourceFile.find(uid=request.data["DataId"])
            if not file.owner.uid == request.data["ParticipantId"]:
                return Response(status=403)
            
            if file.metadata["FileType"] == "STL":
                file_data = DataCurator.loadCacheFile(file)
                return HttpResponse(bytes(file_data), status=200, headers={
                    "Content-Type": "application/octet-stream"
                })
            
            elif file.metadata["FileType"] == "Blender Scene":
                file_data = DataCurator.loadCacheFile(file)
                return HttpResponse(bytes(file_data), status=200, headers={
                    "Content-Type": "application/octet-stream"
                })

            elif file.metadata["FileType"] == "Electrodes":
                if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "CacheType", "DataId", "RecordingId"]):
                    return Response(status=400, data={"message": "Malformed Input"})
                
                recording = models.Recording.find(uid=request.data["RecordingId"], source=file)
                if recording:
                    file_data = Database.loadSourceFile(recording.pointer, recording.hashed, bytes=True)
                    return HttpResponse(bytes(file_data), status=200, headers={
                        "Content-Type": "application/octet-stream"
                    })
        
        return Response(status=400, data={"message": "Malformed Input"})
        
class RecordingTimeShiftHandler(RestViews.APIView):

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "Analysis":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "AnalysisId", "RecordingId", "Alignment"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            Analysis = models.Analysis.find(uid=request.data["AnalysisId"])
            if not Analysis:
                return Response(status=403)
            
            Recording = Analysis.recordings.filter(uid=request.data["RecordingId"]).first()
            if not Recording.source.owner.uid == request.data["ParticipantId"]:
                return Response(status=403)
            
            rel = models.RecordingRel.find(analysis=Analysis, recording=Recording)
            if not rel:
                return Response(status=403)
            
            try:
                Recording.adjusted_alignment = float(request.data["Alignment"])
                Recording.save()
            except:
                return Response(status=400, data={"message": "Time Alignment is not valid"})

        elif request.data["RequestType"] == "Recording":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "RecordingId", "Alignment"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            Recording = models.Recording.objects.filter(uid=request.data["RecordingId"]).first()
            if not Recording.source.owner.uid == request.data["ParticipantId"]:
                return Response(status=403)

            if Recording.type in ["SynchronizedMDAT", "CustomizedStreamingData", "CustomizedTimelineData", "ExternalSensorStreaming"]:
                related_recordings = models.Recording.find_all(source=Recording.source)
            else:
                related_recordings = [Recording]
                
            for rec in related_recordings:
                try:
                    rec.adjusted_alignment = float(request.data["Alignment"])
                    rec.save()
                except:
                    return Response(status=400, data={"message": "Time Alignment is not valid"})

        return Response(status=200)

class TimeSeriesRecordingHandler(RestViews.APIView):

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        if request.data["RequestType"] == "Overview":
            Recordings = Database.listRecordings(request.data["ParticipantId"])
            return Response(status=200, data=Recordings)

        elif request.data["RequestType"] == "RawTimeseries":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "RecordingId"]):
                return Response(status=400, data={"message": "Malformed Input"})
        
            recording = models.Recording.find(uid=request.data["RecordingId"])
            if not recording.source.owner.uid == request.data["ParticipantId"]:
                return Response(status=403)
        
            Data = Database.loadSourceFile(recording.pointer, recording.hashed)
            Data["Alignment"] = recording.adjusted_alignment
            if "ChannelIndex" in request.data.keys():
                Data["Data"] = Data["Data"][:,int(request.data["ChannelIndex"])]
                Data["Missing"] = Data["Missing"][:,int(request.data["ChannelIndex"])]
            
            if not "Time" in Data.keys():
                Data["Time"] = np.arange(len(Data["Data"]))/Data["SamplingRate"]

            return Response(status=200, data=Data)
        return Response(status=400, data={"message": "Malformed Input"})

class DataSourceFileHandler(RestViews.APIView):

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)

        if request.data["RequestType"] == "All":
            SourceFiles = Database.listSourceFiles(request.data["ParticipantId"])
            return Response(status=200, data=SourceFiles)
        
        elif request.data["RequestType"] == "Delete":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "SourceId"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Delete"):
                return Response(status=403)
        
            Participant = models.Participant.find(uid=request.data["ParticipantId"])
            source = models.SourceFile.find(uid=request.data["SourceId"], owner=Participant)
            if not source:
                return Response(status=400, data={"message": "Source File not found."})
            source.delete()
            return Response(status=200)

        return Response(status=400, data={"message": "Malformed Input"})
    
    def get(self, request):
        ParticipantId = self.request.query_params.get('ParticipantId')
        RequestType = self.request.query_params.get('RequestType')
        SourceId = self.request.query_params.get('SourceId')

        Permissions = Database.checkAccessPermission(request.user, ParticipantId, 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)
        
        Participant = models.Participant.find(uid=ParticipantId)
        source = models.SourceFile.find(uid=SourceId, owner=Participant)
        if not source:
            return Response(status=400, data={"message": "Source File not found."})
        
        if not source.metadata["Uploader"] == request.user.pk:
            return Response(status=403)
        
        file_data = DataCurator.loadCacheFile(source)
        with BytesIO() as fp:
            filename = source.name
            response = HttpResponse( file_data, content_type="text/json" )
            response["Content-Disposition"] = "attachment; filename=" + filename
            return response

class NeuroImageFileHandler(RestViews.APIView):

    parser_classes = [RestParsers.JSONParser]
    permission_classes = [IsAuthenticated]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        Permissions = Database.checkAccessPermission(request.user, request.data["ParticipantId"], 
                                study_uid=request.user.configuration["ActiveStudy"] if "ActiveStudy" in request.user.configuration.keys() else None)
        if not Permissions:
            return Response(status=403)

        if request.data["RequestType"] == "ListAll":
            SourceFiles = Database.listSourceFiles(request.data["ParticipantId"], file_type="NeuroImage")
            SourceFiles.append({
                "Id": "TemplateElectrode_Medtronic_B33015",
                "Name": "Medtronic_B33015",
                "Timezone": "",
                "Type": "NeuroImaging Data",
                "DateOfUpload": current_time(),
                "DateOfRecording": current_time(),
                "DataSize": 0,
                "DataType": "TemplateElectrodes"
            })
            return Response(status=200, data=SourceFiles)
        
        elif request.data["RequestType"] == "Delete":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "SourceId"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Delete"):
                return Response(status=403)
            
            Participant = models.Participant.find(uid=request.data["ParticipantId"])
            source = models.SourceFile.find(uid=request.data["SourceId"], owner=Participant)
            if not source:
                return Response(status=400, data={"message": "Source File not found."})
            source.delete()
            return Response(status=200)

        elif request.data["RequestType"] == "UpdateModel":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "SourceId", "Metadata"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if not Database.checkManagePermission(request.user, request.data["ParticipantId"], "Edit"):
                return Response(status=403)
            
            Participant = models.Participant.find(uid=request.data["ParticipantId"])
            source = models.SourceFile.find(uid=request.data["SourceId"], owner=Participant)
            if not source:
                return Response(status=400, data={"message": "Source File not found."})
            
            for key in request.data["Metadata"].keys():
                if key == "Name":
                    source.name = request.data["Metadata"]["Name"]
                else:
                    source.metadata[key] = request.data["Metadata"][key]
            
            source.save()
            return Response(status=200)

        elif request.data["RequestType"] == "GetPagination":
            if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "SourceId"]):
                return Response(status=400, data={"message": "Malformed Input"})
            
            if request.data["SourceId"].startswith("TemplateElectrode"):
                if not get_or_none(sanitize_input)(request.data, required_keys=["ParticipantId", "RequestType", "SourceId", "ElectrodeName"]):
                    return Response(status=400, data={"message": "Malformed Input"})

                if request.data["ElectrodeName"] == "Medtronic_B33015":
                    model = ImageDatabase.createElectrodeSourceFile(request.data["ParticipantId"], request.data["ElectrodeName"])
                    recordings = models.Recording.find_all(source=model)
                    return Response(status=200, data=[{
                        "RecordingId": recording.uid,
                        "SourceId": model.uid,
                        "Name": recording.name,
                        "TargetPoint": model.metadata["TargetPoint"],
                        "EntryPoint": model.metadata["EntryPoint"]
                    } for recording in recordings])
            
            else:
                file = models.SourceFile.find(uid=request.data["SourceId"])
                if not file.owner.uid == request.data["ParticipantId"]:
                    return Response(status=403)
                
                if file.metadata["FileType"] == "Electrodes":
                    recordings = models.Recording.find_all(source=file)
                    return Response(status=200, data=[{
                        "RecordingId": recording.uid,
                        "SourceId": file.uid,
                        "Name": recording.name,
                        "TargetPoint": file.metadata["TargetPoint"],
                        "EntryPoint": file.metadata["EntryPoint"]
                    } for recording in recordings])

            return Response(status=200)

        return Response(status=400, data={"message": "Malformed Input"})
        