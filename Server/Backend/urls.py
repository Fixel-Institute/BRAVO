from django.urls import path
from django.conf import settings

from . import views

urlpatterns = [
	path('', views.Homepage.as_view()),
]
