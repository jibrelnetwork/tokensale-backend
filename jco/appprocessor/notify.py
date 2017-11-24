#!/usr/bin/env python

import os
import logging
import requests
import time
import sys
import traceback
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Tuple
from email.utils import formatdate
from jinja2 import FileSystemLoader, Environment
import django
django.setup()

# from jco.commonconfig.config import MAILGUN__API_MESSAGES_URL, MAILGUN__API_EVENTS_URL, MAILGUN__API_KEY
# from jco.commonconfig.config import EMAIL_NOTIFICATIONS__ENABLED, EMAIL_NOTIFICATIONS__SENDER
# from jco.commonconfig.config import EMAIL_NOTIFICATIONS__BACKUP_ENABLED
# from jco.commonconfig.config import EMAIL_NOTIFICATIONS__BACKUP_SENDER, EMAIL_NOTIFICATIONS__BACKUP_ADDRESS
# from jco.commonconfig.config import FORCE_SCANNING_ADDRESS__ENABLED, FORCE_SCANNING_ADDRESS__EMAIL_RECIPIENT
# from jco.commonconfig.config import CHECK_MAIL_DELIVERY__DAYS_DEPTH
# from jco.commonconfig.config import INVESTMENTS__USD__MIN_LIMIT, INVESTMENTS__USD__MAX_LIMIT
# from jco.commonconfig.config import INVESTMENTS__PUBLIC_SALE__START_DATE, INVESTMENTS__PUBLIC_SALE__END_DATE
from jco.commonconfig import config
from jco.appdb.models import *
from jco.appdb.db import session
from jco.api import models as api_models
from jco.commonutils.utils import *


EMAIL_NOTIFICATIONS__TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')


def _format_jnt_value(value: float) -> str:
    return "{0:.0f}".format(int(value))


def _format_jnt_value_subject(value: float) -> str:
    return "{0:.0f}".format(int(value))


def _format_fiat_value(value: float) -> str:
    return "{0:.2f}".format(value)


def _format_coin_value(value: float) -> str:
    return "{0:.2f}".format(value)


def _format_conversion_rate(value: float) -> str:
    return "{0:.2f}".format(value)


def _format_date_period(start_date: datetime, end_date: datetime) -> str:
    return '{0:%d %b %Y} - {1:%d %b %Y}'.format(start_date, end_date)


def _format_email_files(*,
                        attachments: List[Tuple[str, Path]] = (),
                        attachments_inline: List[Tuple[str, Path]] = ()) -> List:
    # read attachments
    attachments_data = []  # type: List[Tuple[str, bytes]]
    for attachment_name, attachment_path in attachments:
        attachment_bytes = attachment_path.read_bytes()
        attachments_data.append((attachment_name, attachment_bytes))

    attachments_inline_data = []  # type: List[Tuple[str, bytes]]
    for attachment_name, attachment_path in attachments_inline:
        attachment_bytes = attachment_path.read_bytes()
        attachments_inline_data.append((attachment_name, attachment_bytes))

    # format files
    files = []
    for attachment_name, attachment_bytes in attachments_data:
        files.append(("attachment", (attachment_name, attachment_bytes)))
    for attachment_name, attachment_bytes in attachments_inline_data:
        files.append(("inline", (attachment_name, attachment_bytes)))

    return files


def get_failed_mails() -> List[str]:
    try:
        begin_dt = datetime.utcnow()
        end_dt = begin_dt - timedelta(days=config.CHECK_MAIL_DELIVERY__DAYS_DEPTH)

        response = requests.get(
            config.MAILGUN__API_EVENTS_URL,
            auth=("api", config.MAILGUN__API_KEY),
            params={"begin": formatdate(time.mktime(begin_dt.timetuple())),
                    "end": formatdate(time.mktime(end_dt.timetuple())),
                    "event": "failed",
                    "severity": "permanent"})

        response.raise_for_status()

        mail_list = []

        failed_mails_json = response.json()
        items = failed_mails_json.get("items")

        while len(items) > 0 and \
                failed_mails_json["paging"].get("next"):

            for item in items:
                if item.get("message"):
                    mail_list.append(item["message"]["headers"]["message-id"])

            response = requests.get(failed_mails_json["paging"].get("next"), auth=("api", config.MAILGUN__API_KEY))
            response.raise_for_status()

            failed_mails_json = response.json()
            items = failed_mails_json.get("items")

        return mail_list

    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error("Failed to get failed mails '{}' due to error:\n{}"
                                      .format(exception_str))
        return None


