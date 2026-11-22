"""Ports of the setup module (P0.5 outline; P1.1 may refine them inside the module).

Repository ports return DTOs; the ORM adapters live in ``infrastructure/``. Setup needs no
other module. The shared ports (clock, audit log, unit of work) come from core.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from apps.core.application.ports import AuditLogger, Clock, UnitOfWork

from .dtos import (
    CaseTypeDTO,
    ChairDTO,
    ChairStatus,
    ChecklistItemDTO,
    ClinicDTO,
    ClinicType,
    FaultCategoryDTO,
    SessionDTO,
    TermDTO,
    TreatmentTypeDTO,
)

__all__ = [
    "AuditLogger",
    "ChairRepository",
    "ClinicRepository",
    "Clock",
    "LookupRepository",
    "SettingRepository",
    "TermRepository",
    "UnitOfWork",
]


@runtime_checkable
class TermRepository(Protocol):
    def current(self) -> TermDTO | None: ...


@runtime_checkable
class ClinicRepository(Protocol):
    def get(self, clinic_id: int) -> ClinicDTO | None: ...

    def list(self, *, type: ClinicType | None = None) -> Sequence[ClinicDTO]: ...


@runtime_checkable
class ChairRepository(Protocol):
    """The chair aggregate: the chair and its status history."""

    def get(self, chair_id: int, *, for_update: bool = False) -> ChairDTO | None: ...

    def list_for_clinic(self, clinic_id: int, *, in_service_only: bool) -> Sequence[ChairDTO]: ...

    def set_status(
        self,
        chair_id: int,
        status: ChairStatus,
        *,
        reason: str,
        by_user_id: int | None,
        at: datetime,
    ) -> ChairDTO:
        """Store the new status and add a history row."""
        ...


@runtime_checkable
class LookupRepository(Protocol):
    """The configuration lists (sessions, case and treatment types, checklist, faults, …)."""

    def sessions_for(self, clinic: ClinicDTO) -> Sequence[SessionDTO]: ...

    def case_type(self, case_type_id: int) -> CaseTypeDTO | None: ...

    def treatment_type(self, treatment_type_id: int) -> TreatmentTypeDTO | None: ...

    def fault_category(self, category_id: int) -> FaultCategoryDTO | None: ...

    def checklist_items(self) -> Sequence[ChecklistItemDTO]: ...


@runtime_checkable
class SettingRepository(Protocol):
    def get(self, key: str) -> Any | None: ...

    def lookups_version(self) -> int: ...
