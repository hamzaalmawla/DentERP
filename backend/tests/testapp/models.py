from django.conf import settings
from django.db import models

from apps.core.infrastructure.history import track_history
from apps.core.models import BaseModel


class Note(BaseModel):
    """A plain module model: soft delete, user fields, history and scope are tested on it."""

    title = models.CharField(max_length=100)
    body = models.TextField(blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, related_name="+"
    )
    due = models.DateField(null=True, blank=True)

    history = track_history()

    def __str__(self) -> str:
        return self.title