def _send_email(sender: str,
                recipient: str,
                email_subject: str,
                email_body: str,
                proposal_id: str,
                *, files: List = ()) -> Tuple[bool, Optional[str]]:
    # send data
    max_attempts = 2
    success = True
    message_id = None

    for attempt in range(max_attempts):
        # noinspection PyBroadException
        try:
            data = {
                "from": sender,
                "to": recipient,
                "subject": email_subject,
                "html": email_body
            }
            response = requests.post(config.MAILGUN__API_MESSAGES_URL, auth=("api", config.MAILGUN__API_KEY), data=data, files=files)
            # check that a request is successful
            response.raise_for_status()

            message_id = response.json().get("id")

            break
        except Exception:
            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            if attempt < max_attempts - 1:
                logging.getLogger(__name__).error(("Failed to send email '{}' to '{}' due to error." +
                                                   " Sleep and try again.\n{}")
                                                  .format(proposal_id, recipient, exception_str))
                time.sleep(20)
            else:
                logging.getLogger(__name__).error("Failed to send email '{}' to '{}' due to error. Abort.\n{}"
                                                  .format(proposal_id, recipient, exception_str))
                success = False

    if config.EMAIL_NOTIFICATIONS__BACKUP_ENABLED:
        # noinspection PyBroadException
        try:
            data = {
                "from": config.EMAIL_NOTIFICATIONS__BACKUP_SENDER,
                "to": config.EMAIL_NOTIFICATIONS__BACKUP_ADDRESS,
                "subject": email_subject + ' >>> ' + recipient,
                "html": email_body
            }

            requests.post(config.MAILGUN__API_MESSAGES_URL, auth=("api", config.MAILGUN__API_KEY), data=data, files=files)
        except Exception:
            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error("Failed to send backup email '{}' due to error:\n{}"
                                              .format(proposal_id, exception_str))

    return success, message_id


# def send_email_payment_data_crypto(proposal: Proposal, investments_limit_min: float) -> Tuple[bool, Optional[str]]:
#     if not config.EMAIL_NOTIFICATIONS__ENABLED:
#         return False, None

#     logging.getLogger(__name__).info('Start to send payment data: {}'.format(proposal))

#     templateLoader = FileSystemLoader(searchpath=EMAIL_NOTIFICATIONS__TEMPLATES_PATH)
#     templateEnv = Environment(loader=templateLoader)
#     template = templateEnv.get_template("email_payment-data_crypto.html")

#     email_text = template.render(cryptocurrency_name=proposal.currency,
#                                  cryptocurrency_amount=proposal.amount,
#                                  jibrel_cryptocurrency_address=proposal.address.address,
#                                  investments_limit_min=investments_limit_min)

#     email_subject = 'Your Jibrel Network Token Application'
#     email_files = _format_email_files(
#         attachments_inline=[("jibrel_logo.png",
#                              Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))])
#     success, message_id = _send_email(config.EMAIL_NOTIFICATIONS__SENDER,
#                           proposal.email,
#                           email_subject,
#                           email_text,
#                           proposal.proposal_id,
#                           files=email_files)

#     logging.getLogger(__name__).info('Finished to send payment data: {}"'.format(proposal))

#     return success, message_id


# def send_email_payment_data_fiat(proposal: Proposal, investments_limit_min: float) -> Tuple[bool, Optional[str]]:
#     if not config.EMAIL_NOTIFICATIONS__ENABLED:
#         return False, None

#     logging.getLogger(__name__).info('Start to send payment data: {}'.format(proposal))

#     templateLoader = FileSystemLoader(searchpath=EMAIL_NOTIFICATIONS__TEMPLATES_PATH)
#     templateEnv = Environment(loader=templateLoader)
#     template = templateEnv.get_template("email_payment-data_fiat.html")

#     email_text = template.render(investments_limit_min=investments_limit_min)

#     email_subject = 'Your Jibrel Network Token Application'
#     email_files = _format_email_files(
#         attachments_inline=[("jibrel_logo.png",
#                              Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))],
#         attachments=[("Declaration of Identity of the Beneficial Owner.docx",
#                       Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH,
#                            "Declaration of Identity of the Beneficial Owner.docx"))])
#     success, message_id = _send_email(config.EMAIL_NOTIFICATIONS__SENDER,
#                           proposal.email,
#                           email_subject,
#                           email_text,
#                           proposal.proposal_id,
#                           files=email_files)

#     logging.getLogger(__name__).info('Finished to send payment data: {}'.format(proposal))

#     return success, message_id


