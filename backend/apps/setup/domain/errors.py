"""Errors of the setup module. Each has a stable ``code`` the app and the dashboard react to.

An error about one value carries ``details["field"]``, the name of that value, so the dashboard
shows it on the right form field.
"""

from apps.core.domain.errors import AccessDeniedError, ConflictError, DomainError
from apps.core.domain.i18n import _


class InvalidValueError(DomainError):
    """A value breaks a rule; ``field`` names it."""

    def __init__(self, code: str, message: str, field: str, **details: object) -> None:
        super().__init__(code, message, {"field": field, **details})


class RecordTakenError(InvalidValueError):
    """Another record (active or not) already uses this value, which must be unique."""


class ReferenceNotFoundError(InvalidValueError):
    """The record a value points to does not exist or is deactivated."""


class SetupAdminRequiredError(AccessDeniedError):
    def __init__(self) -> None:
        super().__init__(
            "permission_denied", _("Only the system administrator can change the setup.")
        )


class ReasonRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("reason_required", _("A reason is required."), {"field": "reason"})


class CurrentTermError(ConflictError):
    def __init__(self) -> None:
        super().__init__(
            "term_is_current",
            _("The current term cannot be deactivated. Make another term current first."),
        )


class ChairCountError(InvalidValueError):
    def __init__(self, field: str = "chairs_to_add") -> None:
        super().__init__(
            "chair_count_invalid",
            _("The number of chairs to add must be between 1 and 100."),
            field,
        )
