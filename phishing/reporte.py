from .models import Url

def cuenta_urls(sitios):
    return len(set([x.url for x in sitios]))

def urls_activas(sitios):
    urls = []
    for sitio in sitios:
        if sitio.codigo < 300 and sitio.codigo >= 200:
            urls.append(sitio)
    return urls

def urls_inactivas(sitios):
    urls = []
    for sitio in sitios:
        if sitio.codigo >= 400 or sitio.codigo < 0:
            urls.append(sitio)
    return urls

def urls_redirecciones(sitios):
    urls = []
    for sitio in sitios:
        if sitio.codigo < 400 and sitio.codigo >= 300:
            urls.append(sitio)
    return urls

def urls_entidades(sitios):
    entidades = []
    for x in sitios:
        for e in x.entidades_afectadas.all():
            entidades.append(e.nombre)
    return list(set(entidades))
        
def urls_titulos(sitios):
    titulos = []
    for x in sitios:
        titulos.append(x.titulo)
    return list(set(titulos))

def urls_dominios(sitios):
    titulos = []
    for x in sitios:
        titulos.append(x.dominio.dominio)
    return list(set(titulos))

def urls_paises(sitios):
    paises = []
    for x in sitios:
        paises.append(x.pais)
    return list(set(paises))
