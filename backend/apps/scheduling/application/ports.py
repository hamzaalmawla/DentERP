"""Ports of the scheduling module (P0.5 outline; P1.8 may refine them inside the module).

Repository ports return DTOs; the ORM adapters live in ``infrastructure/``. Other modules are
reached through their facades only.
"""

from collections.abc import Sequence
from datetime import date
from typing import Protocol, runtime_checkable

from apps.academics.application.facade import AcademicsFacade
from apps.core.application.ports import AuditLogger, Clock, UnitOfWork
from apps.setup.application.facade import SetupFacade

from .dtos import ChairAssignmentDTO

__all__ = [
    "AcademicsFacade",  # enrolled students, students per chair, supervisor scope
    "AuditLogger",
    "ChairAssignmentRepository",
    "Clock",
    "SetupFacade",  # chairs in service, sessions
    "UnitOfWork",
]


@runtime_checkable
class ChairAssignmentRepository(Protocol):
    """Chair assignments with their attendance."""

    def on_day(self, clinic_id: int, day: date) -> Sequence[ChairAssignmentDTO]: ...

    def for_student(self, student_id: int, from_day: date) -> Sequence[ChairAssignmentDTO]: ...

    def for_chair(self, chair_id: int, from_day: date) -> Sequence[ChairAssignmentDTO]: ...
