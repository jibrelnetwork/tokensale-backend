import logging
from django.contrib import admin

from django.utils.html import format_html
from django.core.urlresolvers import reverse
from django.shortcuts import redirect, get_object_or_404, render
from django.utils.crypto import get_random_string
from django.conf.urls import url
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.utils.safestring import mark_safe
from django.http import HttpResponse
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils import timezone


from rest_framework.authtoken.models import Token
from allauth.account.models import EmailAddress

from jco.api.models import (
    Address,
    Account,
    Document,
    Jnt,
    Operation,
    PresaleJnt,
    Transaction,
    UserJntPrice,
    Withdraw,
)

from jco.api import tasks
from jco.api import serializers
from jco.commonutils import ga_integration


logger = logging.getLogger(__name__)

# Globally disable delete selected
admin.site.disable_action('delete_selected')


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


class ReadonlyMixin:
    """
    Readonly view for non-superusers
    """

    def get_readonly_fields(self, request, obj=None):
        if request.user.is_superuser is False:
            fields = [f.name for f in self.model._meta.fields]
            return fields
        return self.readonly_fields

    def save_model(self, request, obj, form, change):
        if request.user.is_superuser is False:
            self.message_user(request, "Saving not allowed")
            return False
        else:
            super().save_model(request, obj, form, change)


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

    actions = ['action_reset_password']

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
        logger.info('Manual Identity verification status reset for %s', account.user.username)
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
        logger.info('Manual Identity approve for %s', account.user.username)
        ga_integration.on_status_verified_manual(account)
        messages.success(request,
                         mark_safe('Verification Status <b>Approved</b> for {}'.format(account.user.username)),
                         extra_tags='safe')
        return HttpResponse('OK')

    def decline_identity_verification(self, request, account_id, *args, **kwargs):
        account = get_object_or_404(Account, pk=account_id)
        logger.info('Manual Identity decline for %s', account.user.username)
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

    def action_reset_password(self, request, queryset):
        accounts = queryset.all()
        for account in accounts:
            logger.info('Manual reset password for %s.', account.user.username)
            account.user.set_password(get_random_string(12))  # set unusable password
            account.user.save()
            serializer = serializers.CustomPasswordResetSerializer(
                data={'email': account.user.username}, context={'request': request})
            serializer.is_valid()
            serializer.save()
            logger.info('Manual reset password for %s complete.', account.user.username)

        usernames = ', '.join([a.user.username for a in accounts])
        self.message_user(request, "Users {}: passwords is dropped, change password emails is sent.".format(usernames))


@admin.register(Transaction)
class TransactionAdmin(ReadonlyMixin, admin.ModelAdmin):
    list_display = ['transaction_id', 'value', 'mined', 'address', 'account_link']
    raw_id_fields = ("address",)
    search_fields = ['address__user__username', 'address__address',
                     'transaction_id']
    list_select_related = ('address__user__account',)

    def account_link(self, obj):
        if obj.address and obj.address.user and obj.address.user.account:
            html = '<a href="{url}">{username}</>'
            url = reverse('admin:api_account_change', args=(obj.address.user.account.pk,))
            username = obj.address.user.username
            return html.format(url=url, username=username)
        else:
            return ''
    account_link.allow_tags = True


@admin.register(Withdraw)
class WithdrawAdmin(ReadonlyMixin, admin.ModelAdmin):
    list_display = ['id', 'transaction_id', 'to', 'value', 'created', 'status', 'account_link']
    search_fields = ['transaction_id', 'to', 'user__username']
    list_select_related = ('user__account',)
    list_filter = ['status']
    list_display_links = None

    def account_link(self, obj):
        html = '<a href="{url}">{username}</>'
        url = reverse('admin:api_account_change', args=(obj.user.account.pk,))
        username = obj.user.username
        return html.format(url=url, username=username)
    account_link.allow_tags = True


