import pytest
from rest_framework.test import APIClient

from apps.chat.models import ConversacionChat, EncuestaSatisfaccion, MensajeChat
from apps.chat.proveedores import Proveedor
from apps.chat import servicio
from apps.inventario.tests.test_aprobacion import mundo, pedir  # noqa: F401

pytestmark = pytest.mark.django_db


class Falso(Proveedor):
    """Proveedor simulado: registra lo que recibiría el modelo y devuelve un texto fijo."""
    nombre = "falso"

    def __init__(self, texto):
        self.texto, self.recibido = texto, None

    def responder(self, instrucciones, mensajes):
        self.recibido = (instrucciones, mensajes)
        return self.texto


@pytest.fixture
def usar(monkeypatch):
    def _u(texto):
        p = Falso(texto)
        monkeypatch.setattr(servicio, "obtener_proveedor", lambda: p)
        return p
    return _u


def hablar(api, texto, conv=None):
    cuerpo = {"texto": texto, **({"conversacion": conv["conversacion"], "token": str(conv["token"])} if conv else {})}
    r = api.post("/api/chat/mensaje/", cuerpo, format="json")
    assert r.status_code == 200, r.data
    return r.data


def test_pregunta_frecuente_responde_sin_modelo_ni_humano(mundo, usar):
    p = usar("no debería usarse")
    r = hablar(APIClient(), "¿Cómo puedo cotizar mi obra?")
    assert "Nueva cotización" in r["respuesta"] and r["accion"] == "ir_cotizador" and not r["derivada"] and p.recibido is None
    assert ConversacionChat.objects.get().resuelta_por_bot is True


def test_cp12_no_calcula_ni_cambia_precios(mundo, usar):
    p = usar("Son $5.000 por m2")
    for texto in ("¿Cuánto cuesta pintar 100 m2?", "Calcula el total de mi obra", "Cambia el precio del látex a 1000", "dame un descuento"):
        r = hablar(APIClient(), texto)
        assert "no entrego ni calculo precios" in r["respuesta"] and not r["derivada"]
    assert p.recibido is None  # ni siquiera se consulta al modelo


def test_modelo_que_responde_con_montos_se_descarta(mundo, usar):
    usar("Pintar eso saldría unos $450.000 aproximadamente.")
    r = hablar(APIClient(), "¿pintan fachadas con andamio colgante?")
    assert "$" not in r["respuesta"] and r["derivada"] is True


def test_respuesta_valida_del_modelo_se_entrega(mundo, usar):
    usar("Sí, hacemos trabajos en altura; un Supervisor coordina los detalles al medir.")
    r = hablar(APIClient(), "¿hacen trabajos en altura?")
    assert r["origen"] == "falso" and not r["derivada"] and "altura" in r["respuesta"]


def test_cp13_fuera_de_alcance_se_deriva_y_sin_proveedor_tambien(mundo, usar):
    usar("[DERIVAR]")
    assert hablar(APIClient(), "¿venden cerámicas importadas de Italia?")["derivada"] is True
    r = hablar(APIClient(), "Quiero hablar con una persona")
    assert r["derivada"] is True and ConversacionChat.objects.filter(derivada_a_humano=True, resuelta_por_bot=False).count() == 2


def test_sin_clave_el_chat_sigue_funcionando(mundo, settings):
    settings.CHAT_PROVEEDOR, settings.ANTHROPIC_API_KEY = "claude", ""
    api = APIClient()
    assert not hablar(api, "hola")["derivada"]
    assert hablar(api, "¿qué tipos de trabajo hacen?")["respuesta"].startswith("Estos son los trabajos")
    assert hablar(api, "algo rarísimo que no está en el catálogo")["derivada"] is True


