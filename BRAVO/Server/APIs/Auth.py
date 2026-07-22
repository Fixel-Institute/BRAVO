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
User Authentication APIs
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

from django.contrib.auth import authenticate, login, logout

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated

from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from django.conf import settings

from modules.HelperFunctions import sanitize_input, get_or_none, get_token
from modules import Database, Auth
from Server import models

class UserRegister(RestViews.APIView):
    
    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["Email", "Password", "UserName", "Institute"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        if len(request.data["Password"]) < 8:
            return Response(status=400, data={"message": "Password need at least 8-character"})

        if len(request.data["UserName"]) == 0:
            return Response(status=400, data={"message": "User's Name must be present."})

        if len(request.data["Institute"]) == 0:
            try:
                user = Auth.registerUser(request.data["Email"], request.data["Password"], user_name=request.data["UserName"])
            except Exception as e:
                return Response(status=400, data={"message": str(e)})
        else:
            institute = models.Institute.find(invite_code=request.data["Institute"])
            if not institute:
                return Response(status=403)

            try:
                user = Auth.registerUser(request.data["Email"], request.data["Password"], user_name=request.data["UserName"], institute=institute)
            except Exception as e:
                return Response(status=400, data={"message": str(e)})
            
            user.save()
            #institute.invite_code = ""
            #institute.save()

        user = authenticate(request, username=request.data["Email"], password=request.data["Password"])
        login(request, user)
        
        return Response(status=200, data=user.get_info())

class UserLogin(RestViews.APIView):
    
    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    
    @method_decorator(csrf_exempt)
    def post(self, request):
        if not get_or_none(sanitize_input)(request.data, required_keys=["Email", "Password"]):
            return Response(status=400, data={"message": "Malformed Input"})
        
        user = authenticate(request, username=request.data["Email"], password=request.data["Password"])
        if user is not None:
            if "Persistent" in request.data:
                if request.data["Persistent"]:
                    request.session.set_expiry(3600 * 24 * 30)  # 30 days
                else:
                    request.session.set_expiry(3600)
            login(request, user)
            
            if "DesktopAuthentication" in request.data:
                x_forwarded_for = request.META.get('HTTP_X_FORWARD_FOR')
                if x_forwarded_for:
                    ip = x_forwarded_for.split(',')[0]
                else:
                    ip = request.META.get('REMOTE_ADDR')

                token = models.AuthenticationTokens(user=user, ip_address=ip, type="Desktop")
                token.save()
                return Response(status=200, data={**user.get_info(), "AuthToken": token.token})

            return Response(status=200, data=user.get_info())
        return Response(status=400, data={"message": "Incorrect Email or Password"})

class FetchAuthorizedInstitute(RestViews.APIView):
    """ NOT IMPLEMENTED
    """

    permission_classes = [AllowAny,]
    parser_classes = [RestParsers.JSONParser]
    def post(self, request):
        return Response(status=404)

class QueryProfile(RestViews.APIView):

    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]
    
    def post(self, request):
        userInfo = request.user.get_info()
        userInfo["APIKey"] = request.user.api_token
        userInfo["Institutes"] = [{"Id": institute.uid, "Name": institute.name} for institute in models.Institute.find_all(members=request.user)]
        userInfo["Studies"] = [{"Id": study.uid, "Name": study.name} for study in models.Study.find_all(members=request.user)]

        if "RequestType" in request.data.keys():
            if request.data["RequestType"] == "RefreshAPIToken":
                request.user.api_token = get_token(64)
                request.user.save()
                userInfo["APIKey"] = request.user.api_token

            elif request.data["RequestType"] == "ChangeMainInstitute":
                if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "InstituteId"]):
                    return Response(status=400, data={"message": "Malformed Input"})

                institute = models.Institute.find(uid=request.data["InstituteId"])
                if not institute:
                    return Response(status=400, data={"message": "Permission Denied"})

                if not institute.has_permission(request.user):
                    return Response(status=400, data={"message": "Permission Denied"})
                
                request.user.institute = institute
                request.user.save()
                return Response(status=200)

            elif request.data["RequestType"] == "ChangeActiveStudy":
                if not get_or_none(sanitize_input)(request.data, required_keys=["RequestType", "StudyId"]):
                    return Response(status=400, data={"message": "Malformed Input"})

                if request.data["StudyId"] == "":
                    if "ActiveStudy" in request.user.configuration.keys():
                        del request.user.configuration["ActiveStudy"]
                        request.user.save()
                    return Response(status=200)

                study = models.Study.find(uid=request.data["StudyId"])
                if not study:
                    return Response(status=403)

                if not models.StudyRel.find(member=request.user, study=study):
                    return Response(status=403)
                
                request.user.configuration["ActiveStudy"] = request.data["StudyId"]
                request.user.save()
                return Response(status=200)

        return Response(status=200, data=userInfo)

class UserLogout(RestViews.APIView):
    
    permission_classes = [IsAuthenticated,]
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(csrf_protect if not settings.DEBUG else csrf_exempt)
    def post(self, request):
        logout(request)
        return Response(status=204)
    