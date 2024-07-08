""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2024 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""

from django.urls import path
from django.conf import settings

from . import Auth, Session, ParticipantManager, DataHandler, Queries

urlpatterns = [
	path('handshake', Auth.Handshake.as_view()),
	path('registration', Auth.UserRegister.as_view()),
	path('authenticate', Auth.UserAuth.as_view()),
	path('authRefresh', Auth.UserTokenRefresh.as_view()),
	path('logout', Auth.UserSignout.as_view()), 
  path('queryProfile', Auth.QueryProfile.as_view()), 
  path('requestSecureKey', Auth.RequestSecureKey.as_view()), 
  
	path('updateSession', Session.UpdateSessionConfig.as_view()),
	path('querySessions', Session.QuerySessionConfigs.as_view()),
  
	path('createStudyParticipant', ParticipantManager.CreateStudyParticipant.as_view()),
	path('createParticipantEvent', ParticipantManager.CreateParticipantEvent.as_view()),
	path('updateStudyParticipant', ParticipantManager.UpdateStudyParticipant.as_view()),
	path('updateDeviceInformation', ParticipantManager.UpdateDeviceInformation.as_view()),
	path('deleteStudyParticipant', ParticipantManager.DeleteStudyParticipant.as_view()),
	path('queryStudyParticipant', ParticipantManager.QueryStudyParticipant.as_view()),
	path('queryParticipantInformation', ParticipantManager.QueryParticipantInformation.as_view()),
	path('CheckAccessPermission', ParticipantManager.CheckAccessPermission.as_view()),
  
	path('uploadData', DataHandler.DataUpload.as_view()),
  path('retrieveDataList', DataHandler.QueryAvailableRecordings.as_view()),
	path('retrieveData', DataHandler.DataRetrieve.as_view()),
  path('queryProcessingQueue', DataHandler.QueryProcessingQueue.as_view()),
  path('clearProcessingQueue', DataHandler.ClearProcessingQueue.as_view()),
  path('getFernetKey', DataHandler.GetSecretKeyFromPassword.as_view()),
  path('queryDatabaseInfo', DataHandler.QueryDatabaseInfo.as_view()),
  path('deleteData', DataHandler.DeleteData.as_view()),
  
	path('queryTherapyHistory', Queries.QueryTherapyHistory.as_view()),
	path('queryBaselinePSDs', Queries.QueryBaselinePSDs.as_view()),
	path('queryTimeSeriesAnalysis', Queries.QueryTimeSeriesAnalysis.as_view()),
	path('queryTimeSeriesRecording', Queries.QueryTimeSeriesRecording.as_view())
]
