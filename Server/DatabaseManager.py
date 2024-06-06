import os, sys

from datetime import datetime
import pytz
from pathlib import Path
from django.conf import settings

import pickle, blosc
import uuid
import json

def processInput(argv):
  if len(argv) > 1:

    if argv[1] == "install_labels":
      from BRAVO import asgi
      from neomodel import install_all_labels
      install_all_labels()
      return True
    
    elif argv[1] == "clear_labels":
      from BRAVO import asgi
      from neomodel import remove_all_labels
      remove_all_labels()
      return True
    
    elif argv[1] == "clear_database":
      from BRAVO import asgi
      from neomodel import db, remove_all_labels, clear_neo4j_database
      remove_all_labels()
      clear_neo4j_database(db=db)
      return True