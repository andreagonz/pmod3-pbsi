from django.urls import path
from .views import monitoreo, valida_urls, home, busca

urlpatterns = [
    path('monitoreo', monitoreo, name='monitoreo'),
    path('valida-urls', valida_urls, name='valida-urls'),
]
