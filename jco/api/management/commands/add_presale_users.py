import csv
import datetime
import logging
import sys

from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.utils.crypto import get_random_string
from django.db import transaction
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from allauth.account.adapter import build_absolute_uri
from allauth.account.models import EmailAddress

from jco.api.models import Account, Address, PresaleJnt
from jco.api.tasks import verify_user
from jco.appprocessor.commands import assign_addresses
from jco.appprocessor.notify import send_email_presale_account_created


class Command(BaseCommand):
    """
    First Name ,First Name,Last name,Birth date,JNT Amount,Email,Country,Passport
    """
    help = 'Creates accounts for presale users from CSV file'

    # def add_arguments(self, parser):
    #     parser.add_argument('poll_id', nargs='+', type=int)

    def handle(self, *args, **options):
        reader = csv.reader(sys.stdin)
        next(reader)
        created_users = []
        success = False
        with transaction.atomic():
            for row in reader:
                user = self.process_row(row)
                created_users.append(user)
                enter_url = self.get_enter_url(user)
                send_email_presale_account_created(user.username, user, enter_url)
            success = True

        if success is True:
            for user in created_users:
                print('Verify', user.pk)
                # verify_user.delay(user.pk)

    def process_row(self, row):
        first_name = row[1].strip()
        last_name = row[2].strip()
        date_of_birth = datetime.datetime.strptime(row[3].strip(), '%m/%d/%Y')
        jnt_amount = row[4].strip().replace(',', '')
        email = row[5].strip()
        country = row[6].strip()
        document_url = row[8].strip()
        password = get_random_string(length=12)

        user = get_user_model().objects.create_user(email, email, password)
        EmailAddress.objects.create(user=user,
                                    email=user.username,
                                    primary=True,
                                    verified=True)
        account = Account.objects.create(
            user=user,
            first_name=first_name,
            last_name=last_name,
            date_of_birth=date_of_birth,
            country=country,
            document_url=document_url,
            is_presale_account=True,
        )
        Address.assign_pair_to_user(user)
        jnt = PresaleJnt.objects.create(
            user=user,
            jnt_value=jnt_amount,
            created=datetime.datetime(2017, 11, 27, 12)
        )
        self.stdout.write(
            self.style.SUCCESS('Account "{}", JNT {} created'.format(user.username, jnt.jnt_value)))
        return user

    def get_enter_url(self, user):
        uid = urlsafe_base64_encode(force_bytes(user.pk)).decode()
        token = default_token_generator.make_token(user)
        location = '/#/welcome/password/change/{uid}/{token}'.format(uid=uid, token=token)
        return build_absolute_uri(None, location)
