import os
import sys
import re
import smtplib
import requests
from subprocess import Popen, PIPE
from urllib.parse import urlparse
from requests.exceptions import ConnectionError
from lxml import html
import hashlib
from bs4 import BeautifulSoup, Comment
from django.conf import settings
from .models import Url, Entidades, Correo, Hash, Comentario, Dominio, Ofuscacion
from django.conf import settings
from django.utils import timezone

b64 = [chr(x) for x in range(ord('A'), ord('Z') + 1)]
b64 += [chr(x) for x in range(ord('a'), ord('z') + 1)]
b64 += [str(x) for x in range(10)]
b64 += ['+', '/', '=']

def error(msg, exit=False):
    """
    Manda un error y de especificarse, se sale del programa
    """
    sys.stderr.write('%s\n' % msg)
    if exit:
        sys.exit(1)

def md5(x):
    return hashlib.md5(x).hexdigest()

def lineas_md5(sitio, texto):
    i = 1
    for x in texto.split('\n'):
        h = ''
        if len(x) == 0:
            h = md5(x.encode('utf-8'))
        else:
            h = md5(x.encode('utf-8') if x[-1] != '\n' else x[:-1].encode('utf-8'))
        try:
            hash = Hash.objects.get(num_linea=i, url=sitio)
            hash.hash = h
            hash.save()
        except Hash.DoesNotExist:
            Hash(hash=h, num_linea=i, url=sitio).save()
        finally:
            i += 1

def entidades_afectadas(sitio, entidades, texto):
    for x in texto.split():
        e = entidades.get(x.lower(), None)
        if not e is None:
            sitio.entidades_afectadas.add(e)
    sitio.save()

def encuentra_ofuscacion(sitio, ofuscaciones, texto):
    for x in ofuscaciones:        
        if len(re.findall(x.regex, texto)) > 0:
            sitio.ofuscacion.add(x)

def leeComentariosHTML(sitio, texto):
    soup = BeautifulSoup(texto,'lxml')
    comments = [x.strip() for x in soup.findAll(text=lambda text:isinstance(text, Comment))]
    match = re.findall('(?:^[\s]*//| //)(.+)', texto)
    match += re.findall('/[*](.*\n?.*)[*]/', texto)
    # match += re.findall(r'\*(([^*]|[\r\n]|(\*+([^*/]|[\r\n])))*)\*+',texto)
    for m in match:
        comments.append(m.strip())
    for x in comments:
        try:
            c = Comentario.objects.get(comentario=x, url=sitio)
        except Comentario.DoesNotExist:
            Comentario(comentario=x, url=sitio).save()

def reporta_urls(sitio, texto):
    soup = BeautifulSoup(texto, 'lxml')
    links = soup.findAll("a")
    l = []
    for link in links:
        if not link.get("href", None) is None:
            if urlparse(link['href']).scheme != "" \
               and urlparse(sitio.url).netloc != urlparse(link['href']).netloc:
                l.append(link["href"])
    sitio.recursos_externos = '\n'.join(l)
    sitio.save()
    
def analisis_texto(sitio, texto):
    sitio.hash_archivo = md5(texto.encode('utf-8'))
    lineas_md5(sitio, texto)
    leeComentariosHTML(sitio, texto)
    reporta_urls(sitio, texto)
    
def obten_archivo(url):
    uh = urlparse(url).path
    p = os.path.basename(uh)
    if not p:
        return 'index.html'
    return p

def hacer_peticion(sesion, sitio, entidades, ofuscaciones, dominios_inactivos, capturas, max_redir):
    """
    Se hace una peticion a la url y se obtiene el codigo de respuesta junto con
    el titulo de la pagina
    """
    codigo = -1
    titulo = None
    ofuscacion = []
    archivo = None
    try:
        headers = {'User-Agent': settings.USER_AGENT}
        req = sesion.get(sitio.url, headers=headers, allow_redirects=False)
        codigo = req.status_code
        if codigo > 0:
            if codigo < 400 and codigo > 300:
                 redireccion = req.headers['location']
                 if redireccion != sitio.url and max_redir > 0:
                     verifica_url(redireccion, entidades, dominios_inactivos, capturas, max_redir - 1)
            elif codigo < 300 and codigo >= 200:
                tree = html.fromstring(req.text)
                t = tree.xpath("//title")
                titulo = t[0].text if len(t) > 0 else ''
                analisis_texto(sitio, req.text)
                encuentra_ofuscacion(sitio, ofuscaciones, req.text)
                sitio.nombre_archivo = obten_archivo(req.url)
                tree = html.fromstring(req.text)
                texto = []
                for x in tree.xpath("//text()"):
                    texto.append(x)
                entidades_afectadas(sitio, entidades, ' '.join(texto))
            sitio.titulo = '' if not titulo else titulo.strip().replace('\n', ' ')
    except Exception as e:
        error(str(e))
    finally:
        return codigo

