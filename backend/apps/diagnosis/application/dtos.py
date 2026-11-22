"""What the diagnosis module gives other modules (P0.5 contract). Frozen dataclasses only."""

from dataclasses import dataclass
from datetime import datetime

from apps.diagnosis.domain.values import DiagnosisStatus, PlanItemStatus

__all__ = [
    "DiagnosisStatus",
    "DiagnosisSummaryDTO",
    "MedicalAlertDTO",
    "PlanItemDTO",
    "PlanItemStatus",
]


@dataclass(frozen=True, slots=True)
class DiagnosisSummaryDTO:
    """A diagnosis without its F1 sections: enough for queues, links and scope checks."""

    id: int
    patient_id: int
    student_id: int
    clinic_id: int
    status: DiagnosisStatus
    version: int
    supervisor_id: int | None = None
    submitted_at: datetime | None = None
    approved_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class PlanItemDTO:
    """One treatment of an approved plan, referred to ``department_id``."""

    id: int
    diagnosis_id: int
    patient_id: int
    treatment_type_id: int
    department_id: int
    status: PlanItemStatus
    teeth: tuple[int, ...] = ()
    note: str = ""


@dataclass(frozen=True, slots=True)
class MedicalAlertDTO:
    """A medical history answer marked as an alert, for the patient's red banner."""

    item_id: int
    question_ar: str
    question_en: str
    details: str = ""
