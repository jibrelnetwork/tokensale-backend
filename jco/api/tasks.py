
from datetime import datetime
import logging

from django.contrib.auth import get_user_model

from jco.commonutils import person_verify
from jco.commonutils import ga_integration
from jco.appprocessor.app_create import celery_app
from jco.appprocessor import notify
from jco.api.models import Account, Notification


logger = logging.getLogger(__name__)


@celery_app.task()
def verify_user(user_id):
    """
    Create OnFido check to verify user document
    """
    user = get_user_model().objects.get(pk=user_id)

    if user.account.onfido_check_status == person_verify.STATUS_COMPLETE:
        logger.warn('Verification completed')
        return

    logger.info('Start verifying process for user %s <%s>', user.pk, user.email)
    if not user.account.onfido_applicant_id:
        applicant_id = person_verify.create_applicant(user_id)
        user.account.onfido_applicant_id = applicant_id
        user.account.save()
        logger.info('Applicant created: %s', user.account.onfido_applicant_id)
    else:
        logger.info('Applicant already exists: %s', user.account.onfido_applicant_id)

    if not user.account.onfido_document_id:
        document_id = person_verify.upload_document(
            user.account.onfido_applicant_id, user.account.document_url, user.account.document_type)
        user.account.onfido_document_id = document_id
        user.account.save()
        logger.info('Document uploaded: %s', user.account.onfido_document_id)
        notify.send_email_kyc_data_received(email=user.email, user_id=user.pk)
    else:
        logger.info('Document already uploaded: %s', user.account.onfido_document_id)

    check_id = person_verify.create_check(user.account.onfido_applicant_id)
    user.account.onfido_check_id = check_id
    user.account.onfido_check_created = datetime.now()
    user.account.save()
    logger.info('Check created: %s', user.account.onfido_check_id)


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

    user.account.onfido_check_status = check.status
    user.account.onfido_check_result = check.result
    if check.result == person_verify.RESULT_CLEAR:
        user.account.is_identity_verified = True
        ga_integration.on_status_verified(user.account)
    elif check.status == person_verify.STATUS_COMPLETE and check.result != person_verify.RESULT_CLEAR:
        ga_integration.on_status_not_verified(user.account)
    user.account.save()
    logger.info('Verification status is: %s, result: %s', check.status, check.result)


@celery_app.task()
def check_user_verification_status_runner():
    accounts_to_check = Account.objects.filter(onfido_check_result=None).exclude(
        onfido_check_id=None).all()
    for account in accounts_to_check:
        logger.info('Run check verification status for user %s <%s>',
                    account.user.pk, account.user.email)
        check_user_verification_status.delay(account.user.pk)


@celery_app.task()
def process_all_notifications_runner():
    logger.info('Run notifications processing')

    notifications_to_send = Notification.objects.filter(is_sended=False).all()
    for notification in notifications_to_send:
        success, message_id = notify.send_notification(notification.pk)
        notification.is_sended = success
        notification.meta['mailgun_message_id'] = message_id
        notification.rendered_message = notification.get_body()

        notification.save()

    logger.info('Finished notifications processing')
