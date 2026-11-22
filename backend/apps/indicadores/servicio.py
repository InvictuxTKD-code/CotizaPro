"""Indicadores de gestión (HU07). Solo lectura: consulta cotizaciones e inventario ya registrados."""
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Sum
from django.utils import timezone

from apps.cotizaciones.models import Cotizacion, DetalleCotizacion, HistorialEstado
from apps.chat.models import ConversacionChat, EncuestaSatisfaccion
from apps.inventario.models import Material, MovimientoInventario

PERIODOS = {30, 90, 365, 0}  # 0 = todo el historial
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def _mes(d):
    return f"{d.year}-{d.month:02d}"


def _etiqueta(clave):
    a, m = clave.split("-")
    return f"{MESES[int(m) - 1]} {a[2:]}"


def _meses_entre(desde, hasta):
    y, m, out = desde.year, desde.month, []
    while (y, m) <= (hasta.year, hasta.month):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _pct(a, b):
    return round(a * 100 / b, 1) if b else None


def calcular_indicadores(dias=90):
    ahora = timezone.now()
    desde = ahora - timedelta(days=dias) if dias else None
    en_periodo = {"fecha_solicitud__gte": desde} if desde else {}
    cots = Cotizacion.objects.filter(**en_periodo)

    por_estado = {e: 0 for e in Cotizacion.Estado.values}
    for fila in cots.values("estado").annotate(n=Count("id")):
        por_estado[fila["estado"]] = fila["n"]
    total = sum(por_estado.values())
    decididas = por_estado["APROBADA"] + por_estado["RECHAZADA"]

    # KPI-01: minutos entre la solicitud y el cálculo del presupuesto
    mins = [(c - s).total_seconds() / 60 for s, c in cots.exclude(fecha_calculo=None).values_list("fecha_solicitud", "fecha_calculo")]
    tiempo_prom = round(sum(mins) / len(mins), 1) if mins else None

    # Ventas = cotizaciones aprobadas (monto neto), fechadas por el momento de la aprobación
    aprob = HistorialEstado.objects.filter(estado_nuevo="APROBADA", cotizacion__estado="APROBADA")
    if desde:
        aprob = aprob.filter(fecha__gte=desde)
    aprob = list(aprob.select_related("cotizacion"))
    ventas_neto = sum((h.cotizacion.neto or 0) for h in aprob)

    # Serie mensual: solicitudes, aprobadas y ventas
    sol_mes, apr_mes, ven_mes = defaultdict(int), defaultdict(int), defaultdict(Decimal)
    for f in cots.values_list("fecha_solicitud", flat=True):
        sol_mes[_mes(f)] += 1
    for h in aprob:
        apr_mes[_mes(h.fecha)] += 1
        ven_mes[_mes(h.fecha)] += h.cotizacion.neto or 0
    if desde:
        inicio = desde
    else:
        primera = Cotizacion.objects.order_by("fecha_solicitud").values_list("fecha_solicitud", flat=True).first()
        inicio = primera or ahora
    claves = _meses_entre(inicio, ahora)[-12:]
    serie = [{"mes": _etiqueta(k), "solicitudes": sol_mes[k], "aprobadas": apr_mes[k], "ventas": int(ven_mes[k])} for k in claves]

    # Trabajos más vendidos (por monto de cotizaciones aprobadas)
    ids = [h.cotizacion_id for h in aprob]
    top = (DetalleCotizacion.objects.filter(cotizacion_id__in=ids).values("tipo_acabado__nombre")
           .annotate(monto=Sum("costo_mano_obra"), cantidad=Sum("cantidad")).order_by("-monto")[:6])
    top_trabajos = [{"trabajo": t["tipo_acabado__nombre"], "monto": int(t["monto"] or 0), "cantidad": float(t["cantidad"] or 0)} for t in top]

    # Inventario: alertas y consumo; KPI-07 = aprobaciones con materiales de M y C descontadas automáticamente
    bajo = [{"id": m.id, "nombre": m.nombre, "stock_actual": float(m.stock_actual), "stock_minimo": float(m.stock_minimo), "unidad": m.unidad}
            for m in Material.objects.filter(activo=True) if m.bajo_minimo]
    mov = MovimientoInventario.objects.filter(tipo="SALIDA", cotizacion__isnull=False)
    if desde:
        mov = mov.filter(fecha__gte=desde)
    consumo = [{"material": f["material__nombre"], "cantidad": float(f["c"]), "unidad": f["material__unidad"]}
               for f in mov.values("material__nombre", "material__unidad").annotate(c=Sum("cantidad")).order_by("-c")[:6]]
    aprob_empresa = [h.cotizacion_id for h in aprob if h.cotizacion.origen_materiales == "EMPRESA"]
    con_descuento = MovimientoInventario.objects.filter(cotizacion_id__in=aprob_empresa).values("cotizacion_id").distinct().count()

    convs = ConversacionChat.objects.filter(mensajes__isnull=False).distinct()
    encuestas = EncuestaSatisfaccion.objects.all()
    if desde:
        convs, encuestas = convs.filter(fecha_inicio__gte=desde), encuestas.filter(fecha__gte=desde)
    n_conv, n_res = convs.count(), convs.filter(resuelta_por_bot=True, derivada_a_humano=False).count()
    punt = list(encuestas.values_list("puntaje", flat=True))
    chat = {"valor": _pct(n_res, n_conv), "casos": n_conv, "meta": "≥ 60 %"}
    satisf = {"valor": _pct(sum(1 for p in punt if p >= 4), len(punt)), "casos": len(punt), "meta": "≥ 85 %"}

    return {
        "periodo_dias": dias, "generado": ahora,
        "resumen": {
            "solicitudes": total, "por_estado": por_estado,
            "ventas_neto": int(ventas_neto), "aprobadas": len(aprob),
            "ticket_promedio": int(ventas_neto / len(aprob)) if aprob else None,
        },
        "kpi": {
            "tiempo_cotizacion_min": {"valor": tiempo_prom, "casos": len(mins), "meta": "≤ 10 min"},
            "registradas": {"valor": total, "casos": total, "meta": "100 %"},
            "conversion": {"valor": _pct(por_estado["APROBADA"], decididas), "casos": decididas, "meta": "≥ 60 %"},
            "inventario_automatico": {"valor": _pct(con_descuento, len(aprob_empresa)), "casos": len(aprob_empresa), "meta": "100 %"},
            "chatbot": chat, "satisfaccion": satisf,
        },
        "serie_mensual": serie, "top_trabajos": top_trabajos,
        "inventario": {"bajo_minimo": bajo, "consumo": consumo},
    }