def nslookup(dominio):
    """
    Se realiza la resolucion de la direccion IP para el dominio
    """
    if re.match("[0-9]{1,3}(.[0-9]{1,3}){3}", dominio):
        return dominio
    process = Popen(['nslookup', dominio], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    if stderr:
        return None
    for x in stdout.decode('utf-8').split('\n')[2:]:
        if 'Address' in x:
            return x.split(' ')[1]
    return None

def get_correo(correo):
    try:
        c = Correo.objects.get(correo=correo)
    except Correo.DoesNotExist:
        c = Correo()
        c.correo = correo
        c.save()
    return c

def whois(sitio):
    """
    Usando whois se obtienen los correos de abuso, netname y pais para la
    direccion IP
    """
    correos, netname, country = [], None, None
    if sitio.ip:
        process = Popen(['whois', sitio.ip], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        if stderr:
            return
        remail = r"([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)"
        sitio.whois = stdout.decode('utf-8')
        for x in sitio.whois.splitlines():
            f = re.findall(remail, x)
            if len(f) > 0 and 'abuse' in f[0].lower():
                sitio.correos.add(get_correo(f[0]))
            elif netname is None and 'netname' in x.lower():
                sitio.netname = x.strip().split(' ')[-1]
            elif country is None and 'country' in x.lower():
                sitio.pais = x.strip().split(' ')[-1].upper()
            elif 'ORGABUSEEMAIL' in x.upper() and len(f) > 0:
                sitio.correos.add(get_correo(f[0]))
    try:
        sitio.save()
    except:
        pass
        
def genera_captura(url, out):
    """
    Se genera la captura de pantalla de la url especificada,
    se guarda el resultado en out
    """
    process = Popen('xvfb-run --server-args="-screen 0, 1280x1200x24" cutycapt --url="%s" --out="%s"' % (url, out), shell=True, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    return not stderr is None
        
def genera_id(sitio):
    return md5(('%s%s' % (sitio.url, sitio.ip)).encode('utf-8'))

def dom_whois(dominio, sitio):
    try:
        d = Dominio.objects.get(dominio=dominio)
    except Dominio.DoesNotExist:
        d = Dominio(dominio=dominio)
        d.save()
    try:
        process = Popen(['whois', dominio], stdout=PIPE, stderr=PIPE)
        stdout, stderr = process.communicate()
        whois = 'Sin Información'
        if not stderr:
            d.whois = stdout.decode('utf-8')
            d.save()
        sitio.dominio = d
        sitio.save()
    except:
        pass

def mkdir(d):
    if not os.path.exists(d):
        os.makedirs(d)

def obten_sesion(proxy):
    """
    Regresa una sesión para realizar peticiones.
    Recibe:
        tor (bool) - De ser True se crea una sesión para usar TOR
        verboso (bool) - De ser True se utiliza el modo verboso
    Regresa:
        sesión
    """
    if proxy is None:
        return requests
    sesion = requests.session()
    # sesion.proxies = {'http':  'socks5://127.0.0.1:9050', 'https': 'socks5://127.0.0.1:9050'}
    sesion.proxies = proxy
    return sesion

def verifica_url(url, entidades, ofuscaciones, dominios_inactivos, capturas, max_redir, proxy):
    if not re.match("^https?://.+", url):
        url = 'http://' + url
    sitios = Url.objects.filter(url=url).order_by('-timestamp')
    dominio = urlparse(url).netloc
    ip = nslookup(dominio)
    existe = False
    sitio = Url()
    sitio.url = url
    for x in sitios:
        if ip == x.ip:
            existe = True
            sitio = x
            break
    if not existe:
        sitio.save()
    if dominios_inactivos.get(dominio, None) is None:
        sesion = obten_sesion(proxy)
        codigo = hacer_peticion(sesion, sitio, entidades, ofuscaciones,
                                dominios_inactivos, capturas, max_redir)
        if existe and sitio.codigo == codigo and ip == sitio.ip:
            sitio.timestamp = timezone.now()
        sitio.ip = ip
        sitio.codigo = codigo
        whois(sitio)
        dom_whois(dominio, sitio)
    if (sitio.codigo >= 200 and sitio.codigo < 300) or sitio.codigo >= 400:
        nombre = '%s.png' % genera_id(sitio)
        captura = os.path.join(capturas, nombre)
        genera_captura(url, captura)
        sitio.captura = '%scapturas/%s' % (settings.MEDIA_URL, nombre)
    else:
        dominios_inactivos[dominio] = 1
    try:
        sitio.save()
    except:
        pass

def almacena_urls(urls, proxy):
    capturas = os.path.join(settings.MEDIA_ROOT, 'capturas')
    mkdir(capturas)
    entidades = {}
    ofuscaciones = [('URL encoded', '(?:%[ABCDEF0-9]{2}){20,}'),
                    ('Base 64', '[%s]{50,}' % ''.join(b64)),
                    ('Texto plano', '(?:[\w]{5,20}[ \n]|[ ?¿<>=()#"\'{}%!¡~;,.:-_&/|°*+[]/])+'),
                    ('Símbolos HTML', '&#[0-9]{2,3};')]
    for x in Entidades.objects.all():
        entidades[x.nombre.lower()] = x
    dominios_inactivos = {}
    for u in urls:
        verifica_url(u, entidades, Ofuscacion.objects.all(), dominios_inactivos,
                     capturas, settings.MAX_REDIRECCIONES, proxy)
