from django.contrib.auth.password_validation import validate_password
from django.db import transaction
from rest_framework import serializers

from apps.usuarios.models import Rol, Usuario

from .models import Cliente
from .validators import normalizar_rut, validar_rut


class RegistroClienteSerializer(serializers.Serializer):
    nombre = serializers.CharField(max_length=100)
    correo = serializers.EmailField(max_length=150)
    password = serializers.CharField(write_only=True)
    tipo = serializers.ChoiceField(choices=Cliente.Tipo.choices)
    nombre_razon_social = serializers.CharField(max_length=150)
    rut = serializers.CharField(max_length=12, validators=[validar_rut])
    telefono = serializers.CharField(max_length=20, required=False, allow_blank=True)

    def validate_correo(self, v):
        if Usuario.objects.filter(correo=v.lower()).exists():
            raise serializers.ValidationError("Ya existe un usuario con ese correo.")
        return v.lower()

    def validate_rut(self, v):
        v = normalizar_rut(v)
        if Cliente.objects.filter(rut=v).exists():
            raise serializers.ValidationError("Ya existe un cliente con ese RUT.")
        return v

    def validate_password(self, v):
        validate_password(v)
        return v

    @transaction.atomic
    def create(self, d):
        u = Usuario.objects.create_user(correo=d["correo"], password=d["password"], nombre=d["nombre"], rol=Rol.CLIENTE)
        return Cliente.objects.create(usuario=u, tipo=d["tipo"], nombre_razon_social=d["nombre_razon_social"], rut=d["rut"],
                                      telefono=d.get("telefono") or None, correo_contacto=d["correo"])
