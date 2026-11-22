import pytest

from apps.auditoria.models import RegistroAuditoria
from apps.cotizaciones.models import Cotizacion, TipoAcabado
from apps.inventario.models import Material
from apps.inventario.tests.test_aprobacion import mundo, pedir, sesion  # noqa: F401
from apps.usuarios.models import Rol

pytestmark = pytest.mark.django_db


def test_solo_admin_edita_precios_y_nombres(mundo):
    url = f"/api/acabados/{mundo['ac'].pk}/"
    assert mundo["eje"].get("/api/acabados/").status_code == 200
    assert mundo["eje"].patch(url, {"precio_unitario": 5000}, format="json").status_code == 403
    assert mundo["cli"].get("/api/acabados/").status_code == 403
    assert mundo["adm"].delete(url).status_code == 405
    r = mundo["adm"].patch(url, {"nombre": "Pintura látex premium", "precio_unitario": 5000}, format="json")
    assert r.status_code == 200 and r.data["precio_unitario"] == 5000
    log = RegistroAuditoria.objects.get(accion="EDITAR_TRABAJO")
    assert "4500" in log.detalle and "5000" in log.detalle and "premium" in log.detalle


def test_validaciones_del_catalogo(mundo):
    adm = mundo["adm"]
    assert adm.patch(f"/api/acabados/{mundo['ac'].pk}/", {"precio_unitario": -1}, format="json").status_code == 400
    dup = adm.post("/api/acabados/", {"nombre": "pintura LÁTEX", "unidad": "M2", "precio_unitario": 1}, format="json")
    assert dup.status_code == 400
    sin_rend = adm.post("/api/acabados/", {"nombre": "Nuevo", "unidad": "M2", "precio_unitario": 1000, "material": mundo["latex"].pk}, format="json")
    assert sin_rend.status_code == 400
    ok = adm.post("/api/acabados/", {"nombre": "Nuevo", "unidad": "ML", "precio_unitario": 1000}, format="json")
    assert ok.status_code == 201


def test_cambio_de_precio_no_altera_cotizaciones_aprobadas_pero_si_pendientes(mundo):
    aprobada, pendiente = pedir(mundo), pedir(mundo)
    mundo["adm"].post(f"/api/cotizaciones/{aprobada}/aprobar/")
    neto_aprobada = Cotizacion.objects.get(pk=aprobada).neto
    assert neto_aprobada == 450000
    mundo["adm"].patch(f"/api/acabados/{mundo['ac'].pk}/", {"precio_unitario": 6000}, format="json")
    assert Cotizacion.objects.get(pk=aprobada).neto == neto_aprobada          # histórico intacto
    assert mundo["adm"].get(f"/api/cotizaciones/{aprobada}/").data["neto"] == 450000
    r = mundo["adm"].post(f"/api/cotizaciones/{pendiente}/calcular/")
    assert r.status_code == 200 and r.data["neto"] == 600000                   # pendiente usa precio nuevo


def test_trabajo_desactivado_sale_del_catalogo_cliente(mundo):
    assert len(mundo["cli"].get("/api/catalogo/acabados/").data) == 1
    mundo["adm"].patch(f"/api/acabados/{mundo['ac'].pk}/", {"activo": False}, format="json")
    assert mundo["cli"].get("/api/catalogo/acabados/").data == []


def test_edicion_de_material_auditada_y_sin_tocar_stock(mundo):
    m = mundo["latex"]
    assert mundo["eje"].patch(f"/api/materiales/{m.pk}/", {"precio_unitario": 1}, format="json").status_code == 403
    r = mundo["adm"].patch(f"/api/materiales/{m.pk}/", {"nombre": "Látex interior", "precio_unitario": 22000, "stock_actual": 999}, format="json")
    assert r.status_code == 200
    m.refresh_from_db()
    assert m.nombre == "Látex interior" and m.precio_unitario == 22000 and m.stock_actual == 10
    assert "20000" in RegistroAuditoria.objects.get(accion="EDITAR_MATERIAL").detalle
    # sin cambios reales no se ensucia la bitácora
    mundo["adm"].patch(f"/api/materiales/{m.pk}/", {"precio_unitario": 22000}, format="json")
    assert RegistroAuditoria.objects.filter(accion="EDITAR_MATERIAL").count() == 1


def test_bitacora_solo_admin(mundo):
    mundo["adm"].patch(f"/api/acabados/{mundo['ac'].pk}/", {"precio_unitario": 5000}, format="json")
    assert mundo["eje"].get("/api/auditoria/").status_code == 403
    r = mundo["adm"].get("/api/auditoria/?entidad=tipo_acabado,material")
    assert r.status_code == 200 and r.data[0]["usuario_nombre"] and r.data[0]["accion"] == "EDITAR_TRABAJO"
