"""What the scheduling module gives other modules (P0.5 contract). Frozen dataclasses only."""

from dataclasses import dataclass
from datetime import date

__all__ = ["ChairAssignmentDTO"]


@dataclass(frozen=True, slots=True)
class ChairAssignmentDTO:
    """A student on a chair for one session of one day. ``present`` is ``None`` until the
    supervisor marks attendance."""

    id: int
    day: date
    session_id: int
    clinic_id: int
    chair_id: int
    course_id: int
    student_id: int
    present: bool | None = None
