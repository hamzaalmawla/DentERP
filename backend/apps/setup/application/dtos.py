"""What the setup module gives other modules (P0.5 contract). Frozen dataclasses only.

Names come in Arabic and English; the caller picks the one for the request's language.
"""

from dataclasses import dataclass
from datetime import date, time

from apps.setup.domain.values import CaseKind, ChairStatus, ClinicType

__all__ = [
    "CaseKind",
    "CaseTypeDTO",
    "ChairDTO",
    "ChairStatus",
    "ChecklistItemDTO",
    "ClinicDTO",
    "ClinicType",
    "DepartmentDTO",
    "FaultCategoryDTO",
    "SessionDTO",
    "TermDTO",
    "TreatmentTypeDTO",
]


@dataclass(frozen=True, slots=True)
class TermDTO:
    id: int
    name: str
    start_date: date
    end_date: date
    is_current: bool


@dataclass(frozen=True, slots=True)
class DepartmentDTO:
    id: int
    name_ar: str
    name_en: str


@dataclass(frozen=True, slots=True)
class ClinicDTO:
    id: int
    number: str
    name_ar: str
    name_en: str
    type: ClinicType
    department_id: int | None
    building: str = ""
    floor: str = ""


@dataclass(frozen=True, slots=True)
class ChairDTO:
    id: int
    clinic_id: int
    number: int
    status: ChairStatus

    @property
    def in_service(self) -> bool:
        return self.status == ChairStatus.IN_SERVICE


@dataclass(frozen=True, slots=True)
class SessionDTO:
    """A session of the clinic day. It belongs to one clinic, or to every clinic of a type."""

    id: int
    name_ar: str
    name_en: str
    start_time: time
    end_time: time
    order: int
    clinic_id: int | None = None
    clinic_type: ClinicType | None = None


@dataclass(frozen=True, slots=True)
class CaseTypeDTO:
    id: int
    name_ar: str
    name_en: str
    kind: CaseKind


@dataclass(frozen=True, slots=True)
class TreatmentTypeDTO:
    """A plan item's treatment; it is referred to ``department_id`` and becomes a case of
    ``case_type_id``."""

    id: int
    name_ar: str
    name_en: str
    department_id: int
    case_type_id: int


@dataclass(frozen=True, slots=True)
class FaultCategoryDTO:
    id: int
    name_ar: str
    name_en: str
    blocks_chair: bool


@dataclass(frozen=True, slots=True)
class ChecklistItemDTO:
    id: int
    name_ar: str
    name_en: str
    order: int
