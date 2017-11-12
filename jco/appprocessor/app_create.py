import logging
import sys
import traceback
from datetime import datetime
from functools import wraps

from flask import Flask, Response, render_template, request
from flask_restful import Api
from flask_cors import CORS
from celery import Celery
from sqlalchemy.dialects.postgresql import JSONB

from jco.commonconfig.config import CELERY_BROKER_URL, CELERY_NAME, FLASK_CORS_ENABLED, BASIC_AUTH__USERNAME, BASIC_AUTH__PASSWD
from jco.appdb.db import db
from jco.commonutils.app_init import initialize_app
from jco.appprocessor.resources import ProposalResource
from jco.appdb.models import *


def check_auth(username, password):
    """ This function is called to check if a username / password
        combination is valid.
    """
    return username == BASIC_AUTH__USERNAME and password == BASIC_AUTH__PASSWD


def authenticate():
    """Sends a 401 response that enables basic auth"""
    return Response(
    'Could not verify your access level for that URL.\n'
    'You have to login with proper credentials', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})


def requires_auth(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return authenticate()
        return f(*args, **kwargs)
    return decorated


def create_flask_app(config_filename):
    app = Flask(__name__)
    app.config.from_object(config_filename)
    api = Api(app)
    db.init_app(app)
    api.add_resource(ProposalResource, '/application', endpoint='application')

    @app.route("/crm/", methods=['GET'])
    @app.route('/crm/index', methods=['GET'])
    @app.route('/crm/accounts', methods=['GET'])
    @requires_auth
    def accounts():
        from celery_tasks import celery_get_account_list

        task = celery_get_account_list.delay()

        accounts = None
        try:
            accounts = task.get(timeout=10)
        except TimeoutError:
            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error("ailed to persist new investment request due to error:\n{}"
                                              .format(exception_str))


        return render_template('www_accounts.html', accounts=accounts)

    @app.route("/crm/proposals/<account_id>", methods=['GET'])
    @app.route("/crm/proposals", methods=['GET'])
    @requires_auth
    def proposals(account_id = None):
        from celery_tasks import celery_get_all_proposals, celery_get_account_proposals

        account = None
        proposals = None

        try:
            if (account_id):
                task = celery_get_account_proposals.delay(account_id)
                account, proposals = task.get(timeout=10)  # type: Tuple[Dict,List[Dict]]
            else:
                task = celery_get_all_proposals.delay()
                proposals = task.get(timeout=10)  # type: List[Dict]
        except TimeoutError:
            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error("ailed to persist new investment request due to error:\n{}"
                                              .format(exception_str))

        return render_template("www_proposals.html", account=account, proposals=proposals)

    @app.route("/crm/transactions/<proposal_id>", methods=['GET'])
    @app.route("/crm/transactions", methods=['GET'])
    @requires_auth
    def transactions(proposal_id=None):
        from celery_tasks import celery_get_all_transactions, celery_get_proposal_transactions

        proposal = None
        transactions = None

        try:
            if (proposal_id):
                task = celery_get_proposal_transactions.delay(proposal_id)
                proposal, transactions = task.get(timeout=10)  # type: Tuple[Dict,List[Dict]]
            else:
                task = celery_get_all_transactions.delay()
                transactions = task.get(timeout=10)  # type: List[Dict]
        except TimeoutError:
            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error("ailed to persist new investment request due to error:\n{}"
                                              .format(exception_str))

        return render_template("www_transactions.html", proposal=proposal, transactions=transactions)

    @app.route('/crm/docsreceived', methods=['POST'])
    @requires_auth
    def docs_received():
        from celery_tasks import celery_set_docs_received

        account_id = request.form.get('id')

        success = False
        if account_id:
            task = celery_set_docs_received.delay(account_id)
            try:
                success = task.get(timeout=10)
            except TimeoutError:
                exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
                logging.getLogger(__name__).error("ailed to persist new investment request due to error:\n{}"
                                                  .format(exception_str))
        if success:
            return "OK", 200
        else:
            return "FAILED", 400

    return app


def create_celery_app(_flask_app):
    # http://flask.pocoo.org/docs/0.12/patterns/celery/
    _celery_app = Celery(CELERY_NAME, broker=CELERY_BROKER_URL, backend='rpc')
    _celery_app.conf.update(result_expires=3600)
    TaskBase = _celery_app.Task

    class ContextTask(TaskBase):
        abstract = True

        def __call__(self, *args, **kwargs):
            with _flask_app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    _celery_app.Task = ContextTask
    return _celery_app


flask_app = create_flask_app('commonconfig.config')
if FLASK_CORS_ENABLED:
    CORS(flask_app)

celery_app = create_celery_app(flask_app)

wsgi_app = initialize_app(flask_app.wsgi_app)
