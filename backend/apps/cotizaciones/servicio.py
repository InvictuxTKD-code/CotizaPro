"""Casos de uso sobre cotizaciones: crear, (re)calcular y registrar estados."""
from django.db import transaction
from django.utils import timezone

from apps.auditoria.servicio import registrar
from apps.inventario.models import Material
from apps.inventario.servicio import descontar_por_aprobacion

from .calculo import calcular_presupuesto
from .models import Cotizacion, DetalleCotizacion, HistorialEstado, InsumoCotizacion


def registrar_estado(cotizacion, anterior, nuevo, usuario):
    return HistorialEstado.objects.create(cotizacion=cotizacion, estado_anterior=anterior, estado_nuevo=nuevo, usuario=usuario)


class _Detalle:  # adaptador liviano para calcular sin guardar
    def __init__(self, d):
        self.acabado, self.cantidad, self.textura = d.tipo_acabado, d.cantidad, d.textura


@transaction.atomic
def calcular_y_guardar(cotizacion, usuario=None, request=None):
    """CU03: calcula con las reglas de negocio y guarda el desglose. Lanza DatosFaltantes si falta algo."""
    detalles = list(cotizacion.detalles.select_related("tipo_acabado", "tipo_acabado__material"))
    insumos_mat = Material.objects.filter(activo=True, categoria__in=_categorias()) if cotizacion.origen_materiales == "EMPRESA" else []
    res = calcular_presupuesto(cotizacion, [_Detalle(d) for d in detalles], insumos_mat)

    for d, l in zip(detalles, res.lineas):
        d.unidad = d.tipo_acabado.unidad
        d.precio_unitario = l.precio
        d.costo_mano_obra = l.mano_obra
        d.material, d.cantidad_material, d.costo_materiales = l.material, l.cantidad_material, l.costo_materiales
        d.save()

    cotizacion.insumos.all().delete()
    InsumoCotizacion.objects.bulk_create(
        [InsumoCotizacion(cotizacion=cotizacion, material=m, cantidad=c, costo=k) for m, c, k in res.insumos]
    )
    cotizacion.neto, cotizacion.iva, cotizacion.total = res.neto, res.iva, res.total
    cotizacion.fecha_calculo = timezone.now()
    cotizacion.save(update_fields=["neto", "iva", "total", "fecha_calculo"])
    registrar("CALCULAR_COTIZACION", "cotizacion", cotizacion.pk, usuario, f"total={res.total}", request)
    return cotizacion


def _categorias():
    from django.conf import settings

    return settings.INSUMOS_POR_PINTOR


class TransicionInvalida(Exception):
    pass


@transaction.atomic
def aprobar(cotizacion, usuario, request=None):
    """CU08 + CU09. Aprueba y, si los materiales son de M y C, descuenta el stock en la MISMA transacción.
    Si el stock no alcanza lanza StockInsuficiente y no queda nada guardado. Devuelve materiales bajo el mínimo."""
    cotizacion = Cotizacion.objects.select_for_update().get(pk=cotizacion.pk)
    if cotizacion.estado != Cotizacion.Estado.PENDIENTE:
        raise TransicionInvalida(f"La cotización ya está {cotizacion.get_estado_display().lower()}.")
    if not cotizacion.calculada:
        raise TransicionInvalida("La cotización aún no está calculada.")
    bajo_minimo = []
    if cotizacion.origen_materiales == Cotizacion.OrigenMateriales.EMPRESA:
        bajo_minimo = descontar_por_aprobacion(cotizacion, usuario, request)
    anterior = cotizacion.estado
    cotizacion.estado = Cotizacion.Estado.APROBADA
    cotizacion.save(update_fields=["estado"])
    registrar_estado(cotizacion, anterior, cotizacion.estado, usuario)
    registrar("APROBAR_COTIZACION", "cotizacion", cotizacion.pk, usuario, f"total={cotizacion.total}", request)
    return bajo_minimo


@transaction.atomic
def rechazar(cotizacion, usuario, motivo=None, request=None):
    cotizacion = Cotizacion.objects.select_for_update().get(pk=cotizacion.pk)
    if cotizacion.estado != Cotizacion.Estado.PENDIENTE:
        raise TransicionInvalida(f"La cotización ya está {cotizacion.get_estado_display().lower()}.")
    anterior = cotizacion.estado
    cotizacion.estado = Cotizacion.Estado.RECHAZADA
    if motivo:
        cotizacion.observaciones = ((cotizacion.observaciones or "") + f"\nRechazo: {motivo}").strip()
    cotizacion.save(update_fields=["estado", "observaciones"])
    registrar_estado(cotizacion, anterior, cotizacion.estado, usuario)
    registrar("RECHAZAR_COTIZACION", "cotizacion", cotizacion.pk, usuario, motivo, request)
