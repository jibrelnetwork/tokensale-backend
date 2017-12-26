import logging
import uuid
import binascii
import os

from allauth.account.models import EmailAddress
from django.db import models, transaction
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.template.loader import render_to_string
from django.utils.timezone import now
from django.contrib.auth.tokens import default_token_generator as token_generator
from django.contrib.sites.shortcuts import get_current_site

from jco.appdb.models import CurrencyType
from jco.appdb.models import TransactionStatus
from jco.appdb.models import NotificationType
from jco.appdb.models import NOTIFICATION_KEYS, NOTIFICATION_SUBJECTS
from jco.appprocessor import notify


logger = logging.getLogger(__name__)


class Account(models.Model):
    first_name = models.CharField(max_length=120, null=False, blank=True)
    last_name = models.CharField(max_length=120, null=False, blank=True)
    fullname = models.CharField(max_length=120, null=False, blank=True)
    citizenship = models.CharField(max_length=120, null=False, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    residency = models.CharField(max_length=120, null=False, blank=True)

    country = models.CharField(max_length=120, null=False, blank=True)
    street = models.CharField(max_length=120, null=False, blank=True)
    town = models.CharField(max_length=120, null=False, blank=True)
    postcode = models.CharField(max_length=120, null=False, blank=True)

    terms_confirmed = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)
    is_identity_verified = models.BooleanField(default=False, verbose_name='Approved')
    is_identity_verification_declined = models.BooleanField(default=False, verbose_name='Declined')

    document_url = models.URLField(max_length=200, null=False, blank=True)
    document_type = models.CharField(max_length=20, null=False, blank=True)
    is_document_skipped = models.BooleanField(default=False)

    onfido_applicant_id = models.CharField(max_length=200, null=True, blank=True)
    onfido_document_id = models.CharField(max_length=200, null=True, blank=True)
    onfido_check_id = models.CharField(max_length=200, null=True, blank=True)
    onfido_check_status = models.CharField(max_length=200, null=True, blank=True)
    onfido_check_result = models.CharField(max_length=200, null=True, blank=True)
    onfido_check_created = models.DateTimeField(null=True, blank=True)
    verification_started_at = models.DateTimeField(null=True, blank=True)
    verification_attempts = models.IntegerField(default=0)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    withdraw_address = models.CharField(max_length=255, null=True, blank=True)

    comment = models.TextField(null=True, blank=True)
    is_presale_account = models.BooleanField(default=False)
    is_sale_allocation = models.BooleanField(default=True)

    tracking = JSONField(blank=True, default=dict)

    class Meta:
        db_table = 'account'

    def reset_verification_state(self, fullreset=True):

        self.onfido_applicant_id = None
        self.onfido_document_id = None
        self.onfido_check_id = None
        self.onfido_check_status = None
        self.onfido_check_result = None
        self.onfido_check_created = None
        self.is_identity_verified = False
        self.is_identity_verification_declined = False
        self.verification_attempts = 0

        if fullreset:
            self.document_type = ''
            self.document_url = ''
            self.first_name = ''
            self.last_name = ''
            self.date_of_birth = None
            self.residency = ''
            self.country = ''
            self.citizenship = ''
        self.save()

    def approve_verification(self):
        self.is_identity_verified = True
        self.is_identity_verification_declined = False
        self.save()
        Address.assign_pair_to_user(self.user)

    def decline_verification(self):
        self.is_identity_verified = False
        self.is_identity_verification_declined = True
        self.save()
        notify.send_email_kyc_account_rejected(self.user.email if self.user else None,
                                               self.user.id if self.user else None)

    def get_jnt_balance(self):
        presale_balance = PresaleJnt.objects.filter(
            user=self.user).aggregate(models.Sum('jnt_value'))['jnt_value__sum'] or 0
        jnt_balance = (Jnt.objects.filter(transaction__address__user=self.user,
                                          transaction__status=TransactionStatus.success)
                       .aggregate(models.Sum('jnt_value')))['jnt_value__sum'] or 0

        withdraws = Withdraw.objects.filter(
            user=self.user).aggregate(models.Sum('value'))['value__sum'] or 0
        return jnt_balance + presale_balance - withdraws

    def __str__(self):
        return '{} {}'.format(self.first_name, self.last_name)


