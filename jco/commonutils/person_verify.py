from __future__ import print_function
import time
import onfido
from onfido.rest import ApiException
from pprint import pprint
import requests
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model


def example():
    # Configure API key authorization: Token
    onfido.configuration.api_key['Authorization'] = 'token=' + 'YOUR_API_KEY'
    onfido.configuration.api_key_prefix['Authorization'] = 'Token'
    # create an instance of the API class
    api_instance = onfido.DefaultApi()

    # setting applicant details
    applicant = onfido.Applicant()
    applicant.first_name = 'John'
    applicant.last_name = 'Smith'
    applicant.dob = datetime.date(1980, 1, 22)
    applicant.country = 'GBR'

    address = onfido.Address()
    address.building_number = '100'
    address.street = 'Main Street'
    address.town = 'London'
    address.postcode = 'SW4 6EH'
    address.country = 'GBR'

    applicant.addresses = [address];

    # setting check request details
    check = onfido.CheckCreationRequest()
    check.type = 'express'

    report = onfido.Report()
    report.name = 'identity'

    check.reports = [report];

    try: 
        # Create Applicant
        api_response = api_instance.create_applicant(data=applicant)
        applicant_id = api_response.id
        api_response = api_instance.create_check(applicant_id, data=check)
        pprint(api_response)
    except ApiException as e:
        pprint(e.body)


def get_client(api_key=None):
    api_key = api_key or settings.ONFIDO_API_KEY
    onfido.configuration.api_key['Authorization'] = 'token=' + api_key
    onfido.configuration.api_key_prefix['Authorization'] = 'Token'
    # create an instance of the API class
    api = onfido.DefaultApi()
    return api


def create_applicant(user_id):
    user = get_user_model().objects.get(pk=user_id)
    
    address = onfido.Address(
        country=user.account.country,
        town=user.account.town,
        street=user.account.street,
        postcode=user.account.postcode,
    )
    
    details = {
        'first_name': user.account.first_name,
        'last_name': user.account.last_name,
        'email': user.email,
        'dob': user.account.date_of_birth,
        'addresses': [address]
    }
    applicant = onfido.Applicant(**details)

    api = get_client()
    resp = api.create_applicant(data=applicant)
    return resp.id


def create_check(applicant_id):
    onfido.Report(name='identity'), 

    reports = [
        onfido.Report(name='document'),
        # onfido.Rep        ort(name='watchlist', variant='full'),
    ]

    check = onfido.CheckCreationRequest(
        type='express',
        reports=reports
    )
    
    api = get_client()
    resp = api.create_check(applicant_id, data=check)
    return resp.id


def upload_document(applicant_id, document_url):
    api = get_client()
    resp = requests.get(document_url)
    if resp.status_code != 200:
        raise RuntimeError("Can't get document file {} for applicant {}".format(
                           document_url, applicant_id))
    with tempfile.NamedTemporaryFile(suffix='.jpg') as fp:
        fp.write(resp.content)
        resp = api.upload_document(applicant_id, file=fp.name, type='passport')
        return resp.id


