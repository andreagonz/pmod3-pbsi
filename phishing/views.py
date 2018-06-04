from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from .forms import (
    UrlsForm, MensajeForm, ProxyForm, Search, HistoricoForm,
    CambiaAsuntoForm, CambiaMensajeForm, FrecuenciaForm
)
from .models import Url, Correo, Proxy, Recurso, Ofuscacion, Entidades
from .phishing import (
    verifica_urls, archivo_texto, monitorea_url,
    whois, archivo_comentarios, archivo_hashes, cambia_frecuencia
)
from .correo import (
    genera_mensaje, manda_correo, obten_asunto, obten_mensaje,
    lee_plantilla_asunto, lee_plantilla_mensaje, cambia_asunto, cambia_mensaje
)
from django.views.generic import TemplateView
from django.template import loader
from django.http import HttpResponse, Http404
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
from shutil import copyfile
import os
from .reporte import (
    cuenta_urls, urls_activas, urls_inactivas, urls_redirecciones,
    urls_entidades, urls_titulos, urls_dominios, urls_paises
)
from datetime import timedelta, datetime
from django.utils import timezone
from time import mktime
import time
from django.urls import reverse_lazy
from django.views.generic.edit import UpdateView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin

@login_required(login_url=reverse_lazy('login'))
def monitoreo(request):
    urls = Url.objects.filter(reportado=False, codigo__lt=300, codigo__gte=200).order_by('-timestamp')
    if len(urls) > 0:
        return redirect('monitoreo-id', pk=urls[0].id)
    return render(request, 'monitoreo.html')

def rmimg(img):
    if img is None:
        return
    f = os.path.join(settings.MEDIA_ROOT, img)
    if os.path.exists(f):
        os.remove(f)

def cpimg(img, img2):
    if img is None or img2 is None:
        return
    f = os.path.join(settings.BASE_DIR, img[1:])
    f2 = os.path.join(settings.BASE_DIR, img2[1:])
    if os.path.exists(f):
        copyfile(f, f2)
    
@login_required(login_url=reverse_lazy('login'))
def monitoreo_id(request, pk):
    url = get_object_or_404(Url, pk=pk)
    if url.codigo < 0 or url.codigo >= 300 or url.reportado == True:
        raise Http404()
    mensaje_form = MensajeForm()
    proxy_form = ProxyForm()
    context = {
        'url': url,
        'dominio': url.dominio.captura_url
    }
    if url.captura_url is None:
        captura_old = None
    else:
        captura_old = '%s_monitoreo.png' % url.captura_url[:url.captura_url.rindex('.')]
    if not url is None:
        datos = {
            'de': settings.CORREO_DE,
            'para': ', '.join([x.correo for x in url.correos.all()]),
            'asunto': obten_asunto(url),
            'mensaje': obten_mensaje(url)
        }
        mensaje_form = MensajeForm(initial=datos)
        if request.method == 'POST' and not url is None:
            if request.POST.get('boton-curl'):
                proxy_form = ProxyForm(request.POST)
                if proxy_form.is_valid():
                    http = proxy_form.cleaned_data['http']
                    https = proxy_form.cleaned_data['https']
                    tor = proxy_form.cleaned_data['tor']
                    proxies = proxy_form.cleaned_data['proxy']
                    proxy = None
                    if tor:
                        proxy = {'http':  'socks5://127.0.0.1:9050', 'https': 'socks5://127.0.0.1:9050'}
                    elif http or https:
                        proxy = {}
                        if http:
                            proxy['http'] = http
                        if https:
                            proxy['https'] = https
                    elif not proxies is None and (not proxies.http is None or
                                                  not proxies.http is None):
                        proxy = {}
                        if not proxies.http is None:
                            proxy['http'] = proxies.http
                        if not proxies.https is None:
                            proxy['https'] = proxies.https                    
                    cpimg(url.captura_url, captura_old)
                    old = {
                        'captura_url': captura_old,
                        'url': url.url,
                        'ip': url.ip,
                        'netname': url.netname,
                        'pk': url.pk
                    }
                    context['url'] = old
                    sitio = monitorea_url(url, proxy)
                    context['nuevo'] = sitio
            elif request.POST.get('boton-mensaje'):
                mensaje_form = MensajeForm(request.POST)
                if mensaje_form.is_valid():
                    de = mensaje_form.cleaned_data['de']
                    para = mensaje_form.cleaned_data['para']
                    asunto = mensaje_form.cleaned_data['asunto']
                    mensaje = mensaje_form.cleaned_data['mensaje']
                    mensaje_form = MensajeForm(request.POST)
                    msg = genera_mensaje(url, de, para, asunto, mensaje)
                    manda_correo(para, msg)
                    for x in Url.objects.filter(url=url.url):
                        x.reportado = True
                        x.save()
                    rmimg(captura_old)
                    context = {
                        'url': url,
                        'de': de,
                        'para': para,
                        'asunto': asunto,
                        'mensaje': mensaje,
                        'captura': url.captura_url
                    }
                    return render(request, 'monitoreo_exito.html', context)
            elif request.POST.get('boton-saltar'):
                for x in Url.objects.filter(url=url.url):
                    x.reportado = True
                    x.save()
                return redirect('monitoreo')
            elif request.POST.get('boton-siguiente'):
                return redirect('monitoreo')
    context['mensaje_form'] = mensaje_form
    context['proxy_form'] = proxy_form
    return render(request, 'monitoreo_id.html', context)

