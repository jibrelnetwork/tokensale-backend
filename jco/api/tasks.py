
from datetime import datetime
import logging

from django.contrib.auth import get_user_model

from jco.commonutils import person_verify


logger = logging.getLogger(__name__)


def verify_user(user_id):
    """
    Create OnFido check to verify user document
    """
    user = get_user_model().objects.get(pk=user_id)

    logger.info('Start verifying process for user %s <%s>', user.pk, user.email)
    if not user.account.onfido_applicant_id:
        applicant_id = person_verify.create_applicant(user_id)
        user.account.onfido_applicant_id = applicant_id
        user.account.save()
        logger.info('Applicant created: %s', user.account.onfido_applicant_id)
    else:
        logger.info('Applicant already exists: %s', user.account.onfido_applicant_id)

    if not user.account.onfido_document_id:
        document_id = person_verify.upload_document(user.account.onfido_applicant_id, user.account.document_url)
        user.account.onfido_document_id = document_id
        user.account.save()
        logger.info('Document uploaded: %s', user.account.onfido_document_id)
    else:
        logger.info('Document already uploaded: %s', user.account.onfido_document_id)

    check_id = person_verify.create_check(user.account.onfido_applicant_id)
    user.account.onfido_check_id = check_id
    user.account.onfido_check_created = datetime.now()
    user.account.save()
    logger.info('Check created: %s', user.account.onfido_check_id)


def check_user_verification_status(user_id):
    """
    Check and store OnFido check status and result 
    """
    user = get_user_model().objects.get(pk=user_id)
    logger.info('Checking verification status for user %s <%s>', user.pk, user.email)
    api = person_verify.get_client()
    
    check = api.find_check(user.account.onfido_applicant_id, user.account.onfido_check_id)

    user.account.onfido_check_status = check.status
    user.account.onfido_check_result = check.result
    user.account.save()
    logger.info('Verification status is: %s, result: %s', check.status, check.result)