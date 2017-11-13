from datetime import datetime 

import pytest
from django.test import TestCase

from rest_framework.test import RequestsClient
from django.contrib.auth.models import User 

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
                         {'username': username, 'password': password})
        token = resp.json()['key']
        self.headers = {'Authorization': 'Token ' + token}



@pytest.fixture
def client(live_server):
    return ApiClient(base_url=live_server.url)


@pytest.fixture
def users():
    return [
        User.objects.create_user('user1', 'user1@main.com', 'password1'),
        User.objects.create_user('user2', 'user2@main.com', 'password2'),
        User.objects.create_user('user3', 'user3@main.com', 'password3'),
    ]


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
                                        mined=datetime(2017, 11, 11, 12),
                                        block_height=100,
                                        address=addresses[0]),
        models.Transaction.objects.create(transaction_id='2000',
                                        value=2.5,
                                        mined=datetime(2017, 11, 12),
                                        block_height=200,
                                        address=addresses[3]),
    ]


def test_transactions_empty(client, users):
    client.authenticate('user1', 'password1')
    resp = client.get('/api/transactions/')
    assert resp.status_code == 200
    assert resp.json() == []


def test_transactions(client, users, addresses, transactions):
    client.authenticate('user1', 'password1')
    resp = client.get('/api/transactions/')
    assert resp.status_code == 200
    assert len(resp.json()) == 2
    assert resp.json() == [
        {'transaction_id': '2000',
         'value': 2.5,
         'mined': '2017-11-12T00:00:00Z',
         'address': addresses[3].id},
        {'transaction_id': '1000',
         'value': 0.5,
         'mined': '2017-11-11T12:00:00Z',
         'address': addresses[0].id},
    ]


def test_transactions_anon(client):
    resp = client.get('/api/transactions/')
    assert resp.status_code == 401


def test_get_account_empty(client, users):
    client.authenticate('user1', 'password1')
    resp = client.get('/api/account/')
    assert resp.status_code == 200
    assert resp.json() == {'citizenship': '',
                           'country': '',
                           'date_of_birth': None,
                           'docs_received': False,
                           'email': '',
                           'first_name': '',
                           'fullname': '',
                           'last_name': '',
                           'notified': False,
                           'residency': '',
                           'terms_confirmed': False}


def test_update_account_empty(client, users):
    client.authenticate('user1', 'password1')
    resp = client.put('/api/account/', {'first_name': 'John', 'terms_confirmed': True})
    assert resp.status_code == 200
    assert resp.json() == {'citizenship': '',
                           'country': '',
                           'date_of_birth': None,
                           'docs_received': False,
                           'email': '',
                           'first_name': 'John',
                           'fullname': '',
                           'last_name': '',
                           'notified': False,
                           'residency': '',
                           'terms_confirmed': True}

    