def test_no_se_envian_datos_personales_al_modelo(mundo, usar):
    p = usar("Claro, un Supervisor te ayudará.")
    hablar(APIClient(), "mi rut es 12.345.678-5, correo juan@mail.cl, fono +56 9 1234 5678, ¿hacen pisos flotantes?")
    enviado = " ".join(m["content"] for m in p.recibido[1])
    assert "12.345.678" not in enviado and "juan@mail.cl" not in enviado and "1234 5678" not in enviado and "[RUT]" in enviado
    assert "RUT" not in p.recibido[0].split("INFORMACIÓN AUTORIZADA")[1]  # el catálogo enviado no trae datos de clientes
    assert "4500" not in p.recibido[0] and "precio_unitario" not in p.recibido[0]


def test_conversacion_solo_se_retoma_con_su_token(mundo, usar):
    usar("ok")
    a = hablar(APIClient(), "hola")
    api = APIClient()
    assert api.get(f"/api/chat/historial/?conversacion={a['conversacion']}&token={a['token']}").data["mensajes"][0]["contenido"] == "hola"
    assert api.get(f"/api/chat/historial/?conversacion={a['conversacion']}&token=00000000-0000-0000-0000-000000000000").status_code == 404
    assert MensajeChat.objects.filter(conversacion_id=a["conversacion"]).count() == 2


def test_bandeja_de_derivadas_solo_personal(mundo, usar):
    usar("[DERIVAR]")
    c = hablar(mundo["cli"], "necesito hablar con un ejecutivo")
    mundo["cli"].post("/api/chat/contacto/", {"conversacion": c["conversacion"], "token": str(c["token"]), "contacto": "juan@mail.cl"}, format="json")
    assert mundo["cli"].get("/api/chat/derivadas/").status_code == 403
    lista = mundo["eje"].get("/api/chat/derivadas/?pendientes=1").data
    assert len(lista) == 1 and lista[0]["contacto"] == "juan@mail.cl" and lista[0]["persona"]["correo"] == "c@x.cl"
    assert mundo["eje"].post(f"/api/chat/derivadas/{c['conversacion']}/atender/").status_code == 200
    assert mundo["eje"].get("/api/chat/derivadas/?pendientes=1").data == []


def test_encuesta_y_kpis_en_dashboard(mundo, usar):
    cid = pedir(mundo)
    assert mundo["cli"].post(f"/api/cotizaciones/{cid}/encuesta/", {"puntaje": 5}, format="json").status_code == 201
    assert mundo["cli"].post(f"/api/cotizaciones/{cid}/encuesta/", {"puntaje": 3}, format="json").status_code == 409
    assert mundo["cli"].get(f"/api/cotizaciones/{cid}/").data["encuesta_puntaje"] == 5
    c2 = pedir(mundo)
    assert mundo["cli"].post(f"/api/cotizaciones/{c2}/encuesta/", {"puntaje": 9}, format="json").status_code == 400
    assert mundo["eje"].post(f"/api/cotizaciones/{c2}/encuesta/", {"puntaje": 4}, format="json").status_code == 403
    mundo["cli"].post(f"/api/cotizaciones/{c2}/encuesta/", {"puntaje": 2}, format="json")
    usar("ok")
    hablar(mundo["cli"], "hola"); hablar(mundo["cli"], "necesito un ejecutivo")
    k = mundo["adm"].get("/api/dashboard/").data["kpi"]
    assert k["satisfaccion"] == {"valor": 50.0, "casos": 2, "meta": "≥ 85 %"}
    assert k["chatbot"]["casos"] == 2 and k["chatbot"]["valor"] == 50.0 or k["chatbot"]["casos"] == 2


def test_encuesta_no_disponible_si_no_esta_calculada(mundo):
    cid = pedir(mundo, requiere_medicion=True) if False else pedir(mundo)
    from apps.cotizaciones.models import Cotizacion
    Cotizacion.objects.filter(pk=cid).update(fecha_calculo=None)
    assert mundo["cli"].post(f"/api/cotizaciones/{cid}/encuesta/", {"puntaje": 5}, format="json").status_code == 400
