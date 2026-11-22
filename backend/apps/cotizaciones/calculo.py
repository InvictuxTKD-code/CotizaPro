"""Motor de cálculo de presupuestos (HU03).

ÚNICO lugar donde se calcula dinero. El chatbot nunca llega aquí por su cuenta.
Funciones puras sobre Decimal, para poder probarlas contra las planillas Excel reales.

Reglas (según planillas de M y C y entrevistas con Don Manuel):
  * Obra vendida (M y C pone los materiales): subtotal = cantidad (m² o ml) × precio unitario del ítem.
    Ese precio YA incluye materiales e insumos: no se suman aparte.
  * Cliente pone los materiales: subtotal = cantidad × precio de solo mano de obra del ítem.
  * Consumo de materiales (solo obra vendida; sirve para descontar inventario y estimar el costo interno):
        m² por galón = rendimiento por mano ÷ manos       (34 ÷ 2 = 17)
        galones      = ceil(cantidad ÷ m² por galón)       (100 ÷ 17 = 5,88 → 6)
    ajustado por la textura (lisa rinde más, rugosa menos).
    Rodillos y brochas: 1 de cada uno por pintor, se renuevan cada 2 semanas.
  * Neto = suma de subtotales. El IVA es opcional (parámetro IVA_PORCENTAJE; por defecto 0).
"""
from dataclasses import dataclass, field
from decimal import ROUND_CEILING, ROUND_HALF_UP, Decimal

from django.conf import settings

D = Decimal


class DatosFaltantes(Exception):
    """Falta información obligatoria: no se calcula y se informa qué falta (HU03 criterio 2)."""

    def __init__(self, faltantes):
        self.faltantes = faltantes
        super().__init__("; ".join(faltantes))


def redondear(valor: Decimal) -> Decimal:
    return valor.quantize(D("1"), rounding=ROUND_HALF_UP)


def galones_necesarios(cantidad, rendimiento_por_mano, manos, textura="NORMAL") -> Decimal:
    factor = D(settings.FACTOR_TEXTURA.get(textura, "1.00"))
    m2_por_galon = D(rendimiento_por_mano) * factor / D(manos)
    return (D(cantidad) / m2_por_galon).to_integral_value(rounding=ROUND_CEILING)


@dataclass
class LineaCalculada:
    mano_obra: Decimal  # subtotal de la partida (cantidad × precio aplicado)
    precio: Decimal = None
    material: object = None
    cantidad_material: Decimal = None
    costo_materiales: Decimal = None


@dataclass
class ResultadoCalculo:
    lineas: list = field(default_factory=list)
    insumos: list = field(default_factory=list)  # [(material, cantidad, costo)]
    costo_interno: Decimal = D(0)  # costo estimado de materiales e insumos (no se cobra aparte)
    neto: Decimal = D(0)
    iva: Decimal = D(0)
    total: Decimal = D(0)


def calcular_presupuesto(cotizacion, detalles, insumos_disponibles=()):
    """`detalles`: objetos con acabado, cantidad, textura. `insumos_disponibles`: materiales de categoría
    rodillo/brocha. Devuelve ResultadoCalculo sin tocar la base de datos."""
    faltantes = []
    empresa = cotizacion.origen_materiales == "EMPRESA"

    if not detalles:
        faltantes.append("Debe haber al menos un ítem a cotizar (superficie o metros lineales).")
    for i, d in enumerate(detalles, 1):
        if d.cantidad is None or D(d.cantidad) <= 0:
            faltantes.append(f"Ítem {i}: falta la cantidad ({d.acabado.nombre}).")
        if empresa and d.acabado.material_id and not d.acabado.rendimiento_m2:
            faltantes.append(f"Ítem {i}: '{d.acabado.nombre}' no tiene rendimiento configurado.")
        if not empresa and d.acabado.precio_mano_obra is None:
            faltantes.append(f"Ítem {i}: '{d.acabado.nombre}' no tiene precio de solo mano de obra (el cliente pone los materiales).")
    if empresa and (cotizacion.num_pintores or 0) > 0 and not cotizacion.semanas_obra:
        faltantes.append("Faltan las semanas de obra para calcular rodillos y brochas.")
    if faltantes:
        raise DatosFaltantes(faltantes)

    res = ResultadoCalculo()
    mo_total = mat_total = ins_total = D(0)

    for d in detalles:
        cantidad = D(d.cantidad)
        precio = D(d.acabado.precio_unitario if empresa else d.acabado.precio_mano_obra)
        mo = cantidad * precio  # sin redondear: igual que Excel
        linea = LineaCalculada(mano_obra=mo, precio=precio)
        # Solo hay consumo de pintura si la pone M y C, el ítem usa pintura y se mide en m²
        if empresa and d.acabado.material_id and d.acabado.unidad == "M2":
            gal = galones_necesarios(cantidad, d.acabado.rendimiento_m2, d.acabado.manos_recomendadas, d.textura)
            costo = gal * D(d.acabado.material.precio_unitario)
            linea.material, linea.cantidad_material, linea.costo_materiales = d.acabado.material, gal, costo
            mat_total += costo
        mo_total += mo
        res.lineas.append(linea)

    if empresa and cotizacion.num_pintores:
        ciclos = (D(cotizacion.semanas_obra) / D(settings.SEMANAS_VIDA_UTIL_INSUMO)).to_integral_value(rounding=ROUND_CEILING)
        cantidad = D(cotizacion.num_pintores) * max(ciclos, D(1))
        for m in insumos_disponibles:
            costo = cantidad * D(m.precio_unitario)
            res.insumos.append((m, cantidad, costo))
            ins_total += costo

    res.costo_interno = redondear(mat_total + ins_total)
    neto = redondear(mo_total)  # materiales e insumos van incluidos en el precio de obra vendida
    iva = redondear(neto * D(settings.IVA_PORCENTAJE) / D(100))
    res.neto, res.iva, res.total = neto, iva, neto + iva
    for l in res.lineas:
        l.mano_obra = redondear(l.mano_obra)
        if l.costo_materiales is not None:
            l.costo_materiales = redondear(l.costo_materiales)
    res.insumos = [(m, c, redondear(k)) for m, c, k in res.insumos]
    return res
