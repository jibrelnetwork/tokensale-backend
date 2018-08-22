import csv
import io
import zipfile

from allauth.account.adapter import DefaultAccountAdapter, build_absolute_uri
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site
from django.contrib.auth import get_user_model

from jco.appprocessor.notify import send_email_verify_email
from jco.api.models import Address, Account, Token, PresaleToken, Transaction


class AccountAdapter(DefaultAccountAdapter):

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Constructs the email confirmation (activation) url.
        Note that if you have architected your system such that email
        confirmations are sent outside of the request context `request`
        can be `None` here.
        """
        return build_absolute_uri(None, '/') + '#/welcome/email/pending/' + emailconfirmation.key

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        activate_url = self.get_email_confirmation_url(
            request,
            emailconfirmation)

        send_email_verify_email(
            emailconfirmation.email_address.email,
            activate_url,
            emailconfirmation.email_address.user.pk
        )


def export_data_to_csv():
    """
    SELECT id, username, is_active, date_joined, last_login FROM auth_user ORDER BY id
    SELECT * FROM address WHERE user_id is not null ORDER BY id
    SELECT * FROM transaction ORDER BY id
    SELECT * FROM "TOKEN" ORDER BY id
    SELECT * FROM presale_token ORDER BY id
    SELECT * FROM account ORDER BY id
    """
    filename = '/tmp/data_export.zip'
    users = get_user_model().objects.filter(is_staff=False, is_superuser=False).order_by('id')
    addresses = Address.objects.exclude(user=None).order_by('id')
    transactions = Transaction.objects.order_by('id')
    token_tokens = Token.objects.order_by('id')
    presale_token = PresaleToken.objects.order_by('id')
    accounts = Account.objects.order_by('id')

    zip_file = zipfile.ZipFile(filename, 'w', zipfile.ZIP_DEFLATED)

    user_fields = ['id', 'username', 'is_active', 'date_joined', 'last_login']
    zip_file.writestr('users.csv', export_queryset(users, user_fields).getvalue())
    zip_file.writestr('addresses.csv', export_queryset(addresses).getvalue())
    zip_file.writestr('transactions.csv', export_queryset(transactions).getvalue())
    zip_file.writestr('token_tokens.csv', export_queryset(token_tokens).getvalue())
    zip_file.writestr('presale_token.csv', export_queryset(presale_token).getvalue())
    zip_file.writestr('accounts.csv', export_queryset(accounts).getvalue())

    zip_file.close()
    return filename


def export_queryset(qs, fields=None):
    field_names = fields or [f.name for f in qs.model._meta.fields]
    string_buffer = io.StringIO()
    writer = csv.DictWriter(string_buffer, fieldnames=field_names)
    writer.writeheader()
    for row in qs.values(*field_names):
        writer.writerow(row)
    string_buffer.seek(0)
    return string_buffer
