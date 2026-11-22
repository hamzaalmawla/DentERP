"""What the notifications module gives other modules (P0.5 contract). Frozen dataclasses only."""

from dataclasses import dataclass
from datetime import datetime

from apps.core.application.dtos import NotificationTarget

__all__ = ["NotificationDTO", "NotificationTarget"]


@dataclass(frozen=True, slots=True)
class NotificationDTO:
    """One notification of one recipient, with the text in the recipient's language."""

    id: int
    recipient_id: int
    type: str
    title: str
    body: str
    created_at: datetime
    target: NotificationTarget | None = None
    read_at: datetime | None = None
