from django.contrib.auth import authenticate
from django.conf import settings
from django.db import transaction
from rest_framework import generics, status, viewsets
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.auditoria.servicio import registrar

from apps.cotizaciones.models import HistorialEstado
from apps.inventario.models import MovimientoInventario

from .models import Rol, Usuario
from .permisos import EsAdministrador
from .serializers import LoginSerializer, PerfilSerializer, UsuarioSerializer

ERROR_CREDENCIALES = "Correo o contraseña incorrectos."


class LoginView(APIView):
    """HU01: rechaza credenciales inválidas, bloquea tras 3 fallos seguidos y devuelve JWT + perfil."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        ser = LoginSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        correo = ser.validated_data["correo"].lower()
        password = ser.validated_data["password"]

        usuario = Usuario.objects.filter(correo=correo).first()

        if usuario and usuario.esta_bloqueado():
            return Response(
                {"detalle": f"Cuenta bloqueada temporalmente por intentos fallidos. Intenta de nuevo en {settings.MINUTOS_BLOQUEO} minutos."},
                status=status.HTTP_423_LOCKED,
            )

        autenticado = authenticate(request, username=correo, password=password) if usuario else None
        if autenticado is None:
            if usuario and usuario.activo:
                if usuario.registrar_fallo():
                    registrar("BLOQUEO_CUENTA", "usuario", usuario.pk, usuario, "3 intentos fallidos seguidos", request)
            # Mismo mensaje exista o no el correo: no se filtra qué cuentas existen.
            return Response({"detalle": ERROR_CREDENCIALES}, status=status.HTTP_401_UNAUTHORIZED)

        autenticado.registrar_acceso()
        refresh = RefreshToken.for_user(autenticado)
        refresh["rol"] = autenticado.rol
        refresh["nombre"] = autenticado.nombre
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh), "usuario": PerfilSerializer(autenticado).data}
        )


class PerfilView(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PerfilSerializer

    def get_object(self):
        return self.request.user


class UsuarioViewSet(viewsets.ModelViewSet):
    """CU11: el administrador crea usuarios, asigna roles y desactiva (sin borrar historial)."""

    permission_classes = [EsAdministrador]
    serializer_class = UsuarioSerializer
    queryset = Usuario.objects.all().order_by("nombre")
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def destroy(self, request, *args, **kwargs):
        """Eliminación definitiva (solo administrador). Se rechaza si dejaría el sistema sin administrador
        o si la persona tiene historial (cotizaciones, aprobaciones, movimientos): ahí se desactiva."""
        u = self.get_object()
        if u.pk == request.user.pk:
            return Response({"detalle": "No puedes eliminar tu propia cuenta."}, status=status.HTTP_400_BAD_REQUEST)
        if u.rol == Rol.ADMINISTRADOR and not Usuario.objects.filter(rol=Rol.ADMINISTRADOR, activo=True).exclude(pk=u.pk).exists():
            return Response({"detalle": "No se puede eliminar al único administrador activo."}, status=status.HTTP_400_BAD_REQUEST)
        cliente = getattr(u, "cliente", None)
        con_historial = (
            HistorialEstado.objects.filter(usuario=u).exists()
            or MovimientoInventario.objects.filter(usuario=u).exists()
            or (cliente is not None and cliente.cotizaciones.exists())
        )
        if con_historial:
            return Response(
                {"detalle": f"{u.nombre} tiene historial en el sistema (cotizaciones, aprobaciones o movimientos), por lo que no se puede eliminar sin perder trazabilidad. Desactívalo: no podrá iniciar sesión y su historial se conserva."},
                status=status.HTTP_409_CONFLICT,
            )
        detalle = f"{u.nombre} <{u.correo}> ({u.rol})"
        pk = u.pk
        with transaction.atomic():
            if cliente is not None:
                cliente.delete()
            u.delete()
        registrar("ELIMINAR_USUARIO", "usuario", pk, request.user, detalle, request)
        return Response(status=status.HTTP_204_NO_CONTENT)
