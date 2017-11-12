# https://fadeit.dk/blog/2015/10/12/mailgun-python-log-handler/

import logging
import requests


class MailgunHandler(logging.Handler):
    def __init__(self, api_url, api_key, sender, recipients, subject):
        # run the regular Handler __init__
        logging.Handler.__init__(self)
        self.api_url = api_url
        self.api_key = api_key
        self.sender = sender
        self.recipients = recipients
        self.subject = subject

    def emit(self, record):
        # record.message is the log message
        for recipient in self.recipients:
            data = {
                "from": self.sender,
                "to": recipient,
                "subject": self.subject,
                "text": self.format(record)
            }
            requests.post(self.api_url, auth=("api", self.api_key), data=data)
