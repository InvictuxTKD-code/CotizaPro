from datetime import timedelta

from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class Rol(models.TextChoices):
    CLIENTE = "CLIENTE", "Cliente"
    EJECUTIVO = "EJECUTIVO", "Supervisor"
    ADMINISTRADOR = "ADMINISTRADOR", "Administrador"


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, correo, password=None, **extra):
        if not correo:
            raise ValueError("El correo es obligatorio")
        usuario = self.model(correo=self.normalize_email(correo).lower(), **extra)
        usuario.set_password(password)  # hash con sal
        usuario.save(using=self._db)
        return usuario

    def create_superuser(self, correo, password=None, **extra):
        extra.setdefault("rol", Rol.ADMINISTRADOR)
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        return self.create_user(correo, password, **extra)


class Usuario(AbstractBaseUser, PermissionsMixin):
    nombre = models.CharField(max_length=100)
    correo = models.EmailField(max_length=150, unique=True)
    rol = models.CharField(max_length=20, choices=Rol.choices, default=Rol.CLIENTE)
    activo = models.BooleanField(default=True)
    intentos_fallidos = models.PositiveSmallIntegerField(default=0)
    bloqueado_hasta = models.DateTimeField(null=True, blank=True)
    ultimo_acceso = models.DateTimeField(null=True, blank=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    is_staff = models.BooleanField(default=False)  # acceso al /admin de Django

    USERNAME_FIELD = "correo"
    REQUIRED_FIELDS = ["nombre"]
    objects = UsuarioManager()

    class Meta:
        db_table = "usuario"

    @property
    def is_active(self):  # Django lo usa para permitir/denegar ingreso
        return self.activo

    def __str__(self):
        return f"{self.nombre} <{self.correo}>"

    # --- Bloqueo por intentos fallidos (HU01 criterio 3) ---
    def esta_bloqueado(self):
        return bool(self.bloqueado_hasta and self.bloqueado_hasta > timezone.now())

    def registrar_fallo(self):
        """Suma un intento fallido; al llegar al máximo bloquea. Devuelve True si quedó bloqueado."""
        self.intentos_fallidos += 1
        bloqueado = self.intentos_fallidos >= settings.MAX_INTENTOS_FALLIDOS
        if bloqueado:
            self.bloqueado_hasta = timezone.now() + timedelta(minutes=settings.MINUTOS_BLOQUEO)
            self.intentos_fallidos = 0
        self.save(update_fields=["intentos_fallidos", "bloqueado_hasta"])
        return bloqueado

    def registrar_acceso(self):
        self.intentos_fallidos = 0
        self.bloqueado_hasta = None
        self.ultimo_acceso = timezone.now()
        self.save(update_fields=["intentos_fallidos", "bloqueado_hasta", "ultimo_acceso"])
