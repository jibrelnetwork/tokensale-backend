import logging
import sys
import traceback
from typing import Tuple, Dict, Any

import requests
from flask import request
from flask_restful import reqparse
from flask_restful import Resource
from flask_restful import fields
from flask_restful import marshal_with
from validate_email import validate_email
from celery.exceptions import TimeoutError

from jco.commonconfig.config import RECAPTCHA__SECRET__KEY, RECAPTCHA__VERIFY__ENABLED
from jco.appdb.models import CurrencyType


address_fields = {
    'error': fields.Boolean,
    'address': fields.String,
}


def email_field(email_str):
    if validate_email(email_str):
        return email_str
    else:
        raise ValueError('{} is not a valid email'.format(email_str))


def currency_field(currency_str):
    if currency_str in [CurrencyType.btc, CurrencyType.eth]:
        return currency_str
    else:
        raise ValueError('{} is not a valid currency'.format(currency_str))


parser = reqparse.RequestParser()
parser.add_argument('fullname', dest='fullname', location='json', required=True)
parser.add_argument('email', dest='email', type=email_field, location='json', required=True)
parser.add_argument('country', dest='country', location='json', required=True)
parser.add_argument('citizenship', dest='citizenship', location='json', required=True)
parser.add_argument('currency', dest='currency', type=currency_field, location='json', required=True)
parser.add_argument('amount', dest='amount', type=float, location='json', required=True)
parser.add_argument('reference_id', dest='reference_id', location='json', required=False)


def get_client_ip(request) -> str:
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def recaptcha_verify(request) -> Tuple[bool, str]:
    data = request.POST
    captcha_rs = data.get('g-recaptcha-response')
    url = "https://www.google.com/recaptcha/api/siteverify"
    params = {
        'secret': RECAPTCHA__SECRET__KEY,
        'response': captcha_rs,
        'remoteip': get_client_ip(request)
    }
    verify_rs = requests.get(url, params=params, verify=True)
    verify_rs = verify_rs.json()

    is_success = verify_rs.get("success", False)
    message = verify_rs.get('error-codes', None) or "An error occurred"

    return is_success, message


class ProposalResource(Resource):
    @marshal_with(address_fields)
    def post(self) -> Tuple[Dict[str, Any], int]:
        from celery_tasks import celery_add_proposal

        if RECAPTCHA__VERIFY__ENABLED:
            is_success, message = recaptcha_verify(request)
            if not is_success:
                return {'address': '', 'error': True}, 400

        parsed_args = parser.parse_args()
        task = celery_add_proposal.delay(parsed_args['fullname'],
                                         parsed_args['email'],
                                         parsed_args['country'],
                                         parsed_args['citizenship'],
                                         parsed_args['currency'],
                                         parsed_args['amount'],
                                         parsed_args['reference_id'] if ('reference_id' in parsed_args) else None)
        try:
            result = task.get(timeout=10)
            is_success = result[0]
            address_str = result[1]
        except TimeoutError:
            exception_str = ''.join(traceback.format_exception(*sys.exc_info()))
            logging.getLogger(__name__).error("ailed to persist new investment request due to error:\n{}"
                                              .format(exception_str))
            is_success = False
            address_str = ''

        address = address_str if is_success else ""
        return_code = 201 if is_success else 400

        return {'address': address, 'error': not is_success}, return_code
