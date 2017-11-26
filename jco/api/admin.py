from django.contrib import admin

from django.utils.html import format_html
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404
from django.conf.urls import url
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.utils.safestring import mark_safe


from jco.api.models import Address, Account, Transaction, Jnt, Withdraw


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'first_name', 'last_name', 'document_url',
                    'onfido_applicant_id', 'onfido_check_id', 'onfido_check_created',
                    'onfido_check_status', 'onfido_check_result',
                    'is_identity_verified', 'is_identity_verification_declined', 'account_actions']

    def username(self, obj):
        return obj.user.username

    def changelist_view(self, request, extra_context=None):
        self.request = request
        return super(AccountAdmin, self).changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            url(
                r'^(?P<account_id>.+)/reset/$',
                self.admin_site.admin_view(self.reset_identity_verification),
                name='account-reset',
            ),
            url(
                r'^(?P<account_id>.+)/approve/$',
                self.admin_site.admin_view(self.approve_identity_verification),
                name='account-approve',
            ),
            url(
                r'^(?P<account_id>.+)/decline/$',
                self.admin_site.admin_view(self.decline_identity_verification),
                name='account-decline',
            ),
        ]
        return custom_urls + urls

    def account_actions(self, obj):
        return format_html(
            '<form></form><form method="post" action="{}"><input type="hidden" name="csrfmiddlewaretoken" value="{token}"><button class="button">Reset</button></form>&nbsp;'
            '<form method="post" action="{}"><input type="hidden" name="csrfmiddlewaretoken" value="{token}"><button class="button">Approve</button></form>&nbsp;'
            '<form method="post" action="{}"><input type="hidden" name="csrfmiddlewaretoken" value="{token}"><button class="button">Decline</button></form>&nbsp;',
            reverse('admin:account-reset', args=[obj.pk]),
            reverse('admin:account-approve', args=[obj.pk]),
            reverse('admin:account-decline', args=[obj.pk]),
            token=get_token(self.request)
        )
    account_actions.short_description = 'Account Actions'
    account_actions.allow_tags = True

    def reset_identity_verification(self, request, account_id, *args, **kwargs):
        account = get_object_or_404(Account, pk=account_id)
        account.reset_verification_state()
        messages.success(request,
                         mark_safe('Verification Status <b>Reset Done</b> for <{}>'.format(account.user.username)))
        return redirect('admin:api_account_changelist')

    def approve_identity_verification(self, request, account_id, *args, **kwargs):
        account = get_object_or_404(Account, pk=account_id)
        account.approve_verification()
        messages.success(request,
                         mark_safe('Verification Status <b>Approved</b> for <{}>'.format(account.user.username)),
                         extra_tags='safe')
        return redirect('admin:api_account_changelist')

    def decline_identity_verification(self, request, account_id, *args, **kwargs):
        account = get_object_or_404(Account, pk=account_id)
        account.decline_verification()
        messages.success(request,
                         mark_safe('Verification Status <b>Declined</b> for <{}>'.format(account.user.username)),
                         extra_tags='safe')
        return redirect('admin:api_account_changelist')


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'value', 'mined', 'address']


@admin.register(Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'value', 'mined', 'address']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['address', 'type', 'is_usable', 'user']


@admin.register(Jnt)
class JntAdmin(admin.ModelAdmin):
    list_display = ['purchase_id', 'currency_to_usd_rate', 'usd_value',
                    'jnt_to_usd_rate', 'jnt_value', 'active', 'created']

