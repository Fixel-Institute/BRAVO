import os, sys 
import subprocess
from pathlib import Path

from celery import Celery 
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'BRAVO.settings')
app = Celery("BRAVO")

app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
