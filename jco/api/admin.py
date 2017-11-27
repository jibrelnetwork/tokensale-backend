from django.contrib import admin

from django.utils.html import format_html
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404, render
from django.conf.urls import url
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.utils.safestring import mark_safe

from rest_framework.authtoken.models import Token

from jco.api.models import Address, Account, Transaction, Jnt, Withdraw


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'first_name', 'last_name', 'document_thumb',
                    'onfido_check_status',
                    'is_identity_verified', 'is_identity_verification_declined', 'account_actions']

    list_filter = ['is_identity_verified', 'is_identity_verification_declined',
                   'onfido_check_status']

    search_fields = ['user__username', 'first_name', 'last_name']

    def username(self, obj):
        return obj.user.username

    def changelist_view(self, request, extra_context=None):
        self.request = request
        return super(AccountAdmin, self).changelist_view(request, extra_context=extra_context)

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            # url(
            #     r'^(?P<account_id>.+)/reset/$',
            #     self.admin_site.admin_view(self.reset_identity_verification),
            #     name='account-reset',
            # ),
            # url(
            #     r'^(?P<account_id>.+)/approve/$',
            #     self.admin_site.admin_view(self.approve_identity_verification),
            #     name='account-approve',
            # ),
            # url(
            #     r'^(?P<account_id>.+)/decline/$',
            #     self.admin_site.admin_view(self.decline_identity_verification),
            #     name='account-decline',
            # ),
            url(
                r'^(?P<account_id>.+)/action/$',
                self.admin_site.admin_view(self.account_action),
                name='account-action',
            ),
        ]
        return custom_urls + urls

    def document_thumb(self, obj):
        if not obj.document_url:
            return ''
        if obj.document_type in ('jpg', 'jpeg', 'png'):
            return format_html('<a href="{src}"><img src="{src}" height="30"/></a>', src=obj.document_url)
        else:
            return obj.document_url
    document_thumb.short_description = 'Passport'
    document_thumb.allow_tags = True

    def account_actions(self, obj):
        return format_html(
            '<a class="button" href="{url}?action=reset">Reset</a>&nbsp;'
            '<a class="button" href="{url}?action=approve">Approve</a>&nbsp;'
            '<a class="button" href="{url}?action=decline">Decline</a>&nbsp;',
            url=reverse('admin:account-action', args=[obj.pk]))

    account_actions.short_description = 'Account Actions'
    account_actions.allow_tags = True

    def reset_identity_verification(self, request, account_id, *args, **kwargs):
        account = get_object_or_404(Account, pk=account_id)
        account.reset_verification_state()
        Token.objects.filter(user=account.user).delete()
        messages.success(request,
                         mark_safe('Verification Status <b>Reset Done</b> for <{}>'.format(account.user.username)))
        return redirect('admin:api_account_changelist')

    def account_action(self, request, account_id, *args, **kwargs):
        # account.reset_verification_state()
        # Token.objects.filter(user=account.user).delete()
        # messages.success(request,
        #                  mark_safe('Verification Status <b>Reset Done</b> for <{}>'.format(account.user.username)))
        # return redirect('admin:api_account_changelist')
        # print('NNNNNNNNNNNNNNNNNNN', self.app_l)
        if request.method == 'POST' and request.POST.get('confirm'):
            action = request.POST.get('action')
            if action == 'reset':
                return self.reset_identity_verification(request, account_id)
            elif action == 'approve':
                return self.approve_identity_verification(request, account_id)
            elif action == 'decline':
                return self.decline_identity_verification(request, account_id)
        else:
            account = get_object_or_404(Account, pk=account_id)
            action = request.GET.get('action')
            return render(request, 'account_action_confirm.html', {'action': action, 'account': account, 'opts': account._meta})

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

