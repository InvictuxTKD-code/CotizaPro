import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from apps.auditoria.models import RegistroAuditoria
from apps.usuarios.models import Rol, Usuario

pytestmark = pytest.mark.django_db
LOGIN = "/api/auth/login/"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def admin():
    return Usuario.objects.create_user("admin@mc.cl", "ClaveSegura123", nombre="Admin", rol=Rol.ADMINISTRADOR)


@pytest.fixture
def ejecutivo():
    return Usuario.objects.create_user("ejec@mc.cl", "ClaveSegura123", nombre="Ejec", rol=Rol.EJECUTIVO)


def token(api, correo, password="ClaveSegura123"):
    r = api.post(LOGIN, {"correo": correo, "password": password}, format="json")
    return r.data["access"]


# HU01 criterio 1
def test_credenciales_invalidas_se_rechazan(api, admin):
    r = api.post(LOGIN, {"correo": "admin@mc.cl", "password": "mala"}, format="json")
    assert r.status_code == 401 and "incorrectos" in r.data["detalle"]


def test_correo_inexistente_mismo_mensaje(api):
    r = api.post(LOGIN, {"correo": "nadie@mc.cl", "password": "x"}, format="json")
    assert r.status_code == 401 and "incorrectos" in r.data["detalle"]


def test_login_correcto_devuelve_tokens_y_rol(api, admin):
    r = api.post(LOGIN, {"correo": "admin@mc.cl", "password": "ClaveSegura123"}, format="json")
    assert r.status_code == 200 and r.data["usuario"]["rol"] == "ADMINISTRADOR" and r.data["access"]
    admin.refresh_from_db()
    assert admin.ultimo_acceso is not None


def test_contrasena_no_se_guarda_en_texto_plano(admin):
    assert admin.password != "ClaveSegura123" and admin.password.startswith("pbkdf2_")


# HU01 criterio 3
def test_bloqueo_tras_3_intentos_fallidos(api, admin):
    for _ in range(3):
        assert api.post(LOGIN, {"correo": "admin@mc.cl", "password": "mala"}, format="json").status_code == 401
    # incluso con la clave correcta, sigue bloqueada
    r = api.post(LOGIN, {"correo": "admin@mc.cl", "password": "ClaveSegura123"}, format="json")
    assert r.status_code == 423
    assert RegistroAuditoria.objects.filter(accion="BLOQUEO_CUENTA", entidad_id=admin.pk).exists()


def test_bloqueo_expira(api, admin):
    admin.bloqueado_hasta = timezone.now() - timezone.timedelta(minutes=1)
    admin.save()
    assert api.post(LOGIN, {"correo": "admin@mc.cl", "password": "ClaveSegura123"}, format="json").status_code == 200


def test_un_acierto_reinicia_el_contador(api, admin):
    api.post(LOGIN, {"correo": "admin@mc.cl", "password": "mala"}, format="json")
    api.post(LOGIN, {"correo": "admin@mc.cl", "password": "mala"}, format="json")
    api.post(LOGIN, {"correo": "admin@mc.cl", "password": "ClaveSegura123"}, format="json")
    admin.refresh_from_db()
    assert admin.intentos_fallidos == 0


def test_cuenta_desactivada_no_ingresa(api, admin):
    admin.activo = False
    admin.save()
    assert api.post(LOGIN, {"correo": "admin@mc.cl", "password": "ClaveSegura123"}, format="json").status_code == 401


# HU01 criterio 2: solo ve las funciones de su rol
def test_endpoints_requieren_token(api):
    assert api.get("/api/usuarios/").status_code == 401


def test_ejecutivo_no_puede_gestionar_usuarios(api, ejecutivo):
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token(api, 'ejec@mc.cl')}")
    assert api.get("/api/usuarios/").status_code == 403


# CU11
def test_admin_crea_usuario_con_rol_y_lo_desactiva(api, admin):
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token(api, 'admin@mc.cl')}")
    r = api.post("/api/usuarios/", {"nombre": "Ana", "correo": "Ana@MC.cl", "rol": "EJECUTIVO", "password": "OtraClave456"}, format="json")
    assert r.status_code == 201 and r.data["correo"] == "ana@mc.cl" and "password" not in r.data
    r = api.patch(f"/api/usuarios/{r.data['id']}/", {"activo": False}, format="json")
    assert r.status_code == 200 and r.data["activo"] is False


def test_correo_duplicado(api, admin):
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token(api, 'admin@mc.cl')}")
    r = api.post("/api/usuarios/", {"nombre": "X", "correo": "admin@mc.cl", "rol": "CLIENTE", "password": "OtraClave456"}, format="json")
    assert r.status_code == 400 and "correo" in r.data


def test_no_se_puede_borrar_la_propia_cuenta(api, admin):
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {token(api, 'admin@mc.cl')}")
    assert api.delete(f"/api/usuarios/{admin.pk}/").status_code == 400
