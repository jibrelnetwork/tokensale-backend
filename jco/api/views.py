from datetime import datetime
from itertools import chain
from operator import itemgetter

from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from rest_framework_extensions.cache.decorators import cache_response

from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from jco.api.models import Transaction, Address, Account, get_raised_tokens, Withdraw
from jco.api.serializers import (
    AccountSerializer,
    AddressSerializer,
    EthAddressSerializer,
    ResendEmailConfirmationSerializer,
    TransactionSerializer,
    WithdrawSerializer,
)
from jco.api import tasks
from jco.appprocessor import commands
from jco.commonutils import ga_integration


class TransactionsListView(APIView):
    """
    View to list all transactions  for user binded ETH and BTC addresses.

    * Requires token authentication.
    """

    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        txs_qs = Transaction.objects.filter(address__user=request.user)
        withdrawals_qs = Withdraw.objects.filter(address__user=request.user)

        txs = TransactionSerializer(txs_qs, many=True).data
        withdrawals = WithdrawSerializer(withdrawals_qs, many=True).data

        result_list = sorted(
            chain(txs, withdrawals),
            key=lambda t: t.pop('_date'),
            reverse=True)
        return Response(result_list)


class AccountView(GenericAPIView):
    """
    View get/set account (profile) info.

    * Requires token authentication.

    get:
    Returns account info for current user.

    put:
    Updates account info for current user.
    """

    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = AccountSerializer

    def ensure_account(self, request):
        try:
            account = request.user.account
        except ObjectDoesNotExist:
            account = Account.objects.create(user=request.user)
        return account

    def get(self, request):
        account = self.ensure_account(request)
        serializer = AccountSerializer(account)
        return Response(serializer.data)

    def put(self, request):
        account = self.ensure_account(request)
        serializer = AccountSerializer(account, data=request.data)
        if serializer.is_valid():
            serializer.save()
            self.maybe_start_identity_verification(account)
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def maybe_start_identity_verification(self, account):
        if account.document_url and not account.onfido_check_id:
            Address.assign_pair_to_user(account.user)
            ga_integration.on_status_registration_complete(account)
            tasks.verify_user.delay(account.user.pk)


class ResendEmailConfirmationView(GenericAPIView):
    """
    Re-send email confirmation email
    """

    permission_classes = (permissions.AllowAny,)
    serializer_class = ResendEmailConfirmationSerializer

    @cache_response(20)
    def post(self, request):
        serializer = ResendEmailConfirmationSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = User.objects.get(username=serializer.data['email'])
            except User.DoesNotExist:
                return Response({'email':  [_('No such user')]}, status=400)
            else:
                send_email_confirmation(request, user)
                return Response({'details': _('Verification e-mail re-sent.')})
        return Response(serializer.errors, status=400)


class RaisedTokensView(GenericAPIView):
    """
    Get raised JNT tokens amount
    """

    permission_classes = (permissions.AllowAny,)

    @cache_response(20)
    def get(self, request):
        data = {'raised_tokens': get_raised_tokens()}
        return Response(data)


class EthAddressView(GenericAPIView):
    """
    Get/set withdraw address for account
    """

    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = EthAddressSerializer

    def ensure_account(self, request):
        try:
            account = request.user.account
        except ObjectDoesNotExist:
            account = Account.objects.create(user=request.user)
        return account

    def get(self, request):
        account = self.ensure_account(request)
        data = {'address': account.withdraw_address}
        return Response(data)

    def put(self, request):
        account = self.ensure_account(request)
        serializer = EthAddressSerializer(data=request.data)
        if serializer.is_valid():
            account.withdraw_address = serializer.data['address']
            account.save()
            return Response(serializer.data)
        return Response({'address':  [_('Invalid Ethereum address')]}, status=400)


class WithdrawView(APIView):
    """
    Withdraw JNT tokens to user's eth address
    """
    def post(self, request):
        if datetime.now() < settings.WITHDRAW_AVAILABLE_SINCE:
            return Response({'detail': _('Withdraw will be available after {}'.format(settings.WITHDRAW_AVAILABLE_SINCE))},
                            status=403)

        if not request.user.account.withdraw_address:
            return Response({'detail': _('No Withdraw address in your account data.')},
                            status=400)
        result = commands.add_withdraw_jnt(request.user.pk)
        if result is True:
            return Response({'detail': _('JNT withdrawal is scheduled.')})
        return Response({'detail': _('JNT withdrawal is failed.')}, status=500)