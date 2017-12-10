import logging
from datetime import datetime

from django.db import transaction
from django.db.models import Sum
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import ugettext_lazy as _
from django.contrib.sites.models import Site
from allauth.account import app_settings as allauth_settings
from allauth.utils import email_address_exists
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from rest_auth.serializers import PasswordResetSerializer, PasswordResetForm
from rest_framework import serializers, exceptions
from rest_framework.fields import CurrentUserDefault
import requests

from jco.api.models import (
    Transaction, Address, Account, Jnt, Withdraw, PresaleJnt, is_user_email_confirmed, Document,
    get_document_filename_extension
)
from jco.commonutils import person_verify
from jco.commonutils import ga_integration
from jco.appdb.models import TransactionStatus, CurrencyType
from jco.appprocessor.notify import send_email_reset_password
from jco.commonutils import ethaddress_verify


logger = logging.getLogger(__name__)

RECAPTCA_API_URL = 'https://www.google.com/recaptcha/api/siteverify'


class AccountSerializer(serializers.ModelSerializer):
    username = serializers.SerializerMethodField()
    jnt_balance = serializers.SerializerMethodField()
    verification_form_status = serializers.SerializerMethodField()
    identity_verification_status = serializers.SerializerMethodField()
    is_email_confirmed = serializers.SerializerMethodField()
    btc_address = serializers.SerializerMethodField()
    eth_address = serializers.SerializerMethodField()

    class Meta:
        model = Account
        fields = ('username', 'first_name', 'last_name', 'date_of_birth',
                  'citizenship', 'residency', 'terms_confirmed', 'document_url', 'document_type',
                  'jnt_balance', 'identity_verification_status', 'verification_form_status',
                  'btc_address', 'eth_address', 'is_document_skipped', 'is_email_confirmed')
        read_only_fields = ('is_identity_verified', 'jnt_balance')

    def get_username(self, obj):
        return obj.user.username

    def get_jnt_balance(self, obj):
        presale_balance = PresaleJnt.objects.filter(
            user=obj.user).aggregate(Sum('jnt_value'))['jnt_value__sum'] or 0
        jnt_balance = (Jnt.objects.filter(transaction__address__user=obj.user,
                                          transaction__status=TransactionStatus.success)
                       .aggregate(Sum('jnt_value')))['jnt_value__sum'] or 0
        return jnt_balance + presale_balance

    def get_verification_form_status(self, obj):
        def personal_data_filled(obj):
            fields = [obj.first_name, obj.last_name, obj.date_of_birth,
                      obj.residency, obj.citizenship]
            if all(fields):
                return True
            else:
                return False

        if obj.is_document_skipped is True:
            return 'passport_skipped'
        elif obj.document_url:
            return 'passport_uploaded'
        elif personal_data_filled(obj) is True:
            return 'personal_data_filled'
        elif obj.terms_confirmed is True:
            return 'terms_confirmed'

    def get_identity_verification_status(self, obj):
        if obj.is_identity_verified is True:
            return 'Approved'
        elif obj.is_identity_verification_declined is True:
            return 'Declined'
        elif obj.document_url:
            return 'Preliminarily Approved'
        elif obj.is_document_skipped is True:
            return 'Pending'

    def get_btc_address(self, obj):
        address = Address.objects.filter(
            user=obj.user, type=CurrencyType.btc).first()
        if address is not None:
            return address.address

    def get_eth_address(self, obj):
        address = Address.objects.filter(
            user=obj.user, type=CurrencyType.eth).first()
        if address is not None:
            return address.address

    def get_is_email_confirmed(self, obj):
        return is_user_email_confirmed(obj.user)


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('address', 'type', )


class TransactionSerializer(serializers.ModelSerializer):
    """
    {
        jnt: 10000,
        type: 'outgoing',
        date: '13:30 10/22/2017',
        TXtype: 'BTC',
        TXhash: '0x00360d2b7d240ec0643b6d819ba81a09e40e5bc2',
        status: 'complete',
        amount: '10 BTC / 72 000 USD',
    }
    """

    type = serializers.SerializerMethodField()
    jnt = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    TXtype = serializers.SerializerMethodField()
    date = serializers.SerializerMethodField()
    TXhash = serializers.CharField(source='transaction_id')
    amount_usd = serializers.SerializerMethodField()
    amount_cryptocurrency = serializers.SerializerMethodField()
    _date = serializers.DateTimeField(source='mined')

    class Meta:
        model = Transaction
        fields = ('jnt', 'status', 'TXtype', 'date', 'type', '_date',
                  'TXhash', 'amount_usd', 'amount_cryptocurrency')

    def get_type(self, obj):
        return 'incoming'

    def get_jnt(self, obj):
        return obj.jnt.jnt_value

    def get_status(self, obj):
        return {
            TransactionStatus.pending: 'waiting',
            TransactionStatus.success: 'complete',
            TransactionStatus.fail: 'failed',
        }.get(obj.status)

    def get_TXtype(self, obj):
        return obj.address.type.upper()

    def get_date(self, obj):
        if obj.mined is not None:
            return datetime.strftime(obj.mined, '%H:%M %m/%d/%Y')

    def get_amount_usd(self, obj):
        return obj.jnt.usd_value

    def get_amount_cryptocurrency(self, obj):
        return obj.value


