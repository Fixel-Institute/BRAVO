from django.shortcuts import render
import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import HttpResponse

from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils.decorators import method_decorator

#from .models import Participant
from .models import PlatformUser

import os, pathlib
RESOURCES = str(pathlib.Path(__file__).parent.resolve())

class Homepage(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):
        context = {}
        
        """
        # If Production
        bundleJSs = os.listdir(RESOURCES + "/../Frontend/build/static/js")
        for file in bundleJSs:
            if file.startswith("main") and file.endswith(".js"):
                context["bundleURL"] = file
        """
        
        # If Development:
        context["ReactBundleURL"] = "http://localhost:3000/static/js/bundle.js"
        
        return render(request, "index.html", context=context)