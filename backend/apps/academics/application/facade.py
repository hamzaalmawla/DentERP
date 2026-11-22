"""The academics module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never academics' models or repositories. Every function takes and
returns ids and DTOs. A missing or inactive row raises ``NotFoundError`` (404 ``not_found``).
``term_id=None`` means the current term (``SetupFacade.current_term``).
"""

from collections.abc import Sequence
from decimal import Decimal
from typing import Protocol, runtime_checkable

from .dtos import (
    CaseRequirementDTO,
    CourseDTO,
    EligibleStudentDTO,
    EnrollmentDTO,
    GradingSchemeDTO,
    StepTemplateDTO,
    SupervisorScopeDTO,
)


@runtime_checkable
class AcademicsFacade(Protocol):
    def get_course(self, course_id: int) -> CourseDTO: ...

    def courses_in_clinic(
        self, clinic_id: int, *, term_id: int | None = None
    ) -> Sequence[CourseDTO]:
        """The courses that run in the clinic in the term."""
        ...

    def students_per_chair(self, course_id: int) -> int:
        """How many students share one chair in this course (1 to 3)."""
        ...

    def case_requirements(self, course_id: int) -> Sequence[CaseRequirementDTO]: ...

    def step_templates(self, course_id: int, case_type_id: int) -> Sequence[StepTemplateDTO]:
        """The steps a new case of this type gets, in order (the course-wide steps and the
        steps of the case type)."""
        ...

    def get_grading_scheme(self, scheme_id: int) -> GradingSchemeDTO: ...

    def validate_grade(
        self, scheme_id: int, *, value: Decimal | None = None, code: str | None = None
    ) -> None:
        """Raise ``DomainError("invalid_grade")`` unless the grade fits the scheme: a number
        within min to max, one of the codes, or pass / fail."""
        ...

    def get_enrollment(self, enrollment_id: int) -> EnrollmentDTO: ...

    def enrollments_of_course(
        self, course_id: int, *, term_id: int | None = None
    ) -> Sequence[EnrollmentDTO]: ...

    def enrollments_of_student(
        self, student_id: int, *, term_id: int | None = None
    ) -> Sequence[EnrollmentDTO]: ...

    def eligible_students(
        self, clinic_id: int, *, term_id: int | None = None
    ) -> Sequence[EligibleStudentDTO]:
        """Students enrolled in the term in a course that runs in the clinic (BR-05), with
        their progress from the workcards facade."""
        ...

    def supervisor_scope(self, user_id: int) -> SupervisorScopeDTO:
        """The supervisor's clinics and courses; empty sets for a user with no scope."""
        ...


class AcademicsFacadeService:
    """The academics facade the container hands out. Built in P1.2."""

    def get_course(self, course_id: int) -> CourseDTO:
        raise NotImplementedError

    def courses_in_clinic(
        self, clinic_id: int, *, term_id: int | None = None
    ) -> Sequence[CourseDTO]:
        raise NotImplementedError

    def students_per_chair(self, course_id: int) -> int:
        raise NotImplementedError

    def case_requirements(self, course_id: int) -> Sequence[CaseRequirementDTO]:
        raise NotImplementedError

    def step_templates(self, course_id: int, case_type_id: int) -> Sequence[StepTemplateDTO]:
        raise NotImplementedError

    def get_grading_scheme(self, scheme_id: int) -> GradingSchemeDTO:
        raise NotImplementedError

    def validate_grade(
        self, scheme_id: int, *, value: Decimal | None = None, code: str | None = None
    ) -> None:
        raise NotImplementedError

    def get_enrollment(self, enrollment_id: int) -> EnrollmentDTO:
        raise NotImplementedError

    def enrollments_of_course(
        self, course_id: int, *, term_id: int | None = None
    ) -> Sequence[EnrollmentDTO]:
        raise NotImplementedError

    def enrollments_of_student(
        self, student_id: int, *, term_id: int | None = None
    ) -> Sequence[EnrollmentDTO]:
        raise NotImplementedError

    def eligible_students(
        self, clinic_id: int, *, term_id: int | None = None
    ) -> Sequence[EligibleStudentDTO]:
        raise NotImplementedError

    def supervisor_scope(self, user_id: int) -> SupervisorScopeDTO:
        raise NotImplementedError
