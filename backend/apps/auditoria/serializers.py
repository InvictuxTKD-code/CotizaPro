from rest_framework import serializers

from .models import RegistroAuditoria


class RegistroAuditoriaSerializer(serializers.ModelSerializer):
    usuario_nombre = serializers.CharField(source="usuario.nombre", default="Sistema", read_only=True)

    class Meta:
        model = RegistroAuditoria
        fields = ["id", "usuario_nombre", "accion", "entidad", "entidad_id", "detalle", "fecha"]
