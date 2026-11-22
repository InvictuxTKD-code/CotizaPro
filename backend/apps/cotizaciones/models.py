from django.conf import settings
from django.db import models
from django.db.models import Q


class Unidad(models.TextChoices):
    M2 = "M2", "m²"
    ML = "ML", "ml"


class Textura(models.TextChoices):
    LISA = "LISA", "Lisa"
    NORMAL = "NORMAL", "Normal"
    RUGOSA = "RUGOSA", "Rugosa"


class TipoAcabado(models.Model):
    """Ítem de servicio del catálogo de M y C (ej. 'Esmalte al agua', 'Guardapolvo')."""

    nombre = models.CharField(max_length=80, unique=True)
    unidad = models.CharField(max_length=2, choices=Unidad.choices, default=Unidad.M2)
    precio_unitario = models.DecimalField(
        max_digits=10, decimal_places=0, help_text="Precio de obra vendida por m² o ml (incluye materiales e insumos)")
    precio_mano_obra = models.DecimalField(
        max_digits=10, decimal_places=0, null=True, blank=True,
        help_text="Precio por m² o ml cuando el cliente pone los materiales (solo mano de obra)")
    # Solo para ítems que consumen pintura por galones (opcionales):
    material = models.ForeignKey(
        "inventario.Material", null=True, blank=True, on_delete=models.SET_NULL, related_name="acabados"
    )
    rendimiento_m2 = models.DecimalField(
        max_digits=8, decimal_places=2, null=True, blank=True, help_text="m² que rinde un galón por mano (ej. 34)"
    )
    manos_recomendadas = models.PositiveSmallIntegerField(default=2)
    activo = models.BooleanField(default=True)

    class Meta:
        db_table = "tipo_acabado"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Cotizacion(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Pendiente"
        APROBADA = "APROBADA", "Aprobada"
        RECHAZADA = "RECHAZADA", "Rechazada"

    class OrigenMateriales(models.TextChoices):
        EMPRESA = "EMPRESA", "M y C"
        CLIENTE = "CLIENTE", "Cliente"

    cliente = models.ForeignKey("clientes.Cliente", on_delete=models.PROTECT, related_name="cotizaciones")
    ejecutivo = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="cotizaciones_a_cargo"
    )
    nombre_obra = models.CharField(max_length=150)
    direccion_obra = models.CharField(max_length=200)
    ciudad = models.CharField(max_length=80)
    origen_materiales = models.CharField(max_length=10, choices=OrigenMateriales.choices)
    requiere_medicion = models.BooleanField(default=False)
    # Para calcular rodillos y brochas (1 de cada uno por pintor, duran ~2 semanas)
    num_pintores = models.PositiveSmallIntegerField(null=True, blank=True)
    semanas_obra = models.PositiveSmallIntegerField(null=True, blank=True)
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)
    fecha_solicitud = models.DateTimeField(auto_now_add=True, db_index=True)
    fecha_calculo = models.DateTimeField(null=True, blank=True)
    neto = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    iva = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    observaciones = models.TextField(blank=True, null=True)

    class Meta:
        db_table = "cotizacion"
        ordering = ["-fecha_solicitud"]

    @property
    def calculada(self):
        return self.fecha_calculo is not None

    def __str__(self):
        return f"Cotización #{self.pk} · {self.nombre_obra}"


class DetalleCotizacion(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="detalles")
    descripcion = models.CharField(max_length=200)
    tipo_superficie = models.CharField(max_length=30, blank=True, default="")
    textura = models.CharField(max_length=10, choices=Textura.choices, default=Textura.NORMAL)
    unidad = models.CharField(max_length=2, choices=Unidad.choices, default=Unidad.M2)
    cantidad = models.DecimalField(max_digits=12, decimal_places=2, help_text="m² o ml según la unidad")
    tipo_acabado = models.ForeignKey(TipoAcabado, on_delete=models.PROTECT)
    material = models.ForeignKey("inventario.Material", null=True, blank=True, on_delete=models.PROTECT)
    cantidad_material = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=0, default=0)
    costo_materiales = models.DecimalField(max_digits=12, decimal_places=0, null=True, blank=True)
    costo_mano_obra = models.DecimalField(max_digits=12, decimal_places=0, default=0)

    class Meta:
        db_table = "detalle_cotizacion"
        constraints = [models.CheckConstraint(condition=Q(cantidad__gt=0), name="detalle_cantidad_positiva")]


class HistorialEstado(models.Model):
    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="historial")
    estado_anterior = models.CharField(max_length=12, null=True, blank=True)
    estado_nuevo = models.CharField(max_length=12)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "historial_estado"
        ordering = ["fecha"]


class InsumoCotizacion(models.Model):
    """Rodillos, brochas y otros insumos estimados para la obra (no van por m²)."""

    cotizacion = models.ForeignKey(Cotizacion, on_delete=models.CASCADE, related_name="insumos")
    material = models.ForeignKey("inventario.Material", on_delete=models.PROTECT)
    cantidad = models.DecimalField(max_digits=10, decimal_places=2)
    costo = models.DecimalField(max_digits=12, decimal_places=0)

    class Meta:
        db_table = "insumo_cotizacion"
