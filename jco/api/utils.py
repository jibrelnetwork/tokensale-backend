from allauth.account.adapter import DefaultAccountAdapter, build_absolute_uri
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.sites.shortcuts import get_current_site

from jco.appprocessor.notify import send_email_verify_email


class AccountAdapter(DefaultAccountAdapter):

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Constructs the email confirmation (activation) url.
        Note that if you have architected your system such that email
        confirmations are sent outside of the request context `request`
        can be `None` here.
        """
        return build_absolute_uri(None, '/') + '#/welcome/email/pending/' + emailconfirmation.key

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        current_site = get_current_site(request)
        activate_url = self.get_email_confirmation_url(
            request,
            emailconfirmation)
        # ctx = {
        #     "user": emailconfirmation.email_address.user,
        #     "activate_url": activate_url,
        #     "current_site": current_site,
        #     "key": emailconfirmation.key,
        # }

        send_email_verify_email(
            emailconfirmation.email_address.email,
            activate_url,
            emailconfirmation.email_address.user.pk
            )
