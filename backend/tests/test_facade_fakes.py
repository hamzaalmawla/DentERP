"""The in-memory facade fakes behave as their contracts say, so the tracks can rely on them
in service tests until the real module is merged."""

from datetime import UTC, date, datetime, time
from decimal import Decimal

import pytest

from apps.academics.application.dtos import (
    CaseRequirementDTO,
    CourseDTO,
    CourseType,
    EnrollmentDTO,
    GradingSchemeDTO,
    GradingType,
    StepTemplateDTO,
    SupervisorScopeDTO,
)
from apps.academics.testing import InMemoryAcademicsFacade
from apps.core.application.dtos import Actor
from apps.core.domain.errors import DomainError, NotFoundError
from apps.diagnosis.application.dtos import (
    DiagnosisStatus,
    DiagnosisSummaryDTO,
    PlanItemDTO,
    PlanItemStatus,
)
from apps.diagnosis.testing import InMemoryDiagnosisFacade
from apps.maintenance.application.dtos import TicketDTO, TicketStatus
from apps.maintenance.testing import InMemoryMaintenanceFacade
from apps.media.application.dtos import MediaDTO, MediaKind, MediaOwner, OwnerKind
from apps.media.testing import InMemoryMediaFacade
from apps.notifications.testing import InMemoryNotificationsFacade
from apps.patients.application.dtos import AssignmentPurpose, PatientSummaryDTO, Sex
from apps.patients.testing import InMemoryPatientsFacade
from apps.referrals.application.dtos import ReferralDTO, ReferralStatus
from apps.referrals.testing import InMemoryReferralsFacade
from apps.reports.application.dtos import HomeFiguresDTO
from apps.reports.testing import InMemoryReportsFacade
from apps.scheduling.application.dtos import ChairAssignmentDTO
from apps.scheduling.testing import InMemorySchedulingFacade
from apps.setup.application.dtos import (
    ChairDTO,
    ChairStatus,
    ClinicDTO,
    ClinicType,
    SessionDTO,
)
from apps.setup.testing import InMemorySetupFacade
from apps.workcards.application.dtos import CaseStatus
from apps.workcards.testing import CaseRequest, InMemoryWorkcardsFacade

NOW = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
DAY = date(2026, 12, 1)


class TestSetupFake:
    @pytest.fixture
    def setup(self):
        setup = InMemorySetupFacade()
        setup.add_clinic(ClinicDTO(1, "1", "التشخيص", "Diagnosis", ClinicType.DIAGNOSIS, 1))
        setup.add_clinic(ClinicDTO(2, "2", "اللبية", "Endodontics", ClinicType.TREATMENT, 2))
        setup.add_chair(ChairDTO(11, 2, 1, ChairStatus.IN_SERVICE))
        setup.add_chair(ChairDTO(12, 2, 2, ChairStatus.OUT_OF_SERVICE))
        return setup

    def test_clinics_by_type(self, setup):
        assert [c.id for c in setup.list_clinics(type=ClinicType.TREATMENT)] == [2]
        assert [c.id for c in setup.list_clinics()] == [1, 2]

    def test_out_of_service_chairs_are_left_out_on_request(self, setup):
        assert [c.id for c in setup.list_chairs(2)] == [11, 12]
        assert [c.id for c in setup.list_chairs(2, in_service_only=True)] == [11]

    def test_set_chair_status_needs_a_reason(self, setup):
        with pytest.raises(DomainError) as error:
            setup.set_chair_status(11, ChairStatus.OUT_OF_SERVICE, reason=" ", by_user_id=5)

        assert error.value.code == "reason_required"

    def test_set_chair_status_records_the_change(self, setup):
        chair = setup.set_chair_status(
            11, ChairStatus.OUT_OF_SERVICE, reason="Broken light", by_user_id=None
        )

        assert not chair.in_service
        assert setup.status_changes[-1].reason == "Broken light"

    def test_sessions_of_the_clinic_type_when_it_has_none(self, setup):
        setup.add_session(
            SessionDTO(1, "الأولى", "First", time(8), time(10), 1, clinic_type=ClinicType.TREATMENT)
        )

        assert [s.id for s in setup.list_sessions(2)] == [1]
        assert setup.list_sessions(1) == ()

    def test_missing_rows_are_not_found(self, setup):
        with pytest.raises(NotFoundError):
            setup.get_clinic(99)
        with pytest.raises(NotFoundError):
            setup.current_term()


