import logging

import requests

from jco import settings


GA_URL = "http://www.google-analytics.com/collect"
logger = logging.getLogger(__name__)


class GAClient:

    def __init__(self, ga_id, account):
        self.ga_id = ga_id
        self.account = account
        self.cid = account.tracking.get('ga_id')

    def send_status(self, status):
        """
        v=1&t=event&tid=UA-103798122-1&cid=1734424917.1494941541&ec=TokensRequest&ea=Status&el=Verified
        &cn=campaign&cs=source&cm=medium&ck=keyword&cc=content
        """
        data = {
            'v': '1',
            't': 'event',  #=event
            'tid': self.ga_id,  #=UA-103798122-1
            'cid': self.cid,  #=1734424917.1494941541
            'ec': 'TokensRequest',  #=TokensRequest
            'ea': 'Status',  #=Status
            'el': status,  #=Verified
        }
        logger.debug("Sending GA event data for user %s: %s", self.account.user.pk, data)
        self.send_data(data)

    def send_transaction(self, transaction_id, summ):
        """
        v=1&t=transaction&tid=UA-103798122-1&cid=1.2.894891330.1494586649&ti=12345
        &tr=14500.123&cu=USD&cn=campaign&cs=source&cm=medium&ck=keyword&cc=content
        """
        data = {
            'v': '1',  #=1
            't': 'transaction',  #=transaction
            'tid': self.ga_id,  #=UA-103798122-1
            'cid': self.cid,  #=1.2.894891330.1494586649
            'ti': transaction_id,  #=12345
            'tr': summ,  #=14500.123
            'cu': 'USD',  #=USD
        }
        logger.debug("Sending GA TX data for user %s: %s", self.account.user.pk, data)
        self.send_data(data)

    def send_item(self, transaction_id, quantity, item_price):
        """
        v=1&t=item&tid=UA-103798122-1&cid=1.2.894891330.1494586649&ti=12345
        &in=JibrelTokens&ip=14500.123&iq=1&1c=qweqeq&
        iv=phones&cn=campaign&cs=source&cm=medium&ck=keyword&cc=content
        """
        data = {
            'v': '1',  #=1
            't': 'item',  #=item
            'tid': self.ga_id,  #=UA-103798122-1
            'cid': self.cid,  #=1.2.894891330.1494586649
            'ti': transaction_id,  #=12345
            'in': 'JibrelTokens',  #=JibrelTokens
            'ip': item_price,  #=14500.123
            'iq': quantity,  #=1
            '1c': '1111',  #=qweqeq
            'iv': 'Tokens',  #=phones
        }
        logger.debug("Sending GA Item data for user %s: %s", self.account.user.pk, data)
        self.send_data(data)

    def send_tx_with_item(self, transaction_id, summ, quantity, item_price):
        self.send_transaction(transaction_id, summ)
        self.send_item(transaction_id, quantity, item_price)

    def make_utm_params(self, tracking_params):
        tp = tracking_params
        utm = {
            'cn': tp.get('utm_campaign', ''),  #=campaign
            'cs': tp.get('utm_source', ''),  #=source
            'cm': tp.get('utm_medium', ''),  #=medium
            'ck': tp.get('utm_keyword', ''),  #=keyword
            'cc': tp.get('utm_content', ''),  #=content
        }
        for k, v in list(utm.items()):
            if not v:
                del utm[k]
        return utm

    def send_data(self, data):
        if not self.cid:
            logger.warn("No GA client ID for user #%s", self.account.user.pk)
            return
        utm = self.make_utm_params(self.account.tracking)
        data.update(utm)
        requests.post(GA_URL, data)


def get_ga_client(account):
    client = GAClient(settings.GA_ID, account)
    return client


def on_status_new(account):
    get_ga_client(account).send_status('New')


def on_status_registration_complete(account):
    get_ga_client(account).send_status('RegistrationComplete')


def on_status_verified(account):
    get_ga_client(account).send_status('Verified')


def on_status_not_verified(account):
    get_ga_client(account).send_status('NotVerified')


def on_transaction_received(account, tx, jnt):
    get_ga_client(account).send_status('SuccessBuy')
    transaction_id = tx.transaction_id
    summ = jnt.usd_value
    quantity = jnt.jnt_value
    item_price = jnt.jnt_to_usd_rate
    get_ga_client(account).send_tx_with_item(transaction_id, summ, quantity, item_price)
