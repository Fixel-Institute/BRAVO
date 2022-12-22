from django.contrib.auth import authenticate, login, logout, get_user_model

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from knox.views import LoginView as KnoxLoginView

from modules import Database
from Backend import models

import pathlib, json
RESOURCES = str(pathlib.Path(__file__).parent.resolve())
with open(RESOURCES + "/../codes.json", "r") as file:
    CODE = json.load(file)
    ERROR_CODE = CODE["ERROR"]

import re
def validateEmail(email):
    return re.fullmatch(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', email)

class UserRegister(RestViews.APIView):
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
                request.session.set_expiry(36000)
                return Response(status=200, data={"user": Database.extractUserInfo(user)})

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class UserAuth(KnoxLoginView):
    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        if "Email" in request.data and "Password" in request.data:
            user = authenticate(request, username=request.data["Email"], password=request.data["Password"])
            if user is not None:
                if user.is_mobile:
                    return Response(status=403, data={"code": ERROR_CODE["PERMISSION_DENIED"]})

                if not models.UserConfigurations.objects.filter(user_id=user.unique_user_id).exists():
                    models.UserConfigurations(user_id=user.unique_user_id).save()

                login(request, user)
                authResponse = super(UserAuth, self).post(request, format=None)
                authResponse.data.update({
                    "user": Database.extractUserInfo(user)
                })
                return Response(status=200, data=authResponse.data)
            else:
                return Response(status=400, data={"code": ERROR_CODE["INCORRECT_PASSWORD_OR_USERNAME"]})

        return Response(status=400, data={"code": ERROR_CODE["MALFORMATED_REQUEST"]})

class FetchAuthorizedInstitute(RestViews.APIView):
    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        return Response(status=200, data={"institutes": Database.extractInstituteInfo()})

class UserSignout(RestViews.APIView):
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        logout(request)
        return Response(status=200)

class Handshake(RestViews.APIView):
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        return Response(status=200)
