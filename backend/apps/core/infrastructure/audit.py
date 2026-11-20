"""ORM adapter of the ``AuditLogger`` port, and a helper that describes a model row for diffs."""

from collections.abc import Iterable, Mapping
from typing import Any

from django.core.serializers.json import DjangoJSONEncoder
from django.db import models

from apps.core.models import AuditLog

from .request_context import current_ip, current_user_id

# Bookkeeping fields every row has; they are not part of a change.
_NOT_AUDITED = frozenset({"created_at", "created_by", "updated_at", "updated_by"})


class OrmAuditLogger:
    def log(
        self,
        action: str,
        *,
        model: str = "",
        object_id: int | str | None = None,
        changes: Mapping[str, Any] | None = None,
        user_id: int | None = None,
    ) -> None:
        AuditLog.objects.create(
            user_id=user_id if user_id is not None else current_user_id(),
            action=str(action),
            model=model,
            object_id="" if object_id is None else str(object_id),
            changes=dict(changes or {}),
            ip=current_ip(),
        )


def model_label(model: type[models.Model] | models.Model) -> str:
    """``"app_label.ModelName"``, the value of ``AuditLog.model``."""
    return model._meta.label


def snapshot(instance: models.Model, exclude: Iterable[str] = ()) -> dict[str, Any]:
    """The row's field values in JSON form (foreign keys as ids), for ``domain.audit.diff``.

    Take one before and one after a change; ``diff(before, after)`` is the audit ``changes``.
    """
    skipped = _NOT_AUDITED | set(exclude)
    encoder = DjangoJSONEncoder()
    values: dict[str, Any] = {}
    for field in instance._meta.concrete_fields:
        if field.name in skipped or field.primary_key:
            continue
        value = getattr(instance, field.attname)
        if value is not None and not isinstance(value, bool | int | float | str | list | dict):
            value = encoder.default(value)
        values[field.name] = value
    return values
