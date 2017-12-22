import os
import random
import string
import requests
import logging
from pathlib import Path
from typing import List, Tuple, Optional, Dict

from jco.appprocessor import notify
from jco.commonconfig import config
from jco.appprocessor.templates.subjects import TEMPLATE__SUBJECT


# Mail-tester.com
MAIL_TESTER__USER = "denalex"
MAIL_TESTER__REPORT_URL = "https://www.mail-tester.com/{}-{}&format={}"

class ReportType:
    json = "json"
    dbug = "dbug"


def get_templates_path() -> str:
    return Path(os.path.dirname(os.path.realpath(__file__)), "templates")


#
# Read a template file
#

def get_template_data(template_name: str) -> Optional[str]:
    try:
        with open(Path(get_templates_path(), template_name), 'r') as template_file:
            template_data=template_file.read()

        return template_data

    except Exception:
        return None


#
# Send an email template to mail-tester.com
#

def send_email_template(template_name: str) -> Tuple[bool, Optional[str], Optional[str]]:
    template_id = template_name + '_' + ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    email = "{}-{}@mail-tester.com".format(MAIL_TESTER__USER,
                                           template_id)
    subject = TEMPLATE__SUBJECT[template_name]
    body = get_template_data(template_name)
    email_files = notify._format_email_files(
        attachments_inline=[(
            "jibrel_logo.png",
            Path(get_templates_path(), "jibrel_logo.png")
        )]
    )

    logging.getLogger(__name__).info("Sending email template {}".format(template_name))

    success, mail_id = notify._send_email(
        email,
        subject,
        body,
        0,
        files=email_files
    )

    return success, mail_id, template_id


#
# Send to test all email templates
#

def send_email_templates() -> List[str]:
    res = list()
    for template_name in TEMPLATE__SUBJECT:
        success, mail_id, template_id = send_email_template(template_name)
        if success:
            res.append(template_id)

    return res


#
# Get an email template's mark using mail-tester.com
#

def get_email_template_mark(template_id: str) -> Dict:
    _url = MAIL_TESTER__REPORT_URL \
        .format(MAIL_TESTER__USER,
                template_id,
                ReportType.json)
    r = requests.get(_url)
    r.raise_for_status()

    return r.json()["displayedMark"] if r.json().get("displayedMark") else None


#
# Get an email template's report url
#

def get_email_template_report(template_id: str) -> str:
    return MAIL_TESTER__REPORT_URL \
            .format(MAIL_TESTER__USER,
                    template_id,
                    ReportType.dbug)
