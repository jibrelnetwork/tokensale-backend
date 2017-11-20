from django.contrib import admin

from jco.api.models import Account, Transaction, Jnt


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ['id', 'username', 'first_name', 'last_name']
    # readonly_fields = ['status']

    # def get_urls(self):
    #     urls = super().get_urls()
    #     my_urls = [
    #         url(r'^restart_manager/$', self.restart_manager, name="restart_manager"),
    #     ]
    #     return my_urls + urls

    # def restart_manager(self, request):
    #     if request.method != 'POST':
    #         return HttpResponse('HTTP Method Not Allowed', status=403)

    #     server = xmlrpc.client.ServerProxy("http://localhost:9001/RPC2")
    #     try:
    #         server.supervisor.stopProcess('apm_service')
    #         server.supervisor.startProcess('apm_service')
    #         info = server.supervisor.getProcessInfo('apm_service')
    #     except Exception as e:
    #         return HttpResponse("Error: " + str(e))
    #     return HttpResponse(str(info))
    def username(self, obj):
        return obj.user.username


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'value', 'mined', 'address']


# @admin.register(Jnt)
# class TransactionAdmin(admin.ModelAdmin):
#     list_display = ['transaction_id', 'value', 'mined', 'address']
