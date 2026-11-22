"""What the maintenance module gives other modules (P0.5 contract). Frozen dataclasses only.

Tickets and rounds hold no patient data (technicians see no patients, design section 8).
"""

from dataclasses import dataclass
from datetime import date, datetime

from apps.maintenance.domain.values import RoundKind, TicketStatus

__all__ = ["RoundDTO", "RoundKind", "TicketDTO", "TicketStatus"]


@dataclass(frozen=True, slots=True)
class RoundDTO:
    id: int
    clinic_id: int
    day: date
    kind: RoundKind
    by_id: int
    submitted_at: datetime
    failed_checks: int = 0


@dataclass(frozen=True, slots=True)
class TicketDTO:
    id: int
    clinic_id: int
    chair_id: int
    category_id: int
    status: TicketStatus
    is_external: bool
    opened_at: datetime
    opened_by_id: int | None = None
    resolved_by_id: int | None = None
    resolved_at: datetime | None = None
