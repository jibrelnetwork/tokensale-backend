import sys
import traceback
import string
import time
import random
from datetime import datetime
from typing import Tuple, Optional, List
import requests
import logging

from sqlalchemy.sql.expression import and_, or_
from sqlalchemy.types import Integer as sa_Integer

from jco.appdb.db import session
from jco.appdb.models import *
from jco.commonutils.formats import format_coin_value


def get_affiliate(_account: Account) -> Optional[Tuple[str, str]]:
    clicksureclickid = _account.get_affiliate_clicksureclickid()
    track_id = _account.get_affiliate_track_id()
    actionpay = _account.get_affiliate_actionpay()
    adpump = _account.get_affiliate_adpump()

    if clicksureclickid:
        return (clicksureclickid, AffiliateNetwork.clicksure)
    elif track_id:
        return (track_id, AffiliateNetwork.runcpa)
    elif actionpay:
        return (actionpay, AffiliateNetwork.actionpay)
    elif adpump:
        return (adpump, AffiliateNetwork.adpump)

    return None


def get_affiliate_url(_account: Account, _event: str, _transaction: Optional[Transaction] = None) -> str:
    affiliate_id, affiliate_network = get_affiliate(_account)

    if affiliate_network == AffiliateNetwork.clicksure:
        if _event == AffiliateEvent.registration:
            _transaction_id = '0x' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            return "https://451418.cpa.clicksure.com/postback?transactionRef={}&clickID={}" \
                .format(_transaction_id, affiliate_id)
        elif _event == AffiliateEvent.transaction and _transaction:
            _transaction_id = _transaction.transaction_id
            return "https://454048.cpa.clicksure.com/postback?transactionRef={}&clickID={}" \
                .format(_transaction_id, affiliate_id)

    elif affiliate_network == AffiliateNetwork.runcpa:
        if _event == AffiliateEvent.registration:
            return "http://runcpa.com/callbacks/event/s2s-partner/QGcal1rP6kwTYWRtxU_EXiyUQ7sYwCPz/cpl200008/{}" \
                .format(affiliate_id)
        elif _event == AffiliateEvent.transaction and _transaction:
            return "http://runcpa.com/callbacks/events/revenue-partner/QGcal1rP6kwTYWRtxU_EXiyUQ7sYwCPz/rs174937/{}/{}" \
                .format(affiliate_id, format_coin_value(_transaction.value))

    elif affiliate_network == AffiliateNetwork.actionpay:
        if _event == AffiliateEvent.registration:
            _transaction_id = '0x' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
            return "https://x.actionpay.ru/ok/16241.png?actionpay={}&apid={}&price=0.006" \
                .format(affiliate_id, _transaction_id)
        elif _event == AffiliateEvent.transaction and _transaction:
            _transaction_id = _transaction.transaction_id
            return "https://x.actionpay.ru/ok/16242.png?actionpay={}&apid={}&price={}" \
                .format(affiliate_id, _transaction_id, format_coin_value(_transaction.value))

    elif affiliate_network == AffiliateNetwork.adpump:
        _url = "https://apypx.com/ok/{aim_ID}.png?adpump={adpump_cookie}&apid={ap_id}&price={price}"

        if _event == AffiliateEvent.registration:
            return _url.format(aim_ID="16347",
                               adpump_cookie=affiliate_id,
                               ap_id=''.join(random.choices(string.ascii_lowercase + string.digits, k=12)),
                               price=0)
        elif _event == AffiliateEvent.transaction:
            return _url.format(aim_ID="16348",
                               adpump_cookie=affiliate_id,
                               ap_id=_transaction.transaction_id,
                               price=format_coin_value(_transaction.value))

    return ""


def check_new_events():
    check_new_registartions()
    check_new_transactions()


def check_new_registartions():
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start to check new affiliates registrations")

        _event = AffiliateEvent.registration

        accounts = session.query(Account) \
            .outerjoin(Affiliate, and_(Account.user_id == Affiliate.user_id,
                                       Affiliate.event == _event)) \
            .filter(or_(Account.tracking.has_key(Account.tracking_key_affiliate_track_id),
                        Account.tracking.has_key(Account.tracking_key_affiliate_clicksureclickid),
                        Account.tracking.has_key(Account.tracking_key_affiliate_adpump),
                        Account.tracking.has_key(Account.tracking_key_affiliate_actionpay))) \
            .filter(Account.is_identity_verified == True) \
            .filter(Affiliate.id.is_(None)) \
            .all()  # type: List[Account]

        for account in accounts:
            try:
                affiliate = Affiliate(user_id=account.user_id,
                                      event=_event,
                                      url=get_affiliate_url(account, _event))
                session.add(affiliate)
                session.commit()
            except Exception:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error("Failed to save affiliate for user_id: {} due to exception:\n{}"
                        .format(account.user_id, exception_str))

                session.rollback()

        logging.getLogger(__name__).info("Finished to check new affiliates registrations")
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to check new affiliates registrations due to exception:\n{}"
                                          .format(exception_str))
        session.rollback()


def check_new_transactions():
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start to check new affiliates transactions")

        _event = AffiliateEvent.transaction

        records = session.query(Transaction, Account) \
            .outerjoin(Address, Address.id == Transaction.address_id) \
            .outerjoin(Account, Account.user_id == Address.user_id) \
            .outerjoin(Affiliate, and_(Affiliate.user_id == Account.user_id,
                                       Affiliate.event == _event,
                                       Affiliate.meta.has_key(Affiliate.meta_key_transaction_id),
                                       Affiliate.meta[Affiliate.meta_key_transaction_id] \
                                            .astext.cast(sa_Integer) == Transaction.id)) \
            .filter(or_(Account.tracking.has_key(Account.tracking_key_affiliate_track_id),
                        Account.tracking.has_key(Account.tracking_key_affiliate_clicksureclickid),
                        Account.tracking.has_key(Account.tracking_key_affiliate_adpump),
                        Account.tracking.has_key(Account.tracking_key_affiliate_actionpay))) \
            .filter(Affiliate.id.is_(None)) \
            .all()  # type: List[Tuple[Transaction, Account]]

        for transaction, account in records:
            try:
                affiliate = Affiliate(user_id=account.user_id,
                                      event=_event,
                                      url=get_affiliate_url(account, _event, transaction),
                                      meta={Affiliate.meta_key_transaction_id: transaction.id})
                session.add(affiliate)
                session.commit()
            except Exception:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error("Failed to save affiliate for transaction_id: {} due to exception:\n{}"
                        .format(transaction.id, exception_str))

                session.rollback()

        logging.getLogger(__name__).info("Finished to check new affiliates transactions")
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to check new affiliates transactions due to exception:\n{}"
                                          .format(exception_str))
        session.rollback()


def scan_affiliates():
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start to scan affiliates")

        affiliates = session.query(Affiliate) \
            .filter(Affiliate.sended.is_(None)) \
            .all()

        for affiliate in affiliates:
            try:
                r = requests.get(affiliate.url)
                r.raise_for_status()
                affiliate.sended = datetime.utcnow()
                affiliate.status = AffiliateStatus.success
            except Exception:
                affiliate.status = r.status_code

            try:
                session.commit()
            except Exception:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error("Failed to update affiliate with id: {} due to exception:\n{}"
                        .format(affiliate.id, exception_str))

                session.rollback()

        logging.getLogger(__name__).info("Finished to scan affiliates")

    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to scan affiliates due to exception:\n{}"
                                          .format(exception_str))
        session.rollback()
