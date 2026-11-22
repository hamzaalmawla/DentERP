"""Ports of the maintenance module (P0.5 outline; P1.9 may refine them inside the module).

Repository ports return DTOs; the ORM adapters live in ``infrastructure/``. Other modules are
reached through their facades only.
"""

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from apps.academics.application.facade import AcademicsFacade
from apps.core.application.ports import AuditLogger, Clock, Notifier, UnitOfWork
from apps.media.application.facade import MediaFacade
from apps.setup.application.facade import SetupFacade

from .dtos import RoundDTO, RoundKind, TicketDTO

__all__ = [
    "AcademicsFacade",  # supervisor scope (a supervisor reports faults in their clinics)
    "AuditLogger",
    "Clock",
    "MediaFacade",  # fault photos
    "Notifier",
    "RoundRepository",
    "SetupFacade",  # chairs, checklist, fault categories, chair status
    "TicketRepository",
    "UnitOfWork",
]


@runtime_checkable
class RoundRepository(Protocol):
    def find(self, clinic_id: int, day: date, kind: RoundKind) -> RoundDTO | None:
        """BR-11: one round per clinic, kind and day."""
        ...

    def on_day(self, clinic_id: int, day: date) -> Sequence[RoundDTO]: ...


@runtime_checkable
class TicketRepository(Protocol):
    def get(self, ticket_id: int, *, for_update: bool = False) -> TicketDTO | None: ...

    def open_tickets(self, clinic_id: int | None) -> Sequence[TicketDTO]: ...

    def open_blocking_for_chair(self, chair_id: int) -> Sequence[TicketDTO]:
        """BR-12: a chair goes back into service only when none is left."""
        ...
