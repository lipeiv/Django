from django.shortcuts import render

# Create your views here.
from django.http import HttpResponse, HttpRequest


def index(request):
    response = HttpResponse("OK")
    response.set_cookie('name', 'lipeipei', max_age=3600)
    cookie = request.COOKIES.get('name')
    print(cookie)
    # response = HttpResponse("cookie:" + cookie)
    return response
