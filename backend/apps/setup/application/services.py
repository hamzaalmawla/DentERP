"""Setup use cases (design section 5): one class per use case, built in ``container.py``.

Every configuration record (``domain.records.Table``) is created and changed by the same two
services, ``SaveRecord`` and ``SetRecordActive``, which apply the record's rules from
``domain.records``. A change to a lookup list also changes the lookups version, so the app
downloads the lists again. Every change is written to the audit log (SYS-04).

Only the system administrator changes the setup (DB-04, DB-06, DB-18). ``SetChairStatus`` is
the exception: maintenance calls it through the facade for a technician or for the system.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, time
from typing import Any

from apps.core.application.dtos import Actor
from apps.core.domain.audit import AuditAction, diff
from apps.core.domain.errors import NotFoundError
from apps.setup.domain.errors import (
    ChairCountError,
    CurrentTermError,
    ReasonRequiredError,
    RecordTakenError,
    ReferenceNotFoundError,
    SetupAdminRequiredError,
)
from apps.setup.domain.records import (
    FIXED_AFTER_CREATE,
    LOOKUP_TABLES,
    MODEL_NAMES,
    ORDERED_TABLES,
    REFERENCES,
    UNIQUE_RULES,
    Table,
    clean,
)
from apps.setup.domain.settings import SETTINGS_BY_KEY, check_windows, clean_settings

from .dtos import ChairDTO, ChairStatus, SavedRecord, SeedReport, SetChairStatusCommand
from .ports import (
    AuditLogger,
    ChairRepository,
    Clock,
    RecordRepository,
    SeedSource,
    SettingRepository,
    TermRepository,
    UnitOfWork,
)

# The role that changes the setup (design section 8). Setup uses no other module, so the code
# is written here rather than read from accounts.
SETUP_ADMIN_ROLE = "super_admin"

SETTING_MODEL = "setup.SystemSetting"
REORDER = "reorder"
CHAIR_STATUS = "chair_status"

MAX_CHAIRS_AT_ONCE = 100


def _ensure_setup_admin(actor: Actor) -> None:
    if actor.role != SETUP_ADMIN_ROLE:
        raise SetupAdminRequiredError()


class _RecordWriter:
    """Applies the rules of ``domain.records`` and stores one record. Shared by ``SaveRecord``
    and ``SeedDefaults`` so the seed cannot store what the dashboard would refuse."""

    def __init__(
        self,
        records: RecordRepository,
        terms: TermRepository,
        settings: SettingRepository,
        audit: AuditLogger,
    ) -> None:
        self._records = records
        self._terms = terms
        self._settings = settings
        self._audit = audit

    def save(self, table: Table, record_id: int | None, values: Mapping[str, Any]) -> int:
        """Create (``record_id`` is ``None``) or change an active record; returns its id. Call
        inside a unit of work."""
        cleaned = clean(table, values)
        before: dict[str, Any] = {}
        if record_id is not None:
            stored = self._records.get(table, record_id, for_update=True)
            if stored is None or not stored.is_active:
                raise NotFoundError()
            before = stored.values
            for field in FIXED_AFTER_CREATE.get(table, ()):
                cleaned[field] = before[field]
        self._check_references(table, cleaned)
        self._check_unique(table, cleaned, record_id)
        if table == Table.TERM and cleaned["is_current"]:
            self._terms.clear_current(except_id=record_id)  # one current term
        if record_id is None:
            record_id = self._records.create(table, cleaned)
            action = AuditAction.CREATE
        else:
            self._records.update(table, record_id, cleaned)
            action = AuditAction.UPDATE
        changes = diff(before, cleaned)
        if changes or action == AuditAction.CREATE:
            if table in LOOKUP_TABLES:
                self._settings.bump_lookups_version()
            self._audit.log(action, model=MODEL_NAMES[table], object_id=record_id, changes=changes)
        return record_id

    def _check_references(self, table: Table, values: Mapping[str, Any]) -> None:
        for reference in REFERENCES.get(table, ()):
            target_id = values.get(reference.field)
            if target_id is not None and not self._records.is_active(reference.table, target_id):
                raise ReferenceNotFoundError(reference.code, reference.message, reference.field)

    def _check_unique(self, table: Table, values: Mapping[str, Any], record_id: int | None) -> None:
        for rule in UNIQUE_RULES.get(table, ()):
            wanted = {field: values[field] for field in rule.fields}
            if self._records.find(table, wanted, exclude_id=record_id) is not None:
                raise RecordTakenError(rule.code, rule.message, rule.field)


# --- Configuration records (DB-04, DB-06) ----------------------------------------------


@dataclass(frozen=True, slots=True)
class SaveRecordCommand:
    table: Table
    values: Mapping[str, Any]
    record_id: int | None = None  # None creates a record


class SaveRecord:
    """Creates or changes one configuration record (a term, a clinic, a tooth code, …).

    The values are checked by the table's rules; unique values are checked against every
    record, deactivated ones included; references must point to active records. Making a term
    current makes the previous current term not current.
    """

    def __init__(
        self,
        records: RecordRepository,
        terms: TermRepository,
        settings: SettingRepository,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._writer = _RecordWriter(records, terms, settings, audit)
        self._uow = uow

    def execute(self, actor: Actor, command: SaveRecordCommand) -> SavedRecord:
        _ensure_setup_admin(actor)
        with self._uow:
            record_id = self._writer.save(command.table, command.record_id, command.values)
        return SavedRecord(command.table, record_id)


@dataclass(frozen=True, slots=True)
class SetRecordActiveCommand:
    table: Table
    record_id: int
    active: bool


class SetRecordActive:
    """Deactivates a record, or activates it again. Nothing is deleted (SYS-10): a deactivated
    chair keeps its history and is left out of distributions and rounds; a deactivated list
    item is no longer offered in the app but stays on the records that used it.

    The current term cannot be deactivated.
    """

    def __init__(
        self,
        records: RecordRepository,
        settings: SettingRepository,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._records = records
        self._settings = settings
        self._audit = audit
        self._uow = uow

    def execute(self, actor: Actor, command: SetRecordActiveCommand) -> SavedRecord:
        _ensure_setup_admin(actor)
        table = command.table
        with self._uow:
            stored = self._records.get(table, command.record_id, for_update=True)
            if stored is None:
                raise NotFoundError()
            if stored.is_active == command.active:
                return SavedRecord(table, stored.id)
            if not command.active and table == Table.TERM and stored.values["is_current"]:
                raise CurrentTermError()
            self._records.set_active(table, stored.id, command.active)
            if table in LOOKUP_TABLES:
                self._settings.bump_lookups_version()
            self._audit.log(
                AuditAction.ACTIVATE if command.active else AuditAction.DEACTIVATE,
                model=MODEL_NAMES[table],
                object_id=stored.id,
                changes=diff({"is_active": stored.is_active}, {"is_active": command.active}),
            )
        return SavedRecord(table, stored.id)


@dataclass(frozen=True, slots=True)
class ReorderCommand:
    table: Table
    # The new position of each record, by id. Records left out keep their position.
    orders: Mapping[int, int]


class Reorder:
    """Stores the order of a list after the administrator dragged its rows."""

    def __init__(
        self,
        records: RecordRepository,
        terms: TermRepository,
        settings: SettingRepository,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._records = records
        self._writer = _RecordWriter(records, terms, settings, audit)
        self._uow = uow

    def execute(self, actor: Actor, command: ReorderCommand) -> None:
        _ensure_setup_admin(actor)
        if command.table not in ORDERED_TABLES:
            raise NotFoundError()
        with self._uow:
            for record_id, order in command.orders.items():
                stored = self._records.get(command.table, record_id)
                if stored is None or not stored.is_active:
                    raise NotFoundError()
                if stored.values["order"] != order:
                    self._writer.save(command.table, record_id, {**stored.values, "order": order})


# --- Chairs (DB-04, MT-07, BR-12) -------------------------------------------------------


@dataclass(frozen=True, slots=True)
class AddChairsCommand:
    clinic_id: int
    count: int


class AddChairs:
    """Adds ``count`` chairs to a clinic, in service, numbered after its highest chair (US-01:
    "create clinic 5 with 12 chairs")."""

    def __init__(
        self,
        records: RecordRepository,
        chairs: ChairRepository,
        terms: TermRepository,
        settings: SettingRepository,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._chairs = chairs
        self._writer = _RecordWriter(records, terms, settings, audit)
        self._uow = uow

    def execute(self, actor: Actor, command: AddChairsCommand) -> Sequence[SavedRecord]:
        _ensure_setup_admin(actor)
        count = command.count
        if isinstance(count, bool) or not isinstance(count, int):
            raise ChairCountError()
        if not 1 <= count <= MAX_CHAIRS_AT_ONCE:
            raise ChairCountError()
        with self._uow:
            first = self._chairs.next_number(command.clinic_id)
            return [
                SavedRecord(
                    Table.CHAIR,
                    self._writer.save(
                        Table.CHAIR, None, {"clinic_id": command.clinic_id, "number": number}
                    ),
                )
                for number in range(first, first + count)
            ]


class SetChairStatus:
    """Puts a chair in or out of service with a reason, and writes its history (MT-07). An
    out-of-service chair cannot be given to students (BR-12). Setting the status the chair
    already has changes nothing.

    Who may do it is checked by the caller: the maintenance module for technicians and
    tickets, the dashboard for the system administrator.
    """

    def __init__(
        self, chairs: ChairRepository, clock: Clock, audit: AuditLogger, uow: UnitOfWork
    ) -> None:
        self._chairs = chairs
        self._clock = clock
        self._audit = audit
        self._uow = uow

    def execute(self, command: SetChairStatusCommand) -> ChairDTO:
        status = ChairStatus(command.status)
        reason = command.reason.strip()
        with self._uow:
            chair = self._chairs.get(command.chair_id, for_update=True)
            if chair is None:
                raise NotFoundError()
            if not reason:
                raise ReasonRequiredError()
            if chair.status == status:
                return chair
            before = chair.status
            chair = self._chairs.set_status(
                chair.id,
                status,
                reason=reason,
                by_user_id=command.by_user_id,
                at=self._clock.now(),
            )
            self._audit.log(
                CHAIR_STATUS,
                model=MODEL_NAMES[Table.CHAIR],
                object_id=chair.id,
                changes={
                    **diff({"status": str(before)}, {"status": str(status)}),
                    "reason": reason,
                },
                user_id=command.by_user_id,
            )
        return chair


# --- System settings (DB-18) -------------------------------------------------------------


class UpdateSettings:
    """Stores the system settings that changed. Settings sent to the app (photo size, round
    times) change the lookups version."""

    def __init__(self, settings: SettingRepository, audit: AuditLogger, uow: UnitOfWork) -> None:
        self._settings = settings
        self._audit = audit
        self._uow = uow

    def execute(self, actor: Actor, values: Mapping[str, Any]) -> dict[str, Any]:
        _ensure_setup_admin(actor)
        cleaned = clean_settings(values)
        with self._uow:
            before = self._settings.all()
            check_windows({**before, **cleaned})
            changed = {key: value for key, value in cleaned.items() if before.get(key) != value}
            if changed:
                self._settings.set_many(changed)
                if any(SETTINGS_BY_KEY[key].in_lookups for key in changed):
                    self._settings.bump_lookups_version()
                self._audit.log(
                    AuditAction.UPDATE,
                    model=SETTING_MODEL,
                    changes=diff({key: before.get(key) for key in changed}, changed),
                )
            return {**before, **cleaned}


# --- Default data (SRS section 4, build-prompts section 1) -------------------------------

# How seed_defaults recognises a record it created before, active or deactivated: by these
# values. A deactivated default is never created again.
SEED_KEYS: Mapping[Table, tuple[str, ...]] = {
    Table.TERM: ("name",),
    Table.DEPARTMENT: ("name_en",),
    Table.CLINIC: ("number",),
    Table.CHAIR: ("clinic_id", "number"),
    Table.SESSION: ("clinic_id", "clinic_type", "order"),
    Table.CASE_TYPE: ("name_en",),
    Table.TOOTH_CODE: ("letter",),
    Table.MEDICAL_HISTORY_ITEM: ("question_en",),
    Table.SOFT_TISSUE_SITE: ("name_en",),
    Table.INDEX_DEFINITION: ("kind", "tooth", "surface"),
    Table.TREATMENT_TYPE: ("name_en",),
    Table.CHECKLIST_ITEM: ("name_en",),
    Table.FAULT_CATEGORY: ("name_en",),
}

# Tables in the order they are seeded: a record comes after the records it refers to.
SEED_ORDER: tuple[Table, ...] = (
    Table.TERM,
    Table.DEPARTMENT,
    Table.CLINIC,
    Table.SESSION,
    Table.CASE_TYPE,
    Table.TREATMENT_TYPE,
    Table.TOOTH_CODE,
    Table.MEDICAL_HISTORY_ITEM,
    Table.SOFT_TISSUE_SITE,
    Table.INDEX_DEFINITION,
    Table.CHECKLIST_ITEM,
    Table.FAULT_CATEGORY,
)

CHAIR_COUNT = "chair_count"  # in a clinic row: the chairs it gets, numbered from 1
REFERENCE_MARK = "@"  # "department_id@": {"name_en": "…"} refers to a record by its values


def _from_json(values: Mapping[str, Any]) -> dict[str, Any]:
    """Dates and times come as text in the seed file."""
    converted = dict(values)
    for key, value in values.items():
        if key.endswith("_date") and isinstance(value, str):
            converted[key] = date.fromisoformat(value)
        elif key.endswith("_time") and isinstance(value, str):
            converted[key] = time.fromisoformat(value)
    return converted


class SeedDefaults:
    """Loads the default lists and the Release 1 data (``python manage.py seed_defaults``).

    Safe to run again: a record that is already there (by ``SEED_KEYS``), active or
    deactivated, is left as it is, and a setting that is already set keeps its value. Records
    go through the same rules as the dashboard's. A term is made current only when no term is
    current yet. Runs as the system, so the audit log shows no user.
    """

    def __init__(
        self,
        records: RecordRepository,
        terms: TermRepository,
        settings: SettingRepository,
        source: SeedSource,
        audit: AuditLogger,
        uow: UnitOfWork,
    ) -> None:
        self._records = records
        self._terms = terms
        self._settings = settings
        self._source = source
        self._audit = audit
        self._writer = _RecordWriter(records, terms, settings, audit)
        self._uow = uow

    def execute(self) -> SeedReport:
        data = self._source.load()
        report = SeedReport()
        with self._uow:
            for table in SEED_ORDER:
                for row in data.get(str(table), ()):
                    record_id = self._seed_row(table, row, report)
                    if table == Table.CLINIC and row.get(CHAIR_COUNT):
                        for number in range(1, int(row[CHAIR_COUNT]) + 1):
                            self._seed_values(
                                Table.CHAIR, {"clinic_id": record_id, "number": number}, report
                            )
            self._seed_settings(data.get("settings", {}), report)
        return report

    def _seed_row(self, table: Table, row: Mapping[str, Any], report: SeedReport) -> int:
        values: dict[str, Any] = {}
        for key, value in _from_json(row).items():
            if key == CHAIR_COUNT:
                continue
            if key.endswith(REFERENCE_MARK):
                field = key.removesuffix(REFERENCE_MARK)
                values[field] = self._resolve(field, table, value)
            else:
                values[key] = value
        if table == Table.TERM and values.get("is_current") and self._terms.current():
            values["is_current"] = False
        return self._seed_values(table, values, report)

    def _seed_values(self, table: Table, values: dict[str, Any], report: SeedReport) -> int:
        key = {field: values.get(field) for field in SEED_KEYS[table]}
        existing = self._records.find(table, key)
        if existing is not None:
            report.existing[table.value] = report.existing.get(table.value, 0) + 1
            return existing
        record_id = self._writer.save(table, None, values)
        report.created[table.value] = report.created.get(table.value, 0) + 1
        return record_id

    def _resolve(self, field: str, table: Table, key: Mapping[str, Any]) -> int:
        target = next(r.table for r in REFERENCES.get(table, ()) if r.field == field)
        record_id = self._records.find(target, key)
        if record_id is None:
            raise NotFoundError(details={"table": str(target), "key": dict(key)})
        return record_id

    def _seed_settings(self, settings: Mapping[str, Any], report: SeedReport) -> None:
        stored = self._settings.all()
        missing = clean_settings({k: v for k, v in settings.items() if k not in stored})
        if missing:
            check_windows({**stored, **missing})
            self._settings.set_many(missing)
            self._settings.bump_lookups_version()
            self._audit.log(AuditAction.CREATE, model=SETTING_MODEL, changes=diff({}, missing))
        report.created["setting"] = len(missing)
        report.existing["setting"] = len(settings) - len(missing)
