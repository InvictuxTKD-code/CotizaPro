import re

from django.core.exceptions import ValidationError


def normalizar_rut(rut: str) -> str:
    """'12.345.678-5' -> '12345678-5' (formato único para la restricción UNIQUE)."""
    limpio = re.sub(r"[^0-9kK]", "", rut or "").upper()
    if len(limpio) < 2:
        return ""
    return f"{limpio[:-1]}-{limpio[-1]}"


def digito_verificador(cuerpo: str) -> str:
    suma, factor = 0, 2
    for d in reversed(cuerpo):
        suma += int(d) * factor
        factor = 2 if factor == 7 else factor + 1
    resto = 11 - (suma % 11)
    return {11: "0", 10: "K"}.get(resto, str(resto))


def validar_rut(valor: str):
    rut = normalizar_rut(valor)
    if not re.fullmatch(r"\d{1,8}-[0-9K]", rut) or digito_verificador(rut.split("-")[0]) != rut[-1]:
        raise ValidationError("RUT inválido.")
