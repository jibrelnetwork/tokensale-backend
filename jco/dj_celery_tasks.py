from celery.schedules import crontab

from jco.commonutils.app_init import initialize_app
from jco.commonutils.celery_postgresql_lock import locked_task
from jco.appprocessor.app_create import celery_app
from jco.appprocessor import commands
import django
django.setup()
from jco.api import tasks as api_tasks


@celery_app.task()
@initialize_app
def celery_add_proposal(*args, **kwargs):
    return commands.add_proposal(*args, **kwargs)


@celery_app.task()
@initialize_app
@locked_task()
def celery_send_email_payment_data():
    return commands.send_email_payment_data()


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
def celery_transaction_processing():
    return commands.transaction_processing()


@celery_app.task()
@initialize_app
@locked_task()
def celery_fetch_tickers_price():
    return commands.fetch_tickers_price()


@celery_app.task()
@initialize_app
@locked_task()
def celery_scan_docs_received():
    return  commands.scan_addresses()


@celery_app.task()
@initialize_app
@locked_task()
def celery_withdraw_processing():
    return  commands.withdraw_processing()


@celery_app.task()
@initialize_app
def celery_get_account_list():
    return  commands.get_account_list()


@celery_app.task()
@initialize_app
def celery_get_all_proposals():
    return commands.get_all_proposals()


@celery_app.task()
@initialize_app
def celery_get_account_proposals(*args, **kwargs):
    return commands.get_account_proposals(*args, **kwargs)


@celery_app.task()
@initialize_app
def celery_get_all_transactions():
    return commands.get_all_transactions()


@celery_app.task()
@initialize_app
def celery_get_proposal_transactions(*args, **kwargs):
    return commands.get_proposal_transactions(*args, **kwargs)


@celery_app.task()
@initialize_app
def celery_set_docs_received(*args, **kwargs):
    return commands.set_docs_received(*args, **kwargs)


@celery_app.task()
@initialize_app
def celery_add_withdraw_jnt(*args, **kwargs):
    return commands.add_withdraw_jnt(*args, **kwargs)


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    # sender.add_periodic_task(crontab(minute='*/1'),
    #                          celery_send_email_payment_data, expires=1 * 60, name='send_email_payment_data')
    # sender.add_periodic_task(crontab(minute=0, hour='*/1'),
    #                          celery_scan_addresses, expires=5 * 60, name='scan_addresses')
    # sender.add_periodic_task(crontab(minute='*/5'),
    #                          calculate_jnt_purchases, expires=5 * 60, name='calculate_jnt_purchases')
    # sender.add_periodic_task(crontab(minute='*/5'),
    #                          celery_transaction_processing, expires=5 * 60, name='transaction_processing')
    # sender.add_periodic_task(crontab(minute='*/1'),
    #                          celery_fetch_tickers_price, expires=1 * 60, name='fetch_tickers_price')

    sender.add_periodic_task(20,
                             api_tasks.check_user_verification_status_runner,
                             expires=1 * 60,
                             name='check_user_verification_status_runner')
    sender.add_periodic_task(20,
                             api_tasks.process_all_notifications_runner,
                             expires=1 * 60,
                             name='process_all_notifications')
