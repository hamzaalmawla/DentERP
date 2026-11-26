"""Errors of the accounts module. Each has a stable ``code`` the app reacts to.

HTTP status by class (``apps.core.domain.errors``): ``DomainError`` 400, ``AccessDeniedError``
403, ``NotFoundError`` 404, ``ConflictError`` 409.
"""

from collections.abc import Sequence
from datetime import datetime

from apps.core.domain.errors import AccessDeniedError, ConflictError, DomainError
from apps.core.domain.i18n import _


class InvalidCredentialsError(DomainError):
    """Wrong username or password. The same error for an unknown, inactive or wrong account,
    so the answer never tells which one it was."""

    def __init__(self) -> None:
        super().__init__("invalid_credentials", _("The username or password is incorrect."))


class AccountLockedError(AccessDeniedError):
    def __init__(self, locked_until: datetime) -> None:
        super().__init__(
            "account_locked",
            _("The account is locked after too many failed logins. Try again later."),
            {"locked_until": locked_until.isoformat()},
        )


class NoRoleError(AccessDeniedError):
    def __init__(self) -> None:
        super().__init__(
            "no_role", _("Your account has no role yet. Ask the system administrator.")
        )


class DashboardNotAllowedError(AccessDeniedError):
    def __init__(self) -> None:
        super().__init__(
            "dashboard_not_allowed",
            _(
                "Students and maintenance technicians use the mobile app. "
                "Your account cannot log in to the dashboard."
            ),
        )


class RoleNotHeldError(AccessDeniedError):
    def __init__(self, role: str) -> None:
        super().__init__(
            "role_not_held", _("You do not hold the role you selected."), {"role": role}
        )


class ActiveRoleRequiredError(AccessDeniedError):
    def __init__(self) -> None:
        super().__init__(
            "active_role_required",
            _("You hold more than one role. Choose the role to use first."),
        )


class PasswordChangeRequiredError(AccessDeniedError):
    def __init__(self) -> None:
        super().__init__(
            "password_change_required", _("Change your temporary password to continue.")
        )


class WrongPasswordError(DomainError):
    def __init__(self) -> None:
        super().__init__("wrong_password", _("The current password is incorrect."))


class PasswordUnchangedError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "password_unchanged", _("The new password must be different from the current one.")
        )


class PasswordInvalidError(DomainError):
    def __init__(self, messages: Sequence[str]) -> None:
        super().__init__(
            "password_invalid",
            _("The new password does not meet the password rules."),
            {"messages": list(messages)},
        )


class InvalidTokenError(DomainError):
    def __init__(self) -> None:
        super().__init__("token_invalid", _("The session has expired. Log in again."))


class UsernameTakenError(ConflictError):
    def __init__(self, username: str) -> None:
        super().__init__(
            "username_taken", _("This username is already used."), {"username": username}
        )


class UniversityIdTakenError(ConflictError):
    def __init__(self, university_id: str) -> None:
        super().__init__(
            "university_id_taken",
            _("This university ID belongs to another user."),
            {"university_id": university_id},
        )


class UnknownDepartmentError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "department_not_found", _("The department was not found or is deactivated.")
        )


class RoleRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("role_required", _("Give the user at least one role."))


class UnknownRoleError(DomainError):
    def __init__(self, roles: Sequence[str]) -> None:
        super().__init__(
            "unknown_role", _("One of the roles does not exist."), {"roles": sorted(roles)}
        )


class OwnAdminRoleError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "own_admin_role",
            _("You cannot remove the system administrator role from your own account."),
        )


class OwnAccountError(DomainError):
    def __init__(self) -> None:
        super().__init__("own_account", _("You cannot deactivate your own account."))


class AccountNotLockedError(ConflictError):
    def __init__(self) -> None:
        super().__init__("account_not_locked", _("The account is not locked."))


class UserManagementDeniedError(AccessDeniedError):
    def __init__(self) -> None:
        super().__init__("permission_denied", _("Only the system administrator can manage users."))


class InvalidUsernameError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            "username_invalid",
            _("A username may only contain letters, digits and . @ + - _ characters."),
        )


class FullNameRequiredError(DomainError):
    def __init__(self) -> None:
        super().__init__("full_name_required", _("Enter the user's full name in Arabic."))


class InvalidDeviceError(DomainError):
    def __init__(self) -> None:
        super().__init__("invalid_device", _("The device details are not valid."))