def context_reporte(sitios):
    activas = urls_activas(sitios)
    inactivas = urls_inactivas(sitios)
    redirecciones = urls_redirecciones(sitios)
    context = {
        'urls_total': cuenta_urls(sitios),
        'num_urls_activas': len(set([x.url for x in activas])),
        'num_urls_inactivas': len(set([x.url for x in inactivas])),
        'num_urls_redirecciones': len(set([x.url for x in redirecciones])),
        'entidades': urls_entidades(sitios),
        'titulos': urls_titulos(sitios),
        'dominios': urls_dominios(sitios),
        'paises': urls_paises(sitios),
        'activas': activas,
        'inactivas': inactivas,
        'redirecciones': redirecciones
    }
    return context

@login_required(login_url=reverse_lazy('login'))
def valida_urls(request):
    if request.method == 'POST':
        form = UrlsForm(request.POST)
        if form.is_valid():
            urls = form.cleaned_data['urls']
            sitios = verifica_urls([x.strip() for x in urls.split('\n') if x.strip()], None, False)
            context = context_reporte(sitios)
            return render(request, 'reporte_urls.html', context)
    else:
        form = UrlsForm()
    return render(request, 'valida_urls.html', {'form': form})

message2 = ""

@login_required(login_url=reverse_lazy('login'))
def url_detalle(request, pk):
    url = get_object_or_404(Url, pk=pk)
    comentarios = archivo_comentarios(url)
    hashes = archivo_hashes(url)
    wi = whois(url.ip)
    wi_dom = whois(url.dominio.dominio)
    context = {
        'url': url,
        'comentarios': comentarios,
        'hashes': hashes,
        'whois': wi,
        'whois_dominio': wi_dom,
    }
    return render(request, 'url_detalle.html', context)

