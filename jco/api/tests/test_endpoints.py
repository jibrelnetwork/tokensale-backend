from datetime import datetime

import pytest
from django.test import TestCase

from rest_framework.test import RequestsClient
from django.contrib.auth.models import User
from allauth.account.models import EmailAddress
from allauth.account.utils import setup_user_email

from jco.api import models
from jco.appdb import models as sa_models
from jco.appdb.db import session as sa_session


def teardown_module(module):
    sa_session.close()
    sa_session.get_bind().dispose()


class ApiClient(RequestsClient):

    def __init__(self, *args, base_url='', **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = base_url

    def request(self, method, url, *args, **kwargs):
        resp = super().request(method, self.base_url + url, *args, **kwargs)
        print('RESPONSE', resp.content)
        return resp

    def authenticate(self, username, password):
        resp = self.post('/auth/login/',
                         {'email': username, 'password': password})
        token = resp.json()['key']
        self.headers = {'Authorization': 'Token ' + token}



@pytest.fixture
def client(live_server):
    return ApiClient(base_url=live_server.url)


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
    assert len(resp.json()) == 4
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
        {'jnt': 30,
         'type': 'incoming',
         'date': '00:00 11/13/2017',
         'TXtype': 'ETH',
         'TXhash': '1500',
         'status': 'waiting',
         'amount_usd': 3,
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
                           'username': 'user1@main.com',
                           'first_name': '',
                           'last_name': '',
                           'terms_confirmed': False,
                           'document_url': '',
                           'document_type': '',
                           'is_identity_verified': False,
                           'identity_verification_status': None,
                           'is_document_skipped': False,
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
                           'username': 'user1@main.com',
                           'first_name': 'John',
                           'last_name': '',
                           'terms_confirmed': True,
                           'document_url': '',
                           'document_type': '',
                           'is_identity_verified': False,
                           'identity_verification_status': None,
                           'is_document_skipped': False,
                           'citizenship': '',
                           'residency': '',
                           'addresses': {'BTC': 'aba', 'ETH': 'aaa'},
                           'jnt_balance': 1.5}


def test_get_raised_tokens_empty(client, users, settings):
    resp = client.get('/api/raised-tokens/')
    assert resp.status_code == 200
    assert resp.json() == {'raised_tokens': settings.RAISED_TOKENS_SHIFT + 0}


def test_get_raised_tokens(client, transactions, settings):
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
    assert resp.json() == {'raised_tokens': settings.RAISED_TOKENS_SHIFT + 2.25}


def test_get_withdraw_address_empty(client, users):
    client.authenticate('user1@main.com', 'password1')
    resp = client.get('/api/withdraw-address/')
    assert resp.status_code == 200
    assert resp.json() == {'address': None}


def test_get_withdraw_address(client, users):
    models.Account.objects.create(withdraw_address='aaaxxx', user=users[0])
    client.authenticate('user1@main.com', 'password1')
    resp = client.get('/api/withdraw-address/')
    assert resp.status_code == 200
    assert resp.json() == {'address': 'aaaxxx'}


def test_put_withdraw_address_empty(client, users):
    client.authenticate('user1@main.com', 'password1')
    resp = client.get('/api/withdraw-address/')
    assert resp.status_code == 200
    assert resp.json() == {'address': None}
    resp = client.put('/api/withdraw-address/', {})
    assert resp.status_code == 400
    resp = client.put('/api/withdraw-address/', {'address': None})
    assert resp.status_code == 400


def test_put_withdraw_address_validate(client, users):
    client.authenticate('user1@main.com', 'password1')
    resp = client.get('/api/withdraw-address/')
    assert resp.status_code == 200
    assert resp.json() == {'address': None}
    resp = client.put('/api/withdraw-address/', {'address': ''})
    assert resp.status_code == 400
    resp = client.put('/api/withdraw-address/', {'address': '1HEVUxtxGjGnuRT5NsamD6V4RdUduRHqFv'})
    assert resp.status_code == 400
    resp = client.put('/api/withdraw-address/', {'address': '3BA2E2565dB2c018aDd0b24483fE99fC2cCCDa8e'})
    assert resp.status_code == 400
    resp = client.put('/api/withdraw-address/', {'address': '0x3BA2E2565dB2c018aDd0b24483fE99fC2cCCDa8'})
    assert resp.status_code == 400
    resp = client.put('/api/withdraw-address/', {'address': '0x3dA2E2565dB2c018aDd0b24483fE99fC2cCCDa8e'})
    assert resp.status_code == 400
    resp = client.put('/api/withdraw-address/', {'address': '0x3BA2E2565dB2c018aDd0b24483fE99fC2cCCDa8e'})
    assert resp.status_code == 200
    assert resp.json() == {'address': '0x3BA2E2565dB2c018aDd0b24483fE99fC2cCCDa8e'}
    resp = client.put('/api/withdraw-address/', {'address': '0xde709f2102306220921060314715629080e2fb77'})
    assert resp.status_code == 200
    assert resp.json() == {'address': '0xde709f2102306220921060314715629080e2fb77'}


def test_withdraw_jnt(client, users, addresses, jnt, settings):
    settings.WITHDRAW_AVAILABLE_SINCE = datetime.now()
    client.authenticate('user1@main.com', 'password1')
    models.Account.objects.create(withdraw_address='aaaxxx', user=users[0])
    resp = client.post('/api/withdraw-jnt/')
    assert resp.status_code == 200
    assert resp.json() == {'detail': 'JNT withdrawal is scheduled.'}

    withdrawals = models.Withdraw.objects.filter(to='aaaxxx').all()
    assert len(withdrawals) == 1
    assert withdrawals[0].value == 60


def test_registration(client):
    user_data = {
        'email': 'aa@aa.aa',
        'password': '123qwerty',
        'password_confirm': '123qwerty',
        'captcha': 'zxc',
        'tracking': {'ga_id': '123.456.7890', 'utm_campaign': 'Cmp1', 'utm_source': 'src'},
    }
    resp = client.post('/auth/registration/', json=user_data)
    assert resp.status_code == 201
    account = models.Account.objects.get(user__username=user_data['email'])
    assert account.tracking == user_data['tracking']


def test_registration_emplty_tracking(client):
    user_data = {
        'email': 'aa@aa.aa',
        'password': '123qwerty',
        'password_confirm': '123qwerty',
        'captcha': 'zxc',
        # 'tracking': {'ga_id': '123.456.7890', 'utm_campaign': 'Cmp1', 'utm_source': 'src'},
    }
    resp = client.post('/auth/registration/', json=user_data)
    assert resp.status_code == 201
    account = models.Account.objects.get(user__username=user_data['email'])
    assert account.tracking == {}