def send_email_investment_received_1(transaction: Transaction) -> Tuple[bool, Optional[str]]:
    if not config.EMAIL_NOTIFICATIONS__ENABLED:
        return False, None

    logging.getLogger(__name__).info('Start to send notification about tx: {}'.format(transaction))

    templateLoader = FileSystemLoader(searchpath=EMAIL_NOTIFICATIONS__TEMPLATES_PATH)
    templateEnv = Environment(loader=templateLoader)
    template = templateEnv.get_template("email_investment-received_1.html")

    email_text = template.render(
        transaction_currency_amount=_format_coin_value(transaction.value),
        transaction_currency_name=transaction.address.proposal.currency,
        transaction_currency_conversion_rate=_format_conversion_rate(transaction.jnt_purchase.currency_to_usd_rate),
        transaction_jnt_amount=_format_jnt_value(transaction.jnt_purchase.jnt_value),
        jnt_purchase_id=transaction.jnt_purchase.purchase_id)

    logging.getLogger(__name__).info('Finished to send notification about tx: {}'.format(transaction))

    email_subject = 'Your purchase of {} Jibrel Network Token has been completed!' \
        .format(_format_jnt_value_subject(transaction.jnt_purchase.jnt_value))
    email_files = _format_email_files(
        attachments_inline=[("jibrel_logo.png",
                             Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))])
    success, message_id = _send_email(config.EMAIL_NOTIFICATIONS__SENDER,
                          transaction.address.proposal.email,
                          email_subject,
                          email_text,
                          transaction.address.proposal.proposal_id,
                          files=email_files)

    return success, message_id


def send_email_investment_received_2(transaction: Transaction,
                                     all_transactions: List[Transaction]) -> Tuple[bool, Optional[str]]:
    if not config.EMAIL_NOTIFICATIONS__ENABLED:
        return False, None

    logging.getLogger(__name__).info('Start to send notification about tx: {}'.format(transaction))

    templateLoader = FileSystemLoader(searchpath=EMAIL_NOTIFICATIONS__TEMPLATES_PATH)
    templateEnv = Environment(loader=templateLoader)
    template_email = templateEnv.get_template("email_investment-received_2.html")

    total_usd_amount = sum(tx.jnt_purchase.usd_value for tx in all_transactions)
    total_jnt_amount = sum(tx.jnt_purchase.jnt_value for tx in all_transactions)

    email_text = template_email.render(
        transaction_currency_name=transaction.address.proposal.currency,
        transaction_currency_amount=_format_coin_value(transaction.value),
        transaction_currency_conversion_rate=_format_conversion_rate(transaction.jnt_purchase.currency_to_usd_rate),
        total_usd_amount=_format_fiat_value(total_usd_amount),
        total_jnt_amount=_format_jnt_value(total_jnt_amount),
        jnt_purchase_id=transaction.jnt_purchase.purchase_id)

    email_subject = 'Your purchase of {} Jibrel Network Token has been completed!' \
        .format(_format_jnt_value_subject(transaction.jnt_purchase.jnt_value))
    email_files = _format_email_files(
        attachments_inline=[("jibrel_logo.png",
                             Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))])
    success, message_id = _send_email(config.EMAIL_NOTIFICATIONS__SENDER,
                          transaction.address.proposal.email,
                          email_subject,
                          email_text,
                          transaction.address.proposal.proposal_id,
                          files=email_files)

    logging.getLogger(__name__).info('Finished to send notification about tx: {}'.format(transaction))

    return success, message_id


def send_email_investment_received_3(transaction: Transaction,
                                     investments_limit_min: float,
                                     public_sale_period_start: datetime,
                                     public_sale_period_end: datetime) -> Tuple[bool, Optional[str]]:
    if not config.EMAIL_NOTIFICATIONS__ENABLED:
        return False, None

    logging.getLogger(__name__).info('Start to send notification about tx: {}'.format(transaction))

    templateLoader = FileSystemLoader(searchpath=EMAIL_NOTIFICATIONS__TEMPLATES_PATH)
    templateEnv = Environment(loader=templateLoader)
    template_email = templateEnv.get_template("email_investment-received_3.html")

    email_text = template_email.render(
        jibrel_cryptocurrency_address=transaction.address.address,
        transaction_currency_name=transaction.address.proposal.currency,
        transaction_currency_amount=_format_coin_value(transaction.value),
        transaction_id=transaction.transaction_id,
        investments_limit_min=_format_fiat_value(investments_limit_min),
        public_sale_period=_format_date_period(public_sale_period_start, public_sale_period_end))

    email_subject = 'Your Jibrel Network Token Application - Investment too low'
    email_files = _format_email_files(
        attachments_inline=[("jibrel_logo.png",
                             Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))])
    success, message_id = _send_email(config.EMAIL_NOTIFICATIONS__SENDER,
                          transaction.address.proposal.email,
                          email_subject,
                          email_text,
                          transaction.address.proposal.proposal_id,
                          files=email_files)

    logging.getLogger(__name__).info('Finished to send notification about tx: {}'.format(transaction))

    return success, message_id


