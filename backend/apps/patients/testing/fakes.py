"""In-memory fake of the patients facade, for other modules' service tests.

patients = InMemoryPatientsFacade()
patients.add_patient(PatientSummaryDTO(3, "2026-000003", "سامر", Sex.MALE))
patients.ensure_assignment(3, student_id=40, purpose=AssignmentPurpose.DIAGNOSIS)
"""

from collections.abc import Sequence
from datetime import UTC, date, datetime
from itertools import count

from apps.core.application.dtos import Actor
from apps.core.domain.errors import NotFoundError
from apps.patients.application.dtos import AssignmentDTO, AssignmentPurpose, PatientSummaryDTO


class InMemoryPatientsFacade:
    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
        self.patients: dict[int, PatientSummaryDTO] = {}
        self.registered_on: dict[int, date] = {}
        self.assignments: list[AssignmentDTO] = []
        self.queue: dict[int, int] = {}  # patient id → clinic id of the waiting entry
        self.readable: set[tuple[int, int]] = set()  # (user id, patient id) in scope
        self._ids = count(1)

    # --- Test set-up ------------------------------------------------------------------

    def add_patient(
        self, patient: PatientSummaryDTO, *, registered_on: date | None = None
    ) -> PatientSummaryDTO:
        self.patients[patient.id] = patient
        self.registered_on[patient.id] = registered_on or self.now.date()
        return patient

    def allow_read(self, user_id: int, patient_id: int) -> None:
        self.readable.add((user_id, patient_id))

    # --- PatientsFacade -----------------------------------------------------------------

    def get_patient_summary(self, patient_id: int) -> PatientSummaryDTO:
        try:
            return self.patients[patient_id]
        except KeyError:
            raise NotFoundError() from None

    def ensure_assignment(
        self,
        patient_id: int,
        student_id: int,
        purpose: AssignmentPurpose,
        *,
        case_id: int | None = None,
    ) -> AssignmentDTO:
        self.get_patient_summary(patient_id)
        for assignment in self.assignments:
            if assignment.active and (
                assignment.patient_id,
                assignment.student_id,
                assignment.purpose,
                assignment.case_id,
            ) == (patient_id, student_id, purpose, case_id):
                return assignment
        assignment = AssignmentDTO(
            id=next(self._ids),
            patient_id=patient_id,
            student_id=student_id,
            purpose=AssignmentPurpose(purpose),
            active=True,
            started_at=self.now,
            case_id=case_id,
        )
        self.assignments.append(assignment)
        return assignment

    def end_assignments(
        self,
        patient_id: int,
        *,
        student_id: int | None = None,
        purpose: AssignmentPurpose | None = None,
        case_id: int | None = None,
    ) -> Sequence[AssignmentDTO]:
        ended = []
        for index, assignment in enumerate(self.assignments):
            if (
                assignment.active
                and assignment.patient_id == patient_id
                and student_id in (None, assignment.student_id)
                and purpose in (None, assignment.purpose)
                and case_id in (None, assignment.case_id)
            ):
                self.assignments[index] = AssignmentDTO(
                    id=assignment.id,
                    patient_id=assignment.patient_id,
                    student_id=assignment.student_id,
                    purpose=assignment.purpose,
                    active=False,
                    started_at=assignment.started_at,
                    case_id=assignment.case_id,
                    ended_at=self.now,
                )
                ended.append(self.assignments[index])
        return tuple(ended)

    def has_active_assignment(
        self, patient_id: int, student_id: int, *, purpose: AssignmentPurpose | None = None
    ) -> bool:
        return any(
            a.active
            and a.patient_id == patient_id
            and a.student_id == student_id
            and purpose in (None, a.purpose)
            for a in self.assignments
        )

    def can_read_patient(self, actor: Actor, patient_id: int) -> bool:
        if patient_id not in self.patients:
            return False
        return (actor.user_id, patient_id) in self.readable or self.has_active_assignment(
            patient_id, actor.user_id
        )

    def registered_count(self, *, from_day: date, to_day: date) -> int:
        return sum(1 for day in self.registered_on.values() if from_day <= day <= to_day)

    def waiting_in_queue(self, *, clinic_ids: Sequence[int] | None = None) -> int:
        return sum(
            1 for clinic in self.queue.values() if clinic_ids is None or clinic in clinic_ids
        )
