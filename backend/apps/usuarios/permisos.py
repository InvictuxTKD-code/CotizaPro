from rest_framework.permissions import BasePermission

from .models import Rol


def _con_rol(*roles):
    class _Permiso(BasePermission):
        message = "Tu rol no tiene permiso para esta acción."

        def has_permission(self, request, view):
            u = request.user
            return bool(u and u.is_authenticated and u.rol in roles)

    return _Permiso


EsAdministrador = _con_rol(Rol.ADMINISTRADOR)
EsPersonalInterno = _con_rol(Rol.ADMINISTRADOR, Rol.EJECUTIVO)
EsCliente = _con_rol(Rol.CLIENTE)
