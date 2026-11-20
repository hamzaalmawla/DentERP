"""Staging: the same server as production, separate containers and database.

Every secret must be set in the environment; nothing has a default here.
"""

from django.core.exceptions import ImproperlyConfigured

from .base import *

DEBUG = False

if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS.")

# nginx terminates HTTPS and passes the original scheme.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
# nginx adds the client address to X-Forwarded-For; read it from there (audit log, throttles).
NUM_PROXIES = env_int("DJANGO_NUM_PROXIES", 1)
REST_FRAMEWORK = {**REST_FRAMEWORK, "NUM_PROXIES": NUM_PROXIES or None}
SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
# The uptime check and the container health check call /health/ over plain HTTP.
SECURE_REDIRECT_EXEMPT = [r"^health/$"]
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 60 * 60)
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

STATIC_ROOT = env("DJANGO_STATIC_ROOT", str(BASE_DIR / "staticfiles"))
