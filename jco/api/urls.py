
from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin

from jco.api import views

urlpatterns = [
    # url(r'^admin/', admin.site.urls),

    # url(r'^rest-auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$', ConfirmEmailView.as_view(),
    # name='account_confirm_email'),
    # url(r'^rest-auth/', include('rest_auth.urls')),
    # url(r'^rest-auth/registration/', include('rest_auth.registration.urls')),
    url(r'^transactions/', views.TransactionsListView.as_view()),
    url(r'^account/', views.AccountView.as_view()),
    url(r'^raised-tokens/', views.RaisedTokensView.as_view()),

    url(r'^withdraw-address/$', views.EthAddressView.as_view()),
    url(r'^withdraw-address/confirm/', views.ChangeAddressConfirmView.as_view()),

    url(r'^document/', views.DocumentView.as_view()),
    
    url(r'^withdraw-jnt/$', views.WithdrawRequestView.as_view()),
    url(r'^withdraw-jnt/confirm/', views.WithdrawConfirmView.as_view()),
]
