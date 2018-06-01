from django.urls import path
from .views import monitoreo

urlpatterns = [
    path('monitoreo', monitoreo, name='monitoreo'),
]
