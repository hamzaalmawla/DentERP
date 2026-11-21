"""Settings shared by every environment.

Environment files (dev, test, staging, prod) import everything from here and change
only what differs. Secrets and per-server values come from environment variables;
deploy/.env.example lists all of them.
"""

from datetime import timedelta
from pathlib import Path

from django.utils.translation import gettext_lazy as _

from .env import env, env_bool, env_int, env_list

BASE_DIR = Path(__file__).resolve().parent.parent.parent

SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# Applications -------------------------------------------------------------
# django.contrib.admin (with Unfold) and import-export are added by the prompts that use
# them (P0.4 and later).

DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "django_filters",
    "drf_spectacular",
    "django_celery_beat",
    "simple_history",
]

LOCAL_APPS = [
    "apps.core",
    "apps.accounts",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.core.infrastructure.request_context.CurrentRequestMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

# Database -----------------------------------------------------------------

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("POSTGRES_DB", "spu_dental"),
        "USER": env("POSTGRES_USER", "spu_dental"),
        "PASSWORD": env("POSTGRES_PASSWORD"),
        "HOST": env("POSTGRES_HOST", "localhost"),
        "PORT": env_int("POSTGRES_PORT", 5432),
        "CONN_MAX_AGE": env_int("POSTGRES_CONN_MAX_AGE", 60),
        "CONN_HEALTH_CHECKS": True,
        "OPTIONS": {"connect_timeout": 5},
    }
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Users ----------------------------------------------------------------------

AUTH_USER_MODEL = "accounts.User"

# Redis: Celery broker and cache -------------------------------------------

REDIS_URL = env("REDIS_URL", "redis://localhost:6379/0")
REDIS_CACHE_URL = env("REDIS_CACHE_URL", "redis://localhost:6379/1")

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_CACHE_URL,
        "KEY_PREFIX": "spu_dental",
        "TIMEOUT": 300,
    }
}

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = None  # tasks report through the database, not result storage
CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_TASK_TIME_LIMIT = 10 * 60
CELERY_TIMEZONE = "Asia/Damascus"
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# Passwords ----------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
        "OPTIONS": {
            "user_attributes": ("username", "full_name_ar", "full_name_en", "university_id"),
        },
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Language and time --------------------------------------------------------
# Arabic first (right to left), English second.

LANGUAGE_CODE = "ar"
LANGUAGES = [
    ("ar", _("Arabic")),
    ("en", _("English")),
]
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Damascus"
USE_I18N = True
USE_TZ = True

# Static files and uploads -------------------------------------------------
# Clinical photos and X-rays go to S3-compatible storage (Garage); static files are
# served from local disk (by nginx in staging and production).

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {"BACKEND": "storages.backends.s3.S3Storage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
}

AWS_S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", "http://localhost:3900")
AWS_S3_REGION_NAME = env("S3_REGION", "garage")
AWS_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY")
AWS_STORAGE_BUCKET_NAME = env("S3_BUCKET", "spu-dental-media")
AWS_S3_ADDRESSING_STYLE = "path"
AWS_S3_SIGNATURE_VERSION = "s3v4"
AWS_DEFAULT_ACL = None
AWS_QUERYSTRING_AUTH = True  # files are private; the app gets signed URLs
AWS_QUERYSTRING_EXPIRE = 15 * 60
AWS_S3_FILE_OVERWRITE = False

DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# Reverse proxies in front of Django (nginx in staging and production). The client IP for
# the audit log and the throttles is then read from X-Forwarded-For. 0 in development.
NUM_PROXIES = env_int("DJANGO_NUM_PROXIES", 0)

# REST API -----------------------------------------------------------------
# Conventions in docs/system-design.md section 7; the pieces live in apps/core/api.
# Authentication, roles and throttles: apps/accounts/api (design section 8).

REST_FRAMEWORK = {
    # JWT only. The authentication class also checks X-Active-Role and the
    # password-change gate (apps/accounts/api/authentication.py).
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.accounts.api.authentication.AccountJWTAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    # Login: 10 a minute per IP; every other endpoint: 120 a minute per user (per IP when
    # anonymous). The rates are read from the shared cache (Redis).
    "DEFAULT_THROTTLE_CLASSES": ["rest_framework.throttling.UserRateThrottle"],
    "DEFAULT_THROTTLE_RATES": {"login": "10/min", "user": "120/min"},
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.MultiPartParser",
        "rest_framework.parsers.FormParser",
    ],
    "DEFAULT_PAGINATION_CLASS": "apps.core.api.pagination.StandardPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.OrderingFilter",
    ],
    "ORDERING_PARAM": "ordering",
    "EXCEPTION_HANDLER": "apps.core.api.errors.exception_handler",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "NUM_PROXIES": NUM_PROXIES or None,
}

# JWT (design sections 7 and 8): access 15 minutes, refresh 30 days, rotated on each use;
# the old refresh token is blacklisted. A password change revokes every token issued before it.
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,  # the Login service records it
    "CHECK_REVOKE_TOKEN": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": env("JWT_SIGNING_KEY", SECRET_KEY),
    "AUTH_HEADER_TYPES": ("Bearer",),
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# Development only: the create_demo_users command refuses to run when this is off.
DEMO_USERS_ALLOWED = False

SPECTACULAR_SETTINGS = {
    "TITLE": "SPU Dental Clinic System API",
    "DESCRIPTION": "API for the student, supervisor and maintenance mobile interfaces.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    # The schema and docs are public (SYS-09); a token sent with them is ignored.
    "SERVE_AUTHENTICATION": [],
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {
        "RoleEnum": "apps.accounts.api.serializers.ROLE_CHOICES",
        "PlatformEnum": "apps.accounts.api.serializers.PLATFORM_CHOICES",
    },
}

# Security shared by every environment ------------------------------------

SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False  # the dashboard's own forms read it
X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"

# Email --------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", "localhost")
EMAIL_PORT = env_int("EMAIL_PORT", 587)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "no-reply@localhost")

# Push notifications (FCM). Path to the Firebase service account JSON file.
FIREBASE_CREDENTIALS_FILE = env("FIREBASE_CREDENTIALS_FILE", "")

# Health check -------------------------------------------------------------

HEALTH_CHECK_TIMEOUT_SECONDS = 2

# Logging ------------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "plain"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", "INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
    },
}
