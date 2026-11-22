from rest_framework import serializers

from .models import Material, MovimientoInventario


class MaterialSerializer(serializers.ModelSerializer):
    bajo_minimo = serializers.BooleanField(read_only=True)

    class Meta:
        model = Material
        fields = ["id", "nombre", "categoria", "unidad", "precio_unitario", "stock_actual", "stock_minimo", "activo", "bajo_minimo"]
        read_only_fields = ["stock_actual"]  # el stock solo cambia por movimientos registrados

    def validate_precio_unitario(self, v):
        if v < 0:
            raise serializers.ValidationError("El precio no puede ser negativo.")
        return v

    def validate_stock_minimo(self, v):
        if v < 0:
            raise serializers.ValidationError("El stock mínimo no puede ser negativo.")
        return v


class MovimientoEntradaSerializer(serializers.Serializer):
    tipo = serializers.ChoiceField(choices=MovimientoInventario.Tipo.choices)
    cantidad = serializers.DecimalField(max_digits=10, decimal_places=2)
    observacion = serializers.CharField(max_length=200, required=False, allow_blank=True)


class MovimientoSerializer(serializers.ModelSerializer):
    material_nombre = serializers.CharField(source="material.nombre", read_only=True)
    usuario_nombre = serializers.CharField(source="usuario.nombre", read_only=True)

    class Meta:
        model = MovimientoInventario
        fields = ["id", "material", "material_nombre", "cotizacion", "usuario_nombre", "tipo", "cantidad",
                  "stock_resultante", "fecha", "observacion"]
