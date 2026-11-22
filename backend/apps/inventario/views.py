from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.auditoria.servicio import describir_cambios, registrar
from apps.usuarios.permisos import EsAdministrador, EsPersonalInterno

from .models import Material, MovimientoInventario
from .serializers import MaterialSerializer, MovimientoEntradaSerializer, MovimientoSerializer
from .servicio import MovimientoInvalido, StockInsuficiente, mover_stock


class MaterialViewSet(viewsets.ModelViewSet):
    """CU10. Lectura para el personal interno; altas, ediciones y movimientos solo el administrador."""

    serializer_class = MaterialSerializer
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None

    def get_permissions(self):
        return [(EsPersonalInterno if self.request.method in ("GET", "HEAD", "OPTIONS") else EsAdministrador)()]

    def get_queryset(self):
        qs = Material.objects.all()
        p = self.request.query_params
        if c := p.get("categoria"):
            qs = qs.filter(categoria__iexact=c)
        if p.get("bajo_minimo") in ("1", "true"):  # alerta de reposición para el bodeguero
            from django.db.models import F
            qs = qs.filter(stock_actual__lte=F("stock_minimo"))
        return qs

    def perform_create(self, serializer):
        m = serializer.save()
        registrar("CREAR_MATERIAL", "material", m.pk, self.request.user, f"{m.nombre}: precio {m.precio_unitario}", self.request)

    def perform_update(self, serializer):
        cambios = describir_cambios(serializer.instance, serializer.validated_data,
                                    ["nombre", "categoria", "unidad", "precio_unitario", "stock_minimo", "activo"])
        m = serializer.save()
        if cambios:
            registrar("EDITAR_MATERIAL", "material", m.pk, self.request.user, f"{m.nombre} · {cambios}", self.request)

    @action(detail=True, methods=["post"])
    def movimientos(self, request, pk=None):
        material = self.get_object()
        ser = MovimientoEntradaSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        try:
            mov = mover_stock(material.pk, request=request, usuario=request.user, **ser.validated_data)
        except StockInsuficiente as e:
            return Response({"detalle": "El stock no puede quedar negativo.", "faltantes": e.faltantes}, status=status.HTTP_409_CONFLICT)
        except MovimientoInvalido as e:
            return Response({"detalle": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(MovimientoSerializer(mov).data, status=status.HTTP_201_CREATED)


class MovimientoViewSet(viewsets.ReadOnlyModelViewSet):
    permission_classes = [EsPersonalInterno]
    serializer_class = MovimientoSerializer

    def get_queryset(self):
        qs = MovimientoInventario.objects.select_related("material", "usuario")
        p = self.request.query_params
        if m := p.get("material"):
            qs = qs.filter(material_id=m)
        if c := p.get("cotizacion"):
            qs = qs.filter(cotizacion_id=c)
        return qs
