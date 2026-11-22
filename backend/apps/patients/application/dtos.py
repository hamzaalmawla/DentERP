"""What the patients module gives other modules (P0.5 contract). Frozen dataclasses only.

A summary holds no clinical data, so reception may see it (design section 8).
"""

from dataclasses import dataclass
from datetime import date, datetime

from apps.patients.domain.values import AssignmentPurpose, Sex

__all__ = ["AssignmentDTO", "AssignmentPurpose", "PatientSummaryDTO", "Sex"]


@dataclass(frozen=True, slots=True)
class PatientSummaryDTO:
    id: int
    file_no: str
    full_name: str
    sex: Sex
    date_of_birth: date | None = None
    phone: str = ""


@dataclass(frozen=True, slots=True)
class AssignmentDTO:
    """A student's access to a patient, for diagnosis or for treatment (BR-03)."""

    id: int
    patient_id: int
    student_id: int
    purpose: AssignmentPurpose
    active: bool
    started_at: datetime
    case_id: int | None = None
    ended_at: datetime | None = None
