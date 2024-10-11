""""""
"""
=========================================================
* UF BRAVO Platform
=========================================================

* Copyright 2024 by Jackson Cagle, Fixel Institute
* The source code is made available under a Creative Common NonCommercial ShareAlike License (CC BY-NC-SA 4.0) (https://creativecommons.org/licenses/by-nc-sa/4.0/) 

 =========================================================

* The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
"""
"""
Neo4j User Model (Customized for Django Auth)
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from uuid import uuid4
import json
import os

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from neomodel import StructuredNode, StringProperty, FloatProperty, IntegerProperty, JSONProperty, Relationship, RelationshipFrom, RelationshipTo
from .HelperFunctions import current_time, AttrDict

from modules import Database
DATABASE_PATH = os.environ.get('DATASERVER_PATH')

class AuthenticationTokens(StructuredNode):
    token_id = StringProperty(default="")
    token_type = StringProperty(default="refresh")
    expiration = FloatProperty(default=0)
    associated_user = RelationshipFrom('PlatformUser', 'HAS_AUTHTOKEN')
    blacklist = IntegerProperty(default=0)

class APIKey(StructuredNode):
    token_id = StringProperty(default=uuid4)
    expiration = FloatProperty(default=0)
    associated_user = RelationshipFrom('PlatformUser', 'HAS_APIKEY')

class PlatformUser(StructuredNode):
    user_id = StringProperty(default=uuid4)

    email = StringProperty(max_length=128, required=True)
    user_name = StringProperty(max_length=128, required=True)
    password = StringProperty(required=True)

    register_date = FloatProperty(default=current_time)
    permission = StringProperty(default="BASIC", max_length=128)
    configuration = JSONProperty(default=dict)

    cached_results = RelationshipTo('CachedResult', 'HAS_CACHE')

    auth_tokens = RelationshipTo('AuthenticationTokens', 'HAS_AUTHTOKEN')
    secure_keys = RelationshipTo('APIKey', 'HAS_APIKEY')

    # Participant.py
    studies = Relationship(".Participant.Study", "MEMBER_OF_STUDY")

    # SourceFile.py
    files = RelationshipTo(".SourceFile.SourceFile", "UPLOADED_FILE")

    is_authenticated = False
    api_access = False

    def serialized(self):
        return AttrDict({"id": self.user_id, "email": self.email, "user_name": self.user_name, "register_date": self.register_date, "permission": self.permission})
    
    def checkPermission(self, participant, permission):
        if permission == "view":
            for study in self.studies:
                approved_access = [studyParticipant.uid for studyParticipant in study.participants]
                if participant.uid in approved_access:
                    return True 
        elif permission == "edit":
            for study in participant.studies:
                if study.checkPermission(self.user_id):
                    return True
        return False

class PlatformUserAuthBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None):
        user = PlatformUser.nodes.get_or_none(email=username)
        if not user:
            return None
        
        password_valid = check_password(password, user.password)
        if not password_valid:
            return None
        
        return user
        
    def get_user(self, user_id):
        user = PlatformUser.nodes.get_or_none(user_id=user_id)
        return user
        
class CachedResult(StructuredNode):
    uid = StringProperty(default=uuid4)
    type = StringProperty(max_length=128)
    date = FloatProperty()
    data_pointer = StringProperty()
    hashed = StringProperty()

    metadata = JSONProperty()

    def createCache(self, user, data):
        self.date = current_time()
        filename, hashed = Database.saveCacheFile(data, user.user_id, self.uid)
        self.data_pointer = filename
        self.hashed = hashed

    def purge(self):
        try: 
            os.remove(DATABASE_PATH + "visualization" + os.path.sep + self.data_pointer)
        except:
            pass
        
        self.delete()

    def clearCaches():
        oldCaches = CachedResult.nodes.filter(date__lt=current_time()-3600).all()
        for cache in oldCaches:
            cache.purge()