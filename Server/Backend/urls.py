from django.urls import path
from django.conf import settings

from .APIs import urls as API_urls
from .MobileEndpoints import urls as MobileEndpoints_urls

urlpatterns = API_urls.urlpatterns + MobileEndpoints_urls.urlpatterns
