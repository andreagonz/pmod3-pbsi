from django.urls import path
from .views import monitoreo, valida_urls, busca, monitoreo_id

urlpatterns = [
    path('monitoreo', monitoreo, name='monitoreo'),
    path('monitoreo/<int:pk>', monitoreo_id, name='monitoreo-id'),
    path('valida-urls', valida_urls, name='valida-urls'),
]
