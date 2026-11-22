from django.conf import settings
from django.db import models
from django.db.models import Q


class Material(models.Model):
    nombre = models.CharField(max_length=120)
    categoria = models.CharField(max_length=40)
    unidad = models.CharField(max_length=15)
    precio_unitario = models.DecimalField(max_digits=12, decimal_places=0)
    stock_actual = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    stock_minimo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "material"
        ordering = ["categoria", "nombre"]
        constraints = [
            # El stock nunca puede quedar negativo: protegido también en la base de datos.
            models.CheckConstraint(condition=Q(stock_actual__gte=0), name="material_stock_no_negativo"),
        ]

    @property
    def bajo_minimo(self):
        return self.stock_actual <= self.stock_minimo

    def __str__(self):
        return self.nombre


class MovimientoInventario(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = "ENTRADA", "Entrada"
        SALIDA = "SALIDA", "Salida"
        AJUSTE = "AJUSTE", "Ajuste"

    material = models.ForeignKey(Material, on_delete=models.PROTECT, related_name="movimientos")
    cotizacion = models.ForeignKey(
        "cotizaciones.Cotizacion", null=True, blank=True, on_delete=models.PROTECT, related_name="movimientos"
    )
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    stock_resultante = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    observacion = models.CharField(max_length=200, blank=True, null=True)

    class Meta:
        db_table = "movimiento_inventario"
        ordering = ["-fecha"]
