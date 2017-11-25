from celery.schedules import crontab

from jco.commonutils.app_init import initialize_app
from jco.commonutils.celery_postgresql_lock import locked_task
from jco.appprocessor.app_create import celery_app
from jco.appprocessor import commands


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
def celery_add_withdraw_jnt(*args, **kwargs):
    return commands.add_withdraw_jnt(*args, **kwargs)


@celery_app.on_after_finalize.connect
def setup_periodic_tasks(sender, **kwargs):
    sender.add_periodic_task(crontab(minute=0, hour='*/1'),
                             celery_scan_addresses, expires=5 * 60, name='scan_addresses')
    sender.add_periodic_task(crontab(minute='*/5'),
                             calculate_jnt_purchases, expires=5 * 60, name='calculate_jnt_purchases')
    sender.add_periodic_task(crontab(minute='*/1'),
                             celery_fetch_tickers_price, expires=1 * 60, name='fetch_tickers_price')
