from django.contrib.auth import authenticate, login, logout, get_user_model

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response
from rest_framework import permissions
from rest_framework.authtoken.serializers import AuthTokenSerializer
from rest_framework.authentication import BasicAuthentication

from knox.views import LoginView as KnoxLoginView
from knox.auth import TokenAuthentication

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
                
                return Response(status=200)

        return Response(status=400)

class UserLogin(KnoxLoginView):
    authentication_classes = [BasicAuthentication]

    def post(self, request, format=None):
        if request.user.is_mobile:
            return super(UserLogin, self).post(request, format=None)

        return Response(status=401)

class UserRefresh(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, format=None):
        return Response(status=200, data={"user": extractUserInfo(request.user)});
        
