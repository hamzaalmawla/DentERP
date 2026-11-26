"""ORM adapters of the setup repository ports."""

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Any

from django.db.models import Max
from django.db.models.functions import Length

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
from apps.setup.models import (
    CaseType,
    Chair,
    ChairStatusChange,
    ChecklistItem,
    Clinic,
    Department,
    FaultCategory,
    IndexDefinition,
    MedicalHistoryItem,
    Session,
    SoftTissueSite,
    SystemSetting,
    Term,
    ToothCode,
    TreatmentType,
)

# Each table's model and the values ``domain.records`` holds for it.
MODELS = {
    Table.TERM: Term,
    Table.DEPARTMENT: Department,
    Table.CLINIC: Clinic,
    Table.CHAIR: Chair,
    Table.SESSION: Session,
    Table.CASE_TYPE: CaseType,
    Table.TOOTH_CODE: ToothCode,
    Table.MEDICAL_HISTORY_ITEM: MedicalHistoryItem,
    Table.SOFT_TISSUE_SITE: SoftTissueSite,
    Table.INDEX_DEFINITION: IndexDefinition,
    Table.TREATMENT_TYPE: TreatmentType,
    Table.CHECKLIST_ITEM: ChecklistItem,
    Table.FAULT_CATEGORY: FaultCategory,
}

FIELDS: Mapping[Table, tuple[str, ...]] = {
    Table.TERM: ("name", "start_date", "end_date", "is_current"),
    Table.DEPARTMENT: ("name_ar", "name_en", "head_id"),
    Table.CLINIC: ("number", "name_ar", "name_en", "building", "floor", "type", "department_id"),
    Table.CHAIR: ("clinic_id", "number"),
    Table.SESSION: (
        "clinic_id",
        "clinic_type",
        "name_ar",
        "name_en",
        "start_time",
        "end_time",
        "order",
    ),
    Table.CASE_TYPE: ("name_ar", "name_en", "kind", "order"),
    Table.TOOTH_CODE: ("letter", "meaning_ar", "meaning_en", "color", "order"),
    Table.MEDICAL_HISTORY_ITEM: ("question_ar", "question_en", "answer_type", "is_alert", "order"),
    Table.SOFT_TISSUE_SITE: ("name_ar", "name_en", "order"),
    Table.INDEX_DEFINITION: ("kind", "tooth", "surface", "min_score", "max_score", "order"),
    Table.TREATMENT_TYPE: ("name_ar", "name_en", "department_id", "case_type_id", "order"),
    Table.CHECKLIST_ITEM: ("name_ar", "name_en", "order"),
    Table.FAULT_CATEGORY: ("name_ar", "name_en", "blocks_chair", "order"),
}


def _plain(value: Any) -> Any:
    """Enum members are stored as their text value."""
    return value.value if hasattr(value, "value") and not isinstance(value, bool) else value


class OrmRecordRepository:
    def get(self, table: Table, record_id: int, *, for_update: bool = False) -> StoredRecord | None:
        rows = MODELS[table].all_objects
        if for_update:
            rows = rows.select_for_update()
        row = rows.filter(pk=record_id).first()
        if row is None:
            return None
        return StoredRecord(
            id=row.pk,
            values={field: getattr(row, field) for field in FIELDS[table]},
            is_active=row.is_active,
        )

    def is_active(self, table: Table, record_id: int) -> bool:
        return MODELS[table].objects.filter(pk=record_id).exists()

    def find(
        self, table: Table, values: Mapping[str, Any], *, exclude_id: int | None = None
    ) -> int | None:
        rows = MODELS[table].all_objects.filter(**{k: _plain(v) for k, v in values.items()})
        if exclude_id is not None:
            rows = rows.exclude(pk=exclude_id)
        return rows.values_list("pk", flat=True).order_by("pk").first()

    def create(self, table: Table, values: Mapping[str, Any]) -> int:
        row = MODELS[table](**{k: _plain(v) for k, v in values.items()})
        row.save()
        return row.pk

    def update(self, table: Table, record_id: int, values: Mapping[str, Any]) -> None:
        row = MODELS[table].all_objects.get(pk=record_id)
        for field, value in values.items():
            setattr(row, field, _plain(value))
        row.save(update_fields=[f.removesuffix("_id") for f in values])

    def set_active(self, table: Table, record_id: int, active: bool) -> None:
        row = MODELS[table].all_objects.get(pk=record_id)
        row.activate() if active else row.deactivate()


