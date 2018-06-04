from django import forms
from .models import Proxy
from django.forms.widgets import SelectDateWidget
from django.utils import timezone

class UrlsForm(forms.Form):
    urls = forms.CharField(label='URLs', widget=forms.Textarea)

class ProxyForm(forms.Form):
    http = forms.URLField(label='HTTP', required=False)
    https = forms.URLField(label='HTTPS', required=False)
    tor = forms.BooleanField(label='Tor', required=False)
    proxy = forms.ModelChoiceField(label='Proxies', queryset=Proxy.objects.all(),
                                   empty_label="Ninguno", required=False)
    
class MensajeForm(forms.Form):
    para = forms.CharField(label='Para')
    de = forms.CharField(label='De')
    asunto = forms.CharField(label='Asunto')
    mensaje = forms.CharField(label='Mensaje', widget=forms.Textarea)

class Search(forms.Form):
    search=forms.CharField(max_length=500,required=True)

class HistoricoForm(forms.Form):
    inicio = forms.DateField(widget=SelectDateWidget
                                 (years=range(timezone.now().year - 10, timezone.now().year + 1)))
    fin = forms.DateField(widget=SelectDateWidget
                              (years=range(timezone.now().year - 10, timezone.now().year + 1)))
