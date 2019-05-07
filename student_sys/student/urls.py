from django.conf.urls import url
from django.shortcuts import render

from student_sys.urls import urlpatterns

urlpatterns[
    url(r'^$', render('index.html')),
]