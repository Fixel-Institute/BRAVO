"""
ASGI config for BRAVO project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os, sys
from pathlib import Path
import json

from django.urls import re_path
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator, OriginValidator
from django.core.asgi import get_asgi_application

import DatabaseManager

BASE_DIR = Path(__file__).resolve().parent
if os.path.exists(os.path.join(BASE_DIR, '.env')):
    with open(os.path.join(BASE_DIR, '.env'), "r") as file:
        config = json.load(file)
    for key in config.keys():
        os.environ[key] = config[key]

    sys.path.append(os.environ["PYTHON_UTILITY"])

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BRAVO.settings')
django_asgi_app = get_asgi_application()

from . import urls

application = ProtocolTypeRouter({
    "http": django_asgi_app,
    "websocket": AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(
                urls.websocket_urlpatterns
            )
        )
    ),
})