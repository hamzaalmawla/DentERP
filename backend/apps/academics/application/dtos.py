"""What the academics module gives other modules (P0.5 contract). Frozen dataclasses only."""

from dataclasses import dataclass
from decimal import Decimal

from apps.academics.domain.values import CourseType, GradingType

__all__ = [
    "CaseRequirementDTO",
    "CourseDTO",
    "CourseType",
    "EligibleStudentDTO",
    "EnrollmentDTO",
    "GradingSchemeDTO",
    "GradingType",
    "StepTemplateDTO",
    "SupervisorScopeDTO",
]


@dataclass(frozen=True, slots=True)
class CourseDTO:
    id: int
    code: str
    name_ar: str
    name_en: str
    type: CourseType
    department_id: int
    term_id: int
    students_per_chair: int
    any_step_order: bool
    clinic_ids: tuple[int, ...] = ()


@dataclass(frozen=True, slots=True)
class CaseRequirementDTO:
    course_id: int
    case_type_id: int
    required_count: int


@dataclass(frozen=True, slots=True)
class GradingSchemeDTO:
    id: int
    type: GradingType
    min_value: Decimal | None = None
    max_value: Decimal | None = None
    codes: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class StepTemplateDTO:
    """One step of a course's cases, copied onto each new case. ``case_type_id`` is ``None``
    for a step that every case type of the course has."""

    id: int
    course_id: int
    case_type_id: int | None
    order: int
    name_ar: str
    name_en: str
    grading_scheme_id: int
    photo_required: bool
    xray_required: bool


@dataclass(frozen=True, slots=True)
class EnrollmentDTO:
    id: int
    student_id: int
    course_id: int
    term_id: int


@dataclass(frozen=True, slots=True)
class EligibleStudentDTO:
    """A student who may be given a referral in a clinic (BR-05), with their progress."""

    student_id: int
    enrollment_id: int
    course_id: int
    completed_count: int
    required_count: int


@dataclass(frozen=True, slots=True)
class SupervisorScopeDTO:
    """The clinics and courses a supervisor works in (design section 8, BR-07)."""

    supervisor_id: int
    clinic_ids: frozenset[int] = frozenset()
    course_ids: frozenset[int] = frozenset()

    def covers(self, *, clinic_id: int | None = None, course_id: int | None = None) -> bool:
        """True when the clinic or the course is in scope."""
        return (clinic_id is not None and clinic_id in self.clinic_ids) or (
            course_id is not None and course_id in self.course_ids
        )
