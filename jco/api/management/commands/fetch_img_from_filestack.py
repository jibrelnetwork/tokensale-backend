import logging

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.db import transaction
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.files.base import ContentFile, File
import requests

from jco.api.models import Account, Document


class Command(BaseCommand):

    help = 'Downloads all documents from filestack and saves in Document models'

    def handle(self, *args, **options):
        accounts = Account.objects.filter(document_url__contains='cdn.filestackcontent.com').all()
        for account in accounts:
            try:
                self.stdout.write('Downloading {} for "{}"'.format(account.document_url, account.user.username))
                resp = requests.get(account.document_url)
                if resp.status_code != 200:
                    self.stdout.write(
                        self.style.ERROR('File "{}" resp status: {}'.format(account.document_url, resp.status_code)))
                    continue

                file = ContentFile(resp.content)
                document = Document.objects.create(user=account.user)
                document.image.save(resp.headers['X-File-Name'], file)

                account.document_url = "https://{}{}".format("saleapi.jibrel.network", document.image.url)
                account.save()
                self.stdout.write(
                    self.style.SUCCESS('Account "{}" updated'.format(account.user.username)))
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR('Error for account "{}": {}'.format(account.user.username, e)))
