from django.contrib import admin
from .models import (
    Entidades, Correo, Ofuscacion, Url,
    Dominio, Hash, Comentario, Recurso
    )


admin.site.register(Entidades)
admin.site.register(Correo)
admin.site.register(Ofuscacion)
admin.site.register(Url)
admin.site.register(Dominio)
admin.site.register(Hash)
admin.site.register(Comentario)
admin.site.register(Recurso)
