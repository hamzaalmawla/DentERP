"""Core domain: errors, audit rules and the translation marker shared by every module."""

from .errors import AccessDeniedError, ConflictError, DomainError, HardDeleteError, NotFoundError

__all__ = [
    "AccessDeniedError",
    "ConflictError",
    "DomainError",
    "HardDeleteError",
    "NotFoundError",
]
