"""In-memory fake of the scheduling facade, for other modules' service tests.

scheduling = InMemorySchedulingFacade()
scheduling.add_assignment(ChairAssignmentDTO(1, day, session_id=1, clinic_id=2,
                                             chair_id=10, course_id=1, student_id=40))
"""

from collections.abc import Sequence
from datetime import date

from apps.scheduling.application.dtos import ChairAssignmentDTO


class InMemorySchedulingFacade:
    def __init__(self) -> None:
        self.assignments: list[ChairAssignmentDTO] = []

    def add_assignment(self, assignment: ChairAssignmentDTO) -> ChairAssignmentDTO:
        self.assignments.append(assignment)
        return assignment

    # --- SchedulingFacade ---------------------------------------------------------------

    def assignments_on(self, clinic_id: int, day: date) -> Sequence[ChairAssignmentDTO]:
        return tuple(
            sorted(
                (a for a in self.assignments if a.clinic_id == clinic_id and a.day == day),
                key=lambda a: (a.session_id, a.chair_id, a.student_id),
            )
        )

    def affected_assignments(
        self, chair_id: int, *, from_day: date
    ) -> Sequence[ChairAssignmentDTO]:
        return tuple(
            sorted(
                (a for a in self.assignments if a.chair_id == chair_id and a.day >= from_day),
                key=lambda a: (a.day, a.session_id),
            )
        )
