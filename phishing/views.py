from django.shortcuts import render
from django.urls import reverse_lazy
from django.contrib.auth.decorators import login_required
from .forms import UrlsForm, MensajeForm, ProxyForm, Search
from .models import Url, Correo
from .phishing import verifica_urls, archivo_texto
from .correo import genera_mensaje, manda_correo, obten_asunto, obten_mensaje
from django.views.generic import TemplateView
from django.template import loader
from django.http import HttpResponse
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.core.exceptions import MultipleObjectsReturned
from django.conf import settings

@login_required(login_url=reverse_lazy('login'))
def monitoreo(request):
    urls = Url.objects.filter(reportado=False, codigo__lt=300, codigo__gte=200).order_by('-timestamp')
    url = None
    if len(urls) > 0:
        url = urls[0]
    mensaje_form = MensajeForm()
    proxy_form = ProxyForm()
    if not url is None:        
        datos = {
            'de': settings.CORREO_USR,
            'para': ', '.join([x.correo for x in url.correos.all()]),
            'asunto': obten_asunto(url),
            'mensaje': obten_mensaje(url)
        }
        mensaje_form = MensajeForm(initial=datos)
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
                    verifica_urls([url.url], proxy)
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
            verifica_urls([x.strip() for x in urls.split('\n') if x.strip()], None, False)
            # return redirect('post_detail', pk=post.pk)
    else:
        form = UrlsForm()
    return render(request, 'valida_urls.html', {'form': form})

message2 = ""

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
