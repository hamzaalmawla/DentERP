"""The setup module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never setup's models or repositories. Every function takes and
returns ids and DTOs. A missing or inactive row raises ``NotFoundError`` (404 ``not_found``).
"""

from collections.abc import Sequence
from typing import Any, Protocol, runtime_checkable

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


@runtime_checkable
class SetupFacade(Protocol):
    def current_term(self) -> TermDTO:
        """The one current term. ``NotFoundError`` when none is marked current.

        (Setup owns the Term table, so ``current_term`` is here, not in academics.)
        """
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
    """The setup facade the container hands out. Built in P1.1."""

    def current_term(self) -> TermDTO:
        raise NotImplementedError

    def get_clinic(self, clinic_id: int) -> ClinicDTO:
        raise NotImplementedError

    def list_clinics(self, *, type: ClinicType | None = None) -> Sequence[ClinicDTO]:
        raise NotImplementedError

    def get_chair(self, chair_id: int) -> ChairDTO:
        raise NotImplementedError

    def list_chairs(self, clinic_id: int, *, in_service_only: bool = False) -> Sequence[ChairDTO]:
        raise NotImplementedError

    def set_chair_status(
        self, chair_id: int, status: ChairStatus, *, reason: str, by_user_id: int | None
    ) -> ChairDTO:
        raise NotImplementedError

    def list_sessions(self, clinic_id: int) -> Sequence[SessionDTO]:
        raise NotImplementedError

    def get_case_type(self, case_type_id: int) -> CaseTypeDTO:
        raise NotImplementedError

    def get_treatment_type(self, treatment_type_id: int) -> TreatmentTypeDTO:
        raise NotImplementedError

    def get_fault_category(self, category_id: int) -> FaultCategoryDTO:
        raise NotImplementedError

    def list_checklist_items(self) -> Sequence[ChecklistItemDTO]:
        raise NotImplementedError

    def get_setting(self, key: str, default: Any = None) -> Any:
        raise NotImplementedError

    def get_lookups_version(self) -> int:
        raise NotImplementedError
