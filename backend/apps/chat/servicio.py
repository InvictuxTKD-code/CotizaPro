"""Asistente virtual (HU05 / CU05).

Reparto de responsabilidades (tesis, tabla 3.18):
  - Django decide ANTES de llamar al modelo: rechaza pedir/calcular precios y deriva a una persona cuando corresponde.
  - El modelo solo redacta respuestas con información pública del catálogo (nombres de trabajos, sin precios ni datos de clientes).
  - Django revisa DESPUÉS lo que respondió el modelo: si trae montos de dinero, lo descarta.
  - Si el proveedor no está disponible, responde con textos predefinidos.
"""
import re
import unicodedata

from django.utils import timezone

from apps.cotizaciones.models import TipoAcabado

from .models import ConversacionChat, MensajeChat
from .proveedores import obtener_proveedor

MAX_TEXTO = 600
HISTORIAL_AL_MODELO = 8

MSG_PRECIOS = ("Por chat no entrego ni calculo precios: los valores los calcula el cotizador con las reglas de M y C, "
               "para que siempre sean correctos. Ingresa los datos de tu obra en «Nueva cotización» y obtendrás el presupuesto detallado, "
               "que además puedes descargar en PDF.")
MSG_DERIVAR = ("Entendido. Voy a derivar tu consulta a un Supervisor de M y C para que te contacte. "
               "Si quieres, déjanos un correo o teléfono para poder responderte.")
MSG_FUERA = ("Esa consulta excede lo que puedo resolver por aquí, así que la derivo a un Supervisor de M y C para que te contacte. "
             "Puedes dejarnos un correo o teléfono.")
MSG_SALUDO = "¡Hola! Soy el asistente de M y C Revestimientos y Pinturas. Puedo resolver dudas sobre cómo cotizar, los servicios y el proceso. ¿En qué te ayudo?"

# --- Reglas previas al modelo -------------------------------------------------------------------
def _norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")


RE_PRECIO = re.compile(r"\b(precio|precios|cuanto (cuesta|cobran|sale|vale|seria|es)|cuanto me (sale|cobran|costaria)|valor|tarifa|cotiza(me|r)? (esto|el|la)? ?precio|calcul[ao]|calcular|descuento|rebaja|presupuesto de|cambia(r)? (el )?precio|modifica(r)? (el )?(precio|valor)|total)\b")
RE_HUMANO = re.compile(r"\b(persona|humano|ejecutivo|supervisor|vendedor|asesor|llamar|llamen|telefono|reclamo|reclamar|queja|hablar con|contactar|urgente)\b")
RE_SALUDO = re.compile(r"^(hola|buenas|buenos dias|buenas tardes|buenas noches|hey|ola)\b[\s!.¡]*$")
RE_DINERO = re.compile(r"(\$\s?\d|\d[\d.,]*\s?(pesos|clp|uf|usd|dolares|mil pesos)|\b(clp|uf)\s?\d)", re.I)
# Datos personales que no deben viajar al proveedor externo
RE_RUT = re.compile(r"\b\d{1,2}\.?\d{3}\.?\d{3}-?[\dkK]\b")
RE_CORREO = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
RE_TEL = re.compile(r"(\+?56)?\s?9[\s-]?\d{4}[\s-]?\d{4}\b")


def anonimizar(texto):
    for rx, rep in ((RE_RUT, "[RUT]"), (RE_CORREO, "[CORREO]"), (RE_TEL, "[TELÉFONO]")):
        texto = rx.sub(rep, texto)
    return texto


# --- Preguntas frecuentes (modo sin modelo y contingencia) -------------------------------------
def _faq():
    trabajos = ", ".join(TipoAcabado.objects.filter(activo=True).order_by("nombre").values_list("nombre", flat=True)) or "pintura y acabados"
    return [
        (("como cotiz", "como pido", "como solicit", "pasos para", "proceso de cotiz", "como empiezo", "como inicio", "quiero cotizar", "necesito cotizar", "puedo cotizar", "como hago para cotizar", "como cotizo", "cotizar mi obra", "cotizar una obra"),
         "Para cotizar: 1) regístrate o inicia sesión, 2) entra a «Nueva cotización», 3) indica los datos de la obra, si los materiales los pone M y C o tú, "
         "y los trabajos con sus metros, 4) envía la solicitud. El sistema calcula el presupuesto y puedes descargarlo en PDF.", "ir_cotizador"),
        (("quien pone los material", "quien pone la pintura", "obra vendida", "incluye los material", "materiales incluidos"),
         "Tú eliges: si los materiales los pone M y C, el valor por m² los incluye (obra vendida). Si los pone tu obra, se cotiza solo la mano de obra y no se descuenta inventario de M y C.", None),
        (("no tengo las medidas", "no tengo medidas", "no se cuantos metros", "no se cuanto mide", "medicion en terreno", "visita a terreno"),
         "Si aún no tienes las medidas, marca «No tengo las medidas» al solicitar. La solicitud queda registrada y un Supervisor coordina la medición en terreno antes de calcular.", "ir_cotizador"),
        (("que servicios", "que trabajos", "que hacen", "que ofrecen", "tipos de trabajo", "que cotizan", "que pintan"),
         f"Estos son los trabajos que cotizamos: {trabajos}.", None),
        (("pdf", "descargar el presupuesto", "descargo el presupuesto", "documento del presupuesto"),
         "Cuando tu cotización ya está calculada, puedes descargar el presupuesto en PDF desde «Mis cotizaciones». Allí se detalla cada trabajo y el total neto.", None),
        (("iva", "impuesto", "neto"),
         "Los presupuestos de M y C se informan en valores netos; el IVA lo considera la empresa que recibe la cotización.", None),
        (("vigencia", "valida", "cuanto dura", "caduca"),
         "El presupuesto en PDF indica 30 días de vigencia.", None),
        (("estado de mi cotizacion", "mi cotizacion esta", "cotizacion pendiente", "cotizacion aprobada", "seguimiento de mi"),
         "Tu cotización puede estar Pendiente (en revisión), Aprobada o Rechazada. Puedes ver el estado y su historial en «Mis cotizaciones».", None),
        (("donde estan", "donde trabajan", "ubicacion", "estan en valdivia", "cobertura"),
         "M y C Revestimientos y Pinturas SpA trabaja desde Valdivia. Para consultas de cobertura de otras zonas, puedo derivarte a un Supervisor.", None),
    ]


