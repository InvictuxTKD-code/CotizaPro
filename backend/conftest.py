import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def limpiar_limites_de_solicitudes():
    """El throttling de DRF usa la caché; se reinicia para que un test no afecte a otro."""
    cache.clear()
    yield