class WithdrawSerializer(TransactionSerializer):

    _date = serializers.DateTimeField(source='created')

    class Meta:
        model = Withdraw
        fields = ('jnt', 'status', 'TXtype', 'date', 'type', '_date',
                  'TXhash', 'amount_usd', 'amount_cryptocurrency')

    def get_type(self, obj):
        return 'outgoing'

    def get_date(self, obj):
        if obj.created is not None:
            return datetime.strftime(obj.created, '%H:%M %m/%d/%Y')

    def get_jnt(self, obj):
        return obj.value

    def get_TXtype(self, obj):
        return 'ETH'

    def get_TXhash(self, obj):
        return 'ETH'

    def get_amount_usd(self, obj):
        return None

    def get_amount_cryptocurrency(self, obj):
        return None


class PresaleJntSerializer(TransactionSerializer):
    _date = serializers.DateTimeField(source='created')
    TXhash = serializers.SerializerMethodField()
    is_presale = serializers.SerializerMethodField()

    class Meta:
        model = PresaleJnt
        fields = ('jnt', 'status', 'TXtype', 'date', 'type', '_date',
                  'TXhash', 'amount_usd', 'amount_cryptocurrency', 'is_presale')

    def get_is_presale(self, obj):
        return True

    def get_type(self, obj):
        return 'incoming'

    def get_date(self, obj):
        if obj.created is not None:
            return datetime.strftime(obj.created, '%H:%M %m/%d/%Y')

    def get_jnt(self, obj):
        return obj.jnt_value

    def get_TXtype(self, obj):
        return 'ETH'

    def get_TXhash(self, obj):
        return 'ANGEL ROUND / PRESALE'

    def get_amount_usd(self, obj):
        return None

    def get_amount_cryptocurrency(self, obj):
        return None

    def get_status(self, obj):
        return 'complete'


class RegisterSerializer(serializers.Serializer):

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    password_confirm = serializers.CharField(required=True, write_only=True)
    captcha = serializers.CharField(required=True, write_only=True)
    tracking = serializers.JSONField(write_only=True, required=False, default=dict)

    def validate_username(self, username):
        username = get_adapter().clean_username(username)
        return username

    def validate_email(self, email):
        email = get_adapter().clean_email(email)

        if email:
            email = email.lower()

        if allauth_settings.UNIQUE_EMAIL:
            if email and email_address_exists(email):
                raise serializers.ValidationError(
                    _("A user is already registered with this e-mail address."))
        return email

    def validate_password(self, password):
        return get_adapter().clean_password(password)

    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError(_("The two password fields didn't match."))
        return data

    def validate_captcha(self, captcha_token):
        if settings.RECAPTCHA_ENABLED is not True:
            return True
        try:
            r = requests.post(
                RECAPTCA_API_URL,
                {
                    'secret': settings.RECAPTCHA_PRIVATE_KEY,
                    'response': captcha_token
                },
                timeout=5
            )
            r.raise_for_status()
        except requests.RequestException as e:
            raise serializers.ValidationError(
                _('Connection to reCaptcha server failed. Please try again')
            )

        json_response = r.json()

        if bool(json_response['success']):
            return True
        else:
            if 'error-codes' in json_response:
                if 'missing-input-secret' in json_response['error-codes'] or \
                        'invalid-input-secret' in json_response['error-codes']:

                    logger.error('Invalid reCaptcha secret key detected')
                    raise serializers.ValidationError(
                        _('Connection to reCaptcha server failed')
                    )
                else:
                    raise serializers.ValidationError(
                        _('reCaptcha invalid or expired, try again')
                    )
            else:
                logger.error('No error-codes received from Google reCaptcha server')
                raise serializers.ValidationError(
                    _('reCaptcha response from Google not valid, try again')
                )

    def custom_signup(self, request, user):
        pass

    def get_cleaned_data(self):
        return {
            'username': self.validated_data.get('email', ''),
            'password1': self.validated_data.get('password', ''),
            'email': self.validated_data.get('email', '')
        }

    def save(self, request):
        adapter = get_adapter()
        user = adapter.new_user(request)
        self.cleaned_data = self.get_cleaned_data()
        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        tracking = self.validated_data.get('tracking', {})
        account = Account.objects.create(user=user, tracking=tracking)
        ga_integration.on_status_new(account)
        return user


