"""In-memory fakes of the setup repository ports, for setup's own service tests.

They share one ``InMemorySetupStore`` and keep the same rules as the ORM adapters: only
active rows are read, ``find`` sees deactivated rows too, a chair's history stays when the
chair is deactivated.

    store = InMemorySetupStore()
    clinic_id = store.records.create(Table.CLINIC, {...})
    service = SaveRecord(store.records, store.terms, store.settings, audit, uow)
"""

import itertools
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from apps.setup.application.dtos import (
    AnswerType,
    CaseKind,
    CaseTypeDTO,
    ChairDTO,
    ChairStatus,
    ChairStatusChangeDTO,
    ChecklistItemDTO,
    ClinicDTO,
    ClinicType,
    DepartmentDTO,
    FaultCategoryDTO,
    IndexDefinitionDTO,
    IndexKind,
    LookupsDTO,
    MedicalHistoryItemDTO,
    SessionDTO,
    SoftTissueSiteDTO,
    Surface,
    TermDTO,
    ToothCodeDTO,
    TreatmentTypeDTO,
)
from apps.setup.application.ports import StoredRecord
from apps.setup.domain.records import Table
from apps.setup.domain.settings import LOOKUPS_VERSION_KEY


@dataclass
class _Row:
    id: int
    values: dict[str, Any]
    is_active: bool = True
    status: ChairStatus = ChairStatus.IN_SERVICE  # chairs only


def _plain(value: Any) -> Any:
    return value.value if hasattr(value, "value") and not isinstance(value, bool) else value


@dataclass
class InMemorySetupStore:
    rows: dict[Table, dict[int, _Row]] = field(default_factory=dict)
    history: list[tuple[datetime, ChairStatusChangeDTO]] = field(default_factory=list)
    settings_values: dict[str, Any] = field(default_factory=dict)
    _ids: Any = field(default_factory=lambda: itertools.count(1))

    def __post_init__(self) -> None:
        self.records = InMemoryRecordRepository(self)
        self.terms = InMemoryTermRepository(self)
        self.clinics = InMemoryClinicRepository(self)
        self.chairs = InMemoryChairRepository(self)
        self.lookups = InMemoryLookupRepository(self)
        self.settings = InMemorySettingRepository(self)

    def table(self, table: Table) -> dict[int, _Row]:
        return self.rows.setdefault(table, {})

    def active(self, table: Table) -> list[_Row]:
        return [row for row in self.table(table).values() if row.is_active]

    def ordered(self, table: Table) -> list[_Row]:
        return sorted(self.active(table), key=lambda row: (row.values.get("order", 0), row.id))


class InMemoryRecordRepository:
    def __init__(self, store: InMemorySetupStore) -> None:
        self._store = store

    def get(self, table: Table, record_id: int, *, for_update: bool = False) -> StoredRecord | None:
        row = self._store.table(table).get(record_id)
        if row is None:
            return None
        return StoredRecord(row.id, dict(row.values), row.is_active)

    def is_active(self, table: Table, record_id: int) -> bool:
        row = self._store.table(table).get(record_id)
        return row is not None and row.is_active

    def find(
        self, table: Table, values: Mapping[str, Any], *, exclude_id: int | None = None
    ) -> int | None:
        wanted = {key: _plain(value) for key, value in values.items()}
        for row in sorted(self._store.table(table).values(), key=lambda r: r.id):
            if row.id != exclude_id and all(row.values.get(k) == v for k, v in wanted.items()):
                return row.id
        return None

    def create(self, table: Table, values: Mapping[str, Any]) -> int:
        record_id = next(self._store._ids)
        self._store.table(table)[record_id] = _Row(
            record_id, {key: _plain(value) for key, value in values.items()}
        )
        return record_id

    def update(self, table: Table, record_id: int, values: Mapping[str, Any]) -> None:
        row = self._store.table(table)[record_id]
        row.values.update({key: _plain(value) for key, value in values.items()})

    def set_active(self, table: Table, record_id: int, active: bool) -> None:
        self._store.table(table)[record_id].is_active = active


