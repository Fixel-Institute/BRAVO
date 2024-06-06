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
Authentication Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from django.contrib.auth import authenticate, hashers
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken

from Backend import models
from modules import Database

import datetime
import pathlib, json
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

import re
def validateEmail(email):
    return re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email)

class UserRegister(RestViews.APIView):
    """ User Registration (Web Account Only).

    **POST**: ``/api/registration``

    Args:
      Email (string): Email address will also serve as unique username. Must be a properly formated Email address and unique within database.
      UserName (string): Human readable name of the user.
      Password (string): Password of the account. Database will hash the password for security. 
        User may also choose to perform end-to-end encryption during transmission if they desire.

    Returns:
      Response Code 200 if success or 400 if error. Response Body contains authentication token and user object.
    """

    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if "Email" in request.data and "Password" in request.data and "UserName" in request.data:
            if len(request.data["Password"]) < 8:
                return Response(status=400, data={"message": "Password must be at least 8 characters"})

            if not validateEmail(request.data["Email"]):
                return Response(status=400, data={"message": "Incorrect Email format"})

            if len(request.data["UserName"]) == 0:
                return Response(status=400, data={"message": "Malformatted Request"})
            
            existUser = models.PlatformUser.nodes.get_or_none(email=request.data["Email"])
            if existUser:
                return Response(status=400, data={"message": "Email already used"})
            
            user = models.PlatformUser(user_name=request.data["UserName"], email=request.data["Email"])
            user.password = hashers.make_password(request.data["Password"])
            user.save()

            user = authenticate(request, username=request.data["Email"], password=request.data["Password"])
            if user is not None:
                refresh = RefreshToken.for_user(user.serialized())
                refresh["user"] = user.user_id
                access = refresh.access_token

                response = Response(status=200, data={
                    "user": Database.extractUserInfo(user)
                })
                response.set_cookie("refreshToken", str(refresh), 
                                    secure=settings.SESSION_COOKIE_SECURE, 
                                    httponly=settings.SESSION_COOKIE_HTTPONLY)
                response.set_cookie("accessToken", str(access), 
                                    secure=settings.SESSION_COOKIE_SECURE, 
                                    httponly=settings.SESSION_COOKIE_HTTPONLY)
                
                dbToken = models.AuthenticationTokens(token_id=str(refresh), expiration=refresh.get("exp")).save()
                dbToken.associated_user.connect(user)
                user.auth_tokens.connect(dbToken)

                study = models.Study(name="Generic Study").save()
                study.managers.connect(user)
                user.studies.connect(study)
                return response
            else:
                return Response(status=400, data={"message": "Fail to create user"})

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class UserAuth(RestViews.APIView):
    """ User Authentication (Web Account Only).

    **POST**: ``/api/authenticate``

    Args:
      Email (string): Email address also serves as unique username.
      Password (string): Password of the account. Database will hash the password for security. 
        User may also choose to perform end-to-end encryption during transmission if they desire.
      Persistent (Boolean): If the token's expiration date should be extremely long or not.

    Returns:
      Response Code 200 if success or 400 if error. Response Body contains user object.
    """

    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    
    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if "Email" in request.data and "Password" in request.data:
            user = authenticate(request, username=request.data["Email"], password=request.data["Password"])
            if user is not None:
                refresh = RefreshToken.for_user(user.serialized())
                refresh["user"] = user.user_id
                if request.data["Persistent"]:
                    refresh.set_exp(lifetime=datetime.timedelta(days=365))
                access = refresh.access_token

                response = Response(status=200, data={
                    "user": Database.extractUserInfo(user)
                })
                response.set_cookie("refreshToken", str(refresh), 
                                    secure=settings.SESSION_COOKIE_SECURE, 
                                    httponly=settings.SESSION_COOKIE_HTTPONLY)
                response.set_cookie("accessToken", str(access), 
                                    secure=settings.SESSION_COOKIE_SECURE, 
                                    httponly=settings.SESSION_COOKIE_HTTPONLY)
                
                dbToken = models.AuthenticationTokens(token_id=str(refresh), expiration=refresh.get("exp")).save()
                dbToken.associated_user.connect(user)
                user.auth_tokens.connect(dbToken)

                return response
            else:
                return Response(status=400, data={"message": "Incorrect Email or Password"})

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class UserSignout(RestViews.APIView):
    """ User logout while detroying the authentication token.

    **POST**: ``/api/logout``

    Returns:
      Response Code 204.
    """

    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        try:
            refreshToken = models.AuthenticationTokens.nodes.get_or_none(token_id=request.COOKIES["refreshToken"])
            for user in refreshToken.associated_user:
                for token in user.auth_tokens:
                    if token.blacklist == 0:
                        token.blacklist = 1
                        token.save()

            response = Response(status=204)
            response.delete_cookie("refreshToken")
            response.delete_cookie("accessToken")
            return response
        
        except Exception as e:
            print(e)
            return Response(status=401)

class UserTokenRefresh(RestViews.APIView):
    """ Verify tokens.

    **POST**: ``/api/authRefresh``

    Returns:
      Response Code 200.
    """

    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        try:
            refresh = RefreshToken(token=request.COOKIES["refreshToken"])
            dbToken = models.AuthenticationTokens.nodes.get(token_id=request.COOKIES["refreshToken"], blacklist=0)

            response = Response(status=200)
            response.set_cookie("accessToken", str(refresh.access_token), 
                                secure=settings.SESSION_COOKIE_SECURE, 
                                httponly=settings.SESSION_COOKIE_HTTPONLY)
            return response
        except Exception as e:
            print(e)
            return Response(status=401)

class Handshake(RestViews.APIView):
    """ Confirming that the BRAVO server exist.

    **POST**: ``/api/handshake``

    Returns:
      Response Code 200.
    """
    
    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        return Response(status=200, data={
            "Version": "3.0.0"
        })

class QueryProfile(RestViews.APIView):
    """ Verify tokens.

    **POST**: ``/api/queryProfile``

    Returns:
      Response Code 200. Response Body contains profile information
    """

    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        data = {}
        data["name"] = request.user.user_name
        key = request.user.secure_keys.get_or_none()
        data["key"] = key.token_id if key else None
        return Response(status=200, data=data)
    
class RequestSecureKey(RestViews.APIView):
    """ Request Secure Key for CORS 

    **POST**: ``/api/requestSecureKey``

    Returns:
      Response Code 200. Response Body contains secure key.
    """

    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        for key in request.user.secure_keys:
            key.delete()
        key = models.SecureKey(expiration=datetime.datetime.utcnow().timestamp() + 3600*24*30).save()
        key.associated_user.connect(request.user)
        request.user.secure_keys.connect(key)
        return Response(status=200, data={"key": key.token_id})
