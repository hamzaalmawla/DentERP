"""Core persistence: the base every model inherits, and the audit log table.

Part of the persistence adapter (design section 5): services never import this file.
"""

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.core.domain.errors import HardDeleteError
from apps.core.infrastructure.request_context import current_user_id


class SoftDeleteQuerySet(models.QuerySet):
    """Rows are never deleted (SYS-10): ``delete()`` raises; ``deactivate()`` hides the rows."""

    def delete(self):
        raise HardDeleteError()

    delete.queryset_only = True

    def deactivate(self) -> int:
        return self.update(
            is_active=False, updated_at=timezone.now(), updated_by_id=current_user_id()
        )

    def activate(self) -> int:
        return self.update(
            is_active=True, updated_at=timezone.now(), updated_by_id=current_user_id()
        )


class ActiveManager(models.Manager.from_queryset(SoftDeleteQuerySet)):
    """The default manager: only active rows."""

    def get_queryset(self):
        return super().get_queryset().filter(is_active=True)


AllObjectsManager = models.Manager.from_queryset(SoftDeleteQuerySet)


class BaseModel(models.Model):
    """The base of every model in the system (design section 6).

    - ``objects`` returns active rows only; ``all_objects`` returns every row.
    - ``delete()`` raises ``HardDeleteError``; ``deactivate()`` sets ``is_active`` to False.
    - ``created_by`` / ``updated_by`` are filled on ``save()`` from the current request's user
      or the enclosing ``acting_as(user_id)`` block. ``updated_by`` is ``None`` when the system
      made the last change. ``bulk_create`` and ``QuerySet.update`` skip ``save()``; set the
      fields yourself there.
    """

    created_at = models.DateTimeField(_("created at"), auto_now_add=True, editable=False)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("created by"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
    )
    updated_at = models.DateTimeField(_("updated at"), auto_now=True, editable=False)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("updated by"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        editable=False,
        related_name="+",
    )
    is_active = models.BooleanField(_("active"), default=True, db_index=True)

    objects = ActiveManager()
    all_objects = AllObjectsManager()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs) -> None:
        user_id = current_user_id()
        if self._state.adding and self.created_by_id is None:
            self.created_by_id = user_id
        self.updated_by_id = user_id
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = {*update_fields, "updated_by", "updated_at"}
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise HardDeleteError()

    def deactivate(self) -> None:
        self.is_active = False
        self.save(update_fields=["is_active"])

    def activate(self) -> None:
        self.is_active = True
        self.save(update_fields=["is_active"])


class AuditLog(BaseModel):
    """One audited action (SYS-04, DB-17). Rows are written once and never changed."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name=_("user"),
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    action = models.CharField(_("action"), max_length=40)
    model = models.CharField(_("record type"), max_length=100, blank=True)
    object_id = models.CharField(_("record id"), max_length=64, blank=True)
    changes = models.JSONField(_("changes"), default=dict, blank=True, encoder=DjangoJSONEncoder)
    ip = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    at = models.DateTimeField(_("time"), default=timezone.now)

    class Meta:
        verbose_name = _("audit log entry")
        verbose_name_plural = _("audit log")
        ordering = ["-at", "-id"]
        indexes = [
            models.Index(fields=["model", "object_id"], name="core_audit_model_object_idx"),
            models.Index(fields=["at"], name="core_audit_at_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.action} {self.model} {self.object_id}".strip()

    def save(self, *args, **kwargs) -> None:
        if not self._state.adding:
            raise ValueError("Audit log rows are written once and never changed.")
        super().save(*args, **kwargs)
