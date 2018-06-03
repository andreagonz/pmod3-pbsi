from django.urls import path
from .views import monitoreo, valida_urls, busca

urlpatterns = [
    path('monitoreo', monitoreo, name='monitoreo'),
    path('valida-urls', valida_urls, name='valida-urls'),
]
