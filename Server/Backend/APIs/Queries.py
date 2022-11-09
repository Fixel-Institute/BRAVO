import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response
from django.http import HttpResponse

from Backend import models

from modules import Database, ImageDatabase
from modules.Percept import Therapy, BrainSenseSurvey, BrainSenseEvent, BrainSenseStream, IndefiniteStream, ChronicBrainSense, TherapeuticPrediction
from utility.PythonUtility import uniqueList
import json
import numpy as np

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class QueryDatabaseInfo(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            databaseInfo = Database.getDatabaseInfo(request.user)
            return Response(status=200, data=databaseInfo)
        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryPatientList(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            Patients = Database.extractPatientList(request.user)
            return Response(status=200, data=Patients)
        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryPatientInfo(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not request.session["patient_deidentified_id"] == request.data["id"]:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.session["patient_deidentified_id"])
            if Authority["Level"] == 0:
                return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

            if Authority["Level"] == 1:
                Patient = Database.extractPatientInfo(request.user, request.session["patient_deidentified_id"])
                return Response(status=200, data=Patient)

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.session["patient_deidentified_id"])
                deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                Patient = Database.extractPatientInfo(request.user, PatientInfo.deidentified_id)
                Patient["Devices"] = deidentification["Devices"]
                return Response(status=200, data=Patient)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryTherapyHistory(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if "id" in request.data:
                if not request.session["patient_deidentified_id"] == request.data["id"]:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.session["patient_deidentified_id"])
                if Authority["Level"] == 0:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                PatientID = request.session["patient_deidentified_id"]
                if Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, PatientID, Authority, "TherapyHistory")
                elif Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, PatientID)
                    Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "TherapyHistory")
                    PatientID = PatientInfo.authorized_patient_id

                TherapyChangeLogs = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
                TherapyConfigurations = Therapy.queryTherapyConfigurations(request.user, PatientID, Authority, therapy_type="")
                TherapyConfigurations = Therapy.extractTherapyDetails(TherapyConfigurations, TherapyChangeLog=TherapyChangeLogs, resolveConflicts=False)
                return Response(status=200, data={"TherapyChangeLogs": TherapyChangeLogs, "TherapyConfigurations": TherapyConfigurations})

            return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryBrainSenseSurveys(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if "id" in request.data:
                if not request.session["patient_deidentified_id"] == request.data["id"]:
                    return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 0:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                if Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseSurvey")
                    data = BrainSenseSurvey.querySurveyResults(request.user, request.data["id"], Authority)
                    return Response(status=200, data=data)

                elif Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, request.data["id"])
                    Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseSurvey")
                    data = BrainSenseSurvey.querySurveyResults(request.user, PatientInfo.authorized_patient_id, Authority)
                    return Response(status=200, data=data)

            return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryBrainSenseStreaming(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not request.session["patient_deidentified_id"] == request.data["id"]:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})
                
            if not "ProcessingSettings" in request.session:
                request.session["ProcessingSettings"] = Database.retrieveProcessingSettings(request.session)
                request.session.modified = True

            if "requestOverview" in request.data:
                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                    data = BrainSenseStream.queryRealtimeStreamOverview(request.user, request.data["id"], Authority)
                    return Response(status=200, data=data)
                elif Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, request.data["id"])
                    Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                    data = BrainSenseStream.queryRealtimeStreamOverview(request.user, PatientInfo.authorized_patient_id, Authority)
                    return Response(status=200, data=data)

            elif "requestData" in request.data:
                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 0:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})


                if "requestFrequency" in request.data:
                    centerFrequencies = request.data["requestFrequency"]
                else:
                    centerFrequencies = [0,0]

                if Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                    BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                    if BrainSenseData == None:
                        return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                    data = BrainSenseStream.processRealtimeStreamRenderingData(BrainSenseData, request.session["ProcessingSettings"]["RealtimeStream"], centerFrequencies=centerFrequencies)
                    return Response(status=200, data=data)

                elif Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, request.data["id"])

                    Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                    if not request.data["recordingId"] in Authority["Permission"]:
                        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                    BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                    if BrainSenseData == None:
                        return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                    data = BrainSenseStream.processRealtimeStreamRenderingData(BrainSenseData, request.session["ProcessingSettings"]["RealtimeStream"], centerFrequencies=centerFrequencies)
                    return Response(status=200, data=data)

            elif "updateStimulationPSD" in request.data:
                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 0:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                if Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                    BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                    if BrainSenseData == None:
                        return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                    BrainSenseData["Stimulation"] = BrainSenseStream.processRealtimeStreamStimulationAmplitude(BrainSenseData)
                    StimPSD = BrainSenseStream.processRealtimeStreamStimulationPSD(BrainSenseData, request.data["channel"], method=request.session["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"], stim_label="Ipsilateral", centerFrequency=request.data["centerFrequency"])
                    return Response(status=200, data=StimPSD)

                elif Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, request.data["id"])

                    Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                    if not request.data["recordingId"] in Authority["Permission"]:
                        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                    BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                    if BrainSenseData == None:
                        return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                    data = BrainSenseStream.processRealtimeStreamRenderingData(BrainSenseData, request.session["ProcessingSettings"]["RealtimeStream"])
                    return Response(status=200, data=data)

            elif "updateCardiacFilter" in request.data:
                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 0 or Authority["Level"] == 2:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                elif Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                else:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                
                BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=True, cardiacFilter=request.data["updateCardiacFilter"])
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                data = BrainSenseStream.processRealtimeStreamRenderingData(BrainSenseData, request.session["ProcessingSettings"]["RealtimeStream"])
                return Response(status=200, data=data)

            return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryIndefiniteStreaming(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not "patient_deidentified_id" in request.session:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if not request.session["patient_deidentified_id"] == request.data["id"]:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if "requestOverview" in request.data:
                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "IndefiniteStream")
                    data = IndefiniteStream.queryMontageDataOverview(request.user, request.data["id"], Authority)
                    return Response(status=200, data=data)
                elif Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, request.data["id"])
                    Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "IndefiniteStream")
                    data = IndefiniteStream.queryMontageDataOverview(request.user, PatientInfo.authorized_patient_id, Authority)
                    return Response(status=200, data=data)

            elif "requestData" in request.data:
                timestamps = request.data["timestamps"]
                devices = request.data["devices"]

                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 0:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                PatientID = request.session["patient_deidentified_id"]
                if Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, request.data["id"])
                    deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                    DeviceIDs = [deidentification["Devices"][i]["ID"] for i in range(len(deidentification["Devices"]))]
                    for device in devices:
                        if not device in DeviceIDs:
                            return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                    PatientID = PatientInfo.authorized_patient_id

                Authority["Permission"] = Database.verifyPermission(request.user, PatientID, Authority, "IndefiniteStream")
                data = IndefiniteStream.queryMontageData(request.user, devices, timestamps, Authority)
                return Response(status=200, data=data)

            return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryChronicBrainSense(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not "patient_deidentified_id" in request.session:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if not request.session["patient_deidentified_id"] == request.data["id"]:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if "requestData" in request.data and "timezoneOffset" in request.data:
                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 0:
                    return Response(status=404)

                elif Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
                    PatientID = request.data["id"]

                elif Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, request.data["id"])
                    deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                    Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
                    PatientID = PatientInfo.authorized_patient_id

                data = dict()
                TherapyHistory = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
                data["ChronicData"] = ChronicBrainSense.queryChronicLFPs(request.user, PatientID, TherapyHistory, Authority)
                data["EventPSDs"] = BrainSenseEvent.queryPatientEventPSDs(request.user, PatientID, TherapyHistory, Authority)

                data["ChronicData"] = ChronicBrainSense.processChronicLFPs(data["ChronicData"], int(request.data["timezoneOffset"]))
                data["EventPSDs"] = BrainSenseEvent.processEventPSDs(data["EventPSDs"])

                return Response(status=200, data=data)

            return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryPredictionModel(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not request.session["patient_deidentified_id"] == request.data["id"]:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if "updatePredictionModels" in request.data:
                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 0:
                    return Response(status=403)

                if Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, request.data["id"])
                    deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                    DeviceIDs = [deidentification["Devices"][i]["ID"] for i in range(len(deidentification["Devices"]))]
                    if not request.data["requestData"] in DeviceIDs:
                        return Response(status=403)
                    Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "BrainSenseStream")
                else:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")

                BrainSenseData, _ = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                if BrainSenseData == None:
                    return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                BrainSenseData["Stimulation"] = BrainSenseStream.processRealtimeStreamStimulationAmplitude(BrainSenseData)

                data = list()
                for stimulationSide in BrainSenseData["Stimulation"]:
                    if len(np.unique(stimulationSide["Amplitude"])) > 3:
                        if not models.PredictionModel.objects.filter(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"]).exists():
                            Features = TherapeuticPrediction.extractPredictionFeatures(BrainSenseData, stimulationSide["Hemisphere"])
                            PredictionModel = models.PredictionModel(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"], model_details=Features)
                            PredictionModel.save()
                        else:
                            PredictionModel = models.PredictionModel.objects.filter(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"]).first()
                            Features = PredictionModel.model_details
                            Features = TherapeuticPrediction.extractPredictionFeatures(BrainSenseData, stimulationSide["Hemisphere"])
                            PredictionModel.model_details = Features
                            PredictionModel.save()
                        data.append(Features)
                    else:
                        data.append({"NoPrediction": True})
                    
                return Response(status=200, data=data)

            elif "updateStimulationPSD" in request.data:
                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 0:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                if Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "BrainSenseStream")
                    BrainSenseData, RecordingID = BrainSenseStream.queryRealtimeStreamRecording(request.user, request.data["recordingId"], Authority, refresh=False)
                    if BrainSenseData == None:
                        return Response(status=400, data={"code": ERROR_CODE["DATA_NOT_FOUND"]})
                    BrainSenseData["Stimulation"] = BrainSenseStream.processRealtimeStreamStimulationAmplitude(BrainSenseData)
                    
                    data = dict()
                    data["StimPSD"] = BrainSenseStream.processRealtimeStreamStimulationPSD(BrainSenseData, request.data["channel"], method=request.session["ProcessingSettings"]["RealtimeStream"]["SpectrogramMethod"]["value"], stim_label="Ipsilateral", centerFrequency=request.data["centerFrequency"])
                    
                    if not "CenterFrequency" in BrainSenseData["Info"]:
                        BrainSenseData["Info"]["CenterFrequency"] = dict()
                    BrainSenseData["Info"]["CenterFrequency"][request.data["channel"]] = request.data["centerFrequency"]
                    models.BrainSenseRecording.objects.filter(recording_id=RecordingID).update(recording_info=BrainSenseData["Info"])
    
                    for stimulationSide in BrainSenseData["Stimulation"]:
                        if len(np.unique(stimulationSide["Amplitude"])) > 3 and stimulationSide["Name"] == request.data["channel"]:
                            Features = TherapeuticPrediction.extractPredictionFeatures(BrainSenseData, stimulationSide["Hemisphere"], centerFrequency=request.data["centerFrequency"])
                            PredictionModel = models.PredictionModel.objects.filter(recording_id=request.data["recordingId"], recording_channel=stimulationSide["Name"]).first()
                            PredictionModel.model_details = Features
                            PredictionModel.save()
                        else:
                            Features = {"NoPrediction": True}

                    data["PredictionModel"] = Features
                    return Response(status=200, data=data)

            return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryPatientEvents(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not "patient_deidentified_id" in request.session:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.session["patient_deidentified_id"])
            if Authority["Level"] == 0:
                return Response(status=404)

            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.session["patient_deidentified_id"], Authority, "ChronicLFPs")
                PatientID = request.session["patient_deidentified_id"]

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.session["patient_deidentified_id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
                PatientID = PatientInfo.authorized_patient_id

            data = dict()
            data["EventPSDs"] = BrainSenseEvent.getAllPatientEvents(request.user, PatientID, Authority)
            return Response(status=200, data=data)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryImageModelDirectory(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not "patient_deidentified_id" in request.session:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.session["patient_deidentified_id"])
            if Authority["Level"] == 0:
                return Response(status=404)

            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.session["patient_deidentified_id"], Authority, "ChronicLFPs")
                PatientID = request.session["patient_deidentified_id"]

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.session["patient_deidentified_id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "Imaging")
                PatientID = PatientInfo.authorized_patient_id

            data = ImageDatabase.extractAvailableModels(PatientID, Authority)
            return Response(status=200, data=data)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryImageModel(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not "patient_deidentified_id" in request.session:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.session["patient_deidentified_id"])
            if Authority["Level"] == 0:
                return Response(status=404)

            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.session["patient_deidentified_id"], Authority, "ChronicLFPs")
                PatientID = request.session["patient_deidentified_id"]

            elif Authority["Level"] == 2:
                PatientInfo = Database.extractAccess(request.user, request.session["patient_deidentified_id"])
                Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "Imaging")
                if not request.data["FileName"] in Authority["Permission"]:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
                PatientID = PatientInfo.authorized_patient_id

            if request.data["FileMode"] == "single":
                if request.data["FileType"] == "stl":
                    file_data = ImageDatabase.stlReader(PatientID, request.data["FileName"])
                    if not file_data:
                        return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                    return HttpResponse(bytes(file_data), status=200, headers={
                        "Content-Type": "application/octet-stream"
                    })

                elif request.data["FileType"] == "tracts":
                    tracts = ImageDatabase.tractReader(PatientID, request.data["FileName"])
                    if not tracts:
                        return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

                    return Response(status=200, data={
                        "points": tracts
                    })

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryAdaptiveGroups(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not "id" in request.data:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            Authority = {}
            Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
            if Authority["Level"] == 0 or Authority["Level"] == 2:
                return Response(status=404)

            elif Authority["Level"] == 1:
                Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
                PatientID = request.session["patient_deidentified_id"]

            data = Therapy.queryAdaptiveGroupForThreshold(request.user, PatientID, Authority)
            return Response(status=200, data=data)

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

class QueryCircadianPower(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if request.user.is_authenticated:
            if not "patient_deidentified_id" in request.session:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if not request.session["patient_deidentified_id"] == request.data["id"]:
                return Response(status=400, data={"code": ERROR_CODE["IMPROPER_SUBMISSION"]})

            if "id" in request.data and "timezoneOffset" in request.data and "therapyInfo" in request.data:
                Authority = {}
                Authority["Level"] = Database.verifyAccess(request.user, request.data["id"])
                if Authority["Level"] == 0:
                    return Response(status=404)

                elif Authority["Level"] == 1:
                    Authority["Permission"] = Database.verifyPermission(request.user, request.data["id"], Authority, "ChronicLFPs")
                    PatientID = request.data["id"]

                elif Authority["Level"] == 2:
                    PatientInfo = Database.extractAccess(request.user, request.data["id"])
                    deidentification = Database.extractPatientInfo(request.user, PatientInfo.authorized_patient_id)
                    Authority["Permission"] = Database.verifyPermission(request.user, PatientInfo.authorized_patient_id, Authority, "ChronicLFPs")
                    PatientID = PatientInfo.authorized_patient_id

                data = dict()
                TherapyHistory = Therapy.queryTherapyHistory(request.user, PatientID, Authority)
                data["ChronicData"] = ChronicBrainSense.queryChronicLFPs(request.user, PatientID, TherapyHistory, Authority)
                data["EventPSDs"] = BrainSenseEvent.queryPatientEventPSDs(request.user, PatientID, TherapyHistory, Authority)
                data["CircadianPower"] = ChronicBrainSense.processCircadianPower(data["ChronicData"], request.data["therapyInfo"], int(request.data["timezoneOffset"]))
                return Response(status=200, data=data["CircadianPower"])

            return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

        return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})
