from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Rol, Usuario


class UsuarioSerializer(serializers.ModelSerializer):
    """Lectura/edición por el administrador (CU11). La contraseña solo se escribe."""

    password = serializers.CharField(write_only=True, required=False, min_length=8)

    class Meta:
        model = Usuario
        fields = ["id", "nombre", "correo", "rol", "activo", "ultimo_acceso", "fecha_creacion", "password"]
        read_only_fields = ["id", "ultimo_acceso", "fecha_creacion"]

    def validate_correo(self, valor):
        valor = valor.lower()
        qs = Usuario.objects.filter(correo=valor)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("Ya existe un usuario con ese correo.")
        return valor

    def validate_password(self, valor):
        validate_password(valor)
        return valor

    def create(self, datos):
        if "password" not in datos:
            raise serializers.ValidationError({"password": "La contraseña es obligatoria."})
        return Usuario.objects.create_user(correo=datos.pop("correo"), password=datos.pop("password"), **datos)

    def update(self, instancia, datos):
        password = datos.pop("password", None)
        for k, v in datos.items():
            setattr(instancia, k, v)
        if password:
            instancia.set_password(password)
        instancia.save()
        return instancia


class PerfilSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "nombre", "correo", "rol"]


class LoginSerializer(serializers.Serializer):
    correo = serializers.EmailField()
    password = serializers.CharField(write_only=True)
