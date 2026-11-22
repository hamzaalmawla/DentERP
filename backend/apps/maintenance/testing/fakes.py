"""In-memory fake of the maintenance facade, for other modules' service tests.

maintenance = InMemoryMaintenanceFacade()
maintenance.add_ticket(TicketDTO(5, clinic_id=2, chair_id=10, category_id=1,
                                 status=TicketStatus.OPEN, is_external=False, opened_at=now))
"""

from collections.abc import Sequence
from datetime import date

from apps.core.application.dtos import Actor
from apps.maintenance.application.dtos import RoundDTO, TicketDTO, TicketStatus

TECHNICIAN = "technician"


class InMemoryMaintenanceFacade:
    def __init__(self) -> None:
        self.rounds: list[RoundDTO] = []
        self.tickets: dict[int, TicketDTO] = {}

    def add_round(self, round_: RoundDTO) -> RoundDTO:
        self.rounds.append(round_)
        return round_

    def add_ticket(self, ticket: TicketDTO) -> TicketDTO:
        self.tickets[ticket.id] = ticket
        return ticket

    # --- MaintenanceFacade --------------------------------------------------------------

    def rounds_on(self, clinic_id: int, day: date) -> Sequence[RoundDTO]:
        return tuple(r for r in self.rounds if r.clinic_id == clinic_id and r.day == day)

    def open_tickets(self, *, clinic_id: int | None = None) -> Sequence[TicketDTO]:
        return tuple(
            sorted(
                (
                    t
                    for t in self.tickets.values()
                    if t.status != TicketStatus.RESOLVED and clinic_id in (None, t.clinic_id)
                ),
                key=lambda t: t.opened_at,
            )
        )

    def can_read_ticket(self, actor: Actor, ticket_id: int) -> bool:
        ticket = self.tickets.get(ticket_id)
        return ticket is not None and (
            actor.role == TECHNICIAN or ticket.opened_by_id == actor.user_id
        )
