import logging

from django.db import models, transaction
from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.template.loader import render_to_string

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

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    withdraw_address = models.CharField(max_length=255, null=True, blank=True)

    comment = models.TextField(null=True, blank=True)
    is_presale_account = models.BooleanField(default=False)

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
    purchase_id = models.CharField(unique=True, max_length=64)
    currency_to_usd_rate = models.FloatField()
    usd_value = models.FloatField()
    jnt_to_usd_rate = models.FloatField()
    jnt_value = models.FloatField()
    active = models.BooleanField()
    created = models.DateTimeField()
    transaction = models.OneToOneField('Transaction', models.DO_NOTHING,
                                    unique=True, related_name='jnt')
    meta = JSONField(default={})  # This field type is a guess.

    class Meta:
        db_table = 'JNT'

    def __str__(self):
        return '{} [{}]'.format(self.purchase_id, self.jnt_value)


def get_raised_tokens():
    """
    Get raised tokens amount
    """
    return (Jnt.objects.all().aggregate(
        models.Sum('jnt_value'))['jnt_value__sum'] or 0) + settings.RAISED_TOKENS_SHIFT


class Withdraw(models.Model):
    transaction_id = models.CharField(max_length=120)
    to = models.CharField(max_length=255)
    value = models.FloatField()
    created = models.DateTimeField()
    mined = models.DateTimeField(null=True)
    block_height = models.IntegerField(blank=True, null=True)
    address = models.ForeignKey(Address, models.DO_NOTHING, null=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING, blank=True, null=True,
                             related_name='withdraws')
    status = models.CharField(max_length=10, default=TransactionStatus.pending)
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
