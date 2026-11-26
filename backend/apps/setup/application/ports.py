"""Ports of the setup module. Adapters: ``infrastructure/``; fakes: ``testing/``.

Read ports return DTOs. ``RecordRepository`` is the write side of the configuration records
(``domain.records.Table``): it stores the plain values the services have checked. Setup needs
no other module; the shared ports (clock, audit log, unit of work) come from core.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol, runtime_checkable

from apps.core.application.ports import AuditLogger, Clock, UnitOfWork
from apps.setup.domain.records import Table

from .dtos import (
    CaseTypeDTO,
    ChairDTO,
    ChairStatus,
    ChairStatusChangeDTO,
    ChecklistItemDTO,
    ClinicDTO,
    ClinicType,
    DepartmentDTO,
    FaultCategoryDTO,
    LookupsDTO,
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
    "RecordRepository",
    "SeedSource",
    "SettingRepository",
    "StoredRecord",
    "TermRepository",
    "UnitOfWork",
]


@dataclass(frozen=True, slots=True)
class StoredRecord:
    id: int
    values: dict[str, Any]
    is_active: bool


@runtime_checkable
class RecordRepository(Protocol):
    """Configuration records as plain values (the names of ``domain.records``)."""

    def get(self, table: Table, record_id: int, *, for_update: bool = False) -> StoredRecord | None:
        """The record, active or deactivated."""
        ...

    def is_active(self, table: Table, record_id: int) -> bool: ...

    def find(
        self, table: Table, values: Mapping[str, Any], *, exclude_id: int | None = None
    ) -> int | None:
        """The id of a record (active or deactivated) holding all these values."""
        ...

    def create(self, table: Table, values: Mapping[str, Any]) -> int: ...

    def update(self, table: Table, record_id: int, values: Mapping[str, Any]) -> None: ...

    def set_active(self, table: Table, record_id: int, active: bool) -> None: ...


@runtime_checkable
class TermRepository(Protocol):
    def current(self) -> TermDTO | None: ...

    def clear_current(self, *, except_id: int | None) -> None:
        """No term but ``except_id`` stays current (one current term)."""
        ...


@runtime_checkable
class ClinicRepository(Protocol):
    def get(self, clinic_id: int) -> ClinicDTO | None: ...

    def list(self, *, type: ClinicType | None = None) -> Sequence[ClinicDTO]:
        """Active clinics, by number (2 before 10)."""
        ...


@runtime_checkable
class ChairRepository(Protocol):
    """The chair aggregate: the chair and its status history. Only active chairs are found."""

    def get(self, chair_id: int, *, for_update: bool = False) -> ChairDTO | None: ...

    def list_for_clinic(
        self, clinic_ids: Sequence[int], *, in_service_only: bool
    ) -> Sequence[ChairDTO]:
        """Active chairs of these clinics, by clinic then number."""
        ...

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

    def history(self, chair_id: int) -> Sequence[ChairStatusChangeDTO]:
        """Status changes of the chair (active or deactivated), oldest first."""
        ...

    def next_number(self, clinic_id: int) -> int:
        """One more than the highest chair number of the clinic, deactivated chairs included."""
        ...


@runtime_checkable
class LookupRepository(Protocol):
    """The configuration lists. Only active rows are found."""

    def department(self, department_id: int) -> DepartmentDTO | None: ...

    def departments(self) -> Sequence[DepartmentDTO]: ...

    def sessions_for(self, clinic: ClinicDTO) -> Sequence[SessionDTO]:
        """The clinic's own sessions, or else those of its clinic type, in order."""
        ...

    def case_type(self, case_type_id: int) -> CaseTypeDTO | None: ...

    def treatment_type(self, treatment_type_id: int) -> TreatmentTypeDTO | None: ...

    def fault_category(self, category_id: int) -> FaultCategoryDTO | None: ...

    def checklist_items(self) -> Sequence[ChecklistItemDTO]: ...

    def lookup_lists(self) -> LookupsDTO:
        """Every list of ``GET /lookups/`` in order; ``version`` and ``settings`` are left
        empty for the caller to fill."""
        ...


@runtime_checkable
class SettingRepository(Protocol):
    def get(self, key: str) -> Any | None: ...

    def all(self) -> dict[str, Any]:
        """Every stored setting, the lookups version included."""
        ...

    def set_many(self, values: Mapping[str, Any]) -> None: ...

    def lookups_version(self) -> int: ...

    def bump_lookups_version(self) -> int:
        """Add one to the lookups version and return the new number; safe when two requests
        change lists at the same time."""
        ...


@runtime_checkable
class SeedSource(Protocol):
    """The default records (``seed_defaults``): for each table, the rows to create, in order.

    A row refers to another record by that record's key values, under ``"<field>@"`` (for
    example ``{"department_id@": {"name_en": "Endodontics"}}``); settings come under the
    ``"settings"`` key.
    """

    def load(self) -> Mapping[str, Any]: ...
