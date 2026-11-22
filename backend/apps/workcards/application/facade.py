"""The workcards module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never workcards' models or repositories. Every function takes and
returns ids and DTOs. A missing or inactive row raises ``NotFoundError``.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from apps.core.application.dtos import Actor

from .dtos import CaseDTO, WorkCardDTO, WorkCardProgressDTO


@runtime_checkable
class WorkcardsFacade(Protocol):
    def create_work_card(self, enrollment_id: int) -> WorkCardDTO:
        """The enrollment's work card, created on first call (one card per enrollment)."""
        ...

    def create_case_from_referral(self, referral_id: int, student_id: int) -> CaseDTO:
        """Open a case on the student's work card for an assigned referral: patient, tooth and
        case type come from the referral's plan item, the steps from the course's templates.
        Refuses with ``DomainError("no_work_card")`` when the student has no card for a course
        of the receiving clinic, and returns the existing case for a referral that has one."""
        ...

    def transfer_open_cases(
        self, patient_id: int, from_student_id: int, to_student_id: int
    ) -> Sequence[CaseDTO]:
        """Move the patient's open cases to another student (SV-09). Steps already approved
        stay credited to the student who did them (BR-09)."""
        ...

    def progress_of(self, enrollment_id: int) -> WorkCardProgressDTO:
        """Completed cases per case type against the course's requirements."""
        ...

    def get_case(self, case_id: int) -> CaseDTO: ...

    def can_read_case(self, actor: Actor, case_id: int) -> bool:
        """The case is in the actor's scope. Used by media for step photos."""
        ...

    def steps_waiting_count(self, actor: Actor) -> int:
        """Submitted steps waiting for the supervisor's approval (home figures)."""
        ...


class WorkcardsFacadeService:
    """The workcards facade the container hands out. Built in P1.6."""

    def create_work_card(self, enrollment_id: int) -> WorkCardDTO:
        raise NotImplementedError

    def create_case_from_referral(self, referral_id: int, student_id: int) -> CaseDTO:
        raise NotImplementedError

    def transfer_open_cases(
        self, patient_id: int, from_student_id: int, to_student_id: int
    ) -> Sequence[CaseDTO]:
        raise NotImplementedError

    def progress_of(self, enrollment_id: int) -> WorkCardProgressDTO:
        raise NotImplementedError

    def get_case(self, case_id: int) -> CaseDTO:
        raise NotImplementedError

    def can_read_case(self, actor: Actor, case_id: int) -> bool:
        raise NotImplementedError

    def steps_waiting_count(self, actor: Actor) -> int:
        raise NotImplementedError
