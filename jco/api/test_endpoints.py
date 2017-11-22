from datetime import datetime 

import pytest
from django.test import TestCase

from rest_framework.test import RequestsClient
from django.contrib.auth.models import User 
from allauth.account.models import EmailAddress 
from allauth.account.utils import setup_user_email 

from jco.api import models 
from jco.appdb import models as sa_models 


class ApiClient(RequestsClient):

    def __init__(self, *args, base_url='', **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = base_url

    def request(self, method, url, *args, **kwargs):
        return super().request(method, self.base_url + url, *args, **kwargs)

    def authenticate(self, username, password):
        resp = self.post('/auth/login/',
                         {'email': username, 'password': password})
        token = resp.json()['key']
        self.headers = {'Authorization': 'Token ' + token}



@pytest.fixture
def client(live_server):
    return ApiClient(base_url=live_server.url)


@pytest.fixture
def users():
    users = [
        User.objects.create_user('user1@main.com', 'user1@main.com', 'password1'),
        User.objects.create_user('user2@main.com', 'user2@main.com', 'password2'),
        User.objects.create_user('user3@main.com', 'user3@main.com', 'password3'),
    ]
    for user in users:
        EmailAddress.objects.create(user=user,
                            email=user.username,
                            primary=True,
                            verified=True)
    return users


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
    ]


def test_transactions_empty(client, users):
    client.authenticate('user1@main.com', 'password1')
    resp = client.get('/api/transactions/')
    assert resp.status_code == 200
    assert resp.json() == []


def test_transactions(client, users, addresses, transactions, jnt):
    models.Withdraw.objects.create(
        transaction_id='3000',
        value=30000,
        mined=datetime(2017, 11, 15),
        created=datetime(2017, 11, 15),
        block_height=200,
        status='success',
        address=addresses[0]
    )
    client.authenticate('user1@main.com', 'password1')
    resp = client.get('/api/transactions/')
    assert resp.status_code == 200
    assert len(resp.json()) == 3
    print("DDD", resp.json())
    assert resp.json() == [
        {'jnt': 30000,
         'type': 'outgoing',
         'date': '00:00 11/15/2017',
         'TXtype': 'ETH',
         'TXhash': '3000',
         'status': 'complete',
         'amount_usd': None,
         'amount_cryptocurrency': None},
        {'jnt': 10,
         'type': 'incoming',
         'date': '00:00 11/14/2017',
         'TXtype': 'ETH',
         'TXhash': '1000',
         'status': 'complete',
         'amount_usd': 1,
         'amount_cryptocurrency': 0.5},
        {'jnt': 20,
         'type': 'incoming',
         'date': '12:00 11/12/2017',
         'TXtype': 'BTC',
         'TXhash': '2000',
         'status': 'complete',
         'amount_usd': 2,
         'amount_cryptocurrency': 2.5},
    ]


def test_transactions_anon(client):
    resp = client.get('/api/transactions/')
    assert resp.status_code == 401


def test_get_account_empty(client, users):
    client.authenticate('user1@main.com', 'password1')
    resp = client.get('/api/account/')
    assert resp.status_code == 200
    assert resp.json() == {'country': '',
                           'date_of_birth': None,
                           'first_name': '',
                           'last_name': '',
                           'terms_confirmed': False,
                           'document_url': '',
                           'is_identity_verified': False,
                           'identity_verification_status': None,
                           'citizenship': '',
                           'residency': '',
                           'addresses': {},
                           'jnt_balance': 0}


def test_update_account(client, users, transactions):
    models.Jnt.objects.create(
        purchase_id='1',
        jnt_value=1.5,
        currency_to_usd_rate=1.0,
        usd_value=1.0,
        jnt_to_usd_rate=1.0,
        active=True,
        created=datetime.now(),
        transaction=transactions[0])
    client.authenticate('user1@main.com', 'password1')
    resp = client.put('/api/account/', {'first_name': 'John', 'terms_confirmed': True})
    assert resp.status_code == 200
    assert resp.json() == {'country': '',
                           'date_of_birth': None,
                           'first_name': 'John',
                           'last_name': '',
                           'terms_confirmed': True,
                           'document_url': '',
                           'is_identity_verified': False,
                           'identity_verification_status': None,
                           'citizenship': '',
                           'residency': '',
                           'addresses': {'BTC': 'aba', 'ETH': 'aaa'},
                           'jnt_balance': 1.5}


def test_get_raised_tokens_empty(client, users):
    resp = client.get('/api/raised-tokens/')
    assert resp.status_code == 200
    assert resp.json() == {'raised_tokens': 0}


def test_get_raised_tokens(client, transactions):
    models.Jnt.objects.create(
        purchase_id='1',
        jnt_value=1.5,
        currency_to_usd_rate=1.0,
        usd_value=1.0,
        jnt_to_usd_rate=1.0,
        active=True,
        created=datetime.now(),
        transaction=transactions[0])
    models.Jnt.objects.create(
        purchase_id='2',
        jnt_value=0.75,
        currency_to_usd_rate=1.0,
        usd_value=1.0,
        jnt_to_usd_rate=1.0,
        active=True,
        created=datetime.now(),
        transaction=transactions[1])
    resp = client.get('/api/raised-tokens/')
    assert resp.status_code == 200
    assert resp.json() == {'raised_tokens': 2.25}


def test_get_etherium_address_empty(client, users):
    client.authenticate('user1@main.com', 'password1')
    resp = client.get('/api/withdraw-address/')
    assert resp.status_code == 200
    assert resp.json() == {'address': None}


def test_get_etherium_address(client, users):
    models.Account.objects.create(etherium_address='aaaxxx', user=users[0])
    client.authenticate('user1@main.com', 'password1')
    resp = client.get('/api/withdraw-address/')
    assert resp.status_code == 200
    assert resp.json() == {'address': 'aaaxxx'}

    

