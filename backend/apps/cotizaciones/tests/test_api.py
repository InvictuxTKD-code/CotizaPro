import pytest
from rest_framework.test import APIClient

from apps.clientes.models import Cliente
from apps.cotizaciones.models import Cotizacion, TipoAcabado
from apps.inventario.models import Material
from apps.usuarios.models import Rol, Usuario

pytestmark = pytest.mark.django_db
CLAVE = "ClaveSegura123"


def cliente_api(rol, correo, rut="11111111-1", con_cliente=False):
    u = Usuario.objects.create_user(correo, CLAVE, nombre=correo, rol=rol)
    c = Cliente.objects.create(usuario=u, tipo="PARTICULAR", nombre_razon_social=f"Cliente {correo}", rut=rut, correo_contacto=correo) if con_cliente else None
    api = APIClient()
    api.credentials(HTTP_AUTHORIZATION="Bearer " + api.post("/api/auth/login/", {"correo": correo, "password": CLAVE}, format="json").data["access"])
    return api, u, c


@pytest.fixture
def catalogo():
    latex = Material.objects.create(nombre="Látex", categoria="Pintura", unidad="galón", precio_unitario=20000)
    Material.objects.create(nombre="Rodillo", categoria="Rodillo", unidad="unidad", precio_unitario=3000)
    Material.objects.create(nombre="Brocha", categoria="Brocha", unidad="unidad", precio_unitario=2000)
    return TipoAcabado.objects.create(nombre="Pintura látex", unidad="M2", precio_unitario=4500, precio_mano_obra=2500, material=latex, rendimiento_m2=34)


def solicitud(acabado, **extra):
    return {"nombre_obra": "Casa Pérez", "direccion_obra": "Calle 1", "ciudad": "Valdivia", "origen_materiales": "CLIENTE",
            "detalles": [{"descripcion": "Muros", "textura": "NORMAL", "cantidad": "100", "tipo_acabado": acabado.pk}], **extra}


def test_registro_de_cliente_y_login():
    api = APIClient()
    r = api.post("/api/auth/registro/", {"nombre": "Ana", "correo": "ana@x.cl", "password": CLAVE, "tipo": "PARTICULAR",
                                         "nombre_razon_social": "Ana Soto", "rut": "12.345.678-5"}, format="json")
    assert r.status_code == 201
    assert Usuario.objects.get(correo="ana@x.cl").rol == "CLIENTE"
    assert Cliente.objects.get(rut="12345678-5")
    assert api.post("/api/auth/login/", {"correo": "ana@x.cl", "password": CLAVE}, format="json").status_code == 200


def test_registro_rechaza_rut_invalido_y_no_permite_elegir_rol():
    api = APIClient()
    base = {"nombre": "A", "correo": "a@x.cl", "password": CLAVE, "tipo": "PARTICULAR", "nombre_razon_social": "A"}
    assert api.post("/api/auth/registro/", {**base, "rut": "12.345.678-9"}, format="json").status_code == 400
    api.post("/api/auth/registro/", {**base, "rut": "12.345.678-5", "rol": "ADMINISTRADOR"}, format="json")
    assert Usuario.objects.get(correo="a@x.cl").rol == "CLIENTE"


# HU02: la solicitud se registra con fecha y estado pendiente; HU03: se calcula sola
def test_cliente_solicita_y_obtiene_presupuesto_automatico(catalogo):
    api, u, c = cliente_api(Rol.CLIENTE, "c@x.cl", con_cliente=True)
    r = api.post("/api/cotizaciones/", solicitud(catalogo), format="json")
    assert r.status_code == 201
    assert r.data["estado"] == "PENDIENTE" and r.data["fecha_solicitud"]
    assert r.data["neto"] == 250000 and r.data["iva"] == 0 and r.data["total"] == 250000  # 100 m² × $2.500 solo mano de obra
    assert r.data["historial"][0]["estado_anterior"] is None and r.data["historial"][0]["estado_nuevo"] == "PENDIENTE"


def test_formulario_valida_campos_obligatorios(catalogo):
    api, *_ = cliente_api(Rol.CLIENTE, "c@x.cl", con_cliente=True)
    r = api.post("/api/cotizaciones/", {"ciudad": "Valdivia"}, format="json")
    assert r.status_code == 400 and "nombre_obra" in r.data and "origen_materiales" in r.data


def test_sin_items_ni_medicion_se_rechaza(catalogo):
    api, *_ = cliente_api(Rol.CLIENTE, "c@x.cl", con_cliente=True)
    body = solicitud(catalogo)
    body["detalles"] = []
    assert api.post("/api/cotizaciones/", body, format="json").status_code == 400


def test_cantidad_cero_se_rechaza(catalogo):
    api, *_ = cliente_api(Rol.CLIENTE, "c@x.cl", con_cliente=True)
    body = solicitud(catalogo)
    body["detalles"][0]["cantidad"] = "0"
    assert api.post("/api/cotizaciones/", body, format="json").status_code == 400


