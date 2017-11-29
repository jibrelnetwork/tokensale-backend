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
        return "OK", 200

    @app.route("/crm/proposals/<account_id>", methods=['GET'])
    @app.route("/crm/proposals", methods=['GET'])
    @requires_auth
    def proposals(account_id = None):
        return "OK", 200

    @app.route("/crm/transactions/<proposal_id>", methods=['GET'])
    @app.route("/crm/transactions", methods=['GET'])
    @requires_auth
    def transactions(proposal_id=None):
        return "OK", 200

    @app.route('/crm/docsreceived', methods=['POST'])
    @requires_auth
    def docs_received():
        return "OK", 200

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


flask_app = create_flask_app('jco.commonconfig.config')
if FLASK_CORS_ENABLED:
    CORS(flask_app)

celery_app = create_celery_app(flask_app)

wsgi_app = initialize_app(flask_app.wsgi_app)
