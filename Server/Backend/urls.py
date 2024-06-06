from django.urls import path, re_path
from django.conf import settings

from . import views

urlpatterns = [
	re_path(r'.*', views.Homepage.as_view()),
]
