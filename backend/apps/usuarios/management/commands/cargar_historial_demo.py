"""Genera cotizaciones de ejemplo repartidas en los últimos meses para mostrar el dashboard (datos ficticios)."""
import random
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.clientes.models import Cliente
from apps.cotizaciones import servicio
from apps.cotizaciones.models import Cotizacion, DetalleCotizacion, HistorialEstado, TipoAcabado
from apps.inventario.models import Material, MovimientoInventario
from apps.inventario.servicio import StockInsuficiente, mover_stock
from apps.usuarios.models import Rol, Usuario

OBRAS = ["Edificio Los Robles", "Hotel Costanera", "Condominio Las Lengas", "Colegio San Pedro", "Oficinas Centro",
         "Casa Pichoy", "Bodega Industrial", "Clínica Austral", "Local Comercial Picarte", "Departamentos Isla Teja"]


class Command(BaseCommand):
    help = "Crea cotizaciones ficticias de los últimos 6 meses (aprobadas, rechazadas y pendientes)."

    def add_arguments(self, parser):
        parser.add_argument("--cantidad", type=int, default=24)

    def handle(self, *args, cantidad, **o):
        random.seed(7)
        adm = Usuario.objects.filter(rol=Rol.ADMINISTRADOR).first()
        cliente = Cliente.objects.first()
        trabajos = list(TipoAcabado.objects.filter(activo=True))
        if not (adm and cliente and trabajos):
            raise CommandError("Primero ejecuta: python manage.py cargar_demo")
        ahora = timezone.now()
        for m in Material.objects.filter(activo=True):  # stock holgado para poder aprobar
            mover_stock(m.pk, "ENTRADA", 500, adm, observacion="Carga demo historial")
        for i in range(cantidad):
            dias_atras = int(random.triangular(2, 180, 40))
            c = Cotizacion.objects.create(
                cliente=cliente, nombre_obra=random.choice(OBRAS), direccion_obra="Dirección demo 123", ciudad="Valdivia",
                origen_materiales=random.choice(["EMPRESA"] * 3 + ["CLIENTE"]), num_pintores=random.randint(2, 6), semanas_obra=random.randint(2, 8))
            for t in random.sample(trabajos, random.randint(1, 3)):
                DetalleCotizacion.objects.create(cotizacion=c, descripcion="Sector demo", cantidad=random.randint(40, 900), tipo_acabado=t, unidad=t.unidad)
            servicio.registrar_estado(c, None, "PENDIENTE", cliente.usuario or adm)
            try:
                servicio.calcular_y_guardar(c, usuario=adm)
            except Exception:
                c.delete(); continue
            suerte = random.random()
            try:
                if suerte < 0.45: servicio.aprobar(c, adm)
                elif suerte < 0.65: servicio.rechazar(c, adm)
            except (StockInsuficiente, servicio.TransicionInvalida):
                pass
            fecha = ahora - timedelta(days=dias_atras)
            Cotizacion.objects.filter(pk=c.pk).update(fecha_solicitud=fecha, fecha_calculo=fecha + timedelta(minutes=random.randint(2, 9)))
            HistorialEstado.objects.filter(cotizacion=c).update(fecha=fecha + timedelta(days=random.randint(0, 6)))
            MovimientoInventario.objects.filter(cotizacion=c).update(fecha=fecha + timedelta(days=1))
        self.stdout.write(self.style.SUCCESS(f"Historial demo creado: {Cotizacion.objects.count()} cotizaciones en total."))
