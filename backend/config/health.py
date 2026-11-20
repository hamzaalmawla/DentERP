"""GET /health/ — used by the uptime check, Docker health checks and deployments.

Returns 200 when the database and Redis both answer, otherwise 503. The body names
each check so a failing service is easy to spot; it never includes error details.
"""

import logging

import redis
from django.conf import settings
from django.db import connection
from django.http import JsonResponse
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


def check_database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        logger.exception("Health check: database is not reachable")
        return False
    return True


def check_redis() -> bool:
    timeout = settings.HEALTH_CHECK_TIMEOUT_SECONDS
    client = redis.Redis.from_url(
        settings.REDIS_URL, socket_timeout=timeout, socket_connect_timeout=timeout
    )
    try:
        return bool(client.ping())
    except Exception:
        logger.exception("Health check: Redis is not reachable")
        return False
    finally:
        client.close()


@never_cache
@require_GET
def health(request):
    checks = {"database": check_database(), "redis": check_redis()}
    healthy = all(checks.values())
    return JsonResponse(
        {
            "status": "ok" if healthy else "error",
            "checks": {name: "ok" if ok else "error" for name, ok in checks.items()},
        },
        status=200 if healthy else 503,
    )
