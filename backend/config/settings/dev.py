"""Development on a developer's laptop with deploy/docker-compose.yml.

Safe defaults are filled in so the project starts without a .env file. They are for
local use only: staging and production refuse to start without real values.
"""

import os

for _name, _value in {
    "DJANGO_SECRET_KEY": "dev-only-insecure-secret-key-do-not-use-elsewhere",
    "POSTGRES_PASSWORD": "spu_dental",
    "S3_ACCESS_KEY_ID": "GK000000000000000000000001",
    "S3_SECRET_ACCESS_KEY": "0" * 64,
}.items():
    os.environ.setdefault(_name, _value)

from .base import *  # noqa: E402

DEBUG = True
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", ["localhost", "127.0.0.1", "0.0.0.0", "web"])

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

DEMO_USERS_ALLOWED = True
