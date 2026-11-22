"""What the workcards module gives other modules (P0.5 contract). Frozen dataclasses only."""

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal

from apps.workcards.domain.values import CaseStatus, StepStatus

__all__ = [
    "CaseDTO",
    "CaseStatus",
    "ProgressDTO",
    "StepDTO",
    "StepStatus",
    "WorkCardDTO",
    "WorkCardProgressDTO",
]


@dataclass(frozen=True, slots=True)
class WorkCardDTO:
    id: int
    enrollment_id: int
    student_id: int
    course_id: int
    card_no: str


@dataclass(frozen=True, slots=True)
class CaseDTO:
    id: int
    work_card_id: int
    student_id: int
    patient_id: int
    case_type_id: int
    clinic_id: int
    status: CaseStatus
    tooth: int | None = None
    referral_id: int | None = None


@dataclass(frozen=True, slots=True)
class StepDTO:
    id: int
    case_id: int
    order: int
    template_id: int
    status: StepStatus
    student_id: int | None = None
    supervisor_id: int | None = None
    grade_value: Decimal | None = None
    grade_code: str | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ProgressDTO:
    """Completed cases of one case type against the course's requirement (BR-09)."""

    case_type_id: int
    completed: int
    required: int


@dataclass(frozen=True, slots=True)
class WorkCardProgressDTO:
    work_card_id: int
    enrollment_id: int
    items: tuple[ProgressDTO, ...] = ()

    @property
    def completed(self) -> int:
        return sum(item.completed for item in self.items)

    @property
    def required(self) -> int:
        return sum(item.required for item in self.items)
