from django.contrib import admin

from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ("correo", "nombre", "rol", "activo", "ultimo_acceso")
    list_filter = ("rol", "activo")
    search_fields = ("correo", "nombre")
