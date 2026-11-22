"""Configuración de CotizaPro. Todo lo sensible viene de variables de entorno."""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR.parent / ".env")

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "dev-insegura-cambiar-en-produccion")
DEBUG = os.getenv("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "corsheaders",
    "apps.usuarios",
    "apps.clientes",
    "apps.inventario",
    "apps.cotizaciones",
    "apps.auditoria",
    "apps.indicadores",
    "apps.chat",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ]
        },
    }
]

# PostgreSQL en Docker/producción. Si no hay POSTGRES_HOST se usa SQLite (solo desarrollo rápido y tests).
if os.getenv("POSTGRES_HOST"):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": os.getenv("POSTGRES_DB", "cotizapro"),
            "USER": os.getenv("POSTGRES_USER", "cotizapro"),
            "PASSWORD": os.getenv("POSTGRES_PASSWORD", "cotizapro"),
            "HOST": os.getenv("POSTGRES_HOST"),
            "PORT": os.getenv("POSTGRES_PORT", "5432"),
        }
    }
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": BASE_DIR / "db.sqlite3"}}

AUTH_USER_MODEL = "usuarios.Usuario"

# Contraseñas con hash y sal (PBKDF2 de Django).
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "es-cl"
TIME_ZONE = "America/Santiago"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "COERCE_DECIMAL_TO_STRING": False,  # montos como números en el JSON (más simple para React)
    "DEFAULT_AUTHENTICATION_CLASSES": ["rest_framework_simplejwt.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # Límite de solicitudes por usuario (sección 3.1.2.4, control 3).
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/min", "user": "240/min", "chat": "20/min"},
}

SIMPLE_JWT = {
    # Sesión corta: el cierre por inactividad lo refuerza el frontend (HU01, criterio 4).
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.getenv("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(hours=8),
    "AUTH_HEADER_TYPES": ("Bearer",),
}

CORS_ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(",")

# Reglas de bloqueo (HU01, criterio 3)
MAX_INTENTOS_FALLIDOS = 3
MINUTOS_BLOQUEO = int(os.getenv("MINUTOS_BLOQUEO", "15"))

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True

# --- Parámetros del motor de cálculo (HU03). Ajustables sin tocar código. ---
# M y C cotiza en valores NETOS: el IVA lo considera la empresa que recibe la cotización.
# Poner IVA_PORCENTAJE=19 en .env para que el sistema lo calcule y lo muestre.
IVA_PORCENTAJE = int(os.getenv("IVA_PORCENTAJE", "0"))
# Cuánto rinde la pintura según la superficie: más lisa rinde más, más rugosa rinde menos.
# SUPUESTO inicial: validar con Don Manuel.
FACTOR_TEXTURA = {"LISA": "1.10", "NORMAL": "1.00", "RUGOSA": "0.85"}
# Rodillos y brochas: 1 de cada uno por pintor, duran ~2 semanas (dato de Don Manuel).
INSUMOS_POR_PINTOR = ["Rodillo", "Brocha"]  # categorías del catálogo de materiales
SEMANAS_VIDA_UTIL_INSUMO = 2

# Asistente virtual (HU05). Sin clave el chat responde con textos predefinidos (contingencia, SLA-03).
CHAT_PROVEEDOR = os.getenv("CHAT_PROVEEDOR", "claude")  # claude | ninguno
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CHAT_MODELO = os.getenv("CHAT_MODELO", "claude-haiku-5-5")
CHAT_TIMEOUT_SEGUNDOS = float(os.getenv("CHAT_TIMEOUT_SEGUNDOS", "8"))
