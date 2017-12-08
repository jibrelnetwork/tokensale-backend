from django.dispatch import receiver
from django.apps import AppConfig

from jco.api import tasks


class ApiConfig(AppConfig):
    name = 'api'

    def ready(self):
        from jco.receivers import connect_all
        connect_all()
