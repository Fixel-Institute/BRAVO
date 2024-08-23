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
from Backend import models, tasks

import pathlib, json
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

import re
def validateEmail(email):
    return re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email)

def ValidateAuthToken(token):
    try:
        refresh = RefreshToken(token)
        user = models.PlatformUser.objects.get(unique_user_id= refresh.get("user"))
        return user
    except AuthenticationFailed:
        return None

class UserRegister(RestViews.APIView):
    """ User Registration (Web Account Only).

    **POST**: ``/api/registration``

    Args:
      Email (string): Email address will also serve as unique username. Must be a properly formated Email address and unique within database.
      UserName (string): Human readable name of the user.
      Institute (string): Common institute name of the user. This allow sharing of data among multiple users within same institute.
      Password (string): Password of the account. Database will hash the password for security. 
        User may also choose to perform end-to-end encryption during transmission if they desire.

    Returns:
      Response Code 200 if success or 400 if error. Response Body contains authentication token and user object.
    """

    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if "Email" in request.data and "Password" in request.data and "UserName" in request.data and "Institute" in request.data:
            if len(request.data["Password"]) < 8:
                return Response(status=400, data={"code": ERROR_CODE["PASSWORD_LENGTH_ERROR"]})

            if not validateEmail(request.data["Email"]):
                return Response(status=400, data={"code": ERROR_CODE["EMAIL_VALIDATION_ERROR"]})

            if len(request.data["UserName"]) == 0 and len(request.data["Institute"]) == 0:
                return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})
            
            User = get_user_model()
            try:
                User.objects.get(email=request.data["Email"])
                return Response(status=400, data={"code": ERROR_CODE["EMAIL_USED_ERROR"]})

            except User.DoesNotExist:
                user = User.objects.create_user(email=request.data["Email"], user_name=request.data["UserName"], institute=request.data["Institute"], password=request.data["Password"])
                user.save()
                
                if not models.UserConfigurations.objects.filter(user_id=user.unique_user_id).exists():
                    models.UserConfigurations(user_id=user.unique_user_id).save()

                user = authenticate(request, username=request.data["Email"], password=request.data["Password"])
                login(request, user)

                refresh = RefreshToken.for_user(user)
                refresh["user"] = str(user.unique_user_id)
                access = refresh.access_token
                return Response(status=200, data={
                    "access": str(access),
                    "refresh": str(refresh),
                    "user": Database.extractUserInfo(user)
                })

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
      Response Code 200 if success or 400 if error. Response Body contains authentication token and user object.
    """

    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    
    def post(self, request):
        if "Email" in request.data and "Password" in request.data:
            user = authenticate(request, username=request.data["Email"], password=request.data["Password"])
            if user is not None:
                if user.is_mobile:
                    return Response(status=400, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                if not models.UserConfigurations.objects.filter(user_id=user.unique_user_id).exists():
                    models.UserConfigurations(user_id=user.unique_user_id).save()

                login(request, user)
                refresh = RefreshToken.for_user(user)
                refresh["user"] = str(user.unique_user_id)

                access = refresh.access_token
                if "Persistent" in request.data:
                    if request.data["Persistent"]:
                        refresh.set_exp(lifetime=datetime.timedelta(weeks= 520))

                #tasks.ClearJWTBlacklists.apply_async(countdown=0)
                return Response(status=200, data={
                    "access": str(access),
                    "refresh": str(refresh),
                    "user": Database.extractUserInfo(user)
                })
            else:
                return Response(status=400, data={"code": ERROR_CODE["INCORRECT_PASSWORD_OR_USERNAME"]})

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class UserTokenRefresh(RestViews.APIView):
    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        try:
            refresh = RefreshToken(token=request.data.get("refresh"))
            refresh.check_exp()
            return Response(status=200, data={
                "access": str(refresh.access_token),
            })
        except Exception as e:
            print(e)
            return Response(status=401)

class FetchAuthorizedInstitute(RestViews.APIView):
    """ NOT IMPLEMENTED
    """

    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        return Response(status=200, data={"institutes": Database.extractInstituteInfo()})

class UserSignout(RestViews.APIView):
    """ User logout while detroying the authentication token.

    **POST**: ``/api/logout``

    Args:
      refresh (string): the refresh-token for persistent connection.

    Returns:
      Response Code 204.
    """

    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if not "refresh" in request.data:
            return Response(status=403)
        
        try: 
            refresh = RefreshToken(token=request.data.get("refresh"))
            logout(request)
            refresh.blacklist()
            return Response(status=204)
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
    def post(self, request):
        return Response(status=200, data={
            "Version": "2.2.3"
        })