def send_email_investment_received_4(transaction: Transaction,
                                     all_transactions: List[Transaction],
                                     investments_limit_min: float,
                                     public_sale_period_start: datetime,
                                     public_sale_period_end: datetime) -> Tuple[bool, Optional[str]]:
    if not config.EMAIL_NOTIFICATIONS__ENABLED:
        return False, None

    logging.getLogger(__name__).info('Start to send notification about tx: {}'.format(transaction))

    templateLoader = FileSystemLoader(searchpath=EMAIL_NOTIFICATIONS__TEMPLATES_PATH)
    templateEnv = Environment(loader=templateLoader)
    template_email = templateEnv.get_template("email_investment-received_4.html")

    total_usd_amount = sum(tx.jnt_purchase.usd_value for tx in all_transactions)

    email_text = template_email.render(
        jibrel_cryptocurrency_address=transaction.address.address,
        transaction_currency_name=transaction.address.proposal.currency,
        transaction_currency_amount=_format_coin_value(transaction.value),
        transaction_id=transaction.transaction_id,
        total_usd_amount=_format_fiat_value(total_usd_amount),
        investments_limit_min=_format_fiat_value(investments_limit_min),
        public_sale_period=_format_date_period(public_sale_period_start, public_sale_period_end))

    email_subject = 'Your Jibrel Network Token Application - Investment too low'
    email_files = _format_email_files(
        attachments_inline=[("jibrel_logo.png",
                             Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))])
    success, message_id = _send_email(config.EMAIL_NOTIFICATIONS__SENDER,
                          transaction.address.proposal.email,
                          email_subject,
                          email_text,
                          transaction.address.proposal.proposal_id,
                          files=email_files)

    logging.getLogger(__name__).info('Finished to send notification about tx: {}'.format(transaction))

    return success, message_id


def send_email_investment_received_5(transaction: Transaction,
                                     investments_limit_max: float,
                                     public_sale_period_start: datetime,
                                     public_sale_period_end: datetime) -> Tuple[bool, Optional[str]]:
    if not config.EMAIL_NOTIFICATIONS__ENABLED:
        return False, None

    logging.getLogger(__name__).info('Start to send notification about tx: {}'.format(transaction))

    templateLoader = FileSystemLoader(searchpath=EMAIL_NOTIFICATIONS__TEMPLATES_PATH)
    templateEnv = Environment(loader=templateLoader)
    template_email = templateEnv.get_template("email_investment-received_5.html")

    email_text = template_email.render(
        transaction_currency_name=transaction.address.proposal.currency,
        transaction_currency_amount=_format_coin_value(transaction.value),
        transaction_id=transaction.transaction_id,
        investments_limit_max=_format_fiat_value(investments_limit_max),
        public_sale_period=_format_date_period(public_sale_period_start, public_sale_period_end))

    email_subject = 'Your Jibrel Network Token Application - Investment too high'
    email_files = _format_email_files(
        attachments_inline=[("jibrel_logo.png",
                             Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))])
    success, message_id = _send_email(config.EMAIL_NOTIFICATIONS__SENDER,
                          transaction.address.proposal.email,
                          email_subject,
                          email_text,
                          transaction.address.proposal.proposal_id,
                          files=email_files)

    logging.getLogger(__name__).info('Finished to send notification about tx: {}'.format(transaction))

    return success, message_id


