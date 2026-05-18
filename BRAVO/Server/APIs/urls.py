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
All API URLs
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from django.urls import path
from django.conf import settings

from . import Auth, WebSession, Participants
from . import FitbitDashboard, OuraRingDashboard, EmpaticaDashboard 
from . import DataHandler, EventAnnotationHandler, DataAnalysis, Therapy, GroupAnalysis, AIModels
from . import AsyncJobScheduling
from . import DataFilter

urlpatterns = [
    path('register', Auth.UserRegister.as_view()),
    path('login', Auth.UserLogin.as_view()),
    path('logout', Auth.UserLogout.as_view()),
    path('queryProfile', Auth.QueryProfile.as_view()),
    
    path('requestFitbitAuth', FitbitDashboard.FitbitAuthHandler.as_view()),
    path('queryFitbitData', FitbitDashboard.QueryFitbitData.as_view()),
    path('requestOuraRingAuth', OuraRingDashboard.OuraRingAuthHandler.as_view()),
    path('queryOuraRingData', OuraRingDashboard.QueryOuraRingData.as_view()),
    path('queryEmpaticaData', EmpaticaDashboard.QueryEmpaticaData.as_view()),

    path('downloadData', DataHandler.DataDownloadHandler.as_view()),
    path('uploadData', DataHandler.DataUploadHandler.as_view()),
    path('setRecordingTimeShift', DataHandler.RecordingTimeShiftHandler.as_view()),
    path('queryRawTimeseries', DataHandler.TimeSeriesRecordingHandler.as_view()),

    path('querySourceFiles', DataHandler.DataSourceFileHandler.as_view()),
    path('queryImageSourceFiles', DataHandler.NeuroImageFileHandler.as_view()),

    path('querySurveyForms', EventAnnotationHandler.QuerySurveyForms.as_view()),
    path('deleteSurveyForms', EventAnnotationHandler.DeleteSurveyForms.as_view()),
    path('setSurveyForms', EventAnnotationHandler.SetSurveyForms.as_view()),
    path('queryParticipantSurveyRecords', EventAnnotationHandler.QueryParticipantSurveyRecords.as_view()),
    
    path('downloadParticipantExport', Participants.ExportParticipant.as_view()),
    path('queryParticipantEvents', EventAnnotationHandler.QueryEventHandler.as_view()),
    path('queryParticipantAnnotations', EventAnnotationHandler.QueryAnnotationHandler.as_view()),
    path('addParticipantAnnotation', EventAnnotationHandler.InsertAnnotationHandler.as_view()),
    path('deleteParticipantAnnotation', EventAnnotationHandler.DeleteAnnotationHandler.as_view()),

    path('querySessions', WebSession.QuerySessionConfig.as_view()),
    path('updateSessions', WebSession.UpdateSessionConfig.as_view()),
    path('queryProcessingQueue', WebSession.QueryProcessingQueue.as_view()),

    path('queryParticipants', Participants.QueryParticipants.as_view()),
    path('queryParticipantInformation', Participants.QueryParticipantInformation.as_view()),
    path('createParticipantInformation', Participants.CreateParticipantInformation.as_view()),
    path('updateParticipantInformation', Participants.UpdateParticipantInformation.as_view()),
    path('deleteParticipantInformation', Participants.DeleteParticipantInformation.as_view()),
    path('updateDeviceInformation', Participants.UpdateDeviceInformation.as_view()),
    path('deleteDeviceInformation', Participants.DeleteDeviceInformation.as_view()),
    path('checkAccessPermission', Participants.CheckAccessPermission.as_view()),
    path('manageStudyInformation', Participants.StudyHandler.as_view()),
    
    path('manageParticipantDevice', Participants.ManageParticipantDevice.as_view()),

    path('queryAnalysisConfigurations', DataAnalysis.QueryAnalysisConfigurations.as_view()),
    path('queryTherapeuticEffectAnalysis', DataAnalysis.QueryTherapeuticEffectAnalysis.as_view()),
    path('queryNeuralActivitySnapshot', DataAnalysis.QueryNeuralActivitySnapshot.as_view()),
    path('queryChronicNeuralActivity', DataAnalysis.QueryChronicNeuralActivity.as_view()),
    path('queryChronicTimeline', DataAnalysis.QueryChronicTimeline.as_view()),
    path('queryTimeseriesAnalysis', DataAnalysis.QueryTimeseriesAnalysis.as_view()),
    path('queryBurstAnalysis', DataAnalysis.QueryBurstAnalysis.as_view()),

    path('queryCustomizedAnalysis', DataAnalysis.QueryCustomizedAnalysis.as_view()),
    path('queryMedicationCycleAnalysis', DataAnalysis.QueryMedicationCycleAnalysis.as_view()),
    
    path('queryAIModels', DataAnalysis.QueryAIModels.as_view()),
    
    path('requestAIPrediction', AIModels.RequestPrediction.as_view()),
    
    path('queryGroupAnalysis', GroupAnalysis.QueryGroupAnalysis.as_view()),
    path('queryAnalysisPipeline', GroupAnalysis.QueryAnalysisPipeline.as_view()),
    path('queryAsyncJobQueue', AsyncJobScheduling.QueryAsyncJobQueue.as_view()),
    
    path('queryTherapyHistory', Therapy.QueryTherapyHistory.as_view()),
    path('assignTherapyLabel', Therapy.AssignTherapyLabel.as_view()),

    path('queryFilterData', DataFilter.QueryFilterData.as_view()),
]