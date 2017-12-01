import unittest
import requests

BASE_URL = ''
USER_NAME = ''
USER_PASSWD = ''

class pnt:
    api_withdraw_address = '/api/withdraw-address/'
    api_transactions = '/api/transactions/'
    api_raised_tokens = '/api/raised-tokens/'
    api_account = '/api/account/'
    auth_user = '/auth/user/'
    auth_registration_confirm_email_resend = '/auth/registration/confirm-email-resend/'
    auth_password_change = '/auth/password/change/'
    auth_password_change = '/auth/password/change/'
    auth_logout = '/auth/logout/'
    auth_login = '/auth/login/'


class TestEndpoints(unittest.TestCase):
    def setUp(self):
        # Login
        r = requests.post(BASE_URL + pnt.auth_login,
                          json={'email': USER_NAME,'password': USER_PASSWD},
                          verify=False)
        r.raise_for_status()
        self.token = r.json()['key']

    def tearDown(self):
        #Logout
        r = requests.post(BASE_URL + pnt.auth_logout,
                          headers = {'Authorization': 'Token {}'.format(self.token)},
                          verify=False)
        r.raise_for_status()


    def test_auth(self):
        r = requests.post(BASE_URL + pnt.auth_password_change,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         json={'old_password': USER_PASSWD,
                               'new_password1': USER_PASSWD,
                               'new_password2': USER_PASSWD},
                         verify=False)
        r.raise_for_status()

        r = requests.post(BASE_URL + pnt.auth_registration_confirm_email_resend,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         json={'email': 'selikhovalexey@rambler.ru'},
                         verify=False)
        r.raise_for_status()

        r = requests.get(BASE_URL + pnt.auth_user,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         verify=False)
        r.raise_for_status()

        r = requests.put(BASE_URL + pnt.auth_user,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         json={'username': USER_NAME,
                               'first_name': '',
                               'last_name': ''},
                         verify=False)
        r.raise_for_status()

        r = requests.patch(BASE_URL + pnt.auth_user,
                           headers={'Authorization': 'Token {}'.format(self.token)},
                           json={'username': USER_NAME},
                           verify=False)
        r.raise_for_status()

        self.assertTrue(True)

    def test_api(self):
        r = requests.get(BASE_URL + pnt.api_account,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         verify=False)
        r.raise_for_status()

        r = requests.put(BASE_URL + pnt.api_account,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         json={'first_name': 'Test',
                               'last_name': 'Test',
                               'date_of_birth': '2017-11-30',
                               'country': '',
                               'citizenship': 'China',
                               'residency': 'China',
                               'terms_confirmed': True,
                               'document_url': 'https://sale.jibrel.network/static/logo.svg',
                               'document_type': 'svg'},
                         verify=False)
        r.raise_for_status()

        r = requests.get(BASE_URL + pnt.api_raised_tokens,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         verify=False)
        r.raise_for_status()

        r = requests.get(BASE_URL + pnt.api_transactions,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         verify=False)
        r.raise_for_status()

        r = requests.get(BASE_URL + pnt.api_withdraw_address,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         verify=False)
        r.raise_for_status()

        r = requests.put(BASE_URL + pnt.api_withdraw_address,
                         headers={'Authorization': 'Token {}'.format(self.token)},
                         json={'address': '0x810d38e1e3be077d40a8e351bd443d7ac94b5ac8'},
                         verify=False)
        r.raise_for_status()

        self.assertTrue(True)


if __name__ == '__main__':
    unittest.main()
