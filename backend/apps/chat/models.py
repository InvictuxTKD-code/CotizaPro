import uuid

from django.conf import settings
from django.db import models
from django.db.models import Q


class ConversacionChat(models.Model):
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="conversaciones")
    cotizacion = models.ForeignKey("cotizaciones.Cotizacion", null=True, blank=True, on_delete=models.SET_NULL, related_name="conversaciones")
    token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)  # evita leer conversaciones ajenas
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    fecha_fin = models.DateTimeField(null=True, blank=True)
    resuelta_por_bot = models.BooleanField(default=False)
    derivada_a_humano = models.BooleanField(default=False)
    contacto = models.CharField(max_length=150, blank=True, default="")  # correo o teléfono para que un ejecutivo contacte
    atendida = models.BooleanField(default=False)  # el ejecutivo ya contactó a la persona

    class Meta:
        db_table = "conversacion_chat"
        ordering = ["-fecha_inicio"]


class MensajeChat(models.Model):
    class Emisor(models.TextChoices):
        USUARIO = "USUARIO", "Usuario"
        ASISTENTE = "ASISTENTE", "Asistente"

    conversacion = models.ForeignKey(ConversacionChat, on_delete=models.CASCADE, related_name="mensajes")
    emisor = models.CharField(max_length=10, choices=Emisor.choices)
    contenido = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "mensaje_chat"
        ordering = ["fecha", "id"]


class EncuestaSatisfaccion(models.Model):
    cotizacion = models.OneToOneField("cotizaciones.Cotizacion", on_delete=models.CASCADE, related_name="encuesta")
    puntaje = models.PositiveSmallIntegerField()
    comentario = models.CharField(max_length=300, blank=True, null=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "encuesta_satisfaccion"
        constraints = [models.CheckConstraint(condition=Q(puntaje__gte=1, puntaje__lte=5), name="encuesta_puntaje_1_a_5")]