def _term(row: Term) -> TermDTO:
    return TermDTO(row.pk, row.name, row.start_date, row.end_date, row.is_current)


class OrmTermRepository:
    def current(self) -> TermDTO | None:
        row = Term.objects.filter(is_current=True).first()
        return _term(row) if row else None

    def clear_current(self, *, except_id: int | None) -> None:
        rows = Term.all_objects.filter(is_current=True)
        if except_id is not None:
            rows = rows.exclude(pk=except_id)
        for row in rows:
            row.is_current = False
            row.save(update_fields=["is_current"])


def _clinic(row: Clinic) -> ClinicDTO:
    return ClinicDTO(
        id=row.pk,
        number=row.number,
        name_ar=row.name_ar,
        name_en=row.name_en,
        type=ClinicType(row.type),
        department_id=row.department_id,
        building=row.building,
        floor=row.floor,
    )


class OrmClinicRepository:
    def get(self, clinic_id: int) -> ClinicDTO | None:
        row = Clinic.objects.filter(pk=clinic_id).first()
        return _clinic(row) if row else None

    def list(self, *, type: ClinicType | None = None) -> Sequence[ClinicDTO]:
        rows = Clinic.objects.order_by(Length("number"), "number")
        if type is not None:
            rows = rows.filter(type=ClinicType(type).value)
        return [_clinic(row) for row in rows]


def _chair(row: Chair) -> ChairDTO:
    return ChairDTO(row.pk, row.clinic_id, row.number, ChairStatus(row.status))


class OrmChairRepository:
    def get(self, chair_id: int, *, for_update: bool = False) -> ChairDTO | None:
        rows = Chair.objects.select_for_update() if for_update else Chair.objects
        row = rows.filter(pk=chair_id).first()
        return _chair(row) if row else None

    def list_for_clinic(
        self, clinic_ids: Sequence[int], *, in_service_only: bool
    ) -> Sequence[ChairDTO]:
        rows = Chair.objects.filter(clinic_id__in=list(clinic_ids)).order_by("clinic_id", "number")
        if in_service_only:
            rows = rows.filter(status=ChairStatus.IN_SERVICE.value)
        return [_chair(row) for row in rows]

    def set_status(
        self,
        chair_id: int,
        status: ChairStatus,
        *,
        reason: str,
        by_user_id: int | None,
        at: datetime,
    ) -> ChairDTO:
        row = Chair.objects.get(pk=chair_id)
        ChairStatusChange.objects.create(
            chair=row,
            from_status=row.status,
            to_status=ChairStatus(status).value,
            reason=reason,
            by_id=by_user_id,
            at=at,
        )
        row.status = ChairStatus(status).value
        row.save(update_fields=["status"])
        return _chair(row)

    def history(self, chair_id: int) -> Sequence[ChairStatusChangeDTO]:
        return [
            ChairStatusChangeDTO(
                chair_id=row.chair_id,
                from_status=ChairStatus(row.from_status),
                to_status=ChairStatus(row.to_status),
                reason=row.reason,
                by_user_id=row.by_id,
            )
            for row in ChairStatusChange.all_objects.filter(chair_id=chair_id).order_by("at", "pk")
        ]

    def next_number(self, clinic_id: int) -> int:
        highest = Chair.all_objects.filter(clinic_id=clinic_id).aggregate(n=Max("number"))["n"]
        return (highest or 0) + 1


def _session(row: Session) -> SessionDTO:
    return SessionDTO(
        id=row.pk,
        name_ar=row.name_ar,
        name_en=row.name_en,
        start_time=row.start_time,
        end_time=row.end_time,
        order=row.order,
        clinic_id=row.clinic_id,
        clinic_type=ClinicType(row.clinic_type) if row.clinic_type else None,
    )


def _department(row: Department) -> DepartmentDTO:
    return DepartmentDTO(row.pk, row.name_ar, row.name_en, row.head_id)


def _case_type(row: CaseType) -> CaseTypeDTO:
    return CaseTypeDTO(row.pk, row.name_ar, row.name_en, CaseKind(row.kind))


def _treatment_type(row: TreatmentType) -> TreatmentTypeDTO:
    return TreatmentTypeDTO(row.pk, row.name_ar, row.name_en, row.department_id, row.case_type_id)


def _fault_category(row: FaultCategory) -> FaultCategoryDTO:
    return FaultCategoryDTO(row.pk, row.name_ar, row.name_en, row.blocks_chair)


