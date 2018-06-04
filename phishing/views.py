from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from .forms import UrlsForm, MensajeForm, ProxyForm, Search
from .models import Url, Correo
from .phishing import (
    verifica_urls, archivo_texto, monitorea_url,
    whois, archivo_comentarios, archivo_hashes
)
from .correo import genera_mensaje, manda_correo, obten_asunto, obten_mensaje
from django.views.generic import TemplateView
from django.template import loader
from django.http import HttpResponse
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings
from shutil import copyfile
import os
from .reporte import (
    cuenta_urls, urls_activas, urls_inactivas, urls_redirecciones,
    urls_entidades, urls_titulos, urls_dominios, urls_paises
)

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
                        'netname': url.netname
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

@login_required(login_url=reverse_lazy('login'))
def valida_urls(request):
    if request.method == 'POST':
        form = UrlsForm(request.POST)
        if form.is_valid():
            urls = form.cleaned_data['urls']
            sitios = verifica_urls([x.strip() for x in urls.split('\n') if x.strip()], None, False)
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
