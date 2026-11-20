"""Production. Staging settings with a long HSTS period."""

from .staging import *

SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 60 * 60 * 24 * 365)
# Covers only subdomains of the dashboard's own host (dental.<spu domain>), not the
# whole university domain.
SECURE_HSTS_INCLUDE_SUBDOMAINS = True

# The HSTS preload list is a commitment for the whole registered domain, which belongs
# to the university, not to this system.
SILENCED_SYSTEM_CHECKS = ["security.W021"]
