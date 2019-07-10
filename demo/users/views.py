from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, HttpRequest


def index(request):

    return HttpResponse("Hello World!")
