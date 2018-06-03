"""phishmon URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from .views import home
from django.contrib.auth import views as auth_views
from django.conf.urls.static import static
from django.conf import settings
from phishing.views import home, busca, monitoreo, valida_urls

urlpatterns = [
    path('', home, name='home'),
    path('admin/', admin.site.urls),
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.logout_then_login, name='logout'),
    # path('homeBusca/', home),
    path('buscar/', busca),
    path('monitoreo/', monitoreo, name='monitoreo'),
    path('valida-urls/', valida_urls, name='valida-urls'),
    # path('seccion/', include('phishing.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
