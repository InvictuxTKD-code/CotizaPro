from django.contrib import admin
from django.urls import include, path

from apps.clientes.views import RegistroClienteView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/auth/registro/", RegistroClienteView.as_view()),
    path("api/auth/", include("apps.usuarios.urls_auth")),
    path("api/usuarios/", include("apps.usuarios.urls")),
    path("api/", include("apps.inventario.urls")),
    path("api/", include("apps.auditoria.urls")),
    path("api/", include("apps.indicadores.urls")),
    path("api/", include("apps.chat.urls")),
    path("api/", include("apps.cotizaciones.urls")),
]
