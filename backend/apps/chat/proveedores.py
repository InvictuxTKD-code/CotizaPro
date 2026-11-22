"""Proveedores del modelo de lenguaje. Cambiar de proveedor = cambiar CHAT_PROVEEDOR en el .env (SLA-03).

Un proveedor recibe SOLO texto: instrucciones + mensajes ya anonimizados. Nunca accede a la base de datos.
Si no hay clave, o el servicio falla / demora, devuelve None y el sistema usa las respuestas predefinidas.
"""
import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

log = logging.getLogger(__name__)


class Proveedor:
    nombre = "ninguno"

    def responder(self, instrucciones, mensajes):  # -> str | None
        return None


class SinProveedor(Proveedor):
    """Modo sin clave: el chat funciona solo con respuestas predefinidas."""


class ClaudeProveedor(Proveedor):
    nombre = "claude"
    URL = "https://api.anthropic.com/v1/messages"

    def responder(self, instrucciones, mensajes):
        clave = settings.ANTHROPIC_API_KEY
        if not clave:
            return None
        cuerpo = json.dumps({"model": settings.CHAT_MODELO, "max_tokens": 400, "system": instrucciones, "messages": mensajes}).encode()
        req = urllib.request.Request(self.URL, data=cuerpo, method="POST", headers={
            "content-type": "application/json", "x-api-key": clave, "anthropic-version": "2023-06-01"})
        try:
            with urllib.request.urlopen(req, timeout=settings.CHAT_TIMEOUT_SEGUNDOS) as r:
                datos = json.load(r)
            texto = "".join(b.get("text", "") for b in datos.get("content", []) if b.get("type") == "text").strip()
            return texto or None
        except (urllib.error.URLError, TimeoutError, ValueError, OSError) as e:  # contingencia: respuestas predefinidas
            log.warning("Proveedor de chat no disponible: %s", e)
            return None


PROVEEDORES = {"claude": ClaudeProveedor, "ninguno": SinProveedor}


def obtener_proveedor():
    return PROVEEDORES.get(settings.CHAT_PROVEEDOR, SinProveedor)()
