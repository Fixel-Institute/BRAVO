from django.urls import path
from django.conf import settings

from . import Wearable

urlpatterns = [
	path('wearable/requestPairing', Wearable.RequestPairingDevice.as_view()),
	path('wearable/queryPairedDevice', Wearable.QueryPairedDevice.as_view()),
	path('wearable/verifyDevicePairing', Wearable.VerifyPairing.as_view()),
]