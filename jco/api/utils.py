from allauth.account.adapter import DefaultAccountAdapter, build_absolute_uri


class AccountAdapter(DefaultAccountAdapter):

    def get_email_confirmation_url(self, request, emailconfirmation):
        """Constructs the email confirmation (activation) url.
        Note that if you have architected your system such that email
        confirmations are sent outside of the request context `request`
        can be `None` here.
        """
        return build_absolute_uri(None, '/') + '#/welcome/email/pending/' + emailconfirmation.key