# Get the UserModel
UserModel = get_user_model()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, allow_blank=False)
    password = serializers.CharField(style={'input_type': 'password'})

    def _validate_email(self, email, password):
        user = None

        if email and password:
            user = authenticate(email=email, password=password)
        else:
            msg = _('Must include "email" and "password".')
            raise exceptions.ValidationError(msg)

        return user

    def _validate_username(self, username, password):
        user = None

        if username and password:
            user = authenticate(username=username, password=password)
        else:
            msg = _('Must include "username" and "password".')
            raise exceptions.ValidationError(msg)

        return user

    def _validate_username_email(self, username, email, password):
        user = None

        if email and password:
            user = authenticate(email=email, password=password)
        elif username and password:
            user = authenticate(username=username, password=password)
        else:
            msg = _('Must include either "username" or "email" and "password".')
            raise exceptions.ValidationError(msg)

        return user

    def validate(self, attrs):
        username = attrs.get('email')
        email = attrs.get('email')
        password = attrs.get('password')

        user = None

        if username:
            username = username.lower()

        if email:
            email = email.lower()

        if 'allauth' in settings.INSTALLED_APPS:
            from allauth.account import app_settings

            # Authentication through email
            if app_settings.AUTHENTICATION_METHOD == app_settings.AuthenticationMethod.EMAIL:
                user = self._validate_email(email, password)

            # Authentication through username
            if app_settings.AUTHENTICATION_METHOD == app_settings.AuthenticationMethod.USERNAME:
                user = self._validate_username(username, password)

            # Authentication through either username or email
            else:
                user = self._validate_username_email(username, email, password)

        else:
            # Authentication without using allauth
            if email:
                try:
                    username = UserModel.objects.get(email__iexact=email).get_username()
                except UserModel.DoesNotExist:
                    pass

            if username:
                user = self._validate_username_email(username, '', password)

        # Did we get back an active user?
        if user:
            if not user.is_active:
                msg = _('User account is disabled.')
                raise exceptions.ValidationError(msg)
        else:
            msg = _('Unable to log in with provided credentials.')
            raise exceptions.ValidationError(msg)

        # If required, is the email verified?
        if 'rest_auth.registration' in settings.INSTALLED_APPS:
            from allauth.account import app_settings
            if app_settings.EMAIL_VERIFICATION == app_settings.EmailVerificationMethod.MANDATORY:
                email_address = user.emailaddress_set.get(email=user.email)
                if not email_address.verified:
                    raise serializers.ValidationError(_('E-mail is not verified.'))

        attrs['user'] = user
        return attrs


class CustomPasswordResetForm(PasswordResetForm):

    def send_mail(self, subject_template_name, email_template_name,
                  context, from_email, to_email, html_email_template_name=None):
        """
        Send a django.core.mail.EmailMultiAlternatives to `to_email`.
        """
        context['uid'] = context['uid'].decode()
        activate_url = '{protocol}://{domain}/#/welcome/password/change/{uid}/{token}'.format(**context)
        send_email_reset_password(to_email, activate_url, None)


class CustomPasswordResetSerializer(PasswordResetSerializer):
    password_reset_form_class = CustomPasswordResetForm


class ResendEmailConfirmationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, allow_blank=False)


class EthAddressSerializer(serializers.Serializer):
    address = serializers.CharField(required=True, allow_blank=False)

    def validate(self, attrs):
        address = attrs.get('address')

        if address:
            if not ethaddress_verify.is_valid_address(address):
                raise serializers.ValidationError(_('Ethereum address is not valid.'))
        else:
            raise serializers.ValidationError(_('Must include "address".'))

        attrs['address'] = address
        return attrs


class DocumentSerializer(serializers.Serializer):
    image = serializers.FileField(required=True)

    class Meta:
        model = Document
        fields = ('image',)

    def save(self, account):
        current_site = Site.objects.get_current()

        with transaction.atomic():
            document = Document.objects.create(user=account.user, **self.validated_data)
            account.document_url = "https://{}{}".format("saleapi.jibrel.network", document.image.url)
            account.document_type = get_document_filename_extension(document.image.name)
            account.save()
