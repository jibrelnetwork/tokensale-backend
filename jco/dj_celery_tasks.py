from celery.schedules import crontab

from jco.commonutils.app_init import initialize_app
from jco.commonutils.celery_postgresql_lock import locked_task
from jco.appprocessor.app_create import celery_app
from jco.appprocessor import commands
import django
django.setup()
from jco.api import tasks as api_tasks
from jco.appprocessor import affiliate


@celery_app.task()
@initialize_app
@locked_task()
def celery_scan_addresses():
    return commands.scan_addresses()


@celery_app.task()
@initialize_app
@locked_task()
def calculate_jnt_purchases():
    return commands.calculate_jnt_purchases()


@celery_app.task()
@initialize_app
@locked_task()
def celery_fetch_tickers_price():
    return commands.fetch_tickers_price()


@celery_app.task()
@initialize_app
@locked_task()
def celery_withdraw_processing():
    return  commands.withdraw_processing()


@celery_app.task()
@initialize_app
@locked_task()
def celery_check_affiliate_events():
    return affiliate.check_new_events()


@celery_app.task()
@initialize_app
@locked_task()
def celery_scan_affiliates():
    return affiliate.scan_affiliates()


@celery_app.task()
@initialize_app
@locked_task()
def celery_withdraw_processing():
    return commands.withdraw_processing()


@celery_app.task()
@initialize_app
@locked_task()
def celery_check_withdraw_transactions():
    return commands.check_withdraw_transactions()


@celery_app.task()
@initialize_app
def celery_get_account_list():
    return commands.get_account_list()


@celery_app.task()
@initialize_app
def celery_get_all_transactions():
    return commands.get_all_transactions()


@celery_app.task()
@initialize_app
def celery_add_withdraw_jnt(*args, **kwargs):
    return commands.add_withdraw_jnt(*args, **kwargs)


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(crontab(minute='*/30'),
                             celery_scan_addresses, expires=5 * 60, name='scan_addresses')
    sender.add_periodic_task(crontab(minute='*/5'),
                             calculate_jnt_purchases, expires=5 * 60, name='calculate_jnt_purchases')
    sender.add_periodic_task(crontab(minute='*/1'),
                             celery_fetch_tickers_price, expires=1 * 60, name='fetch_tickers_price')
    sender.add_periodic_task(crontab(minute='*/10'),
                             celery_check_affiliate_events, expires=5 * 60, name='celery_check_affiliate_events')
    sender.add_periodic_task(crontab(minute='*/10'),
                             celery_scan_affiliates, expires=5 * 60, name='celery_scan_affiliates')
    sender.add_periodic_task(crontab(minute='*/10'),
                             celery_withdraw_processing, expires=5 * 60, name='celery_withdraw_processing')
    sender.add_periodic_task(crontab(minute='*/10'),
                             celery_check_withdraw_transactions, expires=5 * 60, name='celery_check_withdraw_transactions')

    sender.add_periodic_task(20,
                             api_tasks.check_user_verification_status_runner,
                             expires=1 * 60,
                             name='check_user_verification_status_runner')
    sender.add_periodic_task(20,
                             api_tasks.process_all_notifications_runner,
                             expires=1 * 60,
                             name='process_all_notifications')
    sender.add_periodic_task(20,
                             api_tasks.retry_uncomplete_verifications,
                             expires=1 * 60,
                             name='retry_uncomplete_verifications')
    sender.add_periodic_task(crontab(minute=0, hour='*/12'),
                             api_tasks.resend_emails_for_unconfirmed_operations,
                             expires=1 * 60,
                             name='resend_emails_for_unconfirmed_operations')
