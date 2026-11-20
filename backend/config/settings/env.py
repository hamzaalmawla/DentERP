"""Read settings from environment variables.

Every secret and every value that differs between environments comes from here.
"""

import os

from django.core.exceptions import ImproperlyConfigured

_MISSING = object()


def env(name: str, default=_MISSING) -> str:
    """Return a variable, or the default. Without a default the variable is required."""
    value = os.environ.get(name)
    if value is None or value == "":
        if default is _MISSING:
            raise ImproperlyConfigured(f"Set the {name} environment variable.")
        return default
    return value


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be a whole number.") from exc


def env_list(name: str, default: list[str] | None = None) -> list[str]:
    """A comma-separated list. Spaces around items are ignored."""
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return list(default or [])
    return [item.strip() for item in value.split(",") if item.strip()]
