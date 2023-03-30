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
Twilio Messaging Scheduler
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

from twilio.rest import Client

from BRAVO import asgi
from Backend import models

def checkMessageSchedule():
    if models.ScheduledSurveys.objects.filter(date__lt=datetime.datetime.utcnow().astimezone(dateutil.tz.tzlocal())).exists():
        schedules = models.ScheduledSurveys.objects.filter(date__lt=datetime.datetime.utcnow().astimezone(dateutil.tz.tzlocal())).all()
        for schedule in schedules:
            linkage = models.RedcapSurveyLink.objects.filter(linkage_id=schedule.linkage_id).first()
            survey = models.CustomizedSurvey.objects.filter(survey_id=linkage.survey_id).first()
            service = models.TwilioService.objects.filter(linkage_id=schedule.linkage_id, report_id=schedule.report_id).first()

            client = Client(service.account_id, service.authToken)
            surveyLink = os.environ.get('CLIENT_ADDRESS') + "/survey/" + survey.url + f"?__passcode={schedule.report_id}"

            message = client.messages.create(
                to=service.receiver["value"],
                messaging_service_sid=service.service_id,
                body=service.receiver["messageFormat"].replace("{%SURVEY_LINK%}", surveyLink))

            print(f"Schedule Sent on {datetime.datetime.now()}")
        schedules.delete()

if __name__ == '__main__':
    while True:
        checkMessageSchedule()
        time.sleep(60)