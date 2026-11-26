"""The setup module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never setup's models or repositories. Every function takes and
returns ids and DTOs. A missing or inactive row raises ``NotFoundError`` (404 ``not_found``).
"""

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from apps.core.domain.errors import NotFoundError

from .dtos import (
    CaseTypeDTO,
    ChairDTO,
    ChairStatus,
    ChecklistItemDTO,
    ClinicDTO,
    ClinicType,
    DepartmentDTO,
    FaultCategoryDTO,
    SessionDTO,
    SetChairStatusCommand,
    TermDTO,
    TreatmentTypeDTO,
)

if TYPE_CHECKING:  # the facade file imports only its DTOs and core at run time (P0.5)
    from .ports import (
        ChairRepository,
        ClinicRepository,
        LookupRepository,
        SettingRepository,
        TermRepository,
    )
    from .services import SetChairStatus


@runtime_checkable
class SetupFacade(Protocol):
    def current_term(self) -> TermDTO:
        """The one current term. ``NotFoundError`` when none is marked current.

        (Setup owns the Term table, so ``current_term`` is here, not in academics.)
        """
        ...

    def get_department(self, department_id: int) -> DepartmentDTO: ...

    def list_departments(self) -> Sequence[DepartmentDTO]:
        """Active departments, by Arabic name (the department of a user, DB-02)."""
        ...

    def get_clinic(self, clinic_id: int) -> ClinicDTO: ...

    def list_clinics(self, *, type: ClinicType | None = None) -> Sequence[ClinicDTO]:
        """Active clinics, ordered by number; only those of ``type`` when given."""
        ...

    def get_chair(self, chair_id: int) -> ChairDTO: ...

    def list_chairs(self, clinic_id: int, *, in_service_only: bool = False) -> Sequence[ChairDTO]:
        """The clinic's active chairs by number. ``in_service_only`` leaves out chairs that are
        out of service, which may not be given to students (BR-12)."""
        ...

    def set_chair_status(
        self, chair_id: int, status: ChairStatus, *, reason: str, by_user_id: int | None
    ) -> ChairDTO:
        """Put a chair in or out of service and write its history (MT-07, BR-12).

        ``reason`` is required (``reason_required``). ``by_user_id`` is ``None`` when the
        system does it (a ticket in a blocking category). Setting the status it already has
        changes nothing.
        """
        ...

    def list_sessions(self, clinic_id: int) -> Sequence[SessionDTO]:
        """The sessions of the clinic's day in order: its own, or those of its clinic type."""
        ...

    def get_case_type(self, case_type_id: int) -> CaseTypeDTO: ...

    def get_treatment_type(self, treatment_type_id: int) -> TreatmentTypeDTO: ...

    def get_fault_category(self, category_id: int) -> FaultCategoryDTO: ...

    def list_checklist_items(self) -> Sequence[ChecklistItemDTO]:
        """The chair round checklist, in order (F6/F18)."""
        ...

    def get_setting(self, key: str, default: Any = None) -> Any:
        """A ``SystemSetting`` value (JSON), or ``default`` when the key is not set."""
        ...

    def get_lookups_version(self) -> int:
        """A number that changes whenever any lookup list changes; the app re-downloads
        ``/lookups/`` when it differs from its cached one."""
        ...


class SetupFacadeService:
    """The setup facade the container hands out. Missing and deactivated rows raise
    ``NotFoundError``."""

    def __init__(
        self,
        *,
        terms: "TermRepository",
        clinics: "ClinicRepository",
        chairs: "ChairRepository",
        lookups: "LookupRepository",
        settings: "SettingRepository",
        set_chair_status: "SetChairStatus",
    ) -> None:
        self._terms = terms
        self._clinics = clinics
        self._chairs = chairs
        self._lookups = lookups
        self._settings = settings
        self._set_chair_status = set_chair_status

    def current_term(self) -> TermDTO:
        return _found(self._terms.current())

    def get_department(self, department_id: int) -> DepartmentDTO:
        return _found(self._lookups.department(department_id))

    def list_departments(self) -> Sequence[DepartmentDTO]:
        return tuple(self._lookups.departments())

    def get_clinic(self, clinic_id: int) -> ClinicDTO:
        return _found(self._clinics.get(clinic_id))

    def list_clinics(self, *, type: ClinicType | None = None) -> Sequence[ClinicDTO]:
        return tuple(self._clinics.list(type=type))

    def get_chair(self, chair_id: int) -> ChairDTO:
        return _found(self._chairs.get(chair_id))

    def list_chairs(self, clinic_id: int, *, in_service_only: bool = False) -> Sequence[ChairDTO]:
        return tuple(self._chairs.list_for_clinic([clinic_id], in_service_only=in_service_only))

    def set_chair_status(
        self, chair_id: int, status: ChairStatus, *, reason: str, by_user_id: int | None
    ) -> ChairDTO:
        return self._set_chair_status.execute(
            SetChairStatusCommand(chair_id, status, reason, by_user_id)
        )

    def list_sessions(self, clinic_id: int) -> Sequence[SessionDTO]:
        return tuple(self._lookups.sessions_for(self.get_clinic(clinic_id)))

    def get_case_type(self, case_type_id: int) -> CaseTypeDTO:
        return _found(self._lookups.case_type(case_type_id))

    def get_treatment_type(self, treatment_type_id: int) -> TreatmentTypeDTO:
        return _found(self._lookups.treatment_type(treatment_type_id))

    def get_fault_category(self, category_id: int) -> FaultCategoryDTO:
        return _found(self._lookups.fault_category(category_id))

    def list_checklist_items(self) -> Sequence[ChecklistItemDTO]:
        return tuple(self._lookups.checklist_items())

    def get_setting(self, key: str, default: Any = None) -> Any:
        value = self._settings.get(key)
        return default if value is None else value

    def get_lookups_version(self) -> int:
        return self._settings.lookups_version()


def _found[T](item: T | None) -> T:
    if item is None:
        raise NotFoundError()
    return item
