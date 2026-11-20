"""Audit log rules (SYS-04): the actions recorded and how a change is described."""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any


class AuditAction(StrEnum):
    """Actions written to the audit log. Modules may log other action names as plain strings."""

    CREATE = "create"
    UPDATE = "update"
    DEACTIVATE = "deactivate"
    ACTIVATE = "activate"
    SUBMIT = "submit"
    APPROVE = "approve"
    RETURN = "return"
    REJECT = "reject"
    ASSIGN = "assign"
    TRANSFER = "transfer"
    LOGIN = "login"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    PASSWORD_CHANGE = "password_change"


def diff(before: Mapping[str, Any], after: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Fields whose value changed, as ``{field: {"old": ..., "new": ...}}``.

    A field missing on one side counts as ``None`` there, so ``diff({}, values)`` describes a
    new record and unchanged fields are left out.
    """
    changes: dict[str, dict[str, Any]] = {}
    for field in sorted(before.keys() | after.keys()):
        old, new = before.get(field), after.get(field)
        if old != new:
            changes[field] = {"old": old, "new": new}
    return changes
