import pytest
from django.utils import timezone

from apps.cotizaciones.models import Cotizacion
from apps.inventario.tests.test_aprobacion import mundo, pedir  # noqa: F401

pytestmark = pytest.mark.django_db


def test_solo_el_gerente_ve_el_dashboard(mundo):
    assert mundo["adm"].get("/api/dashboard/").status_code == 200
    assert mundo["eje"].get("/api/dashboard/").status_code == 403
    assert mundo["cli"].get("/api/dashboard/").status_code == 403
    assert APIClientAnon().get("/api/dashboard/").status_code == 401


def APIClientAnon():
    from rest_framework.test import APIClient
    return APIClient()


def test_indicadores_reflejan_los_datos_reales(mundo):
    a, b, c = pedir(mundo), pedir(mundo), pedir(mundo)
    mundo["adm"].post(f"/api/cotizaciones/{a}/aprobar/")
    mundo["adm"].post(f"/api/cotizaciones/{b}/rechazar/")
    d = mundo["adm"].get("/api/dashboard/?dias=30").data
    assert d["resumen"]["solicitudes"] == 3
    assert d["resumen"]["por_estado"] == {"PENDIENTE": 1, "APROBADA": 1, "RECHAZADA": 1}
    assert d["resumen"]["ventas_neto"] == 450000 and d["resumen"]["ticket_promedio"] == 450000
    assert d["kpi"]["conversion"] == {"valor": 50.0, "casos": 2, "meta": "≥ 60 %"}
    assert d["kpi"]["inventario_automatico"]["valor"] == 100.0
    assert d["kpi"]["tiempo_cotizacion_min"]["valor"] < 1
    assert d["kpi"]["chatbot"]["valor"] is None and d["kpi"]["chatbot"]["casos"] == 0
    assert d["top_trabajos"][0] == {"trabajo": "Pintura látex", "monto": 450000, "cantidad": 100.0}
    assert d["serie_mensual"][-1]["solicitudes"] == 3 and d["serie_mensual"][-1]["ventas"] == 450000
    assert d["inventario"]["consumo"][0]["material"] == "Látex"
    assert [m["nombre"] for m in d["inventario"]["bajo_minimo"]] == ["Látex"]  # 10 - 6 = 4 <= 5


def test_periodo_excluye_cotizaciones_antiguas(mundo):
    a = pedir(mundo)
    Cotizacion.objects.filter(pk=a).update(fecha_solicitud=timezone.now() - timezone.timedelta(days=200))
    assert mundo["adm"].get("/api/dashboard/?dias=90").data["resumen"]["solicitudes"] == 0
    assert mundo["adm"].get("/api/dashboard/?dias=0").data["resumen"]["solicitudes"] == 1
    assert mundo["adm"].get("/api/dashboard/?dias=abc").status_code == 200  # valor inválido → 90 días
