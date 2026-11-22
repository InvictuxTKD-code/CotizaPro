from rest_framework.response import Response
from rest_framework.views import APIView

from apps.usuarios.permisos import EsAdministrador

from .servicio import PERIODOS, calcular_indicadores


class DashboardView(APIView):
    """HU07 / CU12. Solo Gerente General (administrador). ?dias=30|90|365|0 (0 = todo)"""

    permission_classes = [EsAdministrador]

    def get(self, request):
        try:
            dias = int(request.query_params.get("dias", 90))
        except ValueError:
            dias = 90
        return Response(calcular_indicadores(dias if dias in PERIODOS else 90))
