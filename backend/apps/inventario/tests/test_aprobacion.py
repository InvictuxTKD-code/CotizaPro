import pytest
from rest_framework.test import APIClient

from apps.auditoria.models import RegistroAuditoria
from apps.clientes.models import Cliente
from apps.cotizaciones.models import Cotizacion, TipoAcabado
from apps.inventario.models import Material, MovimientoInventario
from apps.usuarios.models import Rol, Usuario

pytestmark = pytest.mark.django_db
CLAVE = "ClaveSegura123"


def sesion(rol, correo, rut=None):
    u = Usuario.objects.create_user(correo, CLAVE, nombre=correo, rol=rol)
    if rut:
        Cliente.objects.create(usuario=u, tipo="PARTICULAR", nombre_razon_social="Cli", rut=rut, correo_contacto=correo)
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION="Bearer " + api.post("/api/auth/login/", {"correo": correo, "password": CLAVE}, format="json").data["access"])
    return api, u


@pytest.fixture
def mundo():
    latex = Material.objects.create(nombre="Látex", categoria="Pintura", unidad="galón", precio_unitario=20000, stock_actual=10, stock_minimo=5)
    rod = Material.objects.create(nombre="Rodillo", categoria="Rodillo", unidad="unidad", precio_unitario=3000, stock_actual=10, stock_minimo=2)
    bro = Material.objects.create(nombre="Brocha", categoria="Brocha", unidad="unidad", precio_unitario=2000, stock_actual=10, stock_minimo=2)
    ac = TipoAcabado.objects.create(nombre="Pintura látex", unidad="M2", precio_unitario=4500, precio_mano_obra=2500, material=latex, rendimiento_m2=34)
    cli, _ = sesion(Rol.CLIENTE, "c@x.cl", "11111111-1")
    adm, u_adm = sesion(Rol.ADMINISTRADOR, "a@x.cl")
    eje, _ = sesion(Rol.EJECUTIVO, "e@x.cl")
    return dict(latex=latex, rod=rod, bro=bro, ac=ac, cli=cli, adm=adm, eje=eje, u_adm=u_adm)


def pedir(m, origen="EMPRESA", m2="100", **extra):
    body = {"nombre_obra": "Obra", "direccion_obra": "X 1", "ciudad": "Valdivia", "origen_materiales": origen,
            "detalles": [{"descripcion": "Muros", "textura": "NORMAL", "cantidad": m2, "tipo_acabado": m["ac"].pk}], **extra}
    r = m["cli"].post("/api/cotizaciones/", body, format="json")
    assert r.status_code == 201, r.data
    return r.data["id"]


# HU04 criterio 1 y 4: descuenta y registra fecha, usuario y cotización
def test_aprobar_descuenta_stock_y_registra_movimientos(mundo):
    cid = pedir(mundo, num_pintores=2, semanas_obra=2)  # 6 galones, 2 rodillos, 2 brochas
    r = mundo["adm"].post(f"/api/cotizaciones/{cid}/aprobar/")
    assert r.status_code == 200 and r.data["estado"] == "APROBADA"
    for k, esperado in (("latex", 4), ("rod", 8), ("bro", 8)):
        mundo[k].refresh_from_db()
        assert mundo[k].stock_actual == esperado
    movs = MovimientoInventario.objects.filter(cotizacion_id=cid)
    assert movs.count() == 3 and all(m.usuario == mundo["u_adm"] and m.tipo == "SALIDA" and m.fecha for m in movs)
    assert RegistroAuditoria.objects.filter(accion="APROBAR_COTIZACION", entidad_id=cid).exists()
    assert [h["estado_nuevo"] for h in r.data["historial"]] == ["PENDIENTE", "APROBADA"]
    # Látex quedó en 4 <= mínimo 5: alerta de reposición para el bodeguero
    assert [a["nombre"] for a in r.data["alertas_reposicion"]] == ["Látex"]


# HU04 criterio 3: si el cliente pone los materiales, el stock no cambia
def test_materiales_del_cliente_no_tocan_inventario(mundo):
    cid = pedir(mundo, origen="CLIENTE")
    assert mundo["adm"].post(f"/api/cotizaciones/{cid}/aprobar/").data["estado"] == "APROBADA"
    mundo["latex"].refresh_from_db()
    assert mundo["latex"].stock_actual == 10 and MovimientoInventario.objects.count() == 0


# HU04 criterio 2: sin stock negativo; todo o nada
def test_stock_insuficiente_no_aprueba_y_no_deja_cambios_parciales(mundo):
    cid = pedir(mundo, m2="1000", num_pintores=2, semanas_obra=2)  # 59 galones > 10 disponibles
    r = mundo["adm"].post(f"/api/cotizaciones/{cid}/aprobar/")
    assert r.status_code == 409 and r.data["faltantes"][0]["material"] == "Látex"
    assert Cotizacion.objects.get(pk=cid).estado == "PENDIENTE"
    for k in ("latex", "rod", "bro"):  # ni siquiera rodillos/brochas se descontaron
        mundo[k].refresh_from_db()
        assert mundo[k].stock_actual == 10
    assert MovimientoInventario.objects.count() == 0


