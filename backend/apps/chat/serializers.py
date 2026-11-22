from rest_framework import serializers

from .models import ConversacionChat, EncuestaSatisfaccion, MensajeChat


class MensajeSerializer(serializers.ModelSerializer):
    class Meta:
        model = MensajeChat
        fields = ["id", "emisor", "contenido", "fecha"]


class EntradaMensajeSerializer(serializers.Serializer):
    conversacion = serializers.IntegerField(required=False)
    token = serializers.UUIDField(required=False)
    texto = serializers.CharField(max_length=2000, trim_whitespace=True)


class ConversacionStaffSerializer(serializers.ModelSerializer):
    mensajes = MensajeSerializer(many=True, read_only=True)
    persona = serializers.SerializerMethodField()

    class Meta:
        model = ConversacionChat
        fields = ["id", "fecha_inicio", "derivada_a_humano", "resuelta_por_bot", "contacto", "atendida", "persona", "mensajes"]

    def get_persona(self, o):
        u = o.usuario
        return {"nombre": u.nombre, "correo": u.correo} if u else None


class EncuestaSerializer(serializers.ModelSerializer):
    puntaje = serializers.IntegerField(min_value=1, max_value=5)
    comentario = serializers.CharField(max_length=300, required=False, allow_blank=True, allow_null=True)

    class Meta:
        model = EncuestaSatisfaccion
        fields = ["puntaje", "comentario", "fecha"]
        read_only_fields = ["fecha"]
