from django.urls import path

from .views import AtenderView, ContactoView, DerivadasView, EncuestaView, HistorialView, MensajeView

urlpatterns = [
    path("chat/mensaje/", MensajeView.as_view()),
    path("chat/historial/", HistorialView.as_view()),
    path("chat/contacto/", ContactoView.as_view()),
    path("chat/derivadas/", DerivadasView.as_view()),
    path("chat/derivadas/<int:pk>/atender/", AtenderView.as_view()),
    path("cotizaciones/<int:pk>/encuesta/", EncuestaView.as_view()),
]
