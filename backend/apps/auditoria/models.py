from django.conf import settings
from django.db import models


class RegistroAuditoria(models.Model):
    """Bitácora de operaciones críticas (aprobaciones, movimientos de stock, bloqueos)."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    accion = models.CharField(max_length=60)
    entidad = models.CharField(max_length=40)
    entidad_id = models.IntegerField(null=True, blank=True)
    detalle = models.TextField(blank=True, null=True)
    ip_origen = models.GenericIPAddressField(null=True, blank=True)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "registro_auditoria"
        ordering = ["-fecha"]

    def __str__(self):
        return f"{self.fecha:%Y-%m-%d %H:%M} {self.accion}"
