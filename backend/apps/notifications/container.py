"""Builds the notifications services with their real adapters (design section 5)."""

from .application.facade import NotificationsFacade, NotificationsFacadeService


def facade() -> NotificationsFacade:
    """The ``Notifier`` other modules' containers pass to their services (P1.10)."""
    return NotificationsFacadeService()
