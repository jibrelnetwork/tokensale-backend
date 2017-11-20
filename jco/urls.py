"""jpo URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.11/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.conf.urls import url, include
    2. Add a URL to urlpatterns:  url(r'^blog/', include('blog.urls'))
"""
from django.conf import settings
from django.conf.urls import url, include
from django.contrib import admin
from django.views.generic import TemplateView, RedirectView


from allauth.account.views import ConfirmEmailView
from rest_framework.documentation import include_docs_urls
from rest_framework.permissions import AllowAny


urlpatterns = [
    url(r'^admin/', admin.site.urls),

    url(r'^docs/', include_docs_urls(title='JCO API', permission_classes=[AllowAny])),

    url(r'^auth/registration/account-confirm-email/(?P<key>[-:\w]+)/$', ConfirmEmailView.as_view(),
    name='account_confirm_email'),
    url(r'^auth/', include('rest_auth.urls')),
    url(r'^auth/registration/', include('rest_auth.registration.urls')),
    url(r'^api/', include('jco.api.urls')),

    url(r'^password-reset/confirm/$',
        TemplateView.as_view(template_name="registration/password_reset_confirm.html"),
        name='password-reset-confirm'),
    url(r'^password-reset-confirm/$',
        TemplateView.as_view(template_name="registration/password_reset_confirm.html"),
        name='password_reset_confirm'),
    url(r'^account_email_verification_sent/$',
        TemplateView.as_view(template_name="registration/password_reset_confirm.html"),
        name='account_email_verification_sent'),
]


if settings.DEBUG:
    from django.conf.urls.static import static
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
