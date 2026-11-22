"""In-memory fake of the workcards facade, for other modules' service tests.

workcards = InMemoryWorkcardsFacade()
workcards.enrollments[7] = (40, 1)  # enrollment id → (student id, course id)
case = workcards.create_case_from_referral(referral_id=12, student_id=40)
"""

from collections.abc import Sequence
from dataclasses import dataclass, replace
from itertools import count

from apps.core.application.dtos import Actor
from apps.core.domain.errors import DomainError, NotFoundError
from apps.core.domain.i18n import _
from apps.workcards.application.dtos import (
    CaseDTO,
    CaseStatus,
    WorkCardDTO,
    WorkCardProgressDTO,
)


@dataclass(frozen=True)
class CaseRequest:
    """What ``create_case_from_referral`` puts on the new case; set per referral in tests."""

    patient_id: int
    case_type_id: int
    clinic_id: int
    tooth: int | None = None


class InMemoryWorkcardsFacade:
    def __init__(self) -> None:
        self.enrollments: dict[int, tuple[int, int]] = {}  # id → (student id, course id)
        self.cards: dict[int, WorkCardDTO] = {}  # enrollment id → card
        self.cases: dict[int, CaseDTO] = {}
        self.referrals: dict[int, CaseRequest] = {}
        self.progress: dict[int, WorkCardProgressDTO] = {}  # enrollment id → progress
        self.waiting_steps: dict[int, int] = {}  # supervisor id → submitted steps
        self.transfers: list[tuple[int, int, int]] = []
        self._ids = count(1)

    # --- WorkcardsFacade ----------------------------------------------------------------

    def create_work_card(self, enrollment_id: int) -> WorkCardDTO:
        if enrollment_id in self.cards:
            return self.cards[enrollment_id]
        try:
            student_id, course_id = self.enrollments[enrollment_id]
        except KeyError:
            raise NotFoundError() from None
        card_id = next(self._ids)
        card = WorkCardDTO(card_id, enrollment_id, student_id, course_id, card_no=str(card_id))
        self.cards[enrollment_id] = card
        return card

    def create_case_from_referral(self, referral_id: int, student_id: int) -> CaseDTO:
        for case in self.cases.values():
            if case.referral_id == referral_id:
                return case
        try:
            request = self.referrals[referral_id]
        except KeyError:
            raise NotFoundError() from None
        card = next((c for c in self.cards.values() if c.student_id == student_id), None)
        if card is None:
            raise DomainError("no_work_card", _("The student has no work card for this clinic."))
        case = CaseDTO(
            id=next(self._ids),
            work_card_id=card.id,
            student_id=student_id,
            patient_id=request.patient_id,
            case_type_id=request.case_type_id,
            clinic_id=request.clinic_id,
            status=CaseStatus.OPEN,
            tooth=request.tooth,
            referral_id=referral_id,
        )
        self.cases[case.id] = case
        return case

    def transfer_open_cases(
        self, patient_id: int, from_student_id: int, to_student_id: int
    ) -> Sequence[CaseDTO]:
        moved = []
        for case in list(self.cases.values()):
            if (case.patient_id, case.student_id, case.status) == (
                patient_id,
                from_student_id,
                CaseStatus.OPEN,
            ):
                self.cases[case.id] = replace(case, student_id=to_student_id)
                moved.append(self.cases[case.id])
        self.transfers.append((patient_id, from_student_id, to_student_id))
        return tuple(moved)

    def progress_of(self, enrollment_id: int) -> WorkCardProgressDTO:
        card = self.create_work_card(enrollment_id)
        return self.progress.get(enrollment_id, WorkCardProgressDTO(card.id, enrollment_id))

    def get_case(self, case_id: int) -> CaseDTO:
        try:
            return self.cases[case_id]
        except KeyError:
            raise NotFoundError() from None

    def can_read_case(self, actor: Actor, case_id: int) -> bool:
        case = self.cases.get(case_id)
        return case is not None and case.student_id == actor.user_id

    def steps_waiting_count(self, actor: Actor) -> int:
        return self.waiting_steps.get(actor.user_id, 0)