class Address(models.Model):
    address = models.CharField(unique=True, max_length=255)
    type = models.CharField(max_length=10)
    is_usable = models.BooleanField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING,
                             blank=True, null=True, related_name='pay_addresses')
    meta = JSONField(default=dict)  # This field type is a guess.

    class Meta:
        db_table = 'address'

    def __str__(self):
        return '{}: {}'.format(self.type, self.address)

    @classmethod
    def assign_pair_to_user(cls, user):
        if cls.objects.filter(user=user).count() > 0:
            logger.info('User %s already have address', user.username)
            return False
        with transaction.atomic():
            eth_addr = (cls.objects.select_for_update()
                        .filter(type=CurrencyType.eth, user=None, is_usable=True).first())
            if not eth_addr:
                logger.error('No more addresses')
                return False
            eth_addr.user = user
            eth_addr.save()
            logger.info('ETH Address %s is assigned to user %s', eth_addr.address, user.username)

            btc_addr = (cls.objects.select_for_update()
                        .filter(type=CurrencyType.btc, user=None, is_usable=True).first())
            btc_addr.user = user
            btc_addr.save()
            logger.info('BTC Address %s is assigned to user %s', btc_addr.address, user.username)
        return True


class Transaction(models.Model):
    transaction_id = models.CharField(unique=True, max_length=120)
    value = models.FloatField()
    mined = models.DateTimeField()
    block_height = models.IntegerField()
    address = models.ForeignKey(Address, models.DO_NOTHING)
    status = models.CharField(max_length=10, default=TransactionStatus.pending)
    meta = JSONField(default=dict)  # This field type is a guess.

    class Meta:
        db_table = 'transaction'

    def __str__(self):
        return '{} [{}]'.format(self.transaction_id, self.value)


class Price(models.Model):
    fixed_currency = models.CharField(max_length=10)
    variable_currency = models.CharField(max_length=10)
    value = models.FloatField()
    created = models.DateTimeField()
    meta = JSONField(default={})  # This field type is a guess.

    class Meta:
        db_table = 'price'


class Jnt(models.Model):
    currency_to_usd_rate = models.FloatField()
    usd_value = models.FloatField()
    jnt_to_usd_rate = models.FloatField(help_text='If you change this value and save - jnt_value'
                                                  ' will be recalculated as '
                                                  'jnt_value = usd_value / jnt_to_usd_rate')
    jnt_value = models.FloatField()
    active = models.BooleanField()
    created = models.DateTimeField()
    is_sale_allocation = models.BooleanField(default=True)
    transaction = models.OneToOneField('Transaction', models.DO_NOTHING,
                                       unique=True, related_name='jnt')
    meta = JSONField(default={})  # This field type is a guess.

    class Meta:
        db_table = 'JNT'

    def __str__(self):
        return '{} [{}]'.format(str(self.created), self.jnt_value)


def get_raised_tokens():
    """
    Get raised tokens amount
    """
    manual_jnt = (PresaleJnt.objects.filter(is_sale_allocation=True, is_presale_round=False)
                  .aggregate(models.Sum('jnt_value'))['jnt_value__sum'] or 0)

    jnt = (Jnt.objects.filter(is_sale_allocation=True)
           .aggregate(models.Sum('jnt_value'))['jnt_value__sum'] or 0)

    return manual_jnt + jnt + settings.RAISED_TOKENS_SHIFT


