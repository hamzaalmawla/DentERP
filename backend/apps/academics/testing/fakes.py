"""In-memory fake of the academics facade, for other modules' service tests.

academics = InMemoryAcademicsFacade()
academics.add_course(CourseDTO(1, "ENDO4", "لبية", "Endo", CourseType.CLINICAL, 2, 1, 1,
                               False, clinic_ids=(5,)))
academics.add_enrollment(EnrollmentDTO(7, student_id=40, course_id=1, term_id=1))
academics.set_scope(SupervisorScopeDTO(30, clinic_ids=frozenset({5})))
"""

from collections.abc import Sequence
from decimal import Decimal

from apps.academics.application.dtos import (
    CaseRequirementDTO,
    CourseDTO,
    EligibleStudentDTO,
    EnrollmentDTO,
    GradingSchemeDTO,
    GradingType,
    StepTemplateDTO,
    SupervisorScopeDTO,
)
from apps.core.domain.errors import DomainError, NotFoundError
from apps.core.domain.i18n import _


def _found[T](rows: dict[int, T], pk: int) -> T:
    try:
        return rows[pk]
    except KeyError:
        raise NotFoundError() from None


class InMemoryAcademicsFacade:
    def __init__(self, current_term_id: int = 1) -> None:
        self.current_term_id = current_term_id
        self.courses: dict[int, CourseDTO] = {}
        self.requirements: list[CaseRequirementDTO] = []
        self.templates: list[StepTemplateDTO] = []
        self.schemes: dict[int, GradingSchemeDTO] = {}
        self.enrollments: dict[int, EnrollmentDTO] = {}
        self.scopes: dict[int, SupervisorScopeDTO] = {}
        self.progress: dict[int, int] = {}  # enrollment id → completed cases

    # --- Test set-up ------------------------------------------------------------------

    def add_course(self, course: CourseDTO) -> CourseDTO:
        self.courses[course.id] = course
        return course

    def add_requirement(self, requirement: CaseRequirementDTO) -> CaseRequirementDTO:
        self.requirements.append(requirement)
        return requirement

    def add_template(self, template: StepTemplateDTO) -> StepTemplateDTO:
        self.templates.append(template)
        return template

    def add_scheme(self, scheme: GradingSchemeDTO) -> GradingSchemeDTO:
        self.schemes[scheme.id] = scheme
        return scheme

    def add_enrollment(self, enrollment: EnrollmentDTO) -> EnrollmentDTO:
        self.enrollments[enrollment.id] = enrollment
        return enrollment

    def set_scope(self, scope: SupervisorScopeDTO) -> SupervisorScopeDTO:
        self.scopes[scope.supervisor_id] = scope
        return scope

    def _term(self, term_id: int | None) -> int:
        return self.current_term_id if term_id is None else term_id

    # --- AcademicsFacade ----------------------------------------------------------------

    def get_course(self, course_id: int) -> CourseDTO:
        return _found(self.courses, course_id)

    def courses_in_clinic(
        self, clinic_id: int, *, term_id: int | None = None
    ) -> Sequence[CourseDTO]:
        term = self._term(term_id)
        return tuple(
            course
            for course in self.courses.values()
            if clinic_id in course.clinic_ids and course.term_id == term
        )

    def students_per_chair(self, course_id: int) -> int:
        return self.get_course(course_id).students_per_chair

    def case_requirements(self, course_id: int) -> Sequence[CaseRequirementDTO]:
        self.get_course(course_id)
        return tuple(r for r in self.requirements if r.course_id == course_id)

    def step_templates(self, course_id: int, case_type_id: int) -> Sequence[StepTemplateDTO]:
        self.get_course(course_id)
        steps = [
            template
            for template in self.templates
            if template.course_id == course_id and template.case_type_id in (None, case_type_id)
        ]
        return tuple(sorted(steps, key=lambda template: template.order))

    def get_grading_scheme(self, scheme_id: int) -> GradingSchemeDTO:
        return _found(self.schemes, scheme_id)

    def validate_grade(
        self, scheme_id: int, *, value: Decimal | None = None, code: str | None = None
    ) -> None:
        scheme = self.get_grading_scheme(scheme_id)
        if scheme.type == GradingType.NUMERIC:
            valid = value is not None and (
                (scheme.min_value is None or value >= scheme.min_value)
                and (scheme.max_value is None or value <= scheme.max_value)
            )
        elif scheme.type == GradingType.CODE:
            valid = code is not None and code in scheme.codes
        else:
            valid = code in ("pass", "fail")
        if not valid:
            raise DomainError("invalid_grade", _("The grade does not fit the grading scheme."))

    def get_enrollment(self, enrollment_id: int) -> EnrollmentDTO:
        return _found(self.enrollments, enrollment_id)

    def enrollments_of_course(
        self, course_id: int, *, term_id: int | None = None
    ) -> Sequence[EnrollmentDTO]:
        term = self._term(term_id)
        return tuple(
            e for e in self.enrollments.values() if e.course_id == course_id and e.term_id == term
        )

    def enrollments_of_student(
        self, student_id: int, *, term_id: int | None = None
    ) -> Sequence[EnrollmentDTO]:
        term = self._term(term_id)
        return tuple(
            e for e in self.enrollments.values() if e.student_id == student_id and e.term_id == term
        )

    def eligible_students(
        self, clinic_id: int, *, term_id: int | None = None
    ) -> Sequence[EligibleStudentDTO]:
        eligible = []
        for course in self.courses_in_clinic(clinic_id, term_id=term_id):
            required = sum(r.required_count for r in self.case_requirements(course.id))
            for enrollment in self.enrollments_of_course(course.id, term_id=term_id):
                eligible.append(
                    EligibleStudentDTO(
                        student_id=enrollment.student_id,
                        enrollment_id=enrollment.id,
                        course_id=course.id,
                        completed_count=self.progress.get(enrollment.id, 0),
                        required_count=required,
                    )
                )
        return tuple(eligible)

    def supervisor_scope(self, user_id: int) -> SupervisorScopeDTO:
        return self.scopes.get(user_id, SupervisorScopeDTO(user_id))
