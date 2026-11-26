"""What the setup module gives other modules and its adapters. Frozen dataclasses only.

Names come in Arabic and English; the caller picks the one for the request's language.
"""

from dataclasses import dataclass, field
from datetime import date, time
from typing import Any

from apps.setup.domain.records import Table
from apps.setup.domain.values import (
    AnswerType,
    CaseKind,
    ChairStatus,
    ClinicType,
    IndexKind,
    Surface,
)

__all__ = [
    "AnswerType",
    "CaseKind",
    "CaseTypeDTO",
    "ChairDTO",
    "ChairStatus",
    "ChairStatusChangeDTO",
    "ChecklistItemDTO",
    "ClinicChairsDTO",
    "ClinicDTO",
    "ClinicType",
    "DepartmentDTO",
    "FaultCategoryDTO",
    "IndexDefinitionDTO",
    "IndexKind",
    "LookupsDTO",
    "MedicalHistoryItemDTO",
    "SavedRecord",
    "SeedReport",
    "SessionDTO",
    "SetChairStatusCommand",
    "SoftTissueSiteDTO",
    "Surface",
    "TermDTO",
    "ToothCodeDTO",
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
    head_id: int | None = None


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


@dataclass(frozen=True, slots=True)
class ToothCodeDTO:
    id: int
    letter: str
    meaning_ar: str
    meaning_en: str
    color: str
    order: int


@dataclass(frozen=True, slots=True)
class MedicalHistoryItemDTO:
    id: int
    question_ar: str
    question_en: str
    answer_type: AnswerType
    is_alert: bool
    order: int


@dataclass(frozen=True, slots=True)
class SoftTissueSiteDTO:
    id: int
    name_ar: str
    name_en: str
    order: int


@dataclass(frozen=True, slots=True)
class IndexDefinitionDTO:
    id: int
    kind: IndexKind
    tooth: int
    surface: Surface
    min_score: int
    max_score: int
    order: int


@dataclass(frozen=True, slots=True)
class LookupsDTO:
    """Every lookup list the app caches (``GET /lookups/``), active rows only, in order."""

    version: int
    departments: tuple[DepartmentDTO, ...] = ()
    case_types: tuple[CaseTypeDTO, ...] = ()
    treatment_types: tuple[TreatmentTypeDTO, ...] = ()
    tooth_codes: tuple[ToothCodeDTO, ...] = ()
    medical_history_items: tuple[MedicalHistoryItemDTO, ...] = ()
    soft_tissue_sites: tuple[SoftTissueSiteDTO, ...] = ()
    index_definitions: tuple[IndexDefinitionDTO, ...] = ()
    checklist_items: tuple[ChecklistItemDTO, ...] = ()
    fault_categories: tuple[FaultCategoryDTO, ...] = ()
    sessions: tuple[SessionDTO, ...] = ()
    # The settings the app needs (photo size limit, round times), by key.
    settings: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class ClinicChairsDTO:
    """A clinic with its active chairs (``GET /clinics/?with=chair_status``)."""

    clinic: ClinicDTO
    chairs: tuple[ChairDTO, ...]

    @property
    def in_service_count(self) -> int:
        return sum(chair.in_service for chair in self.chairs)

    @property
    def out_of_service_count(self) -> int:
        return len(self.chairs) - self.in_service_count


@dataclass(frozen=True, slots=True)
class ChairStatusChangeDTO:
    """One row of a chair's status history."""

    chair_id: int
    from_status: ChairStatus
    to_status: ChairStatus
    reason: str
    by_user_id: int | None


@dataclass(frozen=True, slots=True)
class SetChairStatusCommand:
    """What ``set_chair_status`` asks the ``SetChairStatus`` service to do."""

    chair_id: int
    status: ChairStatus
    reason: str
    by_user_id: int | None  # None when the system does it (a ticket in a blocking category)


@dataclass(frozen=True, slots=True)
class SavedRecord:
    """A configuration record a service created or changed."""

    table: Table
    id: int


@dataclass(frozen=True, slots=True)
class SeedReport:
    """What ``seed_defaults`` did: records created and records already there, by table."""

    created: dict[str, int] = field(default_factory=dict)
    existing: dict[str, int] = field(default_factory=dict)
