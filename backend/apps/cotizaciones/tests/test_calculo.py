"""Pruebas del motor de cálculo contra los casos reales de M y C (criterio de aceptación 3.3.3)."""
from decimal import Decimal as D

import pytest

from apps.cotizaciones.calculo import DatosFaltantes, calcular_presupuesto, galones_necesarios
from apps.cotizaciones.models import Cotizacion, TipoAcabado
from apps.inventario.models import Material

pytestmark = pytest.mark.django_db


class Det:
    def __init__(self, acabado, cantidad, textura="NORMAL"):
        self.acabado, self.cantidad, self.textura = acabado, cantidad, textura


def acabado(nombre, unidad, precio, material=None, rend=None, precio_mo=None):
    return TipoAcabado.objects.create(nombre=nombre, unidad=unidad, precio_unitario=precio, precio_mano_obra=precio_mo,
                                      material=material, rendimiento_m2=rend)


# --- Regla de galones explicada por Don Manuel: 34 m² por galón, 2 manos => 17 m²; 100/17 = 5,88 => 6 ---
def test_galones_ejemplo_del_gerente():
    assert galones_necesarios(100, 34, 2) == 6


def test_superficie_lisa_rinde_mas_y_rugosa_menos():
    assert galones_necesarios(100, 34, 2, "LISA") < galones_necesarios(100, 34, 2, "RUGOSA")


def test_exacto_no_sobrecompra():
    assert galones_necesarios(34, 34, 2) == 2  # 34/17 = 2 exacto


# --- Caso real COD-011 (hotel, 5 ítems), obra vendida: el neto es el total del Excel (sin IVA) ---
def test_presupuesto_cod_011_coincide_con_excel():
    casos = [("Guardapolvo epóxica", "ML", 7000, 1440), ("Esmalte puertas madera", "M2", 15500, 584),
             ("Epóxica metálicos", "M2", 12000, 50), ("Tinte y sello enchapadas", "M2", 15500, 1210),
             ("Tinte endolados", "ML", 6000, 4645)]
    cot = Cotizacion(origen_materiales="EMPRESA")
    r = calcular_presupuesto(cot, [Det(acabado(n, u, p), c) for n, u, p, c in casos])
    assert r.neto == D(66_357_000)  # SUM de la planilla Excel
    assert r.iva == 0 and r.total == D(66_357_000)  # M y C cotiza neto: el IVA lo ve la empresa receptora


def test_iva_opcional_se_puede_activar(settings):
    settings.IVA_PORCENTAJE = 19
    r = calcular_presupuesto(Cotizacion(origen_materiales="EMPRESA"), [Det(acabado("X", "M2", 1000), 100)])
    assert (r.neto, r.iva, r.total) == (D(100_000), D(19_000), D(119_000))


# --- Caso real COD-010 (25 ítems con decimales) ---
COD_010 = [(247.9113, 4500), (441.384, 4000), (770.3214, 4500), (3086.7895, 10500), (3086.7895, 4000), (91.6903, 10500),
           (91.6903, 4000), (10688.98, 10500), (10688.98, 4000), (142.40884, 11000), (142.40884, 4000), (4885.0411, 10500),
           (4885.0411, 4000), (219.986, 6500), (159.034, 10500), (84.068158, 11000), (395.9332, 7000), (1172.9512, 10500),
           (1486.0056, 7000), (356.58, 7000), (19.2095, 10500), (356.58, 7000), (3085.02, 6000), (356.58, 6000), (5164.9, 3500)]


def test_presupuesto_cod_010_coincide_con_excel():
    # La cantidad se guarda con 2 decimales; el Excel usa 4-6. Se prueba el motor sobre los valores exactos.
    cot = Cotizacion(origen_materiales="EMPRESA")
    dets = [Det(acabado(f"it{i}", "M2", p), D(str(c))) for i, (c, p) in enumerate(COD_010)]
    assert calcular_presupuesto(cot, dets).neto == D(353_829_623)  # total de la planilla Excel


# --- Obra vendida: el precio YA incluye materiales; el consumo solo sirve para inventario y costo interno ---
def test_obra_vendida_no_suma_materiales_pero_calcula_consumo():
    latex = Material.objects.create(nombre="Látex", categoria="Pintura", unidad="galón", precio_unitario=20000)
    rodillo = Material.objects.create(nombre="Rodillo", categoria="Rodillo", unidad="unidad", precio_unitario=3000)
    brocha = Material.objects.create(nombre="Brocha", categoria="Brocha", unidad="unidad", precio_unitario=2000)
    a = acabado("Látex", "M2", 4500, latex, 34)
    cot = Cotizacion(origen_materiales="EMPRESA", num_pintores=2, semanas_obra=3)
    r = calcular_presupuesto(cot, [Det(a, 100)], [rodillo, brocha])
    assert r.neto == D(450_000)  # 100 m² × $4.500, sin sumar materiales
    assert r.lineas[0].cantidad_material == 6 and r.lineas[0].costo_materiales == 120_000
    # 3 semanas / 2 = 1,5 -> 2 ciclos; 2 pintores x 2 = 4 de cada uno
    assert [(m.nombre, c) for m, c, _ in r.insumos] == [("Rodillo", 4), ("Brocha", 4)]
    assert r.costo_interno == D(120_000 + 12_000 + 8_000)


# --- Cliente pone los materiales: precio de solo mano de obra, sin consumo ---
def test_si_el_cliente_pone_materiales_usa_precio_de_mano_de_obra():
    latex = Material.objects.create(nombre="Látex", categoria="Pintura", unidad="galón", precio_unitario=20000)
    r = calcular_presupuesto(Cotizacion(origen_materiales="CLIENTE", num_pintores=5, semanas_obra=4),
                             [Det(acabado("Látex", "M2", 4500, latex, 34, precio_mo=2500), 100)])
    assert r.lineas[0].costo_materiales is None and r.insumos == [] and r.neto == D(250_000)


def test_cliente_sin_precio_de_mano_de_obra_informa_que_falta():
    with pytest.raises(DatosFaltantes) as e:
        calcular_presupuesto(Cotizacion(origen_materiales="CLIENTE"), [Det(acabado("Látex", "M2", 4500), 100)])
    assert "solo mano de obra" in e.value.faltantes[0]


def test_metros_lineales_no_consumen_galones():
    latex = Material.objects.create(nombre="Látex", categoria="Pintura", unidad="galón", precio_unitario=20000)
    r = calcular_presupuesto(Cotizacion(origen_materiales="EMPRESA"), [Det(acabado("Guardapolvo", "ML", 7000, latex, 34), 100)])
    assert r.lineas[0].costo_materiales is None


# --- HU03 criterio 2: si falta un dato no calcula y dice cuál ---
def test_sin_items_no_calcula():
    with pytest.raises(DatosFaltantes):
        calcular_presupuesto(Cotizacion(origen_materiales="CLIENTE"), [])


def test_empresa_con_pintores_sin_semanas_informa_que_falta():
    a = acabado("X", "M2", 100)
    with pytest.raises(DatosFaltantes) as e:
        calcular_presupuesto(Cotizacion(origen_materiales="EMPRESA", num_pintores=2), [Det(a, 10)])
    assert "semanas" in e.value.faltantes[0]
