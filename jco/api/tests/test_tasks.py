from unittest import mock
from datetime import datetime, timedelta

import pytest
import pytz

from jco.api import tasks
from jco.api import models as m


@mock.patch('jco.api.tasks.person_verify')
def test_verify_user_all_ok(person_verify, live_server, accounts):
    acc = accounts[0]
    acc.document_url = 'url_1'
    acc.document_type = 'type_1'
    acc.verification_started_at = datetime.now() - timedelta(minutes=6)
    acc.save()
    user_id = acc.user.pk
    person_verify.create_applicant.return_value = 'applicant_1'
    person_verify.upload_document.return_value = 'document_1'
    person_verify.create_check.return_value = 'check_1'
    tasks.verify_user(accounts[0].user.pk)

    person_verify.create_applicant.assert_called_with(user_id)
    person_verify.upload_document.assert_called_with(
        'applicant_1', 'url_1', 'type_1')
    person_verify.create_check.assert_called_with('applicant_1')

    notice = m.Notification.objects.filter(email=acc.user.username).all()
    assert len(notice) == 1
    assert notice[0].type == m.NotificationType.kyc_data_received


@mock.patch('jco.api.tasks.person_verify')
def test_verify_user_doc_id_exist(person_verify, live_server, accounts):
    acc = accounts[0]
    acc.onfido_document_id = 'docid_1'
    acc.save()
    user_id = acc.user.pk
    person_verify.create_applicant.return_value = 'applicant_1'
    person_verify.upload_document.return_value = 'document_1'
    person_verify.create_check.return_value = 'check_1'
    tasks.verify_user(acc.user.pk)

    person_verify.create_applicant.assert_called_with(user_id)
    person_verify.upload_document.assert_not_called()
    person_verify.create_check.assert_called_with('applicant_1')

    notice = m.Notification.objects.filter(email=acc.user.username).all()
    assert len(notice) == 0


@mock.patch('jco.api.tasks.person_verify')
def test_verify_user_applicant_id_exist(person_verify, live_server, accounts):
    acc = accounts[0]
    acc.onfido_applicant_id = 'appid_1'
    acc.document_url = 'url_1'
    acc.document_type = 'type_1'
    acc.save()
    person_verify.create_applicant.return_value = 'applicant_1'
    person_verify.upload_document.return_value = 'document_1'
    person_verify.create_check.return_value = 'check_1'
    tasks.verify_user(acc.user.pk)

    person_verify.create_applicant.assert_not_called()
    person_verify.upload_document.assert_called_with(
        'appid_1', 'url_1', 'type_1')
    person_verify.create_check.assert_called_with('appid_1')

    notice = m.Notification.objects.filter(email=acc.user.username).all()
    assert len(notice) == 1


@mock.patch('jco.api.tasks.person_verify')
def test_verify_user_check_started(person_verify, live_server, accounts):
    acc = accounts[0]
    acc.verification_started_at = datetime.now() - timedelta(minutes=4)
    acc.save()
    tasks.verify_user(acc.user.pk)

    person_verify.create_applicant.assert_not_called()
    person_verify.upload_document.assert_not_called()
    person_verify.create_check.assert_not_called()

    notice = m.Notification.objects.filter(email=acc.user.username).all()
    assert len(notice) == 0


@mock.patch('jco.api.tasks.verify_user')
def test_retry_uncomplete_verifications(verify_user, accounts, live_server):
    accounts[0].onfido_check_id = '123'
    accounts[0].document_url = 'ooo'
    accounts[1].verification_started_at = datetime.now() - timedelta(minutes=4)
    accounts[1].document_url = 'aaa'
    accounts[2].document_url = 'bbb'
    accounts[3].verification_started_at = datetime.now() - timedelta(minutes=6)
    accounts[3].document_url = 'ccc'
    accounts[4].document_url = 'ccc'
    accounts[4].is_identity_verified = True
    accounts[5].document_url = 'ccc'
    accounts[5].is_identity_verification_declined = True
    accounts[6].document_url = 'ccc'
    accounts[6].verification_attempts = tasks.MAX_VERIFICATION_ATTEMPTS

    accounts[0].save()
    accounts[1].save()
    accounts[2].save()
    accounts[3].save()
    accounts[4].save()
    accounts[5].save()
    accounts[6].save()

    tasks.retry_uncomplete_verifications()
    assert verify_user.delay.call_count == 2
    verify_user.delay.assert_has_calls([
        mock.call(accounts[2].user.pk),
        mock.call(accounts[3].user.pk),
    ])


def make_operations(user):

    for n in range(1, 7):
        mocked_dt = datetime(2017, 12, n, tzinfo=pytz.utc)
        with mock.patch('django.utils.timezone.now', mock.Mock(return_value=mocked_dt)):
            m.Operation.objects.create(last_notification_sent_at=datetime(2017, 12, n),
                                       user=user,
                                       operation=m.Operation.OP_CHANGE_ADDRESS,
                                       params={'n': n, 't': 0})
        mocked_dt = datetime(2017, 12, n, 12, tzinfo=pytz.utc)
        with mock.patch('django.utils.timezone.now', mock.Mock(return_value=mocked_dt)):
            m.Operation.objects.create(last_notification_sent_at=datetime(2017, 12, n, 12),
                                       user=user,
                                       operation=m.Operation.OP_CHANGE_ADDRESS,
                                       params={'n': n, 't': 12})


@mock.patch('jco.api.tasks.timezone')
@mock.patch.object(m.Operation, 'get_handler')
def test_resend_emails_for_unconfirmed_operations(mock_get_handler, mock_datetime, users, accounts, live_server):
    mock_datetime.now.return_value = datetime(2017, 12, 7, tzinfo=pytz.utc)
    make_operations(users[0])
    mock_handler = mock.Mock()
    mock_get_handler.return_value = mock_handler
    mock_handler.send_confirmation_email.return_value = True
    tasks.resend_emails_for_unconfirmed_operations()
    mock_handler.send_confirmation_email.assert_has_calls([
        mock.call(mock.ANY, mock.ANY, {'n': 2, 't': 12}),
        mock.call(mock.ANY, mock.ANY, {'n': 3, 't': 0}),
        mock.call(mock.ANY, mock.ANY, {'n': 3, 't': 12}),
        mock.call(mock.ANY, mock.ANY, {'n': 4, 't': 0}),
        mock.call(mock.ANY, mock.ANY, {'n': 4, 't': 12}),
        mock.call(mock.ANY, mock.ANY, {'n': 5, 't': 12}),
        ])
