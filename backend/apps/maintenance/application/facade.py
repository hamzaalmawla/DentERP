"""The maintenance module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never maintenance's models or repositories. Every function takes
and returns ids and DTOs.
"""

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from apps.core.application.dtos import Actor

from .dtos import RoundDTO, TicketDTO


@runtime_checkable
class MaintenanceFacade(Protocol):
    def rounds_on(self, clinic_id: int, day: date) -> Sequence[RoundDTO]:
        """The clinic's morning and afternoon rounds of the day (F6/F18 report)."""
        ...

    def open_tickets(self, *, clinic_id: int | None = None) -> Sequence[TicketDTO]:
        """Tickets not yet resolved, oldest first; in one clinic or in all."""
        ...

    def can_read_ticket(self, actor: Actor, ticket_id: int) -> bool:
        """The ticket is in the actor's scope. Used by media for fault photos."""
        ...


class MaintenanceFacadeService:
    """The maintenance facade the container hands out. Built in P1.9."""

    def rounds_on(self, clinic_id: int, day: date) -> Sequence[RoundDTO]:
        raise NotImplementedError

    def open_tickets(self, *, clinic_id: int | None = None) -> Sequence[TicketDTO]:
        raise NotImplementedError

    def can_read_ticket(self, actor: Actor, ticket_id: int) -> bool:
        raise NotImplementedError
