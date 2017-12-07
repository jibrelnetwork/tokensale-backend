
from datetime import datetime, timedelta
import logging

from django.contrib.auth import get_user_model
from django.conf import settings
from django.db.models import Q
from django.db import transaction
from django.utils import timezone

from jco.commonutils import person_verify
from jco.commonutils import ga_integration
from jco.appprocessor.app_create import celery_app
from jco.appprocessor import notify as notify_lib
from jco.api.models import Account, Notification


logger = logging.getLogger(__name__)


MAX_VERIFICATION_ATTEMPTS = 3


@celery_app.task()
def verify_user(user_id, notify=True):
    """
    Create OnFido check to verify user document
    """
    user = get_user_model().objects.get(pk=user_id)

    with transaction.atomic():
        now = timezone.now()
        account = Account.objects.select_for_update().get(user=user)

        if account.onfido_check_status == person_verify.STATUS_COMPLETE:
            logger.warn('Verification completed for %s, exiting', user.username)
            return

        if account.onfido_check_id is not None:
            logger.warn('Check exists for %s, exiting', user.username)
            return

        if (account.verification_started_at and
           (now - account.verification_started_at) < timedelta(minutes=5)):
            logger.info('Verification already started for %s, exiting', user.username)
            return

        logger.info('Start verifying process for user %s <%s>', user.pk, user.username)
        account.verification_started_at = now
        account.verification_attempts += 1
        account.save()

    if not account.onfido_applicant_id:
        applicant_id = person_verify.create_applicant(user_id)
        account.onfido_applicant_id = applicant_id
        account.save()
        logger.info('Applicant %s created for %s',
                    account.onfido_applicant_id, user.username)
    else:
        logger.info('Applicant for %s already exists: %s',
                    user.username, account.onfido_applicant_id)

    if not account.onfido_document_id:
        document_id = person_verify.upload_document(
            account.onfido_applicant_id, account.document_url, account.document_type)
        account.onfido_document_id = document_id
        account.save()
        logger.info('Document for %s uploaded: %s',
                    user.username, account.onfido_document_id)
        if notify:
            notify_lib.send_email_kyc_data_received(email=user.email, user_id=user.pk)
    else:
        logger.info('Document for %s already uploaded: %s',
                    user.username, account.onfido_document_id)

    check_id = person_verify.create_check(account.onfido_applicant_id)
    account.onfido_check_id = check_id
    account.onfido_check_created = timezone.now()
    account.save()
    logger.info('Check for %s created: %s', user.username, account.onfido_check_id)


@celery_app.task()
def check_user_verification_status(user_id):
    """
    Check and store OnFido check status and result
    """
    user = get_user_model().objects.get(pk=user_id)
    logger.info('Checking verification status for user %s <%s>', user.pk, user.email)
    if user.account.onfido_check_status == person_verify.STATUS_COMPLETE:
        logger.warn('Verification completed')
        return
    api = person_verify.get_client()

    check = api.find_check(user.account.onfido_applicant_id, user.account.onfido_check_id)

    logger.info('Verification status is: %s, result: %s', check.status, check.result)
    user.account.onfido_check_status = check.status
    user.account.onfido_check_result = check.result
    if check.result == person_verify.RESULT_CLEAR:
        for report_id in check.reports:
            report = api.find_report(user.account.onfido_check_id, report_id)
            if report.name == 'document':
                if report.properties['issuing_country'].upper() in settings.COUNTRIES_NOT_ALLOWED:
                    user.account.is_identity_verification_declined = True
                    ga_integration.on_status_not_verified(user.account)
                    user.account.save()
                    logger.info('User %s is rejected by country: %s',
                                user.email, report.properties['issuing_country'])
                    return
        user.account.is_identity_verified = True
        ga_integration.on_status_verified(user.account)
    elif check.status == person_verify.STATUS_COMPLETE and check.result != person_verify.RESULT_CLEAR:
        ga_integration.on_status_not_verified(user.account)
    user.account.save()


@celery_app.task()
def check_user_verification_status_runner():
    accounts_to_check = Account.objects.filter(onfido_check_result=None).exclude(
        onfido_check_id=None).all()
    for account in accounts_to_check:
        logger.info('Run check verification status for user %s <%s>',
                    account.user.pk, account.user.email)
        check_user_verification_status.delay(account.user.pk)


@celery_app.task()
def retry_uncomplete_verifications():
    now = datetime.now()
    condition = (
        Q(onfido_check_id=None) &
        Q(is_identity_verified=False) &
        Q(is_identity_verification_declined=False) &
        Q(verification_attempts__lt=MAX_VERIFICATION_ATTEMPTS) &
        ~Q(document_url='') &
        (Q(verification_started_at__lt=(now - timedelta(minutes=5))) |
         Q(verification_started_at=None))
    )
    accounts_to_verify = Account.objects.filter(condition).all()
    for account in accounts_to_verify:
        logger.info('Retry uncomplete account verification %s <%s>',
                    account.user.pk, account.user.email)
        verify_user.delay(account.user.pk)


@celery_app.task()
def process_all_notifications_runner():
    logger.info('Run notifications processing')

    notifications_to_send = Notification.objects.filter(is_sended=False).all()
    for notification in notifications_to_send:
        success, message_id = notify_lib.send_notification(notification.pk)
        notification.is_sended = success
        notification.meta['mailgun_message_id'] = message_id
        notification.rendered_message = notification.get_body()

        notification.save()

    logger.info('Finished notifications processing')
