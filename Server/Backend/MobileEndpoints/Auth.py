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
Authentication Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import datetime

from django.contrib.auth import authenticate, login, logout, get_user_model

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import AuthenticationFailed

from rest_framework_simplejwt.tokens import RefreshToken

from modules import Database
from Backend import models

import pathlib, json
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

import random
import string
def generate_key(length):
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))

class UserAuth(RestViews.APIView):
    """ User Authentication (Web Account Only).

    **POST**: ``/mobile/auth/login``

    Args:
      Username (string): Unique username.
      Password (string): Password of the account. Database will hash the password for security. 
        User may also choose to perform end-to-end encryption during transmission if they desire.

    Returns:
      Response Code 200 if success or 400 if error. Response Body contains authentication token and user object.
    """

    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    
    def post(self, request):
        if "Username" in request.data and "Password" in request.data:
            if models.MobileUser.objects.filter(user_name=request.data["Username"]).exists():
                user = models.MobileUser.objects.filter(user_name=request.data["Username"]).first()
                if user.check_password(request.data["Password"]):
                    if user.is_active:
                        return Response(status=401)
                    else:
                        user.is_active = True
                        user.active_token = generate_key(64)
                        user.save()
                        return Response(status=200, data={
                            "username": user.user_name,
                            "configuration": user.configuration,
                            "token": user.active_token
                        })
                else:
                    return Response(status=400, data={"code": ERROR_CODE["INCORRECT_PASSWORD_OR_USERNAME"]})
            else:
                return Response(status=400, data={"code": ERROR_CODE["INCORRECT_PASSWORD_OR_USERNAME"]})

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class UserSignout(RestViews.APIView):
    """ User logout while detroying the authentication token.

    **POST**: ``/mobile/auth/logout``

    Args:
      currentToken (string): the refresh-token for persistent connection.

    Returns:
      Response Code 204.
    """

    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if not "currentToken" in request.data or not "Username" in request.data:
            return Response(status=403)
        
        if models.MobileUser.objects.filter(user_name=request.data["Username"]).exists():
            user = models.MobileUser.objects.filter(user_name=request.data["Username"]).first()
            if user.is_active and user.active_token == request.data["currentToken"]:
                user.is_active = False
                user.active_token = ""
                user.save()
                return Response(status=200)
            return Response(status=200)
        
        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
