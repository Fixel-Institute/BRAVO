from django.urls import path
from django.conf import settings

from knox import views as KnoxViews

from . import Wearable, Auth

urlpatterns = [
	path('auth/login', Auth.UserLogin.as_view()),
	path('auth/logout', KnoxViews.LogoutView.as_view()),
	path('auth/logoutall', KnoxViews.LogoutAllView.as_view()),
	path('auth/refresh', Auth.UserRefresh.as_view()),

	path('wearable/requestPairing', Wearable.RequestPairingDevice.as_view()),
	path('wearable/queryPairedDevice', Wearable.QueryPairedDevice.as_view()),
	path('wearable/verifyDevicePairing', Wearable.VerifyPairing.as_view()),
]

websocket_urlpatterns = [
    path("socket/wearableStream", Wearable.StreamRelay.as_asgi()),
]