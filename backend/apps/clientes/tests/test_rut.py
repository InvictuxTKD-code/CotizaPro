import pytest
from django.core.exceptions import ValidationError

from apps.clientes.validators import normalizar_rut, validar_rut


def test_normaliza():
    assert normalizar_rut("78.136.827-K") == "78136827-K"


@pytest.mark.parametrize("rut", ["78.136.827-K", "11.111.111-1", "12.345.678-5"])
def test_rut_validos(rut):
    validar_rut(rut)


@pytest.mark.parametrize("rut", ["12.345.678-9", "abc", "", "1-1"])
def test_rut_invalidos(rut):
    with pytest.raises(ValidationError):
        validar_rut(rut)
