# import sys
# from datetime import datetime
# import logging
# from pathlib import Path
# from typing import Dict, List

# from .mailgun_handler import MailgunHandler

from jco.settings import *

try:
    from jco.settings_local import *
except ImportError:
    pass


SQLALCHEMY_DATABASE_URI = JCO_DATABASE_URI
if 'pytest' in ' '.join(sys.argv):
    db_name = SQLALCHEMY_DATABASE_URI.split('/')[-1]
    SQLALCHEMY_DATABASE_URI = '/'.join(SQLALCHEMY_DATABASE_URI.split('/')[:-1] + ['test_' + db_name])


print('SQLA DB URI', SQLALCHEMY_DATABASE_URI)


def getLoggingConfig(path):
    return LOGGING
# def getLoggingConfig(rootLogDir: Path) -> Dict:
#     appLogLevel = logging.DEBUG if DEBUG else logging.INFO
#     sqlAlchemyLogLevel = logging.WARNING if DEBUG else logging.ERROR
#     appHandlers = ['handler_file', 'handler_console']
#     appHandlers = ['handler_console']
#     if LOGGING__MAILGUN__ENABLED is True and DEBUG is False:
#         appHandlers.append('handler_mailgun')

#     mailFormat = '''
#     Message type:\t\t%(levelname)s
#     Location:\t\t%(pathname)s:%(lineno)d
#     Module:\t\t%(module)s
#     Function:\t\t%(funcName)s
#     Time:\t\t%(asctime)s
#     Message:
#     %(message)s
#     '''

#     return {
#         'version': 1,
#         'disable_existing_loggers': False,
#         'formatters': {
#             'formatter_verbose': {
#                 'format': '%(asctime)s > %(threadName)s > %(levelname)s > %(name)s:%(lineno)d:%(funcName)s >>> %(message)s'
#             },
#             'formatter_brief': {
#                 'format': '%(asctime)s > %(levelname)s > %(message)s'
#             },
#             'formatter_mail': {
#                 'format': mailFormat
#             },
#         },
#         'handlers': {
#             'handler_file': {
#                 'formatter': 'formatter_verbose',
#                 'class': 'logging.handlers.RotatingFileHandler',
#                 'filename': str(rootLogDir / 'mainapp.log'),
#                 'maxBytes': 1024 * 1024,
#                 'backupCount': 1000,
#             },
#             'handler_console': {
#                 'formatter': 'formatter_verbose',
#                 'class': 'logging.StreamHandler',
#                 'stream': sys.stdout,
#             },
#             'handler_mailgun': {
#                 'level': logging.ERROR,
#                 'formatter': 'formatter_mail',
#                 'class': MailgunHandler.__module__ + '.' + MailgunHandler.__name__,
#                 'api_url': MAILGUN__API_MESSAGES_URL,
#                 'api_key': MAILGUN__API_KEY,
#                 'sender': LOGGING__MAILGUN__SENDER,
#                 'recipients': LOGGING__MAILGUN__RECIPIENTS,
#                 'subject': LOGGING__MAILGUN__SUBJECT,
#             },
#         },
#         'loggers': {
#             '': {'handlers': appHandlers, 'level': appLogLevel, 'propagate': False},
#             'sqlalchemy': {'handlers': appHandlers, 'level': sqlAlchemyLogLevel, 'propagate': False},
#         },
#     }
