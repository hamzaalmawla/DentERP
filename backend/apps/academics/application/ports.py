"""Ports of the academics module (P0.5 outline; P1.2 may refine them inside the module).

Repository ports return DTOs; the ORM adapters live in ``infrastructure/``. Other modules are
reached through their facades only.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from apps.core.application.ports import AuditLogger, Clock, UnitOfWork
from apps.setup.application.facade import SetupFacade
from apps.workcards.application.facade import WorkcardsFacade

from .dtos import (
    CaseRequirementDTO,
    CourseDTO,
    EnrollmentDTO,
    GradingSchemeDTO,
    StepTemplateDTO,
    SupervisorScopeDTO,
)

__all__ = [
    "AuditLogger",
    "Clock",
    "CourseRepository",
    "EnrollmentRepository",
    "GradingSchemeRepository",
    "SetupFacade",  # current term, clinics
    "SupervisorScopeRepository",
    "UnitOfWork",
    "WorkcardsFacade",  # a work card on enrollment; progress for eligible_students
]


@runtime_checkable
class CourseRepository(Protocol):
    """The course aggregate: clinics, case requirements and step templates."""

    def get(self, course_id: int) -> CourseDTO | None: ...

    def in_clinic(self, clinic_id: int, term_id: int) -> Sequence[CourseDTO]: ...

    def requirements(self, course_id: int) -> Sequence[CaseRequirementDTO]: ...

    def templates(self, course_id: int, case_type_id: int) -> Sequence[StepTemplateDTO]: ...


@runtime_checkable
class GradingSchemeRepository(Protocol):
    def get(self, scheme_id: int) -> GradingSchemeDTO | None: ...


@runtime_checkable
class EnrollmentRepository(Protocol):
    def get(self, enrollment_id: int) -> EnrollmentDTO | None: ...

    def of_course(self, course_id: int, term_id: int) -> Sequence[EnrollmentDTO]: ...

    def of_student(self, student_id: int, term_id: int) -> Sequence[EnrollmentDTO]: ...

    def create(self, student_id: int, course_id: int, term_id: int) -> EnrollmentDTO: ...


@runtime_checkable
class SupervisorScopeRepository(Protocol):
    def scope_of(self, user_id: int) -> SupervisorScopeDTO: ...
