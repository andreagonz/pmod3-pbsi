from django.db import models
from django_countries.fields import CountryField
from django.contrib import admin
from .storage import OverwriteStorage

class Entidades(models.Model):
    
    nombre = models.CharField(max_length=128, unique=True)

    def __str__(self):
        return self.nombre
    
class Ofuscacion(models.Model):

    regex = models.CharField(max_length=128)
    nombre = models.CharField(max_length=128)

    def __str__(self):
        return self.nombre
    
class Correo(models.Model):

    correo = models.CharField(max_length=512, unique=True)

    def __str__(self):
        return self.correo

class Dominio(models.Model):
    
    dominio = models.CharField(max_length=256, unique=True)
    captura = models.ImageField(storage=OverwriteStorage(),
                                upload_to='capturas', blank=True, null=True)

    @property
    def captura_url(self):
        if self.captura and hasattr(self.captura, 'url'):
            return self.captura.url
    
    def __str__(self):
        return self.dominio

class Url(models.Model):

    identificador = models.CharField(max_length=32, unique=True)
    url = models.CharField(max_length=512)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip = models.CharField(max_length=15, null=True)
    codigo = models.IntegerField(default=-1)
    titulo = models.CharField(max_length=512, null=True)
    captura = models.ImageField(storage=OverwriteStorage(),
                                upload_to='capturas', blank=True, null=True)
    ofuscacion = models.ManyToManyField(Ofuscacion)
    hash_archivo = models.CharField(max_length=32, null=True)
    entidades_afectadas = models.ManyToManyField(Entidades)
    reportado = models.BooleanField(default=False)
    pais = CountryField(null=True)
    correos = models.ManyToManyField(Correo)
    dominio = models.ForeignKey(Dominio, on_delete=models.PROTECT, null=True)
    netname = models.CharField(max_length=128, null=True)
    archivo = models.FileField(storage=OverwriteStorage(),
                               upload_to='capturas', blank=True, null=True)
    
    class Meta:
        unique_together = ('url', 'ip',)

    @property
    def captura_url(self):
        if self.captura and hasattr(self.captura, 'url'):
            return self.captura.url
        
    def __str__(self):
        return self.url
         
class Recurso(models.Model):

    es_phishtank = models.BooleanField(default=False)
    recurso = models.CharField(max_length=256, unique=True)
    max_urls = models.IntegerField(default=-1)

    def __str__(self):
        return self.recurso
    
class Proxy(models.Model):

    http = models.CharField(max_length=256)
    https = models.CharField(max_length=256)
    
# class Configuracion(models.Model):

    # nombre = models.CharField(max_length=128)
    # datos = models.CharField(max_length=512)
    
# class Grafica(models.Model):
    # tipo = pastel
    # atributo = codigo_respuesta
