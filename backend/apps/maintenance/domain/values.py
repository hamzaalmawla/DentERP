"""Values of the maintenance module that other modules read through its DTOs."""

from enum import StrEnum


class RoundKind(StrEnum):
    MORNING = "morning"
    AFTERNOON = "afternoon"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    EXTERNAL_REPAIR = "external_repair"
    RESOLVED = "resolved"