class TestAcademicsFake:
    @pytest.fixture
    def academics(self):
        academics = InMemoryAcademicsFacade(current_term_id=1)
        academics.add_course(
            CourseDTO(1, "ENDO", "لبية", "Endo", CourseType.CLINICAL, 2, 1, 1, False, (2,))
        )
        academics.add_requirement(CaseRequirementDTO(1, case_type_id=3, required_count=4))
        academics.add_enrollment(EnrollmentDTO(7, student_id=40, course_id=1, term_id=1))
        academics.add_enrollment(EnrollmentDTO(8, student_id=41, course_id=1, term_id=0))
        return academics

    def test_eligible_students_are_enrolled_this_term_in_a_course_of_the_clinic(self, academics):
        eligible = academics.eligible_students(2)

        assert [(s.student_id, s.required_count) for s in eligible] == [(40, 4)]
        assert academics.eligible_students(1) == ()

    @pytest.mark.parametrize(
        ("scheme", "grade", "valid"),
        [
            (
                GradingSchemeDTO(1, GradingType.NUMERIC, Decimal(0), Decimal(100)),
                {"value": 80},
                True,
            ),
            (
                GradingSchemeDTO(1, GradingType.NUMERIC, Decimal(0), Decimal(100)),
                {"value": 101},
                False,
            ),
            (GradingSchemeDTO(1, GradingType.CODE, codes=("A", "B")), {"code": "B"}, True),
            (GradingSchemeDTO(1, GradingType.CODE, codes=("A", "B")), {"code": "C"}, False),
            (GradingSchemeDTO(1, GradingType.PASS_FAIL), {"code": "pass"}, True),
            (GradingSchemeDTO(1, GradingType.PASS_FAIL), {"value": 1}, False),
        ],
    )
    def test_validate_grade(self, academics, scheme, grade, valid):
        academics.add_scheme(scheme)
        if valid:
            academics.validate_grade(1, **grade)
        else:
            with pytest.raises(DomainError, match="invalid_grade"):
                academics.validate_grade(1, **grade)

    def test_step_templates_in_order_with_the_course_wide_steps(self, academics):
        for order, case_type in ((2, 3), (1, None), (3, 9)):
            academics.add_template(
                StepTemplateDTO(order, 1, case_type, order, "خطوة", "Step", 1, False, False)
            )

        assert [t.order for t in academics.step_templates(1, 3)] == [1, 2]

    def test_supervisor_scope(self, academics):
        academics.set_scope(SupervisorScopeDTO(30, clinic_ids=frozenset({2})))

        assert academics.supervisor_scope(30).covers(clinic_id=2)
        assert not academics.supervisor_scope(31).covers(clinic_id=2)


class TestPatientsFake:
    @pytest.fixture
    def patients(self):
        patients = InMemoryPatientsFacade(now=NOW)
        patients.add_patient(PatientSummaryDTO(3, "2026-000003", "سامر", Sex.MALE))
        return patients

    def test_ensure_assignment_is_safe_to_repeat(self, patients):
        first = patients.ensure_assignment(3, 40, AssignmentPurpose.DIAGNOSIS)
        second = patients.ensure_assignment(3, 40, AssignmentPurpose.DIAGNOSIS)

        assert first == second
        assert patients.has_active_assignment(3, 40)

    def test_end_assignments(self, patients):
        patients.ensure_assignment(3, 40, AssignmentPurpose.DIAGNOSIS)

        ended = patients.end_assignments(3, student_id=40)

        assert [a.active for a in ended] == [False]
        assert not patients.has_active_assignment(3, 40)

    def test_can_read_only_an_assigned_patient(self, patients):
        patients.ensure_assignment(3, 40, AssignmentPurpose.TREATMENT)

        assert patients.can_read_patient(Actor(40, "student"), 3)
        assert not patients.can_read_patient(Actor(41, "student"), 3)

    def test_unknown_patient(self, patients):
        with pytest.raises(NotFoundError):
            patients.ensure_assignment(99, 40, AssignmentPurpose.DIAGNOSIS)


class TestDiagnosisFake:
    @pytest.fixture
    def diagnosis(self):
        diagnosis = InMemoryDiagnosisFacade()
        diagnosis.add_diagnosis(DiagnosisSummaryDTO(4, 3, 40, 1, DiagnosisStatus.APPROVED, 1))
        diagnosis.add_diagnosis(DiagnosisSummaryDTO(5, 3, 40, 1, DiagnosisStatus.DRAFT, 1))
        diagnosis.add_plan_item(PlanItemDTO(9, 4, 3, 2, 2, PlanItemStatus.PLANNED, (36,)))
        return diagnosis

    def test_plan_items_only_of_an_approved_diagnosis(self, diagnosis):
        assert [i.id for i in diagnosis.approved_plan_items(4)] == [9]
        with pytest.raises(DomainError, match="diagnosis_not_approved"):
            diagnosis.approved_plan_items(5)

    def test_plan_item_moves(self, diagnosis):
        diagnosis.mark_plan_items([9], PlanItemStatus.REFERRED)
        (item,) = diagnosis.mark_plan_items([9], PlanItemStatus.DONE)

        assert item.status == PlanItemStatus.DONE
        with pytest.raises(DomainError, match="plan_item_status"):
            diagnosis.mark_plan_items([9], PlanItemStatus.REFERRED)


