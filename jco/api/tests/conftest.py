from datetime import datetime

import pytest

from django.contrib.auth.models import User
from allauth.account.models import EmailAddress

from jco.api import models
from jco.appdb import models as sa_models


@pytest.fixture
def users():
    users = [
        User.objects.create_user('user1@main.com', 'user1@main.com', 'password1'),
        User.objects.create_user('user2@main.com', 'user2@main.com', 'password2'),
        User.objects.create_user('user3@main.com', 'user3@main.com', 'password3'),
        User.objects.create_user('user4@main.com', 'user4@main.com', 'password4'),
        User.objects.create_user('user5@main.com', 'user5@main.com', 'password5'),
    ]
    for user in users:
        EmailAddress.objects.create(user=user,
                                    email=user.username,
                                    primary=True,
                                    verified=True)
    return users


@pytest.fixture
def accounts(users):
    _accounts = []
    for user in users:
        _accounts.append(models.Account.objects.create(user=user))
    return _accounts


@pytest.fixture
def addresses(users):
    return [
        models.Address.objects.create(address='aaa',
                                      type=sa_models.CurrencyType.eth,
                                      is_usable=True,
                                      user=users[0]),
        models.Address.objects.create(address='aab',
                                      type=sa_models.CurrencyType.eth,
                                      is_usable=True,
                                      user=users[1]),
        models.Address.objects.create(address='aac',
                                      type=sa_models.CurrencyType.eth,
                                      is_usable=True,
                                      user=None),

        models.Address.objects.create(address='aba',
                                      type=sa_models.CurrencyType.btc,
                                      is_usable=True,
                                      user=users[0]),
        models.Address.objects.create(address='abb',
                                      type=sa_models.CurrencyType.btc,
                                      is_usable=True,
                                      user=users[1]),
        models.Address.objects.create(address='abc',
                                      type=sa_models.CurrencyType.btc,
                                      is_usable=True,
                                      user=None),
    ]


@pytest.fixture
def transactions(addresses):
    return [
        models.Transaction.objects.create(transaction_id='1000',
                                          value=0.5,
                                          mined=datetime(2017, 11, 14),
                                          block_height=100,
                                          status='success',
                                          address=addresses[0]),
        models.Transaction.objects.create(transaction_id='2000',
                                          value=2.5,
                                          mined=datetime(2017, 11, 12, 12),
                                          block_height=200,
                                          status='success',
                                          address=addresses[3]),
        models.Transaction.objects.create(transaction_id='3000',
                                          value=2.5,
                                          mined=datetime(2017, 11, 13),
                                          block_height=300,
                                          status='success',
                                          address=addresses[2]),
        models.Transaction.objects.create(transaction_id='1500',
                                          value=0.5,
                                          mined=datetime(2017, 11, 13),
                                          block_height=110,
                                          status='pending',
                                          address=addresses[0]),
        models.Transaction.objects.create(transaction_id='999',
                                          value=0.5,
                                          mined=datetime(2017, 11, 13),
                                          block_height=111,
                                          status='success',
                                          address=addresses[0]),
    ]


@pytest.fixture
def jnt(transactions):
    return[
        models.Jnt.objects.create(
            purchase_id='1',
            jnt_value=10,
            currency_to_usd_rate=1.0,
            usd_value=1.0,
            jnt_to_usd_rate=1.0,
            active=True,
            created=datetime(2017, 10, 22, 10),
            transaction=transactions[0]),
        models.Jnt.objects.create(
            purchase_id='2',
            jnt_value=20,
            currency_to_usd_rate=1.0,
            usd_value=2.0,
            jnt_to_usd_rate=1.0,
            active=True,
            created=datetime(2017, 10, 22, 11),
            transaction=transactions[1]),
        models.Jnt.objects.create(
            purchase_id='3',
            jnt_value=30,
            currency_to_usd_rate=1.0,
            usd_value=3.0,
            jnt_to_usd_rate=1.0,
            active=True,
            created=datetime(2017, 10, 22, 12),
            transaction=transactions[2]),
        models.Jnt.objects.create(
            purchase_id='4',
            jnt_value=30,
            currency_to_usd_rate=1.0,
            usd_value=3.0,
            jnt_to_usd_rate=1.0,
            active=True,
            created=datetime(2017, 10, 22, 12),
            transaction=transactions[3]),
    ]