def test_no_se_aprueba_dos_veces(mundo):
    cid = pedir(mundo)
    assert mundo["adm"].post(f"/api/cotizaciones/{cid}/aprobar/").status_code == 200
    assert mundo["adm"].post(f"/api/cotizaciones/{cid}/aprobar/").status_code == 400
    mundo["latex"].refresh_from_db()
    assert mundo["latex"].stock_actual == 4  # no se descontó dos veces


def test_no_se_aprueba_sin_calcular(mundo):
    r = mundo["cli"].post("/api/cotizaciones/", {"nombre_obra": "O", "direccion_obra": "X", "ciudad": "V",
                                                 "origen_materiales": "EMPRESA", "requiere_medicion": True}, format="json")
    assert mundo["adm"].post(f"/api/cotizaciones/{r.data['id']}/aprobar/").status_code == 400


def test_solo_el_administrador_aprueba(mundo):
    cid = pedir(mundo)
    assert mundo["eje"].post(f"/api/cotizaciones/{cid}/aprobar/").status_code == 403
    assert mundo["cli"].post(f"/api/cotizaciones/{cid}/aprobar/").status_code == 403


def test_rechazar_deja_historial_y_no_toca_stock(mundo):
    cid = pedir(mundo)
    r = mundo["eje"].post(f"/api/cotizaciones/{cid}/rechazar/", {"motivo": "Cliente no acepta precio"}, format="json")
    assert r.status_code == 200 and r.data["estado"] == "RECHAZADA"
    mundo["latex"].refresh_from_db()
    assert mundo["latex"].stock_actual == 10
    assert mundo["adm"].post(f"/api/cotizaciones/{cid}/aprobar/").status_code == 400  # ya rechazada
    assert mundo["cli"].post(f"/api/cotizaciones/{cid}/rechazar/").status_code == 403


# CU10: gestión del catálogo y stock
def test_admin_crea_material_y_registra_entrada(mundo):
    r = mundo["adm"].post("/api/materiales/", {"nombre": "Lija", "categoria": "Lija", "unidad": "unidad", "precio_unitario": 500, "stock_minimo": 5}, format="json")
    assert r.status_code == 201 and r.data["stock_actual"] == 0
    mid = r.data["id"]
    assert mundo["adm"].post(f"/api/materiales/{mid}/movimientos/", {"tipo": "ENTRADA", "cantidad": "20"}, format="json").status_code == 201
    assert Material.objects.get(pk=mid).stock_actual == 20


def test_el_stock_no_se_edita_directo_ni_queda_negativo(mundo):
    mid = mundo["latex"].pk
    mundo["adm"].patch(f"/api/materiales/{mid}/", {"stock_actual": 999}, format="json")
    mundo["latex"].refresh_from_db()
    assert mundo["latex"].stock_actual == 10
    r = mundo["adm"].post(f"/api/materiales/{mid}/movimientos/", {"tipo": "SALIDA", "cantidad": "11"}, format="json")
    assert r.status_code == 409
    assert mundo["adm"].post(f"/api/materiales/{mid}/movimientos/", {"tipo": "ENTRADA", "cantidad": "-3"}, format="json").status_code == 400
    assert mundo["adm"].post(f"/api/materiales/{mid}/movimientos/", {"tipo": "AJUSTE", "cantidad": "-4"}, format="json").status_code == 201
    mundo["latex"].refresh_from_db()
    assert mundo["latex"].stock_actual == 6


def test_permisos_inventario(mundo):
    assert mundo["cli"].get("/api/materiales/").status_code == 403
    assert mundo["eje"].get("/api/materiales/").status_code == 200
    assert mundo["eje"].post("/api/materiales/", {"nombre": "X"}, format="json").status_code == 403


def test_filtro_bajo_minimo(mundo):
    mundo["latex"].stock_actual = 3
    mundo["latex"].save()
    r = mundo["eje"].get("/api/materiales/?bajo_minimo=1")
    assert [m["nombre"] for m in r.data] == ["Látex"]


# HU08: PDF
def test_pdf_con_datos_del_cliente_items_y_total(mundo):
    cid = pedir(mundo, origen="EMPRESA")
    r = mundo["cli"].get(f"/api/cotizaciones/{cid}/pdf/")
    assert r.status_code == 200 and r["Content-Type"] == "application/pdf" and r.content.startswith(b"%PDF")
    assert f"COD-{cid:03d}" in r["Content-Disposition"]
    from apps.cotizaciones.pdf import generar_pdf
    assert len(generar_pdf(Cotizacion.objects.get(pk=cid))) > 1500


def test_pdf_no_disponible_si_no_esta_calculada(mundo):
    r = mundo["cli"].post("/api/cotizaciones/", {"nombre_obra": "O", "direccion_obra": "X", "ciudad": "V",
                                                 "origen_materiales": "CLIENTE", "requiere_medicion": True}, format="json")
    assert mundo["cli"].get(f"/api/cotizaciones/{r.data['id']}/pdf/").status_code == 409


def test_cliente_no_descarga_pdf_ajeno(mundo):
    cid = pedir(mundo)
    otro, _ = sesion(Rol.CLIENTE, "otro@x.cl", "22222222-2")
    assert otro.get(f"/api/cotizaciones/{cid}/pdf/").status_code == 404
    assert mundo["eje"].get(f"/api/cotizaciones/{cid}/pdf/").status_code == 200