class InMemoryTermRepository:
    def __init__(self, store: InMemorySetupStore) -> None:
        self._store = store

    def current(self) -> TermDTO | None:
        for row in self._store.active(Table.TERM):
            if row.values["is_current"]:
                v = row.values
                return TermDTO(row.id, v["name"], v["start_date"], v["end_date"], True)
        return None

    def clear_current(self, *, except_id: int | None) -> None:
        for row in self._store.table(Table.TERM).values():
            if row.id != except_id:
                row.values["is_current"] = False


def _clinic(row: _Row) -> ClinicDTO:
    v = row.values
    return ClinicDTO(
        row.id,
        v["number"],
        v["name_ar"],
        v["name_en"],
        ClinicType(v["type"]),
        v.get("department_id"),
        v.get("building", ""),
        v.get("floor", ""),
    )


class InMemoryClinicRepository:
    def __init__(self, store: InMemorySetupStore) -> None:
        self._store = store

    def get(self, clinic_id: int) -> ClinicDTO | None:
        row = self._store.table(Table.CLINIC).get(clinic_id)
        return _clinic(row) if row and row.is_active else None

    def list(self, *, type: ClinicType | None = None) -> Sequence[ClinicDTO]:
        rows = sorted(
            self._store.active(Table.CLINIC),
            key=lambda r: (len(r.values["number"]), r.values["number"]),
        )
        return [_clinic(r) for r in rows if type is None or r.values["type"] == type]


def _chair(row: _Row) -> ChairDTO:
    return ChairDTO(row.id, row.values["clinic_id"], row.values["number"], row.status)


class InMemoryChairRepository:
    def __init__(self, store: InMemorySetupStore) -> None:
        self._store = store

    def get(self, chair_id: int, *, for_update: bool = False) -> ChairDTO | None:
        row = self._store.table(Table.CHAIR).get(chair_id)
        return _chair(row) if row and row.is_active else None

    def list_for_clinic(
        self, clinic_ids: Sequence[int], *, in_service_only: bool
    ) -> Sequence[ChairDTO]:
        rows = sorted(
            (r for r in self._store.active(Table.CHAIR) if r.values["clinic_id"] in clinic_ids),
            key=lambda r: (r.values["clinic_id"], r.values["number"]),
        )
        return [
            _chair(r) for r in rows if not in_service_only or r.status == ChairStatus.IN_SERVICE
        ]

    def set_status(
        self,
        chair_id: int,
        status: ChairStatus,
        *,
        reason: str,
        by_user_id: int | None,
        at: datetime,
    ) -> ChairDTO:
        row = self._store.table(Table.CHAIR)[chair_id]
        self._store.history.append(
            (
                at,
                ChairStatusChangeDTO(chair_id, row.status, ChairStatus(status), reason, by_user_id),
            )
        )
        row.status = ChairStatus(status)
        return _chair(row)

    def history(self, chair_id: int) -> Sequence[ChairStatusChangeDTO]:
        return [change for _at, change in self._store.history if change.chair_id == chair_id]

    def next_number(self, clinic_id: int) -> int:
        numbers = [
            r.values["number"]
            for r in self._store.table(Table.CHAIR).values()
            if r.values["clinic_id"] == clinic_id
        ]
        return max(numbers, default=0) + 1


