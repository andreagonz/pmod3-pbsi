from django.urls import path
from .views import monitoreo, valida_urls

urlpatterns = [
    path('monitoreo', monitoreo, name='monitoreo'),
    path('valida-urls', valida_urls, name='valida-urls'),
]
