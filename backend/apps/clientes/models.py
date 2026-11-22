from django.conf import settings
from django.db import models

from .validators import normalizar_rut, validar_rut


class Cliente(models.Model):
    class Tipo(models.TextChoices):
        CONSTRUCTORA = "CONSTRUCTORA", "Constructora"
        PARTICULAR = "PARTICULAR", "Particular"

    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="cliente"
    )
    tipo = models.CharField(max_length=15, choices=Tipo.choices)
    nombre_razon_social = models.CharField(max_length=150)
    rut = models.CharField(max_length=12, unique=True, validators=[validar_rut])
    telefono = models.CharField(max_length=20, blank=True, null=True)
    correo_contacto = models.EmailField(max_length=150)

    class Meta:
        db_table = "cliente"

    def save(self, *args, **kwargs):
        self.rut = normalizar_rut(self.rut)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre_razon_social} ({self.rut})"