@login_required(login_url=reverse_lazy('login'))
def busca(request):
	resultados_ip=list()
	resultados_mail=list()
	resultados_dom=list()
	resultados_com=list()
	resultados_hash=list()
	message = "No se encontraron coincidencias"
	message2=""
	if request.method == "POST":
		campoBusqueda= Search(request.POST)
		if campoBusqueda.is_valid():
			match = campoBusqueda.cleaned_data['search']
			template = loader.get_template('results.html')
			query = SearchQuery(match)
			vector = SearchVector('ip')
			qs = Url.objects.annotate(
				search=vector).filter(
				search=query).values('id')
			vector_mail=SearchVector('correo')
			qs_mail = Correo.objects.annotate(
				search=vector_mail).filter(
				search=query).values('id')
			vector_com = SearchVector('comentario')	
			qs_com = Comentario.objects.filter(
				comentario__contains=match).values('url_id','id')
			vector_hash= SearchVector('hash')			
			qs_hash = Hash.objects.annotate(
				search=vector_hash).filter(
				search=query).values('url_id','id')
			#if len(qs)!=0:
			#return redirect('muestraResultados',reg=qs)
			###################################
			try:
				for i in qs.get():
					row = Url.objects.filter(id=qs.get()[i])
					resultados_ip.append(row.values().get())
			except:
				pass
			#resultados = qs.get()
			#return render(request,'results.html',{'resultados':resultados,'match':match})
			#elif len(qs_mail)!=0:					
			try:
				for i in qs_mail.get():
					row = Url.objects.filter(id=qs_mail.get()[i])
					resultados_mail.append(row.values().get())		
			except:
				pass
			try:					
				
				row = Url.objects.filter(id=qs_com.get()['url_id']).values().get()
				comm = Comentario.objects.filter(id=qs_com.get()['id']).values('comentario','num_linea').get()
				row['comentario']=comm['comentario']
				row['numero_linea']=comm['num_linea']	
				resultados_com.append(row)	
				
			except MultipleObjectsReturned:
				for i in qs_com:
					row = Url.objects.filter(id=i['url_id']).values().get()
					print(type(row))
					comm = Comentario.objects.filter(id=i['id']).values('comentario','num_linea').get()
					row['comentario']=comm['comentario']
					row['numero_linea']=comm['num_linea']
					resultados_com.append(row)
			except:
				pass	
			return render(request,'results.html',{'resultados_ip':resultados_ip,'resultados_mail':resultados_mail,'resultados_com':resultados_com,'match':match})
			#return HttpResponse(template.render({'campoBusqueda':campoBusqueda}, request))
		else:
			message2 = "Campo Vacío. \nIngresa una IP, URL, Hash ,etc."
			return render(request,'busqueda.html',{'message2':message2})	
	else:	 
		campoBusqueda= Search()
		return render(request, 'busqueda.html', {})

@login_required(login_url=reverse_lazy('login'))
def muestraResultados(request,srch):
	return render(request,'results.html',{})
    
@login_required(login_url=reverse_lazy('login'))
def historico(request):
    fin = timezone.now()
    inicio = fin - timedelta(days=1)
    form = HistoricoForm()
    if request.method == 'POST':
        form = HistoricoForm(request.POST)
        if form.is_valid():
            inicio = form.cleaned_data['inicio']
            fin = form.cleaned_data['fin']
    sitios = Url.objects.filter(timestamp__lte=fin, timestamp__gte=inicio)
    context = context_reporte(sitios)
    context['inicio'] = inicio
    context['fin'] = fin
    context['form'] = form
    return render(request, 'historico.html', context)

@login_required(login_url=reverse_lazy('login'))
def ajustes(request):
    proxies = Proxy.objects.all()
    recursos = Recurso.objects.all()
    asunto_form = CambiaAsuntoForm(initial={'asunto': lee_plantilla_asunto()})
    mensaje_form = CambiaMensajeForm(initial={'mensaje': lee_plantilla_mensaje()})
    actualizacion_form = FrecuenciaForm()
    verificacion_form = FrecuenciaForm()
    if request.method == 'POST':
        if request.POST.get('cambia-asunto'):
            asunto_form = CambiaAsuntoForm(request.POST)
            if asunto_form.is_valid():
                asunto = asunto_form.cleaned_data['asunto']
                cambia_asunto(asunto)
        elif request.POST.get('cambia-mensaje'):
            mensaje_form = CambiaMensajeForm(request.POST)
            if mensaje_form.is_valid():
                mensaje = mensaje_form.cleaned_data['mensaje']
                cambia_mensaje(mensaje)
        elif request.POST.get('cambia-actualizacion'):
            actualizacion_form = FrecuenciaForm(request.POST)
            if actualizacion_form.is_valid():
                actualizacion = actualizacion_form.cleaned_data['frecuencia']
                if actualizacion < 1:
                    actualizacion = 8
                cambia_frecuencia('actualiza', actualizacion)
        elif request.POST.get('cambia-verificacion'):
            verificacion_form = FrecuenciaForm(request.POST)
            if verificacion_form.is_valid():
                verificacion = verificacion_form.cleaned_data['frecuencia']
                if verificacion < 1:
                    verificacion = 1
                cambia_frecuencia('verifica', verificacion)
    context = {
        'recursos': recursos,
        'proxies': proxies,
        'asunto_form': asunto_form,
        'mensaje_form': mensaje_form,
        'actualizacion_form': actualizacion_form,
        'verificacion_form': verificacion_form,
    }
    return render(request, 'ajustes.html', context)

