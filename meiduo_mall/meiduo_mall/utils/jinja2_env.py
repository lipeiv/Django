from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from jinja2 import Environment


def jinja2_environment(**option):
    env = Environment(**option)
    env.globals.update({
        "static": staticfiles_storage.url,
        "url": reverse,
    })
