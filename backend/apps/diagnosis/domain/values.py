"""Values of the diagnosis module that other modules read through its DTOs."""

from enum import StrEnum


class DiagnosisStatus(StrEnum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    APPROVED = "approved"
    RETURNED = "returned"


class PlanItemStatus(StrEnum):
    PLANNED = "planned"
    REFERRED = "referred"
    DONE = "done"
    CANCELLED = "cancelled"
