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
"""
Django settings for BRAVO project.

Generated by 'django-admin startproject' using Django 3.2.9.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

from pathlib import Path
import os, sys
import json
import datetime

BASE_DIR = Path(__file__).resolve().parent.parent
if os.path.exists(os.path.join(BASE_DIR, '.env')):
    with open(os.path.join(BASE_DIR, '.env'), "r") as file:
        config = json.load(file)
    for key in config.keys():
        os.environ[key] = config[key]
    sys.path.append(os.environ["PYTHON_UTILITY"])

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')

DATASERVER_PATH = os.environ.get('DATASERVER_PATH')
os.makedirs(DATASERVER_PATH + "cache", exist_ok=True)
os.makedirs(DATASERVER_PATH + "imaging", exist_ok=True)
os.makedirs(DATASERVER_PATH + "sessions", exist_ok=True)
os.makedirs(DATASERVER_PATH + "recordings", exist_ok=True)

# SECURITY WARNING: don't run with debug turned on in production!
MODE = os.environ.get('MODE')
if not MODE == "PRODUCTION":
    DEBUG = True
    STATIC_URL = '/static/'
    SECURE_SSL_REDIRECT = False
    CSRF_TRUSTED_ORIGINS = ['http://localhost:3000', 'https://uf-bravo.jcagle.solutions', 'http://' + os.environ.get('SERVER_ADDRESS')]
    SECURE_PROXY_SSL_HEADER = ()
    SESSION_EXPIRE_AT_BROWSER_CLOSE = False
    CORS_ALLOW_ALL_ORIGINS = True
else:
    DEBUG = False
    BASE_URL = 'https://' + os.environ.get('SERVER_ADDRESS')
    STATIC_URL = BASE_URL + '/static/'
    SECURE_SSL_REDIRECT = False
    CSRF_TRUSTED_ORIGINS = [BASE_URL]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True

ALLOWED_HOSTS = ['localhost', os.environ.get('SERVER_ADDRESS'), "uf-bravo.jcagle.solutions"]
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", 'https://uf-bravo.jcagle.solutions', os.environ.get('CLIENT_ADDRESS')]
CORS_ALLOW_HEADERS = [
    'content-type',
    'cache-control',
    'x-requested-with',
    'csrfmiddlewaretoken',
    'credentials',
    'authorization'
]

# Application definition
INSTALLED_APPS = [
    'daphne',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',
    'rest_framework',
    'channels',
    'Backend',
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'BRAVO.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ]
}

SIMPLE_JWT = {
    "REFRESH_TOKEN_LIFETIME": datetime.timedelta(hours=4),
    "ACCESS_TOKEN_LIFETIME": datetime.timedelta(minutes=5),
}

ASGI_APPLICATION = 'BRAVO.asgi.application'
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [(os.environ.get('REDIS_HOST'), 6379)],
            "capacity": 1500,  # default 100
            "expiry": 10,  # default 60
        },
    },
}

# Celery Scheduler
CELERY_TIMEZONE = "UTC"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60
CELERY_BROKER_URL = 'redis://localhost:6379'
CELERY_RESULT_BACKEND = 'redis://localhost:6379'

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

BRAVODatabase = os.environ.get('BRAVO_DATABASE')
if BRAVODatabase:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'NAME': os.environ.get('BRAVO_DATABASE'),
            'USER': os.environ.get('BRAVO_DATABASE_USER'),
            'PASSWORD': os.environ.get('BRAVO_DATABASE_PASSWORD'),
            'HOST': os.environ.get('BRAVO_DATABASE_HOST'),
            'PORT': os.environ.get('BRAVO_DATABASE_PORT'),
            'PROTOCOL': "tcp",
            'OPTIONS': {
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
            },
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.mysql',
            'OPTIONS': {
                'read_default_file': os.path.join(BASE_DIR, 'mysql.config'),
                'init_command': "SET sql_mode='STRICT_TRANS_TABLES'"
            },
        }
    }

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators
AUTH_USER_MODEL = "Backend.PlatformUser"

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_L10N = True
USE_TZ = True

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django DB Automatic Reconnect
import importlib

from django.conf import settings
from django.db.backends.utils import CursorWrapper

for name, config in settings.DATABASES.items():
    module = importlib.import_module(config["ENGINE"] + ".base")

    def ensure_connection(self):
        if self.connection is not None:
            try:
                with CursorWrapper(self.create_cursor(), self) as cursor:
                    cursor.execute("SELECT 1")
                return
            except Exception:
                pass

        with self.wrap_database_errors:
            self.connect()

    module.DatabaseWrapper.ensure_connection = ensure_connection
    