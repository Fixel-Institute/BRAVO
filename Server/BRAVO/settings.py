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

# SECURITY WARNING: don't run with debug turned on in production!
MODE = os.environ.get('MODE')
if not MODE == "PRODUCTION":
    DEBUG = True
    STATIC_URL = '/static/'
    SECURE_SSL_REDIRECT = False
    CSRF_TRUSTED_ORIGINS = ['http://localhost:3000', 'http://' + os.environ.get('SERVER_ADDRESS')]
    SECURE_PROXY_SSL_HEADER = ()
    SESSION_EXPIRE_AT_BROWSER_CLOSE = False
else:
    DEBUG = False
    BASE_URL = 'https://' + os.environ.get('SERVER_ADDRESS')
    STATIC_URL = BASE_URL + '/static/'
    SECURE_SSL_REDIRECT = False
    CSRF_TRUSTED_ORIGINS = [BASE_URL]
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SESSION_EXPIRE_AT_BROWSER_CLOSE = True

ALLOWED_HOSTS = ['localhost', os.environ.get('SERVER_ADDRESS')]
CORS_ALLOWED_ORIGINS = ["http://localhost:3000", os.environ.get('CLIENT_ADDRESS')]
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
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'knox',
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
        'knox.auth.TokenAuthentication',
    ]
}

REST_KNOX = {
    'TOKEN_TTL': None,
}

ASGI_APPLICATION = 'BRAVO.asgi.application'
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("127.0.0.1", 6379)],
            "capacity": 1500,  # default 100
            "expiry": 10,  # default 60
        },
    },
}

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

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
