"""The patients module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never patients' models or repositories. Every function takes and
returns ids and DTOs. A missing or inactive patient raises ``NotFoundError``.

Patient alerts are not here: ``GET /patients/{id}/`` reads them from
``DiagnosisFacade.medical_alerts``.
"""

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from apps.core.application.dtos import Actor

from .dtos import AssignmentDTO, AssignmentPurpose, PatientSummaryDTO


@runtime_checkable
class PatientsFacade(Protocol):
    def get_patient_summary(self, patient_id: int) -> PatientSummaryDTO: ...

    def ensure_assignment(
        self,
        patient_id: int,
        student_id: int,
        purpose: AssignmentPurpose,
        *,
        case_id: int | None = None,
    ) -> AssignmentDTO:
        """Give the student access to the patient. Returns the active assignment with the same
        patient, student, purpose and case if there is one, so calling it twice is safe."""
        ...

    def end_assignments(
        self,
        patient_id: int,
        *,
        student_id: int | None = None,
        purpose: AssignmentPurpose | None = None,
        case_id: int | None = None,
    ) -> Sequence[AssignmentDTO]:
        """End the patient's active assignments that match the filters; returns them."""
        ...

    def has_active_assignment(
        self, patient_id: int, student_id: int, *, purpose: AssignmentPurpose | None = None
    ) -> bool:
        """BR-03: the student may work on the patient."""
        ...

    def can_read_patient(self, actor: Actor, patient_id: int) -> bool:
        """The patient is in the actor's scope (design section 8). Used by media for photos."""
        ...

    def registered_count(self, *, from_day: date, to_day: date) -> int:
        """Patients registered between the two days, both included (home figures, DB-16)."""
        ...

    def waiting_in_queue(self, *, clinic_ids: Sequence[int] | None = None) -> int:
        """Patients waiting in the diagnosis queue, in these clinics or in all."""
        ...


class PatientsFacadeService:
    """The patients facade the container hands out. Built in P1.3."""

    def get_patient_summary(self, patient_id: int) -> PatientSummaryDTO:
        raise NotImplementedError

    def ensure_assignment(
        self,
        patient_id: int,
        student_id: int,
        purpose: AssignmentPurpose,
        *,
        case_id: int | None = None,
    ) -> AssignmentDTO:
        raise NotImplementedError

    def end_assignments(
        self,
        patient_id: int,
        *,
        student_id: int | None = None,
        purpose: AssignmentPurpose | None = None,
        case_id: int | None = None,
    ) -> Sequence[AssignmentDTO]:
        raise NotImplementedError

    def has_active_assignment(
        self, patient_id: int, student_id: int, *, purpose: AssignmentPurpose | None = None
    ) -> bool:
        raise NotImplementedError

    def can_read_patient(self, actor: Actor, patient_id: int) -> bool:
        raise NotImplementedError

    def registered_count(self, *, from_day: date, to_day: date) -> int:
        raise NotImplementedError

    def waiting_in_queue(self, *, clinic_ids: Sequence[int] | None = None) -> int:
        raise NotImplementedError
