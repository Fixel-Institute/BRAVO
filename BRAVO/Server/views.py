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
SQL Table Definitions
===================================================
@author: Jackson Cagle, University of Florida
@email: jackson.cagle@neurology.ufl.edu
"""

import os
from uuid import uuid4
import datetime

from django.shortcuts import render
from django.http.response import HttpResponseRedirect
import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers

from django.views.decorators.csrf import ensure_csrf_cookie 
from django.utils.decorators import method_decorator

from Server import models

ConsecutiveError = {}

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARD_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

class StaticProxy(RestViews.APIView):
    def get(self, request):
        return HttpResponseRedirect('//' + os.environ["SERVER_HOST"] + ':3000' + request.path)

class Homepage(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]

    @method_decorator(ensure_csrf_cookie)
    def get(self, request):

        requestTime = datetime.datetime.now().timestamp()
        requestIpAddr = get_client_ip(request)

        if models.BlacklistRecords.exists(ip_address=requestIpAddr):
            return render(request, "404.html")
        
        if str(request.user) == "AnonymousUser":
            if not requestIpAddr in ConsecutiveError.keys():
                ConsecutiveError[requestIpAddr] = {
                    "LastRequest": requestTime,
                    "Count": 1
                }

            else:
                if requestTime - ConsecutiveError[requestIpAddr]["LastRequest"] < 10:
                    ConsecutiveError[requestIpAddr]["Count"] += 1
                else:
                    ConsecutiveError[requestIpAddr]["LastRequest"] = requestTime
                    ConsecutiveError[requestIpAddr]["Count"] = 1
                
                if ConsecutiveError[requestIpAddr]["Count"] > 10:
                    models.BlacklistRecords(ip_address=requestIpAddr, reason="Frequent Request").save()
        
        AllKeys = list(ConsecutiveError.keys())
        for key in AllKeys:
            if requestTime - ConsecutiveError[key]["LastRequest"] > 30:
                del ConsecutiveError[key]

        context = {}
        
        # If Development Uncomment the following: 
        # return render(request, "index_dev.html", context=context)
        return render(request, "index.html", context=context)
