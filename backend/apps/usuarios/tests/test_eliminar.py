import pytest
from rest_framework.test import APIClient

from apps.auditoria.models import RegistroAuditoria
from apps.clientes.models import Cliente
from apps.inventario.tests.test_aprobacion import mundo, pedir, sesion  # noqa: F401
from apps.usuarios.models import Rol, Usuario

pytestmark = pytest.mark.django_db


def test_solo_admin_elimina_usuarios_sin_historial(mundo):
    _, extra = sesion(Rol.EJECUTIVO, "nuevo@x.cl")
    assert mundo["eje"].delete(f"/api/usuarios/{extra.pk}/").status_code == 403
    assert APIClient().delete(f"/api/usuarios/{extra.pk}/").status_code == 401
    assert mundo["adm"].delete(f"/api/usuarios/{extra.pk}/").status_code == 204
    assert not Usuario.objects.filter(pk=extra.pk).exists()
    log = RegistroAuditoria.objects.get(accion="ELIMINAR_USUARIO")
    assert "nuevo@x.cl" in log.detalle and log.usuario == mundo["u_adm"]


def test_no_se_puede_eliminar_a_si_mismo(mundo):
    r = mundo["adm"].delete(f"/api/usuarios/{mundo['u_adm'].pk}/")
    assert r.status_code == 400 and "propia" in r.data["detalle"]
    assert Usuario.objects.filter(pk=mundo["u_adm"].pk).exists()


def test_un_admin_puede_eliminar_a_otro_admin_sin_historial(mundo):
    _, otro = sesion(Rol.ADMINISTRADOR, "a2@x.cl")
    assert mundo["adm"].delete(f"/api/usuarios/{otro.pk}/").status_code == 204


def test_con_historial_se_exige_desactivar(mundo):
    pedir(mundo)  # el cliente tiene una cotización
    cli = Usuario.objects.get(correo="c@x.cl")
    r = mundo["adm"].delete(f"/api/usuarios/{cli.pk}/")
    assert r.status_code == 409 and "Desactívalo" in r.data["detalle"]
    assert Usuario.objects.filter(pk=cli.pk).exists()
    assert mundo["adm"].patch(f"/api/usuarios/{cli.pk}/", {"activo": False}, format="json").status_code == 200


def test_eliminar_cliente_sin_cotizaciones_libera_su_rut(mundo):
    _, u = sesion(Rol.CLIENTE, "sin@x.cl", "22222222-2")
    assert mundo["adm"].delete(f"/api/usuarios/{u.pk}/").status_code == 204
    assert not Cliente.objects.filter(rut="22222222-2").exists()
