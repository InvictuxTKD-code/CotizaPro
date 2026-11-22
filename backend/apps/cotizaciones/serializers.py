from rest_framework import serializers

from apps.clientes.models import Cliente
from apps.inventario.models import Material

from .models import Cotizacion, DetalleCotizacion, HistorialEstado, InsumoCotizacion, TipoAcabado


def es_cliente(request):
    u = getattr(request, "user", None)
    return bool(u and u.is_authenticated and u.rol == "CLIENTE")


class TipoAcabadoSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoAcabado
        fields = ["id", "nombre", "unidad", "precio_unitario"]


class TipoAcabadoAdminSerializer(serializers.ModelSerializer):
    """Trabajo del catálogo con todos sus precios y reglas. Solo el administrador lo modifica."""

    material = serializers.PrimaryKeyRelatedField(queryset=Material.objects.all(), allow_null=True, required=False)
    material_nombre = serializers.CharField(source="material.nombre", read_only=True, default=None)

    class Meta:
        model = TipoAcabado
        fields = ["id", "nombre", "unidad", "precio_unitario", "precio_mano_obra", "material", "material_nombre",
                  "rendimiento_m2", "manos_recomendadas", "activo"]

    def validate_nombre(self, v):
        v = " ".join(v.split())
        qs = TipoAcabado.objects.all()
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if any(n.casefold() == v.casefold() for n in qs.values_list("nombre", flat=True)):
            raise serializers.ValidationError("Ya existe un trabajo con ese nombre.")
        return v

    def validate_precio_unitario(self, v):
        if v is None or v < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return v

    def validate_precio_mano_obra(self, v):
        if v is not None and v < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return v

    def validate_manos_recomendadas(self, v):
        if v < 1:
            raise serializers.ValidationError("Debe ser al menos 1 mano.")
        return v

    def validate(self, d):
        g = lambda k: d[k] if k in d else getattr(self.instance, k, None)
        if g("material") and g("unidad") == "M2" and not g("rendimiento_m2"):
            raise serializers.ValidationError({"rendimiento_m2": "Si el trabajo consume pintura, indica cuántos m² rinde un galón por mano."})
        if g("rendimiento_m2") is not None and g("rendimiento_m2") <= 0:
            raise serializers.ValidationError({"rendimiento_m2": "Debe ser mayor a 0."})
        return d


class DetalleEntradaSerializer(serializers.ModelSerializer):
    """Lo que envía el cliente o el supervisor: solo qué y cuánto. Los precios los pone el sistema."""

    tipo_acabado = serializers.PrimaryKeyRelatedField(queryset=TipoAcabado.objects.filter(activo=True))

    class Meta:
        model = DetalleCotizacion
        fields = ["descripcion", "tipo_superficie", "textura", "cantidad", "tipo_acabado"]

    def validate_cantidad(self, v):
        if v <= 0:
            raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return v


class DetalleSalidaSerializer(serializers.ModelSerializer):
    acabado = serializers.CharField(source="tipo_acabado.nombre", read_only=True)
    subtotal = serializers.DecimalField(source="costo_mano_obra", max_digits=12, decimal_places=0, read_only=True)
    material_nombre = serializers.CharField(source="material.nombre", read_only=True, default=None)

    CAMPOS_INTERNOS = ("material_nombre", "cantidad_material", "costo_materiales")  # el cliente no los ve

    class Meta:
        model = DetalleCotizacion
        fields = ["id", "descripcion", "tipo_superficie", "textura", "unidad", "cantidad", "tipo_acabado", "acabado", "precio_unitario",
                  "subtotal", "material_nombre", "cantidad_material", "costo_materiales"]

    def to_representation(self, instancia):
        datos = super().to_representation(instancia)
        if es_cliente(self.context.get("request")):
            for c in self.CAMPOS_INTERNOS:
                datos.pop(c, None)
        return datos


class InsumoSalidaSerializer(serializers.ModelSerializer):
    material = serializers.CharField(source="material.nombre")

    class Meta:
        model = InsumoCotizacion
        fields = ["material", "cantidad", "costo"]


class HistorialSerializer(serializers.ModelSerializer):
    usuario = serializers.CharField(source="usuario.nombre")

    class Meta:
        model = HistorialEstado
        fields = ["estado_anterior", "estado_nuevo", "usuario", "fecha"]


class CotizacionListaSerializer(serializers.ModelSerializer):
    cliente_nombre = serializers.CharField(source="cliente.nombre_razon_social")
    calculada = serializers.BooleanField(read_only=True)

    class Meta:
        model = Cotizacion
        fields = ["id", "cliente", "cliente_nombre", "nombre_obra", "ciudad", "estado", "origen_materiales",
                  "requiere_medicion", "calculada", "total", "fecha_solicitud"]


class CotizacionDetalleSerializer(CotizacionListaSerializer):
    detalles = DetalleSalidaSerializer(many=True, read_only=True)
    insumos = InsumoSalidaSerializer(many=True, read_only=True)
    historial = HistorialSerializer(many=True, read_only=True)

    class Meta(CotizacionListaSerializer.Meta):
        fields = CotizacionListaSerializer.Meta.fields + [
            "direccion_obra", "num_pintores", "semanas_obra", "neto", "iva", "fecha_calculo",
            "observaciones", "detalles", "insumos", "historial"]

    def to_representation(self, instancia):
        datos = super().to_representation(instancia)
        if es_cliente(self.context.get("request")):
            datos.pop("insumos", None)  # consumo y costo interno: solo personal de M y C
            datos["encuesta_puntaje"] = getattr(getattr(instancia, "encuesta", None), "puntaje", None)
        else:  # costo estimado de materiales e insumos (referencia interna / margen)
            datos["costo_interno_materiales"] = float(
                sum((d.costo_materiales or 0) for d in instancia.detalles.all()) + sum(i.costo for i in instancia.insumos.all()))
        return datos


class CotizacionCrearSerializer(serializers.ModelSerializer):
    """HU02: formulario de solicitud."""

    detalles = DetalleEntradaSerializer(many=True, required=False)
    cliente = serializers.PrimaryKeyRelatedField(queryset=Cliente.objects.all(), required=False)

    class Meta:
        model = Cotizacion
        fields = ["cliente", "nombre_obra", "direccion_obra", "ciudad", "origen_materiales", "requiere_medicion",
                  "num_pintores", "semanas_obra", "observaciones", "detalles"]

    def validate(self, datos):
        # Si faltan medidas se permite enviar sin ítems: el supervisor mide en terreno (CU02 flujo alterno).
        if not datos.get("requiere_medicion") and not datos.get("detalles"):
            raise serializers.ValidationError({"detalles": "Agrega al menos un ítem o marca que requiere medición en terreno."})
        # Si el cliente pone los materiales no se piden datos de inventario (HU02 criterio 2)
        if datos.get("origen_materiales") == "CLIENTE":
            datos["num_pintores"] = datos["semanas_obra"] = None
        return datos


class MedidasSerializer(serializers.Serializer):
    """CU07: el supervisor carga las medidas tomadas en terreno."""

    detalles = DetalleEntradaSerializer(many=True, allow_empty=False)
    num_pintores = serializers.IntegerField(required=False, min_value=0, allow_null=True)
    semanas_obra = serializers.IntegerField(required=False, min_value=1, allow_null=True)
