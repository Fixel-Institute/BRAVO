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
Analysis Processing Service
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
@date: Thu Sep 16 12:05:09 2021
"""

import os
import sys
from pathlib import Path
import json
import datetime
import dateutil
import time
import numpy as np
import pytz
from cryptography.fernet import Fernet

import websocket
from BRAVO import asgi

from Backend import models
from modules.Percept import Sessions
from modules import Database, AnalysisBuilder
from decoder import Percept

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

def processAnalysis():
    ws = websocket.WebSocket()
    if models.ProcessingQueue.objects.filter(type="ProcessAnalysis", state="InProgress").exists():
        print(datetime.datetime.now())
        BatchQueues = models.ProcessingQueue.objects.filter(type="ProcessAnalysis", state="InProgress").order_by("datetime").all()
        for queue in BatchQueues:
            ErrorMessage = ""

            print(f"Start Processing {queue.descriptor['analysisId']}")

            user = models.PlatformUser.objects.filter(unique_user_id=queue.owner).first()
            try:
                Results = AnalysisBuilder.processAnalysis(user, queue.descriptor["analysisId"])
            except Exception as e:
                print(e.__cause__)
                queue.state="Error"
                queue.save()
                
            print(f"End Processing {queue.descriptor['analysisId']}")

            queue.state="Complete"
            queue.save()

            try:
                ws.connect("ws://localhost:3001/socket/notification")
                ws.send(json.dumps({
                    "NotificationType": "AnalysisProcessing",
                    "TaskUser": str(user.unique_user_id),
                    "TaskID": queue.descriptor["analysisId"],
                    "Authorization": os.environ["ENCRYPTION_KEY"],
                    "State": "EndProcessing",
                    "Message": Results,
                }))
                ws.close()
            except Exception as e:
                print(e)
                


if __name__ == '__main__':
    processAnalysis()
