"""Each settings module loads on its own, in a clean process, with only its variables set."""

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent

PRINT_SETTINGS = """
import json, django
from django.conf import settings
django.setup()
print(json.dumps({
    "DEBUG": settings.DEBUG,
    "LANGUAGE_CODE": settings.LANGUAGE_CODE,
    "LANGUAGES": [code for code, _ in settings.LANGUAGES],
    "TIME_ZONE": settings.TIME_ZONE,
    "USE_TZ": settings.USE_TZ,
    "DB_ENGINE": settings.DATABASES["default"]["ENGINE"],
    "DB_HOST": settings.DATABASES["default"]["HOST"],
    "DB_PASSWORD": settings.DATABASES["default"]["PASSWORD"],
    "BROKER": settings.CELERY_BROKER_URL,
    "CACHE_BACKEND": settings.CACHES["default"]["BACKEND"],
    "SECRET_KEY": settings.SECRET_KEY,
    "ALLOWED_HOSTS": settings.ALLOWED_HOSTS,
    "SESSION_COOKIE_SECURE": getattr(settings, "SESSION_COOKIE_SECURE", False),
    "HSTS": settings.SECURE_HSTS_SECONDS,
}))
"""

# Values a server provides. Nothing else from the developer's or CI's environment leaks in.
SERVER_ENV = {
    "DJANGO_SECRET_KEY": "x7#kq9!vT2m@Lp4$wZr8&nB6^cY1*eH3(uJ5)oF0-sA7+dG9=iK2",
    "DJANGO_ALLOWED_HOSTS": "dental.example.org",
    "POSTGRES_HOST": "db",
    "POSTGRES_PASSWORD": "server-db-password",
    "REDIS_URL": "redis://redis:6379/0",
    "S3_ACCESS_KEY_ID": "GK1234567890abcdef12345678",
    "S3_SECRET_ACCESS_KEY": "f" * 64,
}


def run_python(module: str, extra_env: dict[str, str], *args: str) -> subprocess.CompletedProcess:
    env = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", "/tmp"),
        "DJANGO_SETTINGS_MODULE": module,
        **extra_env,
    }
    return subprocess.run(
        [sys.executable, *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )


def load(module: str, extra_env: dict[str, str]) -> dict:
    result = run_python(module, extra_env, "-c", PRINT_SETTINGS)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize(
    ("module", "extra_env"),
    [
        ("config.settings.dev", {}),
        ("config.settings.test", {}),
        ("config.settings.staging", SERVER_ENV),
        ("config.settings.prod", SERVER_ENV),
    ],
)
def test_settings_module_loads_with_shared_defaults(module, extra_env):
    loaded = load(module, extra_env)

    assert loaded["LANGUAGE_CODE"] == "ar"
    assert loaded["LANGUAGES"] == ["ar", "en"]
    assert loaded["TIME_ZONE"] == "Asia/Damascus"
    assert loaded["USE_TZ"] is True
    assert loaded["DB_ENGINE"] == "django.db.backends.postgresql"
    assert loaded["BROKER"].startswith("redis://")
    assert loaded["CACHE_BACKEND"] == "django.core.cache.backends.redis.RedisCache"


def test_dev_starts_without_any_environment_variables():
    loaded = load("config.settings.dev", {})

    assert loaded["DEBUG"] is True
    assert loaded["DB_HOST"] == "localhost"


@pytest.mark.parametrize("module", ["config.settings.staging", "config.settings.prod"])
def test_server_settings_take_secrets_from_the_environment(module):
    loaded = load(module, SERVER_ENV)

    assert loaded["DEBUG"] is False
    assert loaded["SECRET_KEY"] == SERVER_ENV["DJANGO_SECRET_KEY"]
    assert loaded["DB_PASSWORD"] == SERVER_ENV["POSTGRES_PASSWORD"]
    assert loaded["DB_HOST"] == "db"
    assert loaded["BROKER"] == "redis://redis:6379/0"
    assert loaded["ALLOWED_HOSTS"] == ["dental.example.org"]
    assert loaded["SESSION_COOKIE_SECURE"] is True


def test_production_uses_a_one_year_hsts_period():
    assert load("config.settings.prod", SERVER_ENV)["HSTS"] == 31_536_000


@pytest.mark.parametrize("module", ["config.settings.staging", "config.settings.prod"])
@pytest.mark.parametrize(
    "missing",
    [
        "DJANGO_SECRET_KEY",
        "DJANGO_ALLOWED_HOSTS",
        "POSTGRES_PASSWORD",
        "S3_ACCESS_KEY_ID",
        "S3_SECRET_ACCESS_KEY",
    ],
)
def test_server_settings_refuse_to_start_without_a_required_variable(module, missing):
    env = {key: value for key, value in SERVER_ENV.items() if key != missing}

    result = run_python(module, env, "-c", PRINT_SETTINGS)

    assert result.returncode != 0
    assert "ImproperlyConfigured" in result.stderr
    assert missing in result.stderr


def test_production_passes_the_django_deployment_checklist():
    result = run_python(
        "config.settings.prod",
        SERVER_ENV,
        "manage.py",
        "check",
        "--deploy",
        "--fail-level",
        "WARNING",
    )

    assert result.returncode == 0, result.stdout + result.stderr
