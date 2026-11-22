from rest_framework import viewsets

from apps.usuarios.permisos import EsAdministrador

from .models import RegistroAuditoria
from .serializers import RegistroAuditoriaSerializer


class AuditoriaViewSet(viewsets.ReadOnlyModelViewSet):
    """Bitácora de operaciones (solo administrador). ?entidad=material,tipo_acabado&limite=30"""

    permission_classes = [EsAdministrador]
    serializer_class = RegistroAuditoriaSerializer
    pagination_class = None

    def get_queryset(self):
        qs = RegistroAuditoria.objects.select_related("usuario")
        p = self.request.query_params
        if e := p.get("entidad"):
            qs = qs.filter(entidad__in=e.split(","))
        if a := p.get("accion"):
            qs = qs.filter(accion__in=a.split(","))
        try:
            limite = max(1, min(int(p.get("limite", 30)), 200))
        except ValueError:
            limite = 30
        return qs[:limite]
