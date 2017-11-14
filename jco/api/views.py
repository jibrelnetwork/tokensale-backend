from rest_framework.views import APIView
from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework import authentication, permissions
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist


from jco.api.models import Transaction, Address, Account
from jco.api.serializers import TransactionSerializer, AddressSerializer, AccountSerializer


class TransactionsListView(APIView):
    """
    View to list all transactions  for user binded ETH and BTC addresses.

    * Requires token authentication.
    """

    authentication_classes = (authentication.TokenAuthentication,)

    def get(self, request):
        txs = Transaction.objects.filter(address__user=request.user)
        serializer = TransactionSerializer(txs, many=True)
        return Response(serializer.data)


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
            return Response(serializer.data)
        return Response(serializer.errors, status=400)