@login_required(login_url=reverse_lazy('login'))
def elimina_proxy(request, pk):
    proxy = get_object_or_404(Proxy, pk=pk)
    proxy.delete()
    return redirect('ajustes')

class ActualizaProxy(LoginRequiredMixin, UpdateView):
    model = Proxy
    template_name = 'actualiza_proxy.html'
    success_url = reverse_lazy('ajustes')
    fields = ('http', 'https')
    
class NuevoProxy(LoginRequiredMixin, CreateView):
    model = Proxy
    template_name = 'nuevo_proxy.html'
    success_url = reverse_lazy('ajustes')
    fields = ('http', 'https')

@login_required(login_url=reverse_lazy('login'))
def elimina_recurso(request, pk):
    recurso = get_object_or_404(Recurso, pk=pk)
    recurso.delete()
    return redirect('ajustes')

class ActualizaRecurso(LoginRequiredMixin, UpdateView):
    model = Recurso
    template_name = 'actualiza_recurso.html'
    success_url = reverse_lazy('ajustes')
    fields = ('es_phishtank', 'recurso', 'max_urls')
    
class NuevoRecurso(LoginRequiredMixin, CreateView):
    model = Recurso
    template_name = 'nuevo_recurso.html'
    success_url = reverse_lazy('ajustes')
    fields = ('es_phishtank', 'recurso', 'max_urls')

@login_required(login_url=reverse_lazy('login'))
def ofuscaciones_view(request):
    of = Ofuscacion.objects.all()
    context = {
        'ofuscaciones': of
    }
    return render(request, 'ofuscaciones.html', context)

@login_required(login_url=reverse_lazy('login'))
def entidades_view(request):
    of = Entidades.objects.all()
    context = {
        'entidades': of
    }
    return render(request, 'entidades.html', context)

@login_required(login_url=reverse_lazy('login'))
def elimina_ofuscacion(request, pk):
    recurso = get_object_or_404(Ofuscacion, pk=pk)
    recurso.delete()
    return redirect('ofuscaciones')

class ActualizaOfuscacion(LoginRequiredMixin, UpdateView):
    model = Ofuscacion
    template_name = 'actualiza_ofuscacion.html'
    success_url = reverse_lazy('ofuscaciones')
    fields = ('nombre', 'regex')
    
class NuevaOfuscacion(LoginRequiredMixin, CreateView):
    model = Ofuscacion
    template_name = 'nueva_ofuscacion.html'
    success_url = reverse_lazy('ofuscaciones')
    fields = ('nombre', 'regex')
    
@login_required(login_url=reverse_lazy('login'))
def elimina_entidad(request, pk):
    entidad = get_object_or_404(Entidades, pk=pk)
    entidad.delete()
    return redirect('entidades')

class ActualizaEntidad(LoginRequiredMixin, UpdateView):
    model = Entidades
    template_name = 'actualiza_entidad.html'
    success_url = reverse_lazy('entidades')
    fields = ('nombre',)
    
class NuevaEntidad(LoginRequiredMixin, CreateView):
    model = Entidades
    template_name = 'nueva_entidad.html'
    success_url = reverse_lazy('entidades')
    fields = ('nombre',)
