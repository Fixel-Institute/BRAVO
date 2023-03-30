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
Mobile Application Authentication Module
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from django.contrib.auth import authenticate, login, logout, get_user_model

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authentication import BasicAuthentication

from rest_framework_simplejwt.tokens import RefreshToken

from modules import Database

import datetime
import pathlib, json
RESOURCES = str(pathlib.Path(__file__).parent.resolve())

import re
def validateEmail(email):
    return re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email)

def extractUserInfo(user):
    return {
        "Type": "online",
        "Email": user.email,
        "Name": user.user_name
    }

class UserRegister(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]

    def post(self, request):
        if "Email" in request.data and "Password" in request.data and "Name" in request.data:
            if len(request.data["Password"]) < 8:
                return Response(status=400)

            if not validateEmail(request.data["Email"]):
                return Response(status=400)

            if len(request.data["Name"]) == 0:
                return Response(status=400)

            User = get_user_model()
            try:
                User.objects.get(email=request.data["Email"])
                return Response(status=400)

            except User.DoesNotExist:
                user = User.objects.create_user(email=request.data["Email"], name=request.data["Name"], password=request.data["Password"])
                user.is_mobile = True
                user.save()

                refresh = RefreshToken.for_user(user)
                refresh["user"] = str(user.unique_user_id)

                access = refresh.access_token
                access.set_exp(lifetime=datetime.timedelta(weeks= 520))

                return Response(status=200, data={
                    "access": str(access),
                    "refresh": str(refresh),
                    "user": Database.extractUserInfo(user)
                })

        return Response(status=400)

class UserLogin(RestViews.APIView):
    authentication_classes = [BasicAuthentication]

    def post(self, request, format=None):
        if "Email" in request.data and "Password" in request.data:
            user = authenticate(request, username=request.data["Email"], password=request.data["Password"])
            if user is not None:
                if not user.is_mobile:
                    return Response(status=400)

                login(request, user)
                refresh = RefreshToken.for_user(user)
                refresh["user"] = str(user.unique_user_id)

                access = refresh.access_token
                access.set_exp(lifetime=datetime.timedelta(weeks= 520))
                return Response(status=200, data={
                    "access": str(access),
                    "refresh": str(refresh),
                    "user": Database.extractUserInfo(user)
                })
            else:
                return Response(status=400)
        return Response(status=401)

class UserRefresh(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        return Response(status=200, data={"user": extractUserInfo(request.user)});
        
