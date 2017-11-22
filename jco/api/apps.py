from django.apps import AppConfig

from jco.api import tasks


class ApiConfig(AppConfig):
    name = 'api'
