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

from django.urls import path
from django.conf import settings

from . import Wearable, Auth, Speech

urlpatterns = [
	path('auth/login', Auth.UserLogin.as_view()),
	path('auth/refresh', Auth.UserRefresh.as_view()),

	path('wearable/requestPairing', Wearable.RequestPairingDevice.as_view()),
	path('wearable/queryPairedDevice', Wearable.QueryPairedDevice.as_view()),
	path('wearable/verifyDevicePairing', Wearable.VerifyPairing.as_view()),

	path('wearable/uploadRecording', Wearable.UploadRecording.as_view()),
	path('speech/uploadRecording', Speech.UploadRecording.as_view()),
]

websocket_urlpatterns = [
    path("socket/wearableStream", Wearable.StreamRelay.as_asgi()),
]
