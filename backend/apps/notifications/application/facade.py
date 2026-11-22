"""The notifications module's public functions (P0.5 contract, docs/contracts.md).

``notify`` is core's ``Notifier`` port: other modules' services receive the ``Notifier`` from
their container and never depend on this module directly. P1.10 makes the container's
``notifier()`` return the real adapter (a row per recipient, then a push through Celery).
"""

from collections.abc import Mapping, Sequence
from typing import Any, Protocol, runtime_checkable

from apps.core.application.dtos import NotificationTarget
from apps.core.application.ports import Notifier


@runtime_checkable
class NotificationsFacade(Notifier, Protocol):
    def unread_count(self, user_id: int) -> int:
        """The user's unread notifications (the badge in the app)."""
        ...


class NotificationsFacadeService:
    """The notifications facade the container hands out. Built in P1.10."""

    def notify(
        self,
        recipient_ids: Sequence[int],
        type: str,
        title_key: str,
        body_key: str,
        params: Mapping[str, Any] | None = None,
        target: NotificationTarget | None = None,
    ) -> None:
        raise NotImplementedError

    def unread_count(self, user_id: int) -> int:
        raise NotImplementedError
