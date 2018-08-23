from datetime import datetime
from itertools import chain
from operator import itemgetter
import logging

from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from django.contrib.auth.models import User
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from rest_framework_extensions.cache.decorators import cache_response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from django.db import transaction

from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from jco.api.models import (
    Transaction,
    Address,
    Account,
    get_raised_tokens,
    Withdraw,
    PresaleToken,
    Operation,
    OperationError,
    get_ico_current_state,
    get_ico_next_state,
)
from jco.api.serializers import (
    AccountSerializer,
    AddressSerializer,
    EthAddressSerializer,
    ResendEmailConfirmationSerializer,
    TransactionSerializer,
    WithdrawSerializer,
    PresaleTokenSerializer,
    DocumentSerializer,
    is_user_email_confirmed,
    OperationConfirmSerializer,
)
from jco.api import tasks
from jco.appprocessor import commands
from jco.commonutils import ga_integration


logger = logging.getLogger(__name__)


class TransactionsListView(APIView):
    """
    View to list all transactions  for user binded ETH and BTC addresses.

    * Requires token authentication.
    """

    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        txs_qs = Transaction.objects.filter(address__user=request.user).exclude(token=None)
        withdrawals_qs = Withdraw.objects.filter(user=request.user)
        presale_token_qs = PresaleToken.objects.filter(user=request.user)

        txs = TransactionSerializer(txs_qs, many=True).data
        withdrawals = WithdrawSerializer(withdrawals_qs, many=True).data
        presale_token = PresaleTokenSerializer(presale_token_qs, many=True).data

        result_list = sorted(
            chain(presale_token, txs, withdrawals),
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
    Get raised TOKEN tokens amount
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
        logger.info('Request address change for %s', request.user.username)
        if is_user_email_confirmed(request.user) is False:
            resp = {'detail': _('Please confirm the e-mail before submitting the Ethereum address')}
            logger.info('email address is not confirmed for %s, aborting', request.user.username)
            return Response(resp, status=403)

        serializer = EthAddressSerializer(data=request.data)
        if serializer.is_valid():
            try:
                operation = Operation.create_operation(
                    operation=Operation.OP_CHANGE_ADDRESS,
                    user=request.user,
                    params=serializer.data
                )
            except Exception:
                logger.exception('Address change failed for %s', request.user.username)
                return Response({'detail': _('Unexpected error, please try again')}, status=500)

            logger.info('Address change for %s: operation #%s created',
                        request.user.username, operation.pk)
            return Response(serializer.data)
        logger.info('Invalid Ethereum address %s for %s',
                    serializer.data.get('address'), request.user.username)
        return Response({'address': [_('Invalid Ethereum address')]}, status=400)


class WithdrawRequestView(APIView):
    """
    Request TOKEN withdrawal link to send via email
    """
    def post(self, request):
        logger.info('Request TOKEN withdraw for %s', request.user.username)
        if datetime.now() < settings.WITHDRAW_AVAILABLE_SINCE:
            logger.info('Request TOKEN withdraw for %s rejected: date', request.user.username)
            return Response({'detail': _('Withdraw will be available after {}'.format(settings.WITHDRAW_AVAILABLE_SINCE))},
                            status=403)

        if not request.user.account.withdraw_address:
            logger.info('Request TOKEN withdraw for %s rejected: no address', request.user.username)
            return Response({'detail': _('No Withdraw address in your account data.')},
                            status=400)

        if request.user.account.is_identity_verified is False:
            logger.info('Request TOKEN withdraw for %s rejected: KYC not verified', request.user.username)
            resp = {'detail': _('Please confirm your identity to withdraw TOKEN')}
            return Response(resp, status=403)

        if is_user_email_confirmed(request.user) is False:
            logger.info('Request TOKEN withdraw for %s rejected: email not confirmed', request.user.username)
            resp = {'detail': _('Your email address is not confirmed yet')}
            return Response(resp, status=403)

        withdraw_id = commands.add_withdraw_token(request.user.pk)
        if not withdraw_id:
            logger.info('Request TOKEN withdraw for %s rejected: balance or error', request.user.username)
            resp = {'detail': _('Impossible withdrawal. Check you balance.')}
            return Response(resp, status=400)

        logger.info('TOKEN Withdraw created: #%s for %s', withdraw_id, request.user.username)
        withdraw = Withdraw.objects.get(pk=withdraw_id)

        try:
            params = {
                'address': request.user.account.withdraw_address,
                'token_amount': withdraw.value,
                'withdraw_id': withdraw.pk,
            }
            operation = Operation.create_operation(
                operation=Operation.OP_WITHDRAW_TOKEN,
                user=request.user,
                params=params
            )
        except Exception:
            logger.exception('Withdraw request failed for %s', request.user.username)
            return Response({'detail': _('Unexpected error, please try again')}, status=500)

        logger.info('TOKEN withdrawal for %s: operation #%s created',
                    request.user.username, operation.pk)
        return Response({'detail': _('TOKEN withdrawal is requested. Check you email for confirmation.')})


class WithdrawConfirmView(GenericAPIView):
    """
    Confirm TOKEN withdrawal
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = OperationConfirmSerializer

    def post(self, request):
        logger.info('Start TOKEN withdraw confirmation')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            operation = Operation.objects.get(pk=serializer.data['operation_id'])
        except Exception:
            logger.exception('TOKEN withdraw confirmation for %s rejected: operation %s does not exist',
                         serializer.data['token'], serializer.data['operation_id'])
            return Response({'detail': _('TOKEN withdrawal is failed.')}, status=403)

        logger.info('TOKEN withdraw confirmation for %s', operation.user.username)
        if datetime.now() < settings.WITHDRAW_AVAILABLE_SINCE:
            logger.info('TOKEN withdraw confirmation for %s rejected: date', operation.user.username)
            return Response({'detail': _('Withdraw will be available after {}'.format(settings.WITHDRAW_AVAILABLE_SINCE))},
                            status=403)

        if is_user_email_confirmed(operation.user) is False:
            logger.info('TOKEN withdraw confirmation for %s rejected: email not confirmed', operation.user.username)
            resp = {'detail': _('You email address is not confirmed yet')}
            return Response(resp, status=403)

        if operation.user.account.is_identity_verified is False:
            logger.info('Request TOKEN withdraw for %s rejected: KYC not verified', operation.user.username)
            resp = {'detail': _('Please confirm your identity to withdraw TOKEN')}
            return Response(resp, status=403)

        try:
            logger.info('TOKEN withdraw confirmation for %s: performing operation #%s',
                        operation.user.username, operation.pk)
            operation.perform(serializer.data['token'])
            logger.info('TOKEN withdraw confirmation for %s: successfull operation #%s',
                        operation.user.username, operation.pk)
        except Exception:
            logger.exception('TOKEN withdraw confirmation for %s: failed operation #%s',
                        operation.user.username, operation.pk)
            return Response({'detail': _('TOKEN withdrawal is failed.')}, status=500)
        return Response({'detail': _('TOKEN withdrawal successfull.')})


class ChangeAddressConfirmView(GenericAPIView):
    """
    Confirm change withdraw address operation
    """
    permission_classes = (permissions.AllowAny,)
    serializer_class = OperationConfirmSerializer

    def post(self, request):
        logger.info('Start change address confirmation')

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            operation = Operation.objects.get(pk=serializer.data['operation_id'])
        except Exception:
            logger.exception('change address confirmation for %s rejected: operation %s does not exist',
                         serializer.data['token'], serializer.data['operation_id'])
            return Response({'detail': _('Your withdrawal address changing is failed')}, status=403)

        if is_user_email_confirmed(operation.user) is False:
            resp = {'detail': _('Please confirm the e-mail before submitting new address')}
            return Response(resp, status=403)

        try:
            operation.perform(serializer.data['token'])
        except Exception:
            logger.exception('Address change operation failure for %s', operation.user.username)
            return Response({'detail': _('Your withdrawal address changing is failed')}, 500)

        return Response({'detail': _('Your withdrawal address is changed')})


class DocumentView(APIView):
    """
    View set document.
    * Requires token authentication.
        
    post:
    Creates a document for current user.
    """

    authentication_classes = (authentication.TokenAuthentication,)
    serializer_class = DocumentSerializer
    parser_classes = (JSONParser, FormParser, MultiPartParser,)

    def post(self, request, *args, **kwargs):
        try:
            account = request.user.account
        except ObjectDoesNotExist:
            return Response({'success': False, 'error': [_('No such account')]}, status=400)

        serializer = DocumentSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(account)
            return Response({'success': True}, 201)
        return Response({'success': False, 'error': [_('An upload has failed')]}, status=400)


class ICOStausView(APIView):
    permission_classes = (permissions.AllowAny,)

    def get(self, request):
        current_state = get_ico_current_state()
        next_state = get_ico_next_state()
        status = {
            "currentState": current_state.id,
            "nextState": next_state.id,
            "currentStateEndsAt": current_state.isoformat(),
            "nextStateStartsAt": next_state.isoformat(),
            "tokenRaised": get_raised_tokens(),
            "tokenTotal": settings.TOKENS__TOTAL_SUPPLY,
            "tokenInitial": "number",
            "pricePerToken": 0.25,
        }
        return Response(status)