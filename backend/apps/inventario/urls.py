from rest_framework.routers import DefaultRouter

from .views import MaterialViewSet, MovimientoViewSet

router = DefaultRouter()
router.register("materiales", MaterialViewSet, basename="material")
router.register("movimientos", MovimientoViewSet, basename="movimiento")
urlpatterns = router.urls