def respuesta_predefinida(texto):
    t = _norm(texto)
    if RE_SALUDO.match(t):
        return MSG_SALUDO, None
    for claves, resp, accion in _faq():
        if any(c in t for c in claves):
            return resp, accion
    return None, None


def _instrucciones():
    trabajos = ", ".join(TipoAcabado.objects.filter(activo=True).order_by("nombre").values_list("nombre", flat=True))
    return f"""Eres el asistente virtual de M y C Revestimientos y Pinturas SpA (Valdivia, Chile). Respondes en español, de forma breve (máximo 4 frases), cordial y profesional.
Tu función: resolver dudas sobre el proceso de cotización y los servicios, y guiar al cliente para usar la plataforma CotizaPro.

REGLAS OBLIGATORIAS
- NUNCA des, estimes, calcules ni modifiques precios, montos, descuentos, totales ni stock. No menciones cifras de dinero. Si te lo piden, indica que el cotizador de la plataforma calcula el presupuesto.
- NO inventes información. Usa solo lo que está en estas instrucciones. Si no lo sabes, no puedes resolverlo o la persona pide hablar con alguien, responde exactamente: [DERIVAR]
- No pidas ni repitas RUT, correo ni teléfono.
- Si la persona quiere cotizar, explícale los pasos e invítala a usar «Nueva cotización». Tú no ejecutas acciones.

INFORMACIÓN AUTORIZADA
- Pasos para cotizar: registrarse o iniciar sesión → «Nueva cotización» → datos de la obra → elegir si los materiales los pone M y C o la obra → agregar trabajos con sus m² o metros lineales → enviar. El sistema calcula el presupuesto; se descarga en PDF cuando está calculado.
- Si los materiales los pone M y C, el valor por m² incluye materiales (obra vendida). Si los pone el cliente, se cotiza solo mano de obra.
- Si el cliente no tiene medidas, puede marcar «No tengo las medidas»; un Supervisor coordina la medición.
- Los presupuestos se informan en valores netos (sin IVA) y tienen 30 días de vigencia. Estados: Pendiente, Aprobada, Rechazada.
- Trabajos que se cotizan: {trabajos}.
"""


def _hay_dinero(texto):
    return bool(RE_DINERO.search(texto))


def _guardar(conv, emisor, contenido):
    return MensajeChat.objects.create(conversacion=conv, emisor=emisor, contenido=contenido)


def procesar_mensaje(conv, texto, proveedor=None):
    """Devuelve dict(respuesta, derivada, accion, origen). Registra la conversación completa."""
    texto = texto.strip()[:MAX_TEXTO]
    _guardar(conv, "USUARIO", texto)
    t = _norm(texto)
    proveedor = proveedor or obtener_proveedor()
    derivada, accion, origen = False, None, "reglas"

    if RE_PRECIO.search(t):  # CP-12: no calcula ni cambia precios
        resp, accion = MSG_PRECIOS, "ir_cotizador"
    elif RE_HUMANO.search(t):
        resp, derivada = MSG_DERIVAR, True
    else:
        resp, accion = respuesta_predefinida(texto)
        if resp is None:
            historial = list(conv.mensajes.order_by("-id")[:HISTORIAL_AL_MODELO])[::-1]
            msgs = []
            for m in historial:
                rol = "user" if m.emisor == "USUARIO" else "assistant"
                contenido = anonimizar(m.contenido)
                if msgs and msgs[-1]["role"] == rol:
                    msgs[-1]["content"] += "\n" + contenido
                else:
                    msgs.append({"role": rol, "content": contenido})
            while msgs and msgs[0]["role"] != "user":
                msgs.pop(0)
            salida = proveedor.responder(_instrucciones(), msgs) if msgs else None
            if salida and "[DERIVAR]" not in salida and not _hay_dinero(salida):
                resp, origen = salida, proveedor.nombre
            else:  # sin proveedor, falla, pide derivar, o intentó dar montos → derivación segura
                resp, derivada = MSG_FUERA, True
                origen = "reglas" if not salida else proveedor.nombre

    _guardar(conv, "ASISTENTE", resp)
    cambios = []
    if derivada and not conv.derivada_a_humano:
        conv.derivada_a_humano, conv.resuelta_por_bot = True, False
        cambios += ["derivada_a_humano", "resuelta_por_bot"]
    elif not derivada and not conv.derivada_a_humano and not conv.resuelta_por_bot:
        conv.resuelta_por_bot = True
        cambios.append("resuelta_por_bot")
    conv.fecha_fin = timezone.now()
    cambios.append("fecha_fin")
    conv.save(update_fields=cambios)
    return {"respuesta": resp, "derivada": conv.derivada_a_humano, "accion": accion, "origen": origen}
