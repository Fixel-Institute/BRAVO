""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2025 by Jackson Cagle, Fixel Institute
* The source code is made available under Open Source GPL-3.0 License

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
SQL Table Definitions
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os
from django.db import models
import json
import hashlib

from modules.HelperFunctions import uuid4_hex, current_time

DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class LLMCache(models.Model):
    uid = models.CharField(max_length=32, default=uuid4_hex, unique=True, primary_key=True)
    name = models.CharField(max_length=512, default="")
    type = models.CharField(max_length=128, default="")
    message = models.CharField(max_length=2048, default="")
    response = models.JSONField(default=dict)
    metadata = models.JSONField(default=dict)

    date = models.FloatField(default=current_time)

    def include(*args, **kwargs):
        return LLMCache.objects.filter(**kwargs).exists()

    def find(*args, **kwargs):
        return LLMCache.objects.filter(**kwargs).first()

    def create(*args, **kwargs):
        file = LLMCache(**kwargs)
        file.save()
        return file

    def get_LLMCache(name, type, message, metadata={}):
        message_hash = hashlib.sha256(json.dumps(message).encode()).hexdigest()
        obj = LLMCache.find(name=name, type=type, message=message_hash, metadata=metadata)
        return obj

    def add_LLMCache(name, type, message, response, metadata={}):
        message_hash = hashlib.sha256(json.dumps(message).encode()).hexdigest()
        obj = LLMCache.create(
            name=name,
            type=type,
            message=message_hash,
            response=response,
            metadata=metadata,
        )
        return obj
    
    def has_permission(self, user):
        return self.owner == user

    def purge(*args, **kwargs):
        return LLMCache.objects.filter(**kwargs).delete()
    
    def get_info(self):
        return {
            "Id": self.uid,
            "Name": self.name,
            "Type": self.type,
            "Message": self.message,
            "Response": self.response,
            "Metadata": self.metadata
        }