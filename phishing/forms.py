from django import forms

class UrlsForm(forms.Form):
    urls = forms.CharField(label='URLs', widget=forms.Textarea)

class ProxyForm(forms.Form):
    servidor = forms.CharField(label='Servidor', required=False)
    puerto = forms.IntegerField(label='Puerto', required=False)
    tor = forms.BooleanField(label='Tor', required=False)
    
class MensajeForm(forms.Form):
    para = forms.CharField(label='Para')
    de = forms.CharField(label='De')
    asunto = forms.CharField(label='Asunto')
    mensaje = forms.CharField(label='Mensaje', widget=forms.Textarea)

class Search(forms.Form):
	search=forms.CharField(max_length=500,required=True)
