"""Ports of the notifications module (P0.5 outline; P1.10 may refine them inside the module).

The push tokens belong to accounts (``DeviceToken``); P1.10 reads them through an accounts
application service, behind the ``DeviceTokenReader`` port below.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from apps.core.application.ports import Clock, UnitOfWork

from .dtos import NotificationDTO

__all__ = [
    "Clock",
    "DeviceTokenReader",
    "NotificationRepository",
    "PushSender",
    "UnitOfWork",
]


@runtime_checkable
class NotificationRepository(Protocol):
    def unread_count(self, user_id: int) -> int: ...

    def of_user(self, user_id: int) -> Sequence[NotificationDTO]: ...


@runtime_checkable
class DeviceTokenReader(Protocol):
    def tokens_of(self, user_id: int) -> Sequence[str]: ...


@runtime_checkable
class PushSender(Protocol):
    def send(self, tokens: Sequence[str], title: str, body: str, data: dict[str, str]) -> None:
        """Send one push message (Firebase Cloud Messaging). Raises on failure; the row
        stays (SYS-03)."""
        ...
