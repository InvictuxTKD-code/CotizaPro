from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import AcabadosView, AcabadoViewSet, CotizacionViewSet

router = DefaultRouter()
router.register("cotizaciones", CotizacionViewSet, basename="cotizacion")
router.register("acabados", AcabadoViewSet, basename="acabado")
urlpatterns = [path("catalogo/acabados/", AcabadosView.as_view()), *router.urls]
