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
from django.http import HttpResponse
from django.contrib.admin import SimpleListFilter

from rest_framework.authtoken.models import Token

from jco.api.models import Address, Account, Transaction, Jnt, Withdraw, Operation, Document
from jco.api import tasks
from jco.commonutils import ga_integration



class FioFilledListFilter(SimpleListFilter):
    # Human-readable title which will be displayed in the
    # right admin sidebar just above the filter options.
    title = 'Form filled'

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'filled'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('true', 'Filled'),
            ('false', 'Not Filled'),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Compare the requested value (either '80s' or '90s')
        # to decide how to filter the queryset.
        if self.value() == 'true':
            return queryset.exclude(first_name='',
                                    last_name='')
        elif self.value() == 'false':
            return queryset.filter(first_name='',
                                   last_name='')
        else:
            return queryset


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'first_name', 'last_name', 'document_thumb',
                    'onfido_check_status',
                    'is_identity_verified', 'is_identity_verification_declined', 'account_actions']

    list_filter = ['is_identity_verified', 'is_identity_verification_declined',
                   'onfido_check_status', FioFilledListFilter]

    search_fields = ['user__username', 'first_name', 'last_name']
    exclude = ['town', 'postcode', 'street', 'notified',]
    readonly_fields = ['user', 'onfido_check_status', 'onfido_check_result',
                        'onfido_check_id', 'onfido_check_created',
                        'onfido_document_id', 'onfido_applicant_id',
                        'withdraw_address', 'tracking']

    class Media:
        js = ['https://static.filestackapi.com/v3/filestack.js', 'api/account.js']

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
            '<a class="button account-action" href="javascript:void(0)" data-url="{url}?action=reset" data-action="reset">Reset</a>&nbsp;'
            '<a class="button account-action" href="javascript:void(0)" data-url="{url}?action=approve" data-action="approve">Approve</a>&nbsp;'
            '<a class="button account-action" href="javascript:void(0)" data-url="{url}?action=decline" data-action="decline">Decline</a>&nbsp;',
            url=reverse('admin:account-action', args=[obj.pk]))

    account_actions.short_description = 'Account Actions'
    account_actions.allow_tags = True

    def reset_identity_verification(self, request, account_id, *args, **kwargs):
        account = get_object_or_404(Account, pk=account_id)
        account.reset_verification_state()
        Token.objects.filter(user=account.user).delete()
        messages.success(request,
                         mark_safe('Verification Status <b>Reset Done</b> for {}'.format(account.user.username)))
        return HttpResponse('OK')

    def account_action(self, request, account_id, *args, **kwargs):

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
        ga_integration.on_status_verified_manual(account)
        messages.success(request,
                         mark_safe('Verification Status <b>Approved</b> for {}'.format(account.user.username)),
                         extra_tags='safe')
        return HttpResponse('OK')

    def decline_identity_verification(self, request, account_id, *args, **kwargs):
        account = get_object_or_404(Account, pk=account_id)
        account.decline_verification()
        ga_integration.on_status_not_verified_manual(account)
        messages.success(request,
                         mark_safe('Verification Status <b>Declined</b> for {}'.format(account.user.username)),
                         extra_tags='safe')
        return HttpResponse('OK')

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.save()
        if '_reverify' in request.POST:
            obj.reset_verification_state(fullreset=False)
            tasks.verify_user.delay(obj.user.pk)
            messages.success(request,
                 mark_safe('Verification <b>Restarted</b> for <b>{}</b> {}'.format(obj, obj.user.username)))


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'value', 'mined', 'address']
    raw_id_fields = ("address",)


@admin.register(Withdraw)
class WithdrawAdmin(admin.ModelAdmin):
    list_display = ['user', 'transaction_id', 'to', 'value', 'created', 'status']
    search_fields = ['transaction_id', 'to', 'user__username']


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ['address', 'type', 'is_usable', 'user']
    search_fields = ['user__username', 'address']


@admin.register(Jnt)
class JntAdmin(admin.ModelAdmin):
    list_display = ['purchase_id', 'currency_to_usd_rate', 'usd_value',
                    'jnt_to_usd_rate', 'jnt_value', 'active', 'created']


@admin.register(Operation)
class OperationAdmin(admin.ModelAdmin):
    list_display = ['user', 'operation', 'params', 'created_at', 'confirmed_at']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['user', 'image']
    search_fields = ['user__username']
