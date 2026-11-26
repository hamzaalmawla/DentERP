"""In-memory fake of the setup facade, for other modules' service tests.

setup = InMemorySetupFacade()
clinic = setup.add_clinic(ClinicDTO(1, "1", "اللبية", "Endodontics", ClinicType.TREATMENT, 2))
setup.add_chair(ChairDTO(10, clinic.id, 1, ChairStatus.IN_SERVICE))
service = OpenTicket(..., setup=setup)
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from typing import Any

from apps.core.domain.errors import DomainError, NotFoundError
from apps.core.domain.i18n import _
from apps.setup.application.dtos import (
    CaseTypeDTO,
    ChairDTO,
    ChairStatus,
    ChecklistItemDTO,
    ClinicDTO,
    ClinicType,
    DepartmentDTO,
    FaultCategoryDTO,
    SessionDTO,
    TermDTO,
    TreatmentTypeDTO,
)


@dataclass(frozen=True)
class ChairStatusChange:
    chair_id: int
    status: ChairStatus
    reason: str
    by_user_id: int | None


def _found[T](rows: dict[int, T], pk: int) -> T:
    try:
        return rows[pk]
    except KeyError:
        raise NotFoundError() from None


class InMemorySetupFacade:
    def __init__(self) -> None:
        self.term: TermDTO | None = None
        self.departments: dict[int, DepartmentDTO] = {}
        self.clinics: dict[int, ClinicDTO] = {}
        self.chairs: dict[int, ChairDTO] = {}
        self.sessions: list[SessionDTO] = []
        self.case_types: dict[int, CaseTypeDTO] = {}
        self.treatment_types: dict[int, TreatmentTypeDTO] = {}
        self.fault_categories: dict[int, FaultCategoryDTO] = {}
        self.checklist: list[ChecklistItemDTO] = []
        self.settings: dict[str, Any] = {}
        self.lookups_version = 1
        self.status_changes: list[ChairStatusChange] = []

    # --- Test set-up ------------------------------------------------------------------

    def add_department(self, department: DepartmentDTO) -> DepartmentDTO:
        self.departments[department.id] = department
        return department

    def add_clinic(self, clinic: ClinicDTO) -> ClinicDTO:
        self.clinics[clinic.id] = clinic
        return clinic

    def add_chair(self, chair: ChairDTO) -> ChairDTO:
        self.chairs[chair.id] = chair
        return chair

    def add_session(self, session: SessionDTO) -> SessionDTO:
        self.sessions.append(session)
        return session

    def add_case_type(self, case_type: CaseTypeDTO) -> CaseTypeDTO:
        self.case_types[case_type.id] = case_type
        return case_type

    def add_treatment_type(self, treatment_type: TreatmentTypeDTO) -> TreatmentTypeDTO:
        self.treatment_types[treatment_type.id] = treatment_type
        return treatment_type

    def add_fault_category(self, category: FaultCategoryDTO) -> FaultCategoryDTO:
        self.fault_categories[category.id] = category
        return category

    # --- SetupFacade --------------------------------------------------------------------

    def current_term(self) -> TermDTO:
        if self.term is None:
            raise NotFoundError()
        return self.term

    def get_department(self, department_id: int) -> DepartmentDTO:
        return _found(self.departments, department_id)

    def list_departments(self) -> Sequence[DepartmentDTO]:
        return tuple(sorted(self.departments.values(), key=lambda d: (d.name_ar, d.id)))

    def get_clinic(self, clinic_id: int) -> ClinicDTO:
        return _found(self.clinics, clinic_id)

    def list_clinics(self, *, type: ClinicType | None = None) -> Sequence[ClinicDTO]:
        # By number, as the real one: 2 before 10.
        clinics = sorted(self.clinics.values(), key=lambda c: (len(c.number), c.number))
        return tuple(clinic for clinic in clinics if type is None or clinic.type == type)

    def get_chair(self, chair_id: int) -> ChairDTO:
        return _found(self.chairs, chair_id)

    def list_chairs(self, clinic_id: int, *, in_service_only: bool = False) -> Sequence[ChairDTO]:
        chairs = sorted(
            (chair for chair in self.chairs.values() if chair.clinic_id == clinic_id),
            key=lambda chair: chair.number,
        )
        return tuple(chair for chair in chairs if chair.in_service or not in_service_only)

    def set_chair_status(
        self, chair_id: int, status: ChairStatus, *, reason: str, by_user_id: int | None
    ) -> ChairDTO:
        chair = self.get_chair(chair_id)
        if not reason.strip():
            raise DomainError("reason_required", _("A reason is required."))
        if chair.status == status:
            return chair
        chair = self.chairs[chair_id] = replace(chair, status=ChairStatus(status))
        self.status_changes.append(ChairStatusChange(chair_id, chair.status, reason, by_user_id))
        return chair

    def list_sessions(self, clinic_id: int) -> Sequence[SessionDTO]:
        clinic = self.get_clinic(clinic_id)
        own = [session for session in self.sessions if session.clinic_id == clinic_id]
        sessions = own or [s for s in self.sessions if s.clinic_type == clinic.type]
        return tuple(sorted(sessions, key=lambda session: session.order))

    def get_case_type(self, case_type_id: int) -> CaseTypeDTO:
        return _found(self.case_types, case_type_id)

    def get_treatment_type(self, treatment_type_id: int) -> TreatmentTypeDTO:
        return _found(self.treatment_types, treatment_type_id)

    def get_fault_category(self, category_id: int) -> FaultCategoryDTO:
        return _found(self.fault_categories, category_id)

    def list_checklist_items(self) -> Sequence[ChecklistItemDTO]:
        return tuple(sorted(self.checklist, key=lambda item: item.order))

    def get_setting(self, key: str, default: Any = None) -> Any:
        return self.settings.get(key, default)

    def get_lookups_version(self) -> int:
        return self.lookups_version
