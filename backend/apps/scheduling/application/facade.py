"""The scheduling module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never scheduling's models or repositories. Every function takes and
returns ids and DTOs.
"""

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from .dtos import ChairAssignmentDTO


@runtime_checkable
class SchedulingFacade(Protocol):
    def assignments_on(self, clinic_id: int, day: date) -> Sequence[ChairAssignmentDTO]:
        """The clinic's distribution and attendance for the day, by session and chair (the
        F8 daily clinic report)."""
        ...

    def affected_assignments(
        self, chair_id: int, *, from_day: date
    ) -> Sequence[ChairAssignmentDTO]:
        """Assignments on the chair from ``from_day`` on, to show the supervisor when the
        chair goes out of service (BR-12)."""
        ...


class SchedulingFacadeService:
    """The scheduling facade the container hands out. Built in P1.8."""

    def assignments_on(self, clinic_id: int, day: date) -> Sequence[ChairAssignmentDTO]:
        raise NotImplementedError

    def affected_assignments(
        self, chair_id: int, *, from_day: date
    ) -> Sequence[ChairAssignmentDTO]:
        raise NotImplementedError