def test_si_el_cliente_pone_materiales_se_ignoran_datos_de_inventario(catalogo):
    api, *_ = cliente_api(Rol.CLIENTE, "c@x.cl", con_cliente=True)
    r = api.post("/api/cotizaciones/", solicitud(catalogo, num_pintores=3, semanas_obra=4), format="json")
    assert r.data["num_pintores"] is None


def test_obra_vendida_cobra_precio_completo_y_oculta_costos_internos_al_cliente(catalogo):
    api, *_ = cliente_api(Rol.CLIENTE, "c@x.cl", con_cliente=True)
    r = api.post("/api/cotizaciones/", solicitud(catalogo, origen_materiales="EMPRESA", num_pintores=2, semanas_obra=2), format="json")
    assert r.data["neto"] == 450000  # 100 m² × $4.500: materiales e insumos incluidos, no se suman
    # El cliente no ve consumo ni costos internos
    assert "insumos" not in r.data and "costo_interno_materiales" not in r.data
    assert not {"cantidad_material", "costo_materiales", "material_nombre"} & set(r.data["detalles"][0])
    # El personal de M y C sí: 6 galones, 2 rodillos y 2 brochas
    ejec, *_ = cliente_api(Rol.EJECUTIVO, "e@x.cl", rut="9-9")
    d = ejec.get(f"/api/cotizaciones/{r.data['id']}/").data
    assert d["detalles"][0]["cantidad_material"] == 6 and len(d["insumos"]) == 2
    assert d["costo_interno_materiales"] == 120000 + 6000 + 4000


# CU07: faltan medidas -> se registra pendiente, sin cálculo; el ejecutivo carga medidas y se calcula
def test_flujo_medicion_en_terreno(catalogo):
    cli, *_ = cliente_api(Rol.CLIENTE, "c@x.cl", con_cliente=True)
    r = cli.post("/api/cotizaciones/", {"nombre_obra": "Obra", "direccion_obra": "X", "ciudad": "Valdivia",
                                        "origen_materiales": "CLIENTE", "requiere_medicion": True}, format="json")
    assert r.status_code == 201 and r.data["calculada"] is False and r.data["total"] is None and r.data["avisos"]
    ejec, *_ = cliente_api(Rol.EJECUTIVO, "e@x.cl", rut="2-7")
    r2 = ejec.put(f"/api/cotizaciones/{r.data['id']}/medidas/", {"detalles": solicitud(catalogo)["detalles"]}, format="json")
    assert r2.status_code == 200 and r2.data["total"] == 250000 and r2.data["requiere_medicion"] is False
    assert cli.put(f"/api/cotizaciones/{r.data['id']}/medidas/", {"detalles": []}, format="json").status_code == 403


def test_cliente_no_calcula_ni_ve_cotizaciones_ajenas(catalogo):
    a, *_ = cliente_api(Rol.CLIENTE, "a@x.cl", rut="11111111-1", con_cliente=True)
    b, *_ = cliente_api(Rol.CLIENTE, "b@x.cl", rut="22222222-2", con_cliente=True)
    id_a = a.post("/api/cotizaciones/", solicitud(catalogo), format="json").data["id"]
    assert b.get(f"/api/cotizaciones/{id_a}/").status_code == 404
    assert b.get("/api/cotizaciones/").data["count"] == 0 if "count" in b.get("/api/cotizaciones/").data else b.get("/api/cotizaciones/").data == []
    assert a.post(f"/api/cotizaciones/{id_a}/calcular/").status_code == 403


# HU06: historial filtrable por cliente, estado y fecha
def test_filtros_del_historial(catalogo):
    a, *_ = cliente_api(Rol.CLIENTE, "a@x.cl", rut="11111111-1", con_cliente=True)
    b, *_ = cliente_api(Rol.CLIENTE, "b@x.cl", rut="22222222-2", con_cliente=True)
    a.post("/api/cotizaciones/", solicitud(catalogo), format="json")
    b.post("/api/cotizaciones/", solicitud(catalogo), format="json")
    Cotizacion.objects.filter(cliente__rut="22222222-2").update(estado="APROBADA")
    ejec, *_ = cliente_api(Rol.EJECUTIVO, "e@x.cl", rut="3-5")

    def n(qs):
        d = ejec.get(f"/api/cotizaciones/{qs}").data
        return len(d["results"] if isinstance(d, dict) and "results" in d else d)

    assert n("") == 2
    assert n("?estado=aprobada") == 1
    assert n("?cliente=Cliente b@x") == 1
    assert n("?cliente=22222222") == 1
    assert n("?desde=2999-01-01") == 0
    assert n("?desde=2000-01-01&hasta=2999-01-01") == 2