class Withdraw(models.Model):
    transaction_id = models.CharField(max_length=120, null=True, blank=True)
    to = models.CharField(max_length=255)
    value = models.FloatField()
    created = models.DateTimeField()
    mined = models.DateTimeField(null=True, blank=True)
    block_height = models.IntegerField(blank=True, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING, blank=True, null=True,
                             related_name='withdraws')
    status = models.CharField(max_length=20, default=TransactionStatus.not_confirmed)
    meta = JSONField(default=dict)  # This field type is a guess.

    class Meta:
        db_table = 'withdraw'


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING,
                             blank=True, null=True, related_name='notifications')

    type = models.CharField(max_length=100)
    email = models.CharField(max_length=120, null=False)
    created = models.DateTimeField(auto_now_add=True)
    sended = models.DateTimeField(null=True)
    is_sended = models.BooleanField(default=False)
    rendered_message = models.TextField(null=True, blank=True)

    meta = JSONField(default=dict)  # This field type is a guess.

    class Meta:
        db_table = 'notification'

    def __str__(self):
        return '{} [{}, {}]'.format(self.type, self.created, self.is_sended)

    def get_subject(self):
        return NOTIFICATION_SUBJECTS[self.get_key()].format(**self.meta)

    def get_template(self):
        return "{}.html".format(self.get_key())

    def get_key(self):
        return NOTIFICATION_KEYS[self.type]

    def get_body(self):
        return render_to_string(self.get_template(), self.meta)


