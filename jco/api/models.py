from django.db import models, transaction
from django.conf import settings
from django.contrib.postgres.fields import JSONField

from jco.appdb.models import CurrencyType
from jco.appdb.models import TransactionStatus


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
    docs_received = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)
    is_identity_verified = models.BooleanField(default=False)

    document_url = models.URLField(max_length=200, null=False, blank=True)

    onfido_applicant_id = models.CharField(max_length=200, null=True, blank=True)
    onfido_document_id = models.CharField(max_length=200, null=True, blank=True)
    onfido_check_id = models.CharField(max_length=200, null=True, blank=True)
    onfido_check_status = models.CharField(max_length=200, null=True, blank=True)
    onfido_check_result = models.CharField(max_length=200, null=True, blank=True)
    onfido_check_created = models.DateTimeField(null=True, blank=True)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        db_table = 'account'

    def reset_verification_state(self):
        self.onfido_applicant_id = None
        self.onfido_document_id = None
        self.onfido_check_id = None
        self.onfido_check_status = None
        self.onfido_check_result = None
        self.onfido_check_created = None
        self.save()


class Address(models.Model):
    address = models.CharField(unique=True, max_length=255)
    type = models.CharField(max_length=10)
    is_usable = models.BooleanField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING,
                             blank=True, null=True, related_name='pay_addresses')
    meta = JSONField(default=dict)  # This field type is a guess.

    class Meta:
        db_table = 'address'

    @classmethod
    def assign_pair_to_user(cls, user):
        with transaction.atomic():
            eth_addr = (cls.objects.select_for_update()
                        .filter(type=CurrencyType.eth, user=None).first())
            eth_addr.user = user
            eth_addr.save()

            btc_addr = (cls.objects.select_for_update()
                        .filter(type=CurrencyType.btc, user=None).first())
            btc_addr.user = user
            btc_addr.save()



class Transaction(models.Model):
    transaction_id = models.CharField(unique=True, max_length=120)
    value = models.FloatField()
    mined = models.DateTimeField()
    block_height = models.IntegerField()
    address = models.ForeignKey(Address, models.DO_NOTHING)
    status = models.CharField(max_length=10)
    meta = JSONField(default=dict)  # This field type is a guess.

    class Meta:
        db_table = 'transaction'


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
    transaction = models.ForeignKey('Transaction', models.DO_NOTHING, unique=True)
    meta = JSONField(default={})  # This field type is a guess.

    class Meta:
        db_table = 'JNT'


def get_raised_tokens():
    """
    Get raised tokens amount
    """
    return Jnt.objects.all().aggregate(models.Sum('jnt_value'))['jnt_value__sum'] or 0


class Withdraw(models.Model):
    transaction_id = models.CharField(unique=True, max_length=120)
    to = models.CharField(unique=True, max_length=255)
    value = models.FloatField()
    created = models.DateTimeField()
    mined = models.DateTimeField()
    block_height = models.IntegerField()
    address = models.ForeignKey(Address, models.DO_NOTHING)
    status = models.CharField(max_length=10)
    meta = JSONField(default=dict)  # This field type is a guess.

    class Meta:
        db_table = 'withdraw'
