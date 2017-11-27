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
from jco.commonconfig import config
from jco.appdb.models import *
from jco.api import models as api_models


EMAIL_NOTIFICATIONS__TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'templates')
logger = logging.getLogger(__name__)


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


#
# Persist notification to the database
#

def add_notification(email: str, type: str, user_id: Optional[int] = None, data: Optional[dict] = None):
    # noinspection PyBroadException
    try:
        logging.getLogger(__name__).info("Start persist notification to the database. email: {}, user_id: {}"
                                         .format(email, user_id))

        if user_id:
            try:
                api_models.Account.objects.get(user_id=user_id)
            except (ValueError, api_models.Account.DoesNotExist):
                logging.getLogger(__name__).error("Invalid user_id: {}.".format(user_id))

        api_models.Notification.objects.create(
            user_id=user_id,
            type=type,
            email=email,
            meta=data if data else dict()
        )

        logging.getLogger(__name__).info("Finished to persist notification to the database. email: {}, account_id: {}"
                                         .format(email, user_id))

        return True
    except Exception:
        exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
        logging.getLogger(__name__).error(
            "Failed to persist notification to the database due to exception:\n{}".format(exception_str))
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


def send_email_identity_not_verified(email, user_id=None):
    add_notification(email, user_id=user_id, type=NotificationType.account_rejected, data={})


def send_email_kyc_data_received(email, user_id=None):
    add_notification(email, user_id=user_id, type=NotificationType.kyc_data_received, data={})


def send_email_kyc_account_rejected(email, user_id=None):
    add_notification(email, user_id=user_id, type=NotificationType.kyc_account_rejected, data={})
