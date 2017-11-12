#!/usr/bin/env python

from jco.commonconfig.config import HOST, PORT, DEBUG
from jco.commonutils.app_init import AppControllerFactory
from jco.appprocessor.app_create import flask_app, wsgi_app  # Need to import wsgi_app for WSGI

if __name__ == '__main__':
    with AppControllerFactory():
        flask_app.run(host=HOST,
                      port=PORT,
                      debug=DEBUG)