class InMemoryLookupRepository:
    def __init__(self, store: InMemorySetupStore) -> None:
        self._store = store

    def _names(self, row: _Row) -> tuple[int, str, str]:
        return row.id, row.values["name_ar"], row.values["name_en"]

    def department(self, department_id: int) -> DepartmentDTO | None:
        row = self._store.table(Table.DEPARTMENT).get(department_id)
        if row is None or not row.is_active:
            return None
        return DepartmentDTO(*self._names(row), row.values.get("head_id"))

    def departments(self) -> Sequence[DepartmentDTO]:
        rows = sorted(
            self._store.active(Table.DEPARTMENT), key=lambda r: (r.values["name_ar"], r.id)
        )
        return [DepartmentDTO(*self._names(r), r.values.get("head_id")) for r in rows]

    def _session(self, row: _Row) -> SessionDTO:
        v = row.values
        return SessionDTO(
            row.id,
            v["name_ar"],
            v["name_en"],
            v["start_time"],
            v["end_time"],
            v["order"],
            v.get("clinic_id"),
            ClinicType(v["clinic_type"]) if v.get("clinic_type") else None,
        )

    def sessions_for(self, clinic: ClinicDTO) -> Sequence[SessionDTO]:
        rows = self._store.ordered(Table.SESSION)
        own = [r for r in rows if r.values.get("clinic_id") == clinic.id]
        chosen = own or [r for r in rows if r.values.get("clinic_type") == clinic.type]
        return [self._session(r) for r in chosen]

    def case_type(self, case_type_id: int) -> CaseTypeDTO | None:
        row = self._store.table(Table.CASE_TYPE).get(case_type_id)
        if row is None or not row.is_active:
            return None
        return CaseTypeDTO(*self._names(row), CaseKind(row.values["kind"]))

    def treatment_type(self, treatment_type_id: int) -> TreatmentTypeDTO | None:
        row = self._store.table(Table.TREATMENT_TYPE).get(treatment_type_id)
        if row is None or not row.is_active:
            return None
        return TreatmentTypeDTO(
            *self._names(row), row.values["department_id"], row.values["case_type_id"]
        )

    def fault_category(self, category_id: int) -> FaultCategoryDTO | None:
        row = self._store.table(Table.FAULT_CATEGORY).get(category_id)
        if row is None or not row.is_active:
            return None
        return FaultCategoryDTO(*self._names(row), row.values["blocks_chair"])

    def checklist_items(self) -> Sequence[ChecklistItemDTO]:
        return [
            ChecklistItemDTO(*self._names(r), r.values["order"])
            for r in self._store.ordered(Table.CHECKLIST_ITEM)
        ]

    def lookup_lists(self) -> LookupsDTO:
        store = self._store
        return LookupsDTO(
            version=0,
            departments=tuple(self.departments()),
            case_types=tuple(self.case_type(r.id) for r in store.ordered(Table.CASE_TYPE)),
            treatment_types=tuple(
                self.treatment_type(r.id) for r in store.ordered(Table.TREATMENT_TYPE)
            ),
            tooth_codes=tuple(
                ToothCodeDTO(
                    r.id,
                    r.values["letter"],
                    r.values["meaning_ar"],
                    r.values["meaning_en"],
                    r.values["color"],
                    r.values["order"],
                )
                for r in store.ordered(Table.TOOTH_CODE)
            ),
            medical_history_items=tuple(
                MedicalHistoryItemDTO(
                    r.id,
                    r.values["question_ar"],
                    r.values["question_en"],
                    AnswerType(r.values["answer_type"]),
                    r.values["is_alert"],
                    r.values["order"],
                )
                for r in store.ordered(Table.MEDICAL_HISTORY_ITEM)
            ),
            soft_tissue_sites=tuple(
                SoftTissueSiteDTO(*self._names(r), r.values["order"])
                for r in store.ordered(Table.SOFT_TISSUE_SITE)
            ),
            index_definitions=tuple(
                IndexDefinitionDTO(
                    r.id,
                    IndexKind(r.values["kind"]),
                    r.values["tooth"],
                    Surface(r.values["surface"]),
                    r.values["min_score"],
                    r.values["max_score"],
                    r.values["order"],
                )
                for r in store.ordered(Table.INDEX_DEFINITION)
            ),
            checklist_items=tuple(self.checklist_items()),
            fault_categories=tuple(
                self.fault_category(r.id) for r in store.ordered(Table.FAULT_CATEGORY)
            ),
            sessions=tuple(self._session(r) for r in store.ordered(Table.SESSION)),
        )


class InMemorySettingRepository:
    def __init__(self, store: InMemorySetupStore) -> None:
        self._values = store.settings_values

    def get(self, key: str) -> Any | None:
        return self._values.get(key)

    def all(self) -> dict[str, Any]:
        return dict(self._values)

    def set_many(self, values: Mapping[str, Any]) -> None:
        self._values.update(values)

    def lookups_version(self) -> int:
        return int(self._values.get(LOOKUPS_VERSION_KEY) or 1)

    def bump_lookups_version(self) -> int:
        self._values[LOOKUPS_VERSION_KEY] = self.lookups_version() + 1
        return self._values[LOOKUPS_VERSION_KEY]


class InMemorySeedSource:
    def __init__(self, data: Mapping[str, Any]) -> None:
        self.data = data

    def load(self) -> Mapping[str, Any]:
        return self.data
