from django.db import models
from django_countries.fields import CountryField
from django.contrib import admin

class Entidades(models.Model):
    
    nombre = models.CharField(max_length=128)

    def __str__(self):
        return self.nombre
    
class Ofuscacion(models.Model):

    regex = models.CharField(max_length=128)
    nombre = models.CharField(max_length=128)

    def __str__(self):
        return self.nombre
    
class Url(models.Model):

    url = models.CharField(max_length=512)
    timestamp = models.DateTimeField(auto_now_add=True)
    ip = models.CharField(max_length=15)
    codigo = models.IntegerField()
    titulo = models.CharField(max_length=512)
    captura = models.CharField(max_length=512)
    whois = models.TextField()
    nombre_archivo = models.CharField(max_length=256)
    ofuscacion = models.ManyToManyField(Ofuscacion)
    hash_archivo = models.CharField(max_length=32)
    entidades_afectadas = models.ManyToManyField(Entidades)
    reportado = models.BooleanField()
    pais = CountryField()
    
    def __str__(self):
        return self.url

class Correo(models.Model):

    correo = models.CharField(max_length=512)
    url = models.ForeignKey(Url, on_delete=models.CASCADE)

    def __str__(self):
        return self.correo
    
class Dominio(models.Model):

    dominio = models.CharField(max_length=256)
    whois = models.TextField()

    def __str__(self):
        return self.dominio
    
class Hash(models.Model):

    hash = models.CharField(max_length=32)
    num_linea = models.IntegerField()
    url = models.ForeignKey(Url, on_delete=models.CASCADE)

    def __str__(self):
        return self.hash
    
class Comentario(models.Model):

    es_bloque = models.BooleanField()
    comentario = models.TextField()
    num_linea = models.IntegerField()
    url = models.ForeignKey(Url, on_delete=models.CASCADE)

    def __str__(self):
        return self.comentario

class Recurso(models.Model):

    es_phishtank = models.BooleanField()
    recurso = models.CharField(max_length=256)
    separador = models.CharField(max_length=32)    

# class Grafica(models.Model):
    # tipo = pastel
    # atributo = codigo_respuesta
