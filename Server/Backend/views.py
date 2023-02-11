from django.shortcuts import render

import rest_framework.views as RestViews
import rest_framework.parsers as RestParsers
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.http import HttpResponse

class Homepage(RestViews.APIView):
    parser_classes = [RestParsers.JSONParser]
    def get(self, request):
        return render(request, "blank.html")