@admin.register(Address)
class AddressAdmin(ReadonlyMixin, admin.ModelAdmin):
    list_display = ['address', 'type', 'is_usable', 'account_link']
    search_fields = ['user__username', 'address']
    list_select_related = ('user__account',)

    def account_link(self, obj):
        if obj.user is None:
            return ''
        html = '<a href="{url}">{username}</>'
        url = reverse('admin:api_account_change', args=(obj.user.account.pk,))
        username = obj.user.username
        return html.format(url=url, username=username)
    account_link.allow_tags = True


@admin.register(Jnt)
class JntAdmin(ReadonlyMixin, admin.ModelAdmin):
    list_display = ['jnt_value', 'currency_to_usd_rate', 'usd_value',
                    'jnt_to_usd_rate', 'created', 'account_link', 'address_link']

    list_select_related = ('transaction__address__user__account',)
    search_fields = ['transaction__address__user__username', 'transaction__address__address',
                     'transaction__transaction_id']

    readonly_fields = ['jnt_value', 'currency_to_usd_rate', 'usd_value', 'active', 'created',
                       'transaction', 'meta']

    def account_link(self, obj):
        html = '<a href="{url}">{username}</>'
        url = reverse('admin:api_account_change', args=(obj.transaction.address.user.account.pk,))
        username = obj.transaction.address.user.username
        return html.format(url=url, username=username)
    account_link.allow_tags = True

    def address_link(self, obj):
        html = '<a href="{url}">{address}</>'
        url = reverse('admin:api_address_change', args=(obj.transaction.address.pk,))
        address = obj.transaction.address.address
        return html.format(url=url, address=address)
    address_link.allow_tags = True

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.jnt_value = obj.usd_value / obj.jnt_to_usd_rate
        super().save_model(request, obj, form, change)


@admin.register(Operation)
class OperationAdmin(ReadonlyMixin, admin.ModelAdmin):
    search_fields = ['user__username', 'key']
    list_display = ['user', 'operation', 'params', 'created_at', 'confirmed_at']
    actions = ['confirm_operation']

    def confirm_operation(self, request, queryset):
        operations = queryset.all()
        for op in operations:
            logger.info('Manual operation confirmation for %s, operation #%s %s', op.user.username, op.pk)
            op.perform(op.key)
            logger.info('Manual operation confirmation for %s, operation #%s %s complete.',
                        op.user.username, op.pk, op.operation)
        op_names = ', '.join(['{}: {}'.format(op.user.username, op.operation) for op in operations])
        self.message_user(request, "Operations {} was confirmed".format(op_names))


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['user', 'image']
    search_fields = ['user__username']


@admin.register(PresaleJnt)
class PresaleJntAdmin(admin.ModelAdmin):
    list_display = ['user', 'jnt_value', 'currency_to_usd_rate', 'usd_value', 'created', 'comment', 'is_sale_allocation']
    search_fields = ['user__username']
    exclude = ['created', 'is_presale_round']

    def save_model(self, request, obj, form, change):
        """
        Given a model instance save it to the database.
        """
        obj.created = timezone.now()
        obj.is_presale_round = False
        super().save_model(request, obj, form, change)


@admin.register(UserJntPrice)
class UserJntPriceAdmin(admin.ModelAdmin):
    list_display = ['pk', 'user', 'value', 'created_at']
    search_fields = ['user__username']


admin.site.unregister(EmailAddress)


@admin.register(EmailAddress)
class EmailAddress(ReadonlyMixin, admin.ModelAdmin):
    list_display = ['user', 'email', 'verified']
    search_fields = ['email']

    actions = ['verify']

    def verify(self, request, queryset):
        emails = queryset.all()
        for email in emails:
            logger.info('Manual email varification %s', email.email)
            email.verified = True
            email.save()
        op_names = ', '.join([em.email for em in emails])
        self.message_user(request, "Emails {} was marked as verified".format(op_names))
