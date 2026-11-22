from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.auditoria.servicio import describir_cambios, registrar
from apps.usuarios.models import Rol
from apps.inventario.serializers import MaterialSerializer
from apps.inventario.servicio import StockInsuficiente
from apps.usuarios.permisos import EsAdministrador, EsPersonalInterno

from .calculo import DatosFaltantes
from .models import Cotizacion, DetalleCotizacion, TipoAcabado
from .serializers import (CotizacionCrearSerializer, CotizacionDetalleSerializer, CotizacionListaSerializer,
                          MedidasSerializer, TipoAcabadoAdminSerializer, TipoAcabadoSerializer)
from .pdf import generar_pdf
from .servicio import TransicionInvalida, aprobar, calcular_y_guardar, rechazar, registrar_estado


class AcabadosView(ListAPIView):
    """Catálogo de ítems de servicio visible para cualquier usuario autenticado."""

    permission_classes = [IsAuthenticated]
    serializer_class = TipoAcabadoSerializer
    queryset = TipoAcabado.objects.filter(activo=True)
    pagination_class = None


CAMPOS_ACABADO = ["nombre", "unidad", "precio_unitario", "precio_mano_obra", "material", "rendimiento_m2", "manos_recomendadas", "activo"]


class AcabadoViewSet(viewsets.ModelViewSet):
    """Catálogo de trabajos y precios. Lectura: personal interno. Alta y edición: solo administrador.
    No se borra: se desactiva (las cotizaciones antiguas siguen refiriéndose a él)."""

    serializer_class = TipoAcabadoAdminSerializer
    queryset = TipoAcabado.objects.select_related("material").order_by("nombre")
    http_method_names = ["get", "post", "patch", "head", "options"]
    pagination_class = None

    def get_permissions(self):
        return [(EsPersonalInterno if self.request.method in ("GET", "HEAD", "OPTIONS") else EsAdministrador)()]

    def perform_create(self, serializer):
        obj = serializer.save()
        registrar("CREAR_TRABAJO", "tipo_acabado", obj.pk, self.request.user,
                  f"{obj.nombre}: precio {obj.precio_unitario}", self.request)

    def perform_update(self, serializer):
        cambios = describir_cambios(serializer.instance, serializer.validated_data, CAMPOS_ACABADO)
        obj = serializer.save()
        if cambios:
            registrar("EDITAR_TRABAJO", "tipo_acabado", obj.pk, self.request.user, f"{obj.nombre} · {cambios}", self.request)