class PresaleJnt(models.Model):
    """
    JNT from presale round
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    jnt_value = models.FloatField()
    created = models.DateTimeField()
    comment = models.CharField(max_length=32, default='ANGEL ROUND / PRESALE')
    is_sale_allocation = models.BooleanField()
    is_presale_round = models.BooleanField()

    class Meta:
        db_table = 'presale_jnt'


class Affiliate(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    event = models.CharField(max_length=20)
    url = models.CharField(max_length=300, null=False)
    created = models.DateTimeField(auto_now_add=True)
    sended = models.DateTimeField(null=True)
    status = models.IntegerField(blank=True, null=True)
    meta = JSONField(default=dict)  # This field type is a guess.

    class Meta:
        db_table = 'affiliate'


class OperationError(Exception):
    """
    Operation execution error
    """

def get_document_filename_extension(filename):
    if len(filename.split(".")) > 1:
        return filename.split(".")[-1]
    else:
        return "unknown"


def unique_document_filename(document, filename):
    extension = get_document_filename_extension(filename)
    return "{}.{}".format(uuid.uuid4(), extension)


class Document(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    image = models.FileField('uploaded document', upload_to=unique_document_filename)  # stores the uploaded documents

    class Meta:
        db_table = 'document'


class ChangeAddressHandler:

    def send_confirmation_email(self, email, confirmation_url, params):
        data = {'confirm_url': confirmation_url}
        return notify.add_notification(
            email, type=NotificationType.withdraw_address_change_request, data=data)

    def run(self, user, params):
        logger.info('Running ChangeAddressHandler for %s', user.username)
        old_address = user.account.withdraw_address
        user.account.withdraw_address = params['address']
        user.account.save()
        logger.info('Withdraw address changed for %s: %s -> %s',
                    user.username, old_address, user.account.withdraw_address)

    def notify_completed(self, email, params):
        return notify.add_notification(
            email, type=NotificationType.withdraw_address_changed)


class WithdrawJntHandler:

    def send_confirmation_email(self, email, confirmation_url, params):
        data = {
            'confirm_url': confirmation_url,
            'withdraw_jnt_amount': params['jnt_amount'],
            'withdraw_address': params['address'],
        }
        return notify.add_notification(
            email, type=NotificationType.withdrawal_request, data=data)

    def run(self, user, params):
        logger.info('Running WithdrawJntHandler for %s', user.username)
        withdraw = Withdraw.objects.get(user=user, pk=params['withdraw_id'])
        if withdraw.status == TransactionStatus.not_confirmed:
            withdraw.status = TransactionStatus.confirmed
            withdraw.save()
            logger.info('Withdraw #%s for %s is in status confirmed now', withdraw.pk, user.username)
        else:
            logger.info('Withdraw #%s is already in status %s', withdraw.pk, withdraw.status)

    def notify_completed(self, email, params):
        data = {
            'withdraw_jnt_amount': params['jnt_amount'],
            'withdraw_address': params['address'],
        }
        return notify.add_notification(
            email, type=NotificationType.withdrawal_processed, data=data)


class Operation(models.Model):
    """
    Some operations are requires email confirmation
    """
    OP_CHANGE_ADDRESS = 'change_address'
    OP_WITHDRAW_JNT = 'withdraw_jnt'

    OP_CHOICES = [
        (OP_CHANGE_ADDRESS, 'Change Withdraw Address'),
        (OP_WITHDRAW_JNT, 'Withdraw JNT '),
    ]

    handlers = {
        OP_CHANGE_ADDRESS: ChangeAddressHandler(),
        OP_WITHDRAW_JNT: WithdrawJntHandler(),
    }

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    key = models.CharField(max_length=40)
    user = models.ForeignKey(settings.AUTH_USER_MODEL)
    operation = models.CharField(max_length=20, choices=OP_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    confirmed_at = models.DateTimeField(null=True)
    params = JSONField(default=dict)

    class Meta:
        db_table = 'operation'

    def save(self, *args, **kwargs):
        if not self.key:
            self.key = self.generate_token()
        return super().save(*args, **kwargs)

    def request_confirmation(self):
        """
        Request operation confirmation - send email with one-time link for this op
        """
        confirmation_url = self.make_confirmation_url()
        return self.get_handler().send_confirmation_email(
            self.user.username, confirmation_url, self.params)

    def perform(self, token):
        logger.info('Performing operation #%s %s for %s', self.pk, self.operation, self.user.username)
        if self.confirmed_at is not None:
            raise OperationError('This operation has already been completed')
        self.validate_token(token)
        self.get_handler().run(self.user, self.params)
        self.confirmed_at = now()
        self.get_handler().notify_completed(self.user.username, self.params)
        self.save()
        logger.info('Operation succeed #%s %s for %s', self.pk, self.operation, self.user.username)

    def validate_token(self, token):
        if self.key != token:
            logger.info('Invalid token %s, op: #%s %s for %s',
                        token, self.pk, self.operation, self.user.username)
            raise OperationError('Invalid token')

    def generate_token(self):
        return binascii.hexlify(os.urandom(20)).decode()

    def make_confirmation_url(self):
        site = get_current_site(None)
        op_url_map = {
            self.OP_WITHDRAW_JNT: 'withdraw-confirm',
            self.OP_CHANGE_ADDRESS: 'change-address-confirm',
        }
        return 'https://{}/#/welcome/{}/request/{}/{}'.format(
            site.domain, op_url_map[self.operation], self.pk, self.key)

    def get_handler(self):
        return self.handlers[self.operation]

    @classmethod
    def create_operation(cls, operation, user, params):
        with transaction.atomic():
            op = cls.objects.create(
                operation=operation,
                user=user,
                params=params
            )
            confirm_success = op.request_confirmation()
            if confirm_success is False:
                raise OperationError("Confirmation message creation failure")
            return op


class UserJntPrice(models.Model):
    """
    # 71 Custom JNT price for user
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING,
                             related_name='custom_jnt_prices')
    created_at = models.DateTimeField(auto_now_add=True)
    value = models.FloatField()

    class Meta:
        db_table = 'user_jnt_price'

    def __str__(self):
        return 'Custom Price for {}: {}$/JNT'.format(self.user.username, self.value)


def is_user_email_confirmed(user):
    try:
        email = EmailAddress.objects.get(email=user.username)
        return email.verified
    except EmailAddress.DoesNotExist:
        logger.error('No EmailAddress for user %s!!', user.username)
        return False