class TestMediaFake:
    def test_attach_and_signed_url(self):
        media = InMemoryMediaFacade(now=NOW)
        media.add_media(MediaDTO(21, MediaKind.PHOTO, uploaded_by_id=40))
        owner = MediaOwner(OwnerKind.STEP, 51, patient_id=3)

        media.attach([21], owner)
        media.attach([21], owner)  # again: nothing changes

        assert [m.id for m in media.media_of(owner)] == [21]
        assert media.signed_url(21).expires_at == datetime(2026, 12, 1, 9, 10, tzinfo=UTC)
        with pytest.raises(DomainError, match="media_already_attached"):
            media.attach([21], MediaOwner(OwnerKind.CASE, 1))
        with pytest.raises(NotFoundError):
            media.get_media([21, 22])


class TestWorkcardsFake:
    def test_case_from_referral_on_the_students_card(self):
        workcards = InMemoryWorkcardsFacade()
        workcards.enrollments[7] = (40, 1)
        card = workcards.create_work_card(7)
        workcards.referrals[12] = CaseRequest(patient_id=3, case_type_id=4, clinic_id=2, tooth=36)

        case = workcards.create_case_from_referral(12, 40)

        assert (case.work_card_id, case.status, case.tooth) == (card.id, CaseStatus.OPEN, 36)
        assert workcards.create_case_from_referral(12, 40) == case
        assert workcards.create_work_card(7) == card

    def test_no_work_card(self):
        workcards = InMemoryWorkcardsFacade()
        workcards.referrals[12] = CaseRequest(patient_id=3, case_type_id=4, clinic_id=2)

        with pytest.raises(DomainError, match="no_work_card"):
            workcards.create_case_from_referral(12, 40)

    def test_transfer_open_cases(self):
        workcards = InMemoryWorkcardsFacade()
        workcards.enrollments[7] = (40, 1)
        workcards.create_work_card(7)
        workcards.referrals[12] = CaseRequest(patient_id=3, case_type_id=4, clinic_id=2)
        case = workcards.create_case_from_referral(12, 40)

        (moved,) = workcards.transfer_open_cases(3, 40, 41)

        assert moved.id == case.id
        assert moved.student_id == 41


class TestReferralsFake:
    @pytest.fixture
    def referrals(self):
        referrals = InMemoryReferralsFacade(now=NOW)
        referrals.add_referral(ReferralDTO(12, 3, 1, 2, 30, ReferralStatus.ASSIGNED, (9,), NOW, 40))
        referrals.add_referral(ReferralDTO(13, 3, 1, 2, 30, ReferralStatus.SENT, (10,), NOW))
        return referrals

    def test_in_treatment_then_completed(self, referrals):
        assert referrals.mark_in_treatment(12).status == ReferralStatus.IN_TREATMENT
        assert referrals.complete_referral(12).completed_at == NOW

    def test_complete_refused_before_assignment(self, referrals):
        with pytest.raises(DomainError, match="referral_not_in_treatment"):
            referrals.complete_referral(13)

    def test_open_count(self, referrals):
        assert referrals.open_referrals_count(clinic_ids=[2]) == 2
        assert referrals.open_referrals_count(clinic_ids=[1]) == 0


class TestSchedulingFake:
    def test_affected_assignments_from_a_day_on(self):
        scheduling = InMemorySchedulingFacade()
        for pk, day in ((1, date(2026, 11, 30)), (2, DAY), (3, date(2026, 12, 2))):
            scheduling.add_assignment(ChairAssignmentDTO(pk, day, 1, 2, 11, 1, 40))

        assert [a.id for a in scheduling.affected_assignments(11, from_day=DAY)] == [2, 3]
        assert [a.id for a in scheduling.assignments_on(2, DAY)] == [2]


class TestMaintenanceFake:
    def test_open_tickets_and_scope(self):
        maintenance = InMemoryMaintenanceFacade()
        maintenance.add_ticket(TicketDTO(5, 2, 11, 1, TicketStatus.OPEN, False, NOW, 30))
        maintenance.add_ticket(TicketDTO(6, 2, 11, 1, TicketStatus.RESOLVED, False, NOW, 30))

        assert [t.id for t in maintenance.open_tickets(clinic_id=2)] == [5]
        assert maintenance.can_read_ticket(Actor(50, "technician"), 5)
        assert maintenance.can_read_ticket(Actor(30, "supervisor"), 5)
        assert not maintenance.can_read_ticket(Actor(40, "student"), 5)


class TestNotificationsFake:
    def test_unread_count(self):
        notifications = InMemoryNotificationsFacade()
        notifications.notify([40, 41], "step_approved", "step_approved_title", "step_approved_body")

        assert notifications.unread_count(40) == 1
        assert notifications.unread_count(42) == 0


class TestReportsFake:
    def test_home_figures(self):
        reports = InMemoryReportsFacade()
        actor = Actor(30, "supervisor")
        reports.figures[actor] = HomeFiguresDTO(approvals_waiting=4)

        assert reports.home_figures(actor).approvals_waiting == 4
        assert reports.home_figures(Actor(1, "reception")) == HomeFiguresDTO()