class CotizacionViewSet(mixins.CreateModelMixin, mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        u = self.request.user
        qs = Cotizacion.objects.select_related("cliente").prefetch_related("detalles", "insumos", "historial")
        if u.rol == Rol.CLIENTE:  # el cliente solo ve lo suyo
            return qs.filter(cliente__usuario=u)
        p = self.request.query_params  # HU06: filtros por cliente, estado y fecha
        if c := p.get("cliente"):
            filtro = Q(cliente__nombre_razon_social__icontains=c) | Q(cliente__rut__icontains=c)
            if c.isdigit() and len(c) <= 6:  # número corto = id de cliente
                filtro |= Q(cliente__id=int(c))
            qs = qs.filter(filtro)
        if e := p.get("estado"):
            qs = qs.filter(estado=e.upper())
        if d := p.get("desde"):
            qs = qs.filter(fecha_solicitud__date__gte=d)
        if h := p.get("hasta"):
            qs = qs.filter(fecha_solicitud__date__lte=h)
        return qs

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}

    def get_serializer_class(self):
        if self.action == "create":
            return CotizacionCrearSerializer
        return CotizacionDetalleSerializer if self.action == "retrieve" else CotizacionListaSerializer

    def create(self, request, *args, **kwargs):
        ser = CotizacionCrearSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        datos = ser.validated_data
        detalles = datos.pop("detalles", [])
        u = request.user

        if u.rol == Rol.CLIENTE:
            cliente = getattr(u, "cliente", None)
            if cliente is None:
                return Response({"detalle": "Tu cuenta no tiene un perfil de cliente."}, status=400)
            datos["cliente"] = cliente
        elif "cliente" not in datos:
            return Response({"cliente": "Indica el cliente."}, status=400)

        with transaction.atomic():
            cot = Cotizacion.objects.create(**datos, ejecutivo=u if u.rol == Rol.EJECUTIVO else None)
            DetalleCotizacion.objects.bulk_create([DetalleCotizacion(cotizacion=cot, unidad=d["tipo_acabado"].unidad, **d) for d in detalles])
            registrar_estado(cot, None, Cotizacion.Estado.PENDIENTE, u)
            registrar("CREAR_COTIZACION", "cotizacion", cot.pk, u, request=request)
            aviso = None
            if detalles and not cot.requiere_medicion:
                try:
                    calcular_y_guardar(cot, u, request)
                except DatosFaltantes as e:
                    aviso = e.faltantes
        if cot.requiere_medicion and not detalles:
            aviso = ["Falta medir en terreno: un supervisor cargará las medidas."]
        cot.refresh_from_db()
        out = CotizacionDetalleSerializer(cot, context={"request": request}).data
        return Response({**out, "avisos": aviso or []}, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"], permission_classes=[EsPersonalInterno])
    def calcular(self, request, pk=None):
        cot = self.get_object()
        if cot.estado != Cotizacion.Estado.PENDIENTE:
            return Response({"detalle": "Solo se recalculan cotizaciones pendientes."}, status=400)
        try:
            calcular_y_guardar(cot, request.user, request)
        except DatosFaltantes as e:
            return Response({"detalle": "No se puede calcular: faltan datos.", "faltantes": e.faltantes}, status=400)
        return Response(CotizacionDetalleSerializer(Cotizacion.objects.get(pk=cot.pk), context={"request": request}).data)

    @action(detail=True, methods=["put"], permission_classes=[EsPersonalInterno])
    def medidas(self, request, pk=None):
        """CU07: registra las medidas de terreno (reemplaza los ítems) y recalcula."""
        cot = self.get_object()
        if cot.estado != Cotizacion.Estado.PENDIENTE:
            return Response({"detalle": "Solo se pueden cargar medidas en cotizaciones pendientes."}, status=400)
        ser = MedidasSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        datos = ser.validated_data
        with transaction.atomic():
            cot.detalles.all().delete()
            DetalleCotizacion.objects.bulk_create(
                [DetalleCotizacion(cotizacion=cot, unidad=d["tipo_acabado"].unidad, **d) for d in datos["detalles"]])
            for campo in ("num_pintores", "semanas_obra"):
                if campo in datos:
                    setattr(cot, campo, datos[campo])
            cot.requiere_medicion = False
            if cot.ejecutivo_id is None and request.user.rol == Rol.EJECUTIVO:
                cot.ejecutivo = request.user
            cot.save()
            registrar("CARGAR_MEDIDAS", "cotizacion", cot.pk, request.user, request=request)
            try:
                calcular_y_guardar(cot, request.user, request)
            except DatosFaltantes as e:
                transaction.set_rollback(True)
                return Response({"detalle": "No se puede calcular: faltan datos.", "faltantes": e.faltantes}, status=400)
        return Response(CotizacionDetalleSerializer(Cotizacion.objects.get(pk=cot.pk), context={"request": request}).data)

    @action(detail=True, methods=["post"], permission_classes=[EsAdministrador])
    def aprobar(self, request, pk=None):
        """CU08: solo el administrador. Descuenta inventario si los materiales son de M y C (todo o nada)."""
        cot = self.get_object()
        try:
            bajo_minimo = aprobar(cot, request.user, request)
        except TransicionInvalida as e:
            return Response({"detalle": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except StockInsuficiente as e:
            return Response({"detalle": "No se puede aprobar: el stock no alcanza.", "faltantes": e.faltantes},
                            status=status.HTTP_409_CONFLICT)
        out = CotizacionDetalleSerializer(Cotizacion.objects.get(pk=cot.pk), context={"request": request}).data
        return Response({**out, "alertas_reposicion": MaterialSerializer(bajo_minimo, many=True).data})

    @action(detail=True, methods=["post"], permission_classes=[EsPersonalInterno])
    def rechazar(self, request, pk=None):
        cot = self.get_object()
        try:
            rechazar(cot, request.user, request.data.get("motivo"), request)
        except TransicionInvalida as e:
            return Response({"detalle": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(CotizacionDetalleSerializer(Cotizacion.objects.get(pk=cot.pk), context={"request": request}).data)

    @action(detail=True, methods=["get"])
    def pdf(self, request, pk=None):
        """HU08: solo si la cotización ya fue calculada. El cliente solo descarga las suyas (get_queryset)."""
        cot = self.get_object()
        if not cot.calculada:
            return Response({"detalle": "La cotización aún no está calculada: no hay presupuesto para descargar."},
                            status=status.HTTP_409_CONFLICT)
        resp = HttpResponse(generar_pdf(cot), content_type="application/pdf")
        resp["Content-Disposition"] = f'attachment; filename="presupuesto-COD-{cot.pk:03d}.pdf"'
        return resp
