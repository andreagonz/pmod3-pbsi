from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from .forms import UrlsForm, MensajeForm, ProxyForm
from .models import Url
from .phishing import almacena_urls
from .correo import genera_mensaje, manda_correo

@login_required(login_url=reverse_lazy('login'))
def monitoreo(request):
    urls = Url.objects.filter(reportado=False, codigo__lt=300, codigo__gte=200).order_by('-timestamp')
    url = None
    if len(urls) > 0:
        url = urls[0]
    mensaje_form = MensajeForm()
    proxy_form = ProxyForm()
    if request.method == 'POST' and not url is None:
        if request.POST.get('boton-curl'):
            proxy_form = ProxyForm(request.POST)
            if proxy_form.is_valid():
                servidor = proxy_form.cleaned_data['servidor']
                puerto = proxy_form.cleaned_data['puerto']
                tor = proxy_form.cleaned_data['tor']
                proxy = None
                if tor:
                    proxy = {'http':  'socks5://127.0.0.1:9050', 'https': 'socks5://127.0.0.1:9050'}
                almacena_urls([url.url], proxy)
        elif request.POST.get('boton-mensaje'):
            mensaje_form = MensajeForm(request.POST)
            if mensaje_form.is_valid():
                de = mensaje_form.cleaned_data['de']
                para = mensaje_form.cleaned_data['para']
                mensaje_form = MensajeForm(request.POST)
                msg = genera_mensaje(url, de, para)
                manda_correo(para, msg)
                url.reportado = True
                url.save()
    context = {
        'url': url,
        'mensaje_form': mensaje_form,
        'proxy_form': proxy_form
    }
    return render(request, 'monitoreo.html', context)

@login_required(login_url=reverse_lazy('login'))
def valida_urls(request):
    if request.method == 'POST':
        form = UrlsForm(request.POST)
        if form.is_valid():
            urls = form.cleaned_data['urls']
            almacena_urls([x.strip() for x in urls.split('\n') if x.strip()], None)
            # return redirect('post_detail', pk=post.pk)
    else:
        form = UrlsForm()
    return render(request, 'valida_urls.html', {'form': form})
