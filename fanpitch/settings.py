"""
Django settings for the FanPitch backend.

Reads everything sensitive from env vars (loaded via python-dotenv in development).
"""
from datetime import timedelta
from pathlib import Path
import os

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def env(key: str, default=None, cast=str):
    val = os.environ.get(key, default)
    if val is None:
        return None
    if cast is bool:
        return str(val).lower() in ("1", "true", "yes", "on")
    if cast is int:
        return int(val)
    if cast is list:
        return [s.strip() for s in str(val).split(",") if s.strip()]
    return val


SECRET_KEY = env("DJANGO_SECRET_KEY", "dev-insecure-key-change-me")
DEBUG = env("DJANGO_DEBUG", "True", bool)
ALLOWED_HOSTS = env("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,0.0.0.0", list)


INSTALLED_APPS = [
    "daphne",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # third-party
    "rest_framework",
    "rest_framework_simplejwt",
    "corsheaders",
    "channels",
    "django_filters",
    "drf_spectacular",
    # local
    "apps.accounts",
    "apps.matches",
    "apps.feed",
    "apps.interactions",
    "apps.gamification",
    "apps.ai",
    "apps.realtime",
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "fanpitch.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "fanpitch.wsgi.application"
ASGI_APPLICATION = "fanpitch.asgi.application"


# Database
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "fanpitch"),
        "USER": env("POSTGRES_USER", "fanpitch"),
        "PASSWORD": env("POSTGRES_PASSWORD", "fanpitch"),
        "HOST": env("POSTGRES_HOST", "127.0.0.1"),
        "PORT": env("POSTGRES_PORT", "5432"),
        "CONN_MAX_AGE": 60,
    }
}

# Channels: Redis layer (falls back to in-memory if REDIS_URL missing — dev only)
REDIS_URL = env("REDIS_URL", "redis://127.0.0.1:6379/0")
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {"hosts": [REDIS_URL]},
    }
}

# Cache (same Redis)
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
    }
}

# Celery
CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_TASK_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
# In DEBUG mode we run tasks synchronously so the demo works without a worker.
# In prod, keep the worker process running.
CELERY_TASK_ALWAYS_EAGER = DEBUG
CELERY_TASK_EAGER_PROPAGATES = DEBUG


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# DRF
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "30/min",
        "user": "120/min",
        "ai": "5/hour",
    },
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=14),
    "ROTATE_REFRESH_TOKENS": True,
}

SPECTACULAR_SETTINGS = {
    "TITLE": "FanPitch API",
    "DESCRIPTION": "Real-time social football experience — AWS Sports Innovation Cup 2026",
    "VERSION": "0.1.0",
}


# CORS — in DEBUG, allow any localhost / 127.0.0.1 port via regex (Flutter web
# uses random ports). We do NOT set CORS_ALLOW_ALL_ORIGINS together with
# CORS_ALLOW_CREDENTIALS because Chrome rejects the wildcard with credentials.
CORS_ALLOWED_ORIGINS = env("CORS_ALLOWED_ORIGINS",
                           "http://localhost:3000,http://127.0.0.1:3000", list)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost(:\d+)?$",
    r"^http://127\.0\.0\.1(:\d+)?$",
]
CORS_ALLOW_CREDENTIALS = True

# AWS / Bedrock / S3
AWS_REGION = env("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = env("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = env("AWS_SECRET_ACCESS_KEY", "")
S3_BUCKET = env("S3_BUCKET", "fanpitch-media-dev")
CLOUDFRONT_DOMAIN = env("CLOUDFRONT_DOMAIN", "")
BEDROCK_ENABLED = env("BEDROCK_ENABLED", "false", bool)
BEDROCK_MODEL_ID = env("BEDROCK_MODEL_ID", "anthropic.claude-3-haiku-20240307-v1:0")

# Football-Data.org
FOOTBALL_DATA_API_KEY = env("FOOTBALL_DATA_API_KEY", "")
FOOTBALL_DATA_BASE_URL = env("FOOTBALL_DATA_BASE_URL", "https://api.football-data.org/v4")

# Simulator
SIMULATOR_DEFAULT_SPEED = env("SIMULATOR_DEFAULT_SPEED", "10", int)

# Logging
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django": {"level": "INFO"},
        "fanpitch": {"level": "DEBUG" if DEBUG else "INFO"},
    },
}
