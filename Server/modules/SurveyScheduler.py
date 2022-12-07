import os, sys, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.parent.resolve())

from datetime import datetime, date, timedelta
import pickle, joblib
import dateutil, pytz
import numpy as np
import pandas as pd
from cryptography.fernet import Fernet
import json

from Backend import models

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

def getStatus():
  status = os.system("systemctl is-active --quiet survey-scheduler")
  return status == 0