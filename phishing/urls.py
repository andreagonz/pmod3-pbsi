from django.urls import path
from .views import monitoreo, valida_urls, busca, monitoreo_id, url_detalle

urlpatterns = [
    path('monitoreo', monitoreo, name='monitoreo'),
    path('monitoreo/<int:pk>', monitoreo_id, name='monitoreo-id'),
    path('valida-urls', valida_urls, name='valida-urls'),
    path('url/<int:pk>', url_detalle, name='url-detalle'),
]
