from django.db import models
from django.conf import settings
from django.contrib.postgres.fields import JSONField


class Account(models.Model):
    first_name = models.CharField(max_length=120, null=False, blank=True)
    last_name = models.CharField(max_length=120, null=False, blank=True)
    fullname = models.CharField(max_length=120, null=False, blank=True)
    email = models.CharField(unique=True, max_length=120, null=False, blank=True)
    country = models.CharField(max_length=120, null=False, blank=True)
    citizenship = models.CharField(max_length=120, null=False, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    residency = models.CharField(max_length=120, null=False, blank=True)
    
    terms_confirmed = models.BooleanField(default=False)
    docs_received = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    notified = models.BooleanField(default=False)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    class Meta:
        db_table = 'account'


class Address(models.Model):
    address = models.CharField(unique=True, max_length=255)
    type = models.CharField(max_length=10)
    is_usable = models.BooleanField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, models.DO_NOTHING,
                             blank=True, null=True, related_name='pay_addresses')
    meta = JSONField(default=dict)  # This field type is a guess.

    class Meta:
        db_table = 'address'


class Transaction(models.Model):
    transaction_id = models.CharField(unique=True, max_length=120)
    value = models.FloatField()
    mined = models.DateTimeField()
    block_height = models.IntegerField()
    address = models.ForeignKey(Address, models.DO_NOTHING)
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
