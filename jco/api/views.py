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
from jco.api.models import (
    Transaction,
    Address,
    Account,
    get_raised_tokens,
    Withdraw,
    PresaleJnt,
    Operation,
    OperationError
)
from jco.api.serializers import (
    AccountSerializer,
    AddressSerializer,
    EthAddressSerializer,
    ResendEmailConfirmationSerializer,
    TransactionSerializer,
    WithdrawSerializer,
    PresaleJntSerializer,
    is_user_email_confirmed,
    OperationConfirmSerializer,
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
        txs_qs = Transaction.objects.filter(address__user=request.user).exclude(jnt=None)
        withdrawals_qs = Withdraw.objects.filter(address__user=request.user)
        presale_jnt_qs = PresaleJnt.objects.filter(user=request.user)

        txs = TransactionSerializer(txs_qs, many=True).data
        withdrawals = WithdrawSerializer(withdrawals_qs, many=True).data
        presale_jnt = PresaleJntSerializer(presale_jnt_qs, many=True).data

        result_list = sorted(
            chain(presale_jnt, txs, withdrawals),
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
            self.maybe_assign_addresses(account)
            return Response(serializer.data)
        return Response(serializer.errors, status=400)

    def maybe_start_identity_verification(self, account):
        if account.document_url and not account.onfido_check_id:
            ga_integration.on_status_registration_complete(account)
            tasks.verify_user.delay(account.user.pk)

    def maybe_assign_addresses(self, account):
        if (account.document_url and not account.onfido_check_id) or account.is_document_skipped:
            Address.assign_pair_to_user(account.user)


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
                return Response({'email': [_('No such user')]}, status=400)
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
        if is_user_email_confirmed(request.user) is False:
            resp = {'detail': _('You email address is not confirmed yet')}
            return Response(resp, status=403)

        serializer = EthAddressSerializer(data=request.data)
        if serializer.is_valid():
            operation = Operation.objects.create(
                operation=Operation.OP_CHANGE_ADDRESS,
                user=request.user,
                params=serializer.data
            )
            operation.request_confirmation()
            return Response(serializer.data)
        return Response({'address': [_('Invalid Ethereum address')]}, status=400)


class WithdrawRequestView(APIView):
    """
    Request JNT withdrawal link to send via email
    """
    def post(self, request):
        if datetime.now() < settings.WITHDRAW_AVAILABLE_SINCE:
            return Response({'detail': _('Withdraw will be available after {}'.format(settings.WITHDRAW_AVAILABLE_SINCE))},
                            status=403)

        if not request.user.account.withdraw_address:
            return Response({'detail': _('No Withdraw address in your account data.')},
                            status=400)

        if is_user_email_confirmed(request.user) is False:
            resp = {'detail': _('You email address is not confirmed yet')}
            return Response(resp, status=403)

        withdraw_id = commands.add_withdraw_jnt(request.user.pk)
        if not withdraw_id:
            resp = {'detail': _('Impossible withdrawal. Check you balance.')}
            return Response(resp, status=400)

        withdraw = Withdraw.objects.get(pk=withdraw_id)
        params = {
            'address': request.user.account.withdraw_address,
            'jnt_amount': withdraw.value,
            'withdraw_id': withdraw.pk,
        }
        operation = Operation.objects.create(
            operation=Operation.OP_WITHDRAW_JNT,
            user=request.user,
            params=params
        )
        operation.request_confirmation()
        return Response({'detail': _('JNT withdrawal is requested. Check you email for confirmation.')})


class WithdrawConfirmView(GenericAPIView):
    """
    Confirm JNT withdrawal
    """
    serializer_class = OperationConfirmSerializer

    def post(self, request):
        if datetime.now() < settings.WITHDRAW_AVAILABLE_SINCE:
            return Response({'detail': _('Withdraw will be available after {}'.format(settings.WITHDRAW_AVAILABLE_SINCE))},
                            status=403)

        if is_user_email_confirmed(request.user) is False:
            resp = {'detail': _('You email address is not confirmed yet')}
            return Response(resp, status=403)

        operation = Operation.objects.get(pk=request.POST['operation_id'])
        try:
            operation.perform(request.POST['token'])
        except OperationError:
            return Response({'detail': _('JNT withdrawal is failed.')}, status=500)
        # if not request.user.account.withdraw_address:
        #     return Response({'detail': _('No Withdraw address in your account data.')},
        #                     status=400)
        return Response({'detail': _('JNT withdrawal successfull.')})


class ChangeAddressConfirmView(GenericAPIView):
    """
    Confirm change withdraw address operation
    """

    serializer_class = OperationConfirmSerializer

    def post(self, request):
        operation = Operation.objects.get(pk=request.POST['operation_id'])
        try:
            operation.perform(request.POST['token'])
        except OperationError:
            return Response({'detail': _('Your withdrawal address changing is failed')}, 500)

        return Response({'detail': _('Your withdrawal address is changed')})
