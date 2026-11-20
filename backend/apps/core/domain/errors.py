"""Errors raised by business rules.

Every rule that refuses an action raises ``DomainError`` (or one of its subclasses) with a
stable ``code`` the app can react to, a message marked with ``_`` from ``domain.i18n``, and
optional ``details``. One API exception handler (``apps.core.api.errors``) turns it into
``{"code", "message", "details"}`` with the message in the request's language.

The subclass chooses the HTTP status; the domain itself knows nothing about HTTP:

=======================  ======  ===========================================================
Class                    Status  Use for
=======================  ======  ===========================================================
``DomainError``          400     A business rule refuses the request (BR-xx)
``NotFoundError``        404     The record does not exist or is outside the user's scope
``AccessDeniedError``    403     The user's role may not do this at all
``ConflictError``        409     The record's current state does not allow the change
=======================  ======  ===========================================================

Placeholders in the message use ``%(name)s`` and are filled from ``details`` after translation.
"""

from collections.abc import Mapping
from typing import Any

from .i18n import _


class DomainError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.message = message
        self.details: dict[str, Any] = dict(details or {})


class NotFoundError(DomainError):
    def __init__(
        self,
        code: str = "not_found",
        message: str = _("The record was not found."),
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message, details)


class AccessDeniedError(DomainError):
    def __init__(
        self,
        code: str = "permission_denied",
        message: str = _("You do not have permission to do this."),
        details: Mapping[str, Any] | None = None,
    ) -> None:
        super().__init__(code, message, details)


class ConflictError(DomainError):
    """The record's state does not allow this change (for example approving an approved step)."""


class HardDeleteError(DomainError):
    """Raised when code tries to delete a row. Records are deactivated instead (SYS-10)."""

    def __init__(self) -> None:
        super().__init__(
            "delete_not_allowed",
            _("Records cannot be deleted. Deactivate the record instead."),
        )
