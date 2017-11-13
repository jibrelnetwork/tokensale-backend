from rest_framework import serializers

from jco.api.models import Transaction, Address, Account


class AccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = Account
        exclude = ('id', 'user', 'created')


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ('address', 'type', )


class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('transaction_id', 'value', 'address', 'mined')