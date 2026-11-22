from .models import RegistroAuditoria


def ip_de(request):
    if request is None:
        return None
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    return (xff.split(",")[0].strip() if xff else request.META.get("REMOTE_ADDR")) or None


def describir_cambios(instancia, nuevos, campos):
    """Texto 'campo: antes → después' solo con lo que realmente cambia (para la bitácora)."""
    partes = []
    for c in campos:
        if c not in nuevos:
            continue
        antes, despues = getattr(instancia, c, None), nuevos[c]
        antes_t = getattr(antes, "nombre", antes)
        despues_t = getattr(despues, "nombre", despues)
        if str(antes_t) != str(despues_t) and not (antes in (None, "") and despues in (None, "")):
            try:  # 4500 y Decimal('4500') se consideran iguales
                if float(antes_t) == float(despues_t):
                    continue
            except (TypeError, ValueError):
                pass
            partes.append(f"{c.replace('_', ' ')}: {antes_t if antes_t not in (None, '') else '—'} → {despues_t if despues_t not in (None, '') else '—'}")
    return "; ".join(partes)


def registrar(accion, entidad, entidad_id=None, usuario=None, detalle=None, request=None):
    return RegistroAuditoria.objects.create(
        usuario=usuario if (usuario and getattr(usuario, "pk", None)) else None,
        accion=accion,
        entidad=entidad,
        entidad_id=entidad_id,
        detalle=detalle,
        ip_origen=ip_de(request),
    )
