from django.urls import path
from django.conf import settings

from . import Auth, Session, Queries, Upload, UpdateRecordings, Surveys

urlpatterns = [
	path('handshake', Auth.Handshake.as_view()),
	path('registration', Auth.UserRegister.as_view()),
	path('authenticate', Auth.UserAuth.as_view()),
	path('logout', Auth.UserSignout.as_view()), 
	path('authorizedInstitute', Auth.FetchAuthorizedInstitute.as_view()), 
	
	path('deidentificationTable', Upload.DeidentificationTable.as_view()),
	path('uploadSessionFiles', Upload.SessionUpload.as_view()),
	path('deleteSessionFiles', Upload.SessionRemove.as_view()),

	path('csrfToken', Session.CSRFToken.as_view()),
	path('updateSession', Session.UpdateSessionConfig.as_view()),
	path('querySessions', Session.QuerySessionConfigs.as_view()),
	path('setPatientID', Session.SetPatientID.as_view()),

	path('updatePatientInformation', UpdateRecordings.PatientInformationUpdate.as_view()),
	path('updateBrainSenseStream', UpdateRecordings.BrainSenseStreamUpdate.as_view()),

	path('queryDatabaseInfo', Queries.QueryDatabaseInfo.as_view()),
	path('queryPatients', Queries.QueryPatientList.as_view()),
	path('queryPatientInfo', Queries.QueryPatientInfo.as_view()),

	path('queryTherapyHistory', Queries.QueryTherapyHistory.as_view()),
	path('queryBrainSenseSurveys', Queries.QueryBrainSenseSurveys.as_view()),
	path('queryBrainSenseStreaming', Queries.QueryBrainSenseStreaming.as_view()),
	path('queryIndefiniteStreaming', Queries.QueryIndefiniteStreaming.as_view()),
	path('queryChronicBrainSense', Queries.QueryChronicBrainSense.as_view()),
	path('querySessionOverview', Queries.QuerySessionOverview.as_view()),

	path('queryPredictionModel', Queries.QueryPredictionModel.as_view()),
	path('queryPatientEvents', Queries.QueryPatientEvents.as_view()),
	path('queryAdaptiveGroups', Queries.QueryAdaptiveGroups.as_view()),
	path('queryCircadianPower', Queries.QueryCircadianPower.as_view()),

	path('queryImageDirectory', Queries.QueryImageModelDirectory.as_view()),
	path('queryImageModel', Queries.QueryImageModel.as_view()),

	path('addNewSurvey', Surveys.AddNewSurvey.as_view()),
	path('queryAvailableSurveys', Surveys.QueryAvailableSurveys.as_view()),
	path('queryAvailableRedcapSchedule', Surveys.QueryAvailableRedcapSchedule.as_view()),
	path('querySurveyContent', Surveys.QuerySurveyContent.as_view()),
	path('updateSurveyContent', Surveys.UpdateSurveyContent.as_view()),
	path('deleteSurvey', Surveys.ArchiveSurvey.as_view()),
	path('submitSurvey', Surveys.SubmitSurveyResults.as_view()),

	path('verifyRedcapLink', Surveys.RedcapVerification.as_view()),
	path('surveySchedulerSetup', Surveys.SetupSurveyScheduler.as_view()),
	path('surveySchedulerStatus', Surveys.SurveySchedulerStatus.as_view()),
]