def _checklist_item(row: ChecklistItem) -> ChecklistItemDTO:
    return ChecklistItemDTO(row.pk, row.name_ar, row.name_en, row.order)


class OrmLookupRepository:
    def department(self, department_id: int) -> DepartmentDTO | None:
        row = Department.objects.filter(pk=department_id).first()
        return _department(row) if row else None

    def departments(self) -> Sequence[DepartmentDTO]:
        return [_department(row) for row in Department.objects.order_by("name_ar", "pk")]

    def sessions_for(self, clinic: ClinicDTO) -> Sequence[SessionDTO]:
        own = Session.objects.filter(clinic_id=clinic.id)
        rows = own if own.exists() else Session.objects.filter(clinic_type=clinic.type.value)
        return [_session(row) for row in rows.order_by("order", "pk")]

    def case_type(self, case_type_id: int) -> CaseTypeDTO | None:
        row = CaseType.objects.filter(pk=case_type_id).first()
        return _case_type(row) if row else None

    def treatment_type(self, treatment_type_id: int) -> TreatmentTypeDTO | None:
        row = TreatmentType.objects.filter(pk=treatment_type_id).first()
        return _treatment_type(row) if row else None

    def fault_category(self, category_id: int) -> FaultCategoryDTO | None:
        row = FaultCategory.objects.filter(pk=category_id).first()
        return _fault_category(row) if row else None

    def checklist_items(self) -> Sequence[ChecklistItemDTO]:
        return [_checklist_item(row) for row in ChecklistItem.objects.order_by("order", "pk")]

    def lookup_lists(self) -> LookupsDTO:
        return LookupsDTO(
            version=0,
            departments=tuple(self.departments()),
            case_types=tuple(_case_type(r) for r in CaseType.objects.order_by("order", "pk")),
            treatment_types=tuple(
                _treatment_type(r)
                for r in TreatmentType.objects.filter(
                    department__is_active=True, case_type__is_active=True
                ).order_by("order", "pk")
            ),
            tooth_codes=tuple(
                ToothCodeDTO(r.pk, r.letter, r.meaning_ar, r.meaning_en, r.color, r.order)
                for r in ToothCode.objects.order_by("order", "pk")
            ),
            medical_history_items=tuple(
                MedicalHistoryItemDTO(
                    r.pk,
                    r.question_ar,
                    r.question_en,
                    AnswerType(r.answer_type),
                    r.is_alert,
                    r.order,
                )
                for r in MedicalHistoryItem.objects.order_by("order", "pk")
            ),
            soft_tissue_sites=tuple(
                SoftTissueSiteDTO(r.pk, r.name_ar, r.name_en, r.order)
                for r in SoftTissueSite.objects.order_by("order", "pk")
            ),
            index_definitions=tuple(
                IndexDefinitionDTO(
                    r.pk,
                    IndexKind(r.kind),
                    r.tooth,
                    Surface(r.surface),
                    r.min_score,
                    r.max_score,
                    r.order,
                )
                for r in IndexDefinition.objects.order_by("order", "pk")
            ),
            checklist_items=tuple(self.checklist_items()),
            fault_categories=tuple(
                _fault_category(r) for r in FaultCategory.objects.order_by("order", "pk")
            ),
            sessions=tuple(
                _session(r)
                for r in Session.objects.exclude(clinic__is_active=False).order_by(
                    "clinic_type", "clinic_id", "order", "pk"
                )
            ),
        )


class OrmSettingRepository:
    def get(self, key: str) -> Any | None:
        return SystemSetting.objects.filter(key=key).values_list("value", flat=True).first()

    def all(self) -> dict[str, Any]:
        return dict(SystemSetting.objects.values_list("key", "value"))

    def set_many(self, values: Mapping[str, Any]) -> None:
        for key, value in values.items():
            row = SystemSetting.all_objects.filter(key=key).first()
            if row is None:
                SystemSetting.objects.create(key=key, value=value)
            else:
                row.value = value
                row.is_active = True
                row.save(update_fields=["value", "is_active"])

    def lookups_version(self) -> int:
        return int(self.get(LOOKUPS_VERSION_KEY) or 1)

    def bump_lookups_version(self) -> int:
        row, _created = SystemSetting.all_objects.select_for_update().get_or_create(
            key=LOOKUPS_VERSION_KEY, defaults={"value": 1}
        )
        row.value = int(row.value or 1) + 1
        row.save(update_fields=["value"])
        return row.value
