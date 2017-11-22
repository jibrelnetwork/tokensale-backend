import logging 

from django.db.models import Sum
from django.conf import settings
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import ugettext_lazy as _
from allauth.account import app_settings as allauth_settings
from allauth.utils import email_address_exists
from allauth.account.adapter import get_adapter
from allauth.account.utils import setup_user_email
from rest_framework import serializers, exceptions
import requests

from jco.api.models import Transaction, Address, Account, Jnt
from jco.commonutils import person_verify


logger = logging.getLogger(__name__)

RECAPTCA_API_URL = 'https://www.google.com/recaptcha/api/siteverify'


class AccountSerializer(serializers.ModelSerializer):
    jnt_balance = serializers.SerializerMethodField()
    identity_verification_status = serializers.SerializerMethodField()
    addresses = serializers.SerializerMethodField()
    
    class Meta:
        model = Account
        fields = ('first_name', 'last_name',  'date_of_birth', 'country',
                  'citizenship', 'residency', 'terms_confirmed', 'document_url',
                  'is_identity_verified', 'jnt_balance', 'identity_verification_status',
                  'addresses')
        read_only_fields = ('is_identity_verified', 'jnt_balance')

    def get_jnt_balance(self, obj):
        return (Jnt.objects.filter(transaction__address__user=obj.user)
                .aggregate(Sum('jnt_value')))['jnt_value__sum'] or 0

    def get_identity_verification_status(self, obj):
        if obj.is_identity_verified is True:
            return 'Approved'
        if obj.onfido_check_status == person_verify.STATUS_IN_PROGRESS:
            return 'Pending'
        if obj.onfido_check_status == person_verify.STATUS_COMPLETE and obj.onfido_check_result == person_verify.RESULT_CONSIDER:
            return 'Declined'

    def get_addresses(self, obj):
        addresses = Address.objects.filter(user=obj.user).all()
        return {a.type: a.address for a in addresses}


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('address', 'type', )


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('transaction_id', 'value', 'address', 'mined')


class RegisterSerializer(serializers.Serializer):

    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True, write_only=True)
    password_confirm = serializers.CharField(required=True, write_only=True)
    captcha = serializers.CharField(required=True, write_only=True)

    def validate_username(self, username):
        username = get_adapter().clean_username(username)
        return username

    def validate_email(self, email):
        email = get_adapter().clean_email(email)
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


class ResendEmailConfirmationSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True, allow_blank=False)