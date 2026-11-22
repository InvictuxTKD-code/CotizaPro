from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import RegistroClienteSerializer


class RegistroClienteView(APIView):
    """Autorregistro de clientes (siempre rol CLIENTE; nunca se puede pedir otro rol)."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        ser = RegistroClienteSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        cliente = ser.save()
        return Response({"id": cliente.pk, "correo": cliente.correo_contacto}, status=status.HTTP_201_CREATED)
