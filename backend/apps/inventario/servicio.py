"""Reglas de inventario. Todo movimiento de stock pasa por aquí (HU04)."""
from collections import defaultdict
from decimal import Decimal

from django.db import transaction

from apps.auditoria.servicio import registrar

from .models import Material, MovimientoInventario


class StockInsuficiente(Exception):
    def __init__(self, faltantes):
        self.faltantes = faltantes  # [{material, requerido, disponible}]
        super().__init__("Stock insuficiente")


class MovimientoInvalido(Exception):
    pass


@transaction.atomic
def mover_stock(material_id, tipo, cantidad, usuario, cotizacion=None, observacion=None, request=None):
    """ENTRADA suma, SALIDA resta, AJUSTE suma o resta según el signo. Nunca deja stock negativo."""
    cantidad = Decimal(cantidad)
    if cantidad == 0:
        raise MovimientoInvalido("La cantidad no puede ser 0.")
    if tipo != MovimientoInventario.Tipo.AJUSTE and cantidad < 0:
        raise MovimientoInvalido("La cantidad debe ser positiva (usa AJUSTE para corregir hacia abajo).")
    m = Material.objects.select_for_update().get(pk=material_id)
    delta = -cantidad if tipo == MovimientoInventario.Tipo.SALIDA else cantidad
    nuevo = m.stock_actual + delta
    if nuevo < 0:
        raise StockInsuficiente([{"material": m.nombre, "requerido": float(-delta), "disponible": float(m.stock_actual)}])
    m.stock_actual = nuevo
    m.save(update_fields=["stock_actual"])
    mov = MovimientoInventario.objects.create(material=m, cotizacion=cotizacion, usuario=usuario, tipo=tipo,
                                              cantidad=abs(cantidad) if tipo != "AJUSTE" else cantidad,
                                              stock_resultante=nuevo, observacion=observacion)
    registrar(f"STOCK_{tipo}", "material", m.pk, usuario, f"cantidad={cantidad}; stock={nuevo}", request)
    return mov


def requerimiento_de_cotizacion(cotizacion):
    """Materiales que consume una cotización: pintura por partida + rodillos/brochas. {material_id: cantidad}"""
    req = defaultdict(Decimal)
    for d in cotizacion.detalles.all():
        if d.material_id and d.cantidad_material:
            req[d.material_id] += d.cantidad_material
    for i in cotizacion.insumos.all():
        req[i.material_id] += i.cantidad
    return req


@transaction.atomic
def descontar_por_aprobacion(cotizacion, usuario, request=None):
    """CU09: todo o nada. Si algún material no alcanza se lanza StockInsuficiente y la transacción
    completa (incluida la aprobación que la contiene) se revierte."""
    req = requerimiento_de_cotizacion(cotizacion)
    materiales = {m.pk: m for m in Material.objects.select_for_update().filter(pk__in=req).order_by("pk")}
    faltantes = [{"material": materiales[mid].nombre, "requerido": float(c), "disponible": float(materiales[mid].stock_actual)}
                 for mid, c in req.items() if materiales[mid].stock_actual < c]
    if faltantes:
        raise StockInsuficiente(faltantes)
    movs = [mover_stock(mid, "SALIDA", c, usuario, cotizacion, f"Aprobación cotización #{cotizacion.pk}", request)
            for mid, c in sorted(req.items())]
    return [m.material for m in movs if m.material.bajo_minimo]  # materiales que quedaron bajo el mínimo
