from pathlib import Path
from decouple import config
import dj_database_url
import sys
import os

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent

# -----------------------------------------------------------------------------
# Básico
# -----------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY", default=".env")

# Stripe (padronizado)
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
# Backcompat: se só houver STRIPE_PUBLIC_KEY no .env, usa como publishable
if not STRIPE_PUBLISHABLE_KEY:
    STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLIC_KEY", default="")

STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")
STRIPE_DEFAULT_PRICE_ID = config("STRIPE_DEFAULT_PRICE_ID", default="")

DEBUG = config("DEBUG", default=False, cast=bool)

ALLOWED_HOSTS = [h for h in config("ALLOWED_HOSTS", default="").split(",") if h]
CSRF_TRUSTED_ORIGINS = [u for u in config("CSRF_TRUSTED_ORIGINS", default="").split(",") if u]
# fallback: se CSRF_TRUSTED_ORIGINS vier vazio, derive de ALLOWED_HOSTS
if not CSRF_TRUSTED_ORIGINS and ALLOWED_HOSTS:
    CSRF_TRUSTED_ORIGINS = [f"https://{h}" for h in ALLOWED_HOSTS if not h.startswith("http")]

# Internationalization / timezone
TIME_ZONE = config("TIME_ZONE", default="America/Sao_Paulo")
USE_TZ = True
LANGUAGE_CODE = "pt-br"
USE_I18N = True
USE_L10N = True

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# -----------------------------------------------------------------------------
# Apps
# -----------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    'sslserver',

    # Terceiros
    "crispy_forms",
    "crispy_bootstrap5",

    # Apps do projeto
    "financas_pessoais",
    "core",
]

CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# -----------------------------------------------------------------------------
# Middleware
# -----------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",  # estáticos em produção
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    'core.views.middleware.ForceAuthMiddleware',   # se você realmente precisar dele
]

# Importante: agora apontando para financas_pessoais
ROOT_URLCONF = "financas_pessoais.urls"
WSGI_APPLICATION = "financas_pessoais.wsgi.application"

# -----------------------------------------------------------------------------
# Templates
# -----------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],  # pasta global opcional
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
            # Opcional: habilita {% static %} sem precisar {% load static %} em cada template.
            # "builtins": ["django.templatetags.static"],
        },
    },
]

# -----------------------------------------------------------------------------
# Banco de dados
# -----------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}
_db_url = config("DATABASE_URL", default=None)
if _db_url:
    DATABASES["default"] = dj_database_url.parse(_db_url, conn_max_age=600, ssl_require=not DEBUG)

# -----------------------------------------------------------------------------
# Arquivos estáticos
# -----------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# -----------------------------------------------------------------------------
# Arquivos de mídia (se houver)
# -----------------------------------------------------------------------------
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LOGIN_URL = 'login'
LOGIN_REDIRECT_URL = 'dashboard'
LOGOUT_REDIRECT_URL = 'landing'

# -----------------------------------------------------------------------------
# Segurança (produção) — use DEBUG=true em dev para evitar HTTPS
# -----------------------------------------------------------------------------
FORCE_SSL = config("FORCE_SSL", default=not DEBUG, cast=bool)

CSRF_COOKIE_SECURE = FORCE_SSL
SESSION_COOKIE_SECURE = FORCE_SSL
SECURE_SSL_REDIRECT = FORCE_SSL
SECURE_HSTS_SECONDS = 31536000 if FORCE_SSL else 0
SECURE_HSTS_INCLUDE_SUBDOMAINS = FORCE_SSL
SECURE_HSTS_PRELOAD = FORCE_SSL
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

# -----------------------------------------------------------------------------
# Logging (simples / console)
# -----------------------------------------------------------------------------
LOG_LEVEL = config("LOG_LEVEL", default="INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{levelname}] {asctime} {name}:{lineno} -> {message}",
            "style": "{",
        },
        "simple": {
            "format": "[{levelname}] {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose" if DEBUG else "simple",
            "stream": sys.stdout,
        },
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
}

# -----------------------------------------------------------------------------
# Sentry (opcional)
# -----------------------------------------------------------------------------
SENTRY_DSN = config("SENTRY_DSN", default=None)
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[DjangoIntegration()],
            send_default_pii=False,
            traces_sample_rate=0.2,
        )
    except Exception:
        pass
