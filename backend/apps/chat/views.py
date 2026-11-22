from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from apps.auditoria.servicio import registrar
from apps.cotizaciones.models import Cotizacion
from apps.usuarios.permisos import EsCliente, EsPersonalInterno

from .models import ConversacionChat, EncuestaSatisfaccion
from .serializers import ConversacionStaffSerializer, EncuestaSerializer, EntradaMensajeSerializer, MensajeSerializer
from .servicio import MSG_SALUDO, procesar_mensaje


def _conversacion(request, datos, crear=False):
    """Una conversación solo se retoma con su id y su token (visitantes incluidos)."""
    if datos.get("conversacion") and datos.get("token"):
        return get_object_or_404(ConversacionChat, pk=datos["conversacion"], token=datos["token"])
    if not crear:
        return None
    u = request.user if request.user.is_authenticated else None
    return ConversacionChat.objects.create(usuario=u)


class _Publica(APIView):
    permission_classes = [AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "chat"


class MensajeView(_Publica):
    """CU05: el usuario (cliente o visitante) escribe y el asistente responde."""

    def post(self, request):
        ser = EntradaMensajeSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        conv = _conversacion(request, ser.validated_data, crear=True)
        res = procesar_mensaje(conv, ser.validated_data["texto"])
        if res["derivada"]:
            registrar("DERIVAR_CHAT", "conversacion_chat", conv.pk, request.user if request.user.is_authenticated else None, "Consulta derivada a un Supervisor", request)
        return Response({"conversacion": conv.pk, "token": conv.token, **res})


class HistorialView(_Publica):
    def get(self, request):
        ser = EntradaMensajeSerializer(data={**request.query_params.dict(), "texto": "-"})
        ser.is_valid(raise_exception=True)
        conv = _conversacion(request, ser.validated_data)
        if conv is None:
            return Response({"mensajes": [], "derivada": False, "saludo": MSG_SALUDO})
        return Response({"mensajes": MensajeSerializer(conv.mensajes.all(), many=True).data, "derivada": conv.derivada_a_humano, "contacto": conv.contacto})


class ContactoView(_Publica):
    """La persona deja un correo o teléfono para que un ejecutivo la contacte (no se envía al modelo)."""

    def post(self, request):
        ser = EntradaMensajeSerializer(data={**request.data, "texto": "-"})
        ser.is_valid(raise_exception=True)
        conv = _conversacion(request, ser.validated_data)
        contacto = str(request.data.get("contacto", "")).strip()[:150]
        if conv is None or not contacto:
            return Response({"detalle": "Indica un correo o teléfono de contacto."}, status=status.HTTP_400_BAD_REQUEST)
        conv.contacto = contacto
        conv.save(update_fields=["contacto"])
        return Response({"ok": True})


class DerivadasView(APIView):
    """Bandeja del personal: consultas que el asistente derivó. ?pendientes=1 solo las no atendidas."""

    permission_classes = [EsPersonalInterno]

    def get(self, request):
        qs = ConversacionChat.objects.filter(derivada_a_humano=True).select_related("usuario").prefetch_related("mensajes")
        if request.query_params.get("pendientes") == "1":
            qs = qs.filter(atendida=False)
        return Response(ConversacionStaffSerializer(qs[:50], many=True).data)


class AtenderView(APIView):
    permission_classes = [EsPersonalInterno]

    def post(self, request, pk):
        conv = get_object_or_404(ConversacionChat, pk=pk, derivada_a_humano=True)
        conv.atendida = True
        conv.save(update_fields=["atendida"])
        registrar("ATENDER_CHAT", "conversacion_chat", conv.pk, request.user, "Consulta derivada atendida", request)
        return Response({"ok": True})


class EncuestaView(APIView):
    """Encuesta de una pregunta (1 a 5) al descargar el presupuesto. Solo el dueño, una vez por cotización."""

    permission_classes = [EsCliente]

    def post(self, request, pk):
        cot = get_object_or_404(Cotizacion, pk=pk, cliente__usuario=request.user)
        if not cot.calculada:
            return Response({"detalle": "La cotización aún no está calculada."}, status=status.HTTP_400_BAD_REQUEST)
        if EncuestaSatisfaccion.objects.filter(cotizacion=cot).exists():
            return Response({"detalle": "Ya respondiste la encuesta de esta cotización. ¡Gracias!"}, status=status.HTTP_409_CONFLICT)
        ser = EncuestaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        ser.save(cotizacion=cot)
        return Response(ser.data, status=status.HTTP_201_CREATED)