def send_email_investment_received_6(transaction: Transaction,
                                     all_transactions: List[Transaction],
                                     investments_limit_max: float,
                                     public_sale_period_start: datetime,
                                     public_sale_period_end: datetime) -> Tuple[bool, Optional[str]]:
    if not config.EMAIL_NOTIFICATIONS__ENABLED:
        return False, None

    logging.getLogger(__name__).info('Start to send notification about tx: {}'.format(transaction))

    templateLoader = FileSystemLoader(searchpath=EMAIL_NOTIFICATIONS__TEMPLATES_PATH)
    templateEnv = Environment(loader=templateLoader)
    template_email = templateEnv.get_template("email_investment-received_6.html")

    total_usd_amount = sum(tx.jnt_purchase.usd_value for tx in all_transactions)

    email_text = template_email.render(
        transaction_currency_name=transaction.address.proposal.currency,
        transaction_currency_amount=_format_coin_value(transaction.value),
        transaction_id=transaction.transaction_id,
        total_usd_amount=_format_fiat_value(total_usd_amount),
        investments_limit_max=_format_fiat_value(investments_limit_max),
        public_sale_period=_format_date_period(public_sale_period_start, public_sale_period_end))

    email_subject = 'Your Jibrel Network Token Application - Investment too high'
    email_files = _format_email_files(
        attachments_inline=[("jibrel_logo.png",
                             Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))])
    success, message_id = _send_email(config.EMAIL_NOTIFICATIONS__SENDER,
                          transaction.address.proposal.email,
                          email_subject,
                          email_text,
                          transaction.address.proposal.proposal_id,
                          files=email_files)

    logging.getLogger(__name__).info('Finished to send notification about tx: {}'.format(transaction))

    return success, message_id


def send_email_docs_received(account: Account) -> bool:
    if not config.EMAIL_NOTIFICATIONS__ENABLED:
        return False

    return True

def send_email_investment_received_7(transaction: Transaction) -> bool:
    if not config.FORCE_SCANNING_ADDRESS__ENABLED:
        return False

    logging.getLogger(__name__).info('Start to send notification about tx: {}'.format(transaction))

    templateLoader = FileSystemLoader(searchpath=EMAIL_NOTIFICATIONS__TEMPLATES_PATH)
    templateEnv = Environment(loader=templateLoader)
    template_email = templateEnv.get_template("email_investment-received_7.html")

    email_text = template_email.render(
        transaction_currency_amount=_format_coin_value(transaction.value),
        transaction_currency_name=transaction.address.type,
        transaction_id=transaction.transaction_id,
        transaction_address=transaction.address.address)

    email_subject = 'Notice of transaction'
    email_files = _format_email_files(
        attachments_inline=[("jibrel_logo.png",
                             Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))])
    success = _send_email(config.EMAIL_NOTIFICATIONS__SENDER,
                          config.FORCE_SCANNING_ADDRESS__EMAIL_RECIPIENT,
                          email_subject,
                          email_text,
                          '',
                          files=email_files)

    logging.getLogger(__name__).info('Finished to send notification about tx: {}'.format(transaction))

    return success



#############################################
#
# new code
#
#############################################

logger = logging.getLogger(__name__)


#
# Persist notification to the database
#

def add_notification(email: str, type: str, user_id: Optional[int] = None, data: Optional[dict] = None):
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start persist notification to the database. email: {}, user_id: {}"
                                         .format(email, user_id))

        if user_id:
            user = session.query(User) \
                .filter(User.id == user_id) \
                .all()  # type: User
            assert len(user) == 1, 'Invalid user_id: {}'.format(user_id)

        notification = Notification(user_id=user_id if user_id else None,
                                    type=type,
                                    email=email,
                                    meta=data if data else {})

        session.add(notification)
        session.commit()

        logging.getLogger(__name__).info("Finished to persist notification to the database. email: {}, account_id: {}"
                                         .format(email, user_id))

        return True
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error(
            "Failed to persist notification to the database due to exception:\n{}".format(exception_str))
        session.rollback()
        return False


def send_notification(notification_id):
    """
    Sending notification
    """
    notification = api_models.Notification.objects.get(pk=notification_id)

    if notification.is_sended:
        logger.warn('Notification #%s aready sent', notification_id)
        return False, None

    subject = notification.get_subject()
    body = notification.get_body()
    email_files = _format_email_files(
    attachments_inline=[("jibrel_logo.png",
                         Path(EMAIL_NOTIFICATIONS__TEMPLATES_PATH, "jibrel_logo.png"))])
    logger.info('Sending notification for %s, type %s', notification.email, notification.type)
    return _send_email(
        config.EMAIL_NOTIFICATIONS__SENDER,
        notification.email,
        subject,
        body,
        notification.user_id,
        files=email_files
    )


def send_email_verify_email(email, activate_url, user_id=None):
    ctx = {
        'activate_url': activate_url,
    }
    add_notification(email, user_id=user_id, type=NotificationType.account_created, data=ctx)


def send_email_reset_password(email, activate_url, user_id=None):
    ctx = {
        'activate_url': activate_url,
    }
    add_notification(email, user_id=user_id, type=NotificationType.password_change_request, data=ctx)
