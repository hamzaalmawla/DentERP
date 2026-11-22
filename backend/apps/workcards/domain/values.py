"""Values of the workcards module that other modules read through its DTOs."""

from enum import StrEnum


class CaseStatus(StrEnum):
    OPEN = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class StepStatus(StrEnum):
    PENDING = "pending"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    RETURNED = "returned"
