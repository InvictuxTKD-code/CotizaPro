"""Carga datos FICTICIOS de demostración (usuarios, acabados y catálogo). No usar en producción real."""
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.clientes.models import Cliente
from apps.cotizaciones.models import TipoAcabado
from apps.inventario.models import Material
from apps.usuarios.models import Rol, Usuario

USUARIOS = [
    ("admin@cotizapro.cl", "Manuel Cofré (Gerente)", Rol.ADMINISTRADOR),
    ("supervisor@cotizapro.cl", "Supervisor Comercial", Rol.EJECUTIVO),
    ("cliente@cotizapro.cl", "Cliente de Prueba", Rol.CLIENTE),
]
# Materiales (precios de ejemplo, NO reales: reemplazar por el catálogo de M y C)
MATERIALES = [  # nombre, categoría, unidad, precio, stock, mínimo
    ("Látex interior blanco 1 gal", "Pintura", "galón", 18900, 40, 10),
    ("Esmalte al agua blanco 1 gal", "Pintura", "galón", 24900, 25, 8),
    ("Rodillo 23 cm", "Rodillo", "unidad", 3500, 30, 10),
    ("Brocha 3 pulgadas", "Brocha", "unidad", 2800, 30, 10),
    ("Cinta enmascarar 48 mm", "Cinta", "unidad", 1900, 50, 15),
]
# Ítems y precios de OBRA VENDIDA (incluyen materiales) tomados de los presupuestos COD-010 y COD-011 de M y C.
# El precio de solo mano de obra (cliente pone materiales) es un placeholder ficticio del 60 %.
# nombre, unidad, precio, material que consume (o None), rendimiento m²/galón por mano
ACABADOS = [
    ("Pintura látex", "M2", 4500, "Látex interior blanco 1 gal", 34),
    ("Esmalte al agua", "M2", 10500, "Esmalte al agua blanco 1 gal", 34),
    ("Esmalte al agua en puertas de madera", "M2", 15500, None, None),
    ("Empaste previo", "M2", 4000, None, None),
    ("Óleo", "M2", 11000, None, None),
    ("Esmalte sintético elementos metálicos", "M2", 11000, None, None),
    ("Barniz", "M2", 10500, None, None),
    ("Pintura epóxica en elementos metálicos", "M2", 12000, None, None),
    ("Tinte y sello en puertas enchapadas", "M2", 15500, None, None),
    ("Guardapolvo", "ML", 7000, None, None),
    ("Esmalte marcos", "ML", 7000, None, None),
    ("Pintura cornisas", "ML", 6000, None, None),
    ("Huinchas junturas tabiques", "ML", 3500, None, None),
]


class Command(BaseCommand):
    help = "Carga usuarios, tipos de acabado y materiales de ejemplo (ficticios)."

    def handle(self, *args, **opts):
        # Renombra la cuenta demo antigua (ejecutivo -> supervisor) para no duplicarla
        Usuario.objects.filter(correo="ejecutivo@cotizapro.cl").update(correo="supervisor@cotizapro.cl", nombre="Supervisor Comercial")
        for correo, nombre, rol in USUARIOS:
            u, nuevo = Usuario.objects.get_or_create(correo=correo, defaults={"nombre": nombre, "rol": rol})
            if nuevo:
                u.set_password("Demo12345!")
                u.save()
                if rol == Rol.ADMINISTRADOR:
                    u.is_staff = u.is_superuser = True
                    u.save()
        cliente_u = Usuario.objects.get(correo="cliente@cotizapro.cl")
        Cliente.objects.get_or_create(
            rut="11111111-1",
            defaults=dict(usuario=cliente_u, tipo="PARTICULAR", nombre_razon_social="Cliente de Prueba",
                          correo_contacto=cliente_u.correo, telefono="+56 9 1111 1111"),
        )
        for n, c, u, p, st, mn in MATERIALES:
            Material.objects.get_or_create(nombre=n, defaults=dict(categoria=c, unidad=u, precio_unitario=p, stock_actual=st, stock_minimo=mn))
        for n, u, p, mat, rend in ACABADOS:
            a, _ = TipoAcabado.objects.get_or_create(nombre=n, defaults=dict(
                unidad=u, precio_unitario=p, rendimiento_m2=rend, manos_recomendadas=2,
                material=Material.objects.get(nombre=mat) if mat else None))
            if a.precio_mano_obra is None:  # PLACEHOLDER ficticio (60 %): reemplazar por el precio real de solo mano de obra
                a.precio_mano_obra = round(p * 0.6, -2)
                a.save(update_fields=["precio_mano_obra"])
        self.stdout.write(self.style.SUCCESS("Datos de demostración cargados. Clave de las cuentas demo: Demo12345!"))
