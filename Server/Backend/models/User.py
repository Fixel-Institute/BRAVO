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

from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.hashers import check_password
from neomodel import StructuredNode, StringProperty, FloatProperty, IntegerProperty, JSONProperty, Relationship
from .HelperFunctions import current_time, AttrDict

class AuthenticationTokens(StructuredNode):
    token_id = StringProperty()
    token_type = StringProperty(default="refresh")
    expiration = FloatProperty()
    associated_user = Relationship('PlatformUser', 'AUTHTOKEN_FOR')
    blacklist = IntegerProperty(default=0)

class SecureKey(StructuredNode):
    token_id = StringProperty(default=uuid4)
    expiration = FloatProperty()
    associated_user = Relationship('PlatformUser', 'SECURE_KEY_FOR')

class PlatformUser(StructuredNode):
    user_id = StringProperty(unique_index=True, default=uuid4)

    email = StringProperty(max_length=128)
    user_name = StringProperty(max_length=128)
    password = StringProperty()

    register_date = FloatProperty(default=current_time)
    permission = StringProperty(default="BASIC", max_length=128)

    secure_keys = Relationship('SecureKey', 'HAS_SECURE_KEY')
    auth_tokens = Relationship('AuthenticationTokens', 'HAS_AUTHTOKEN')
    studies = Relationship(".Participant.Study", "MEMBER_OF_STUDY")
    configuration = JSONProperty(default=dict)

    is_authenticated = False
    api_access = False

    files = Relationship(".SourceFile.SourceFile", "UPLOADED_FILE")

    def serialized(self):
        return AttrDict({"id": self.user_id, "email": self.email, "user_name": self.user_name, "register_date": self.register_date, "permission": self.permission})
    
    def getConfiguration(self):
        try:
            return self.configuration
        except:
            return None

    def setConfiguration(self, config):
        try:
            self.configuration = config
            self.save()
            return True
        except:
            return False

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
        

