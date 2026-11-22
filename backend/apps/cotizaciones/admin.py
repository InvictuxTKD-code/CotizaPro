from django.contrib import admin

from .models import Cotizacion, DetalleCotizacion, HistorialEstado, InsumoCotizacion, TipoAcabado

admin.site.register(TipoAcabado)
admin.site.register(Cotizacion)
admin.site.register(DetalleCotizacion)
admin.site.register(HistorialEstado)
admin.site.register(InsumoCotizacion)
