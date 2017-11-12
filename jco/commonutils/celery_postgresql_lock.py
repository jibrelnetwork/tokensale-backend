# https://stackoverflow.com/questions/20894771/celery-beat-limit-to-single-task-instance-at-a-time

import logging
import sys
import traceback

from sqlalchemy import func, text, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.engine import Engine
from contextlib import contextmanager
from functools import wraps

from jco.appdb.db import db


def _psql_advisory_lock_blocking(conn, lock_id, shared, timeout):
    lock_fn = (func.pg_advisory_xact_lock_shared
               if shared else
               func.pg_advisory_xact_lock)
    if timeout:
        conn.execute(text('SET statement_timeout TO :timeout'), timeout=timeout)
    try:
        conn.execute(select([lock_fn(lock_id)]))
    except DBAPIError:
        return False
    return True


def _psql_advisory_lock_nonblocking(conn, lock_id, shared):
    lock_fn = (func.pg_try_advisory_xact_lock_shared
               if shared else
               func.pg_try_advisory_xact_lock)
    return conn.execute(select([lock_fn(lock_id)])).scalar()


class _DatabaseLockFailed(Exception):
    pass


@contextmanager
def _db_lock(engine, name, shared=False, block=True, timeout=None):
    """
    Context manager which acquires a PSQL advisory transaction lock with a
    specified name.
    """
    lock_id = hash(name)

    with engine.begin() as conn, conn.begin():
        if block:
            isLocked = _psql_advisory_lock_blocking(conn, lock_id, shared, timeout)
        else:
            isLocked = _psql_advisory_lock_nonblocking(conn, lock_id, shared)
        if not isLocked:
            raise _DatabaseLockFailed()
        yield


def _getDbEngine() -> Engine:
    """
    Integration of decorator with the app
    :return: SQLAlchemy engine object
    :rtype:
    """
    return db.engine


def locked_task(name=None, block=True, timeout='1s'):
    """
    Using a PostgreSQL advisory transaction lock, only runs this task if the
    lock is available. Otherwise logs a message and returns `None`.
    """

    def with_task(fn):
        lock_id = name or 'celery:{}.{}'.format(fn.__module__, fn.__name__)

        @wraps(fn)
        def f(*args, **kwargs):
            try:
                with _db_lock(_getDbEngine(), name=lock_id, block=block, timeout=timeout):
                    return fn(*args, **kwargs)
            except _DatabaseLockFailed:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error("Failed to get lock for the Celery task '{}' due to error:\n{}"
                                                  .format(fn.__name__, exception_str))
                return None

        return f

    return with_task
