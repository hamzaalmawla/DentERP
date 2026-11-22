# Module contracts (Release 1)

Nov 22, 2026 · P0.5

This file is the agreement between **Track A** and **Track B** (design section 13). Each module
publishes a **facade**: the only functions another module may call. A facade takes and returns
ids and DTOs (frozen dataclasses), never Django model instances. Until a module is built, its
facade raises `NotImplementedError` and other modules test against its in-memory fake.

## How the contract works

| Piece | Where | What |
| --- | --- | --- |
| Facade | `apps/<module>/application/facade.py` | `<Module>Facade`, a `typing.Protocol`, with a docstring per function; `<Module>FacadeService`, the implementation the container hands out |
| DTOs | `apps/<module>/application/dtos.py` | Frozen dataclasses other modules read; the status and type enums are re-exported here |
| Fake | `apps/<module>/testing/fakes.py` | `InMemory<Module>Facade`, with `add_…` helpers to set up a test |
| Container | `apps/<module>/container.py` | `facade()` builds the real facade; other modules' containers call it to pass the port to their services |
| Ports | `apps/<module>/application/ports.py` | The module's repository ports and the facades of the other modules it needs (re-exported, with a comment on why) |

**Rules** (checked by `backend/tests/test_import_rules.py`, kept for the whole project):

- A module imports another module's `application/facade.py` and `application/dtos.py` only.
- Only `container.py` may import another module's `container` (to build the port).
- `api/` may import `apps.accounts.api` (permission classes, `request_actor`); `admin.py` may
  import `apps.accounts.dashboard.navigation` (`register_screen`) and `apps.core.dashboard`.
- Every module may import `apps.core`; core imports no other module.
- A facade file imports only its own DTOs and core, so facades never import each other.

**Shared ports are not repeated.** `Clock`, `Notifier`, `FileStorage`, `UnitOfWork` and
`AuditLogger` are in `apps/core/application/ports.py`, their fakes in `apps/core/testing`.
Services that send notifications take core's `Notifier` (fake: `FakeNotifier`), not the
notifications facade.

**Changing a contract.** Change the Protocol, the service, the fake and this file in the same
pull request; `backend/tests/test_contracts.py` fails when the three do not match. Tell the
other track in the pull request description. Repository ports inside a module may change freely.

**Errors.** A missing or inactive row raises `NotFoundError` (404 `not_found`). Other refusals
raise `DomainError` with the code named in the table.

## Who owns what

| Module | Owner | Built in | Dashboard sidebar group (`register_screen`) |
| --- | --- | --- | --- |
| setup | Setup and academics (built first) | P1.1 | `Group.FACILITIES` (departments, clinics with chairs, sessions, terms) · `Group.LISTS` · `Group.SETTINGS` |
| academics | Setup and academics (built first) | P1.2 | `Group.ACADEMIC_SETUP` (courses with inlines, grading schemes, enrollments, import students) |
| patients | Track A | P1.3 | `Group.PATIENTS` (patients, diagnosis queue) |
| diagnosis | Track A | P1.4 | `Group.CLINICAL` (diagnoses, read-only) · `Group.APPROVALS` (approve / return) |
| media | Track A | P1.5 | none: photos show inside the screens of their records |
| workcards | Track A | P1.6 | `Group.CLINICAL` (work cards and cases, read-only) · `Group.APPROVALS` (steps, complete case) |
| referrals | Track A | P1.7 | `Group.CLINICAL` (referral board) |
| scheduling | Track B | P1.8 | `Group.SCHEDULING` (distribution planner, attendance) |
| maintenance | Track B | P1.9 | `Group.MAINTENANCE` (chair status board, tickets, rounds) |
| notifications | Track B | P1.10 | none in Release 1 |
| reports | Track B | P1.11 | `Group.REPORTS` (F8, chair status F6/F18, referral statistics) · figures on `Group.HOME` |

`Group` is `apps.accounts.dashboard.navigation.Group`; the role → groups map is fixed there
(design section 11). No screen is registered yet: there are no models. Department on users
(P0.3 #15) is added by P1.1 once the `Department` table exists.

## setup

`SetupFacade` · DTOs in `apps.setup.application.dtos` · fake `InMemorySetupFacade`

| Function | Returns | Notes |
| --- | --- | --- |
| `current_term()` | `TermDTO` | The one current term. Here, not in academics, because setup owns `Term` |
| `get_clinic(clinic_id)` | `ClinicDTO` | |
| `list_clinics(*, type=None)` | `Sequence[ClinicDTO]` | By number; filter by `ClinicType` |
| `get_chair(chair_id)` | `ChairDTO` | |
| `list_chairs(clinic_id, *, in_service_only=False)` | `Sequence[ChairDTO]` | Out-of-service chairs left out on request (BR-12) |
| `set_chair_status(chair_id, status, *, reason, by_user_id)` | `ChairDTO` | Writes history; `reason_required`; `by_user_id=None` for the system |
| `list_sessions(clinic_id)` | `Sequence[SessionDTO]` | The clinic's own sessions, or those of its clinic type |
| `get_case_type(case_type_id)` | `CaseTypeDTO` | |
| `get_treatment_type(treatment_type_id)` | `TreatmentTypeDTO` | Gives `department_id` and `case_type_id` |
| `get_fault_category(category_id)` | `FaultCategoryDTO` | `blocks_chair` |
| `list_checklist_items()` | `Sequence[ChecklistItemDTO]` | Round checklist in order |
| `get_setting(key, default=None)` | JSON value | `SystemSetting` |
| `get_lookups_version()` | `int` | Changes whenever a list changes |

DTOs: `TermDTO`, `DepartmentDTO`, `ClinicDTO`, `ChairDTO`, `SessionDTO`, `CaseTypeDTO`,
`TreatmentTypeDTO`, `FaultCategoryDTO`, `ChecklistItemDTO`. Enums: `ClinicType`
(diagnosis, treatment, lab), `ChairStatus` (in_service, out_of_service), `CaseKind`.
Uses: no other module.

## academics

`AcademicsFacade` · fake `InMemoryAcademicsFacade` · `term_id=None` means the current term

| Function | Returns | Notes |
| --- | --- | --- |
| `get_course(course_id)` | `CourseDTO` | With `clinic_ids`, `students_per_chair`, `any_step_order` |
| `courses_in_clinic(clinic_id, *, term_id=None)` | `Sequence[CourseDTO]` | |
| `students_per_chair(course_id)` | `int` | 1–3 |
| `case_requirements(course_id)` | `Sequence[CaseRequirementDTO]` | |
| `step_templates(course_id, case_type_id)` | `Sequence[StepTemplateDTO]` | Course-wide and case-type steps, in order |
| `get_grading_scheme(scheme_id)` | `GradingSchemeDTO` | |
| `validate_grade(scheme_id, *, value=None, code=None)` | `None` | `invalid_grade` |
| `get_enrollment(enrollment_id)` | `EnrollmentDTO` | |
| `enrollments_of_course(course_id, *, term_id=None)` | `Sequence[EnrollmentDTO]` | |
| `enrollments_of_student(student_id, *, term_id=None)` | `Sequence[EnrollmentDTO]` | |
| `eligible_students(clinic_id, *, term_id=None)` | `Sequence[EligibleStudentDTO]` | BR-05, with progress from workcards |
| `supervisor_scope(user_id)` | `SupervisorScopeDTO` | `clinic_ids`, `course_ids`, `covers(clinic_id=, course_id=)` |

Enums: `CourseType`, `GradingType` (numeric, code, pass_fail).
Uses: setup (current term), workcards (`create_work_card` on enrollment, `progress_of`).

## patients

`PatientsFacade` · fake `InMemoryPatientsFacade`

| Function | Returns | Notes |
| --- | --- | --- |
| `get_patient_summary(patient_id)` | `PatientSummaryDTO` | No clinical data |
| `ensure_assignment(patient_id, student_id, purpose, *, case_id=None)` | `AssignmentDTO` | Safe to call twice |
| `end_assignments(patient_id, *, student_id=None, purpose=None, case_id=None)` | `Sequence[AssignmentDTO]` | The ones it ended |
| `has_active_assignment(patient_id, student_id, *, purpose=None)` | `bool` | BR-03 |
| `can_read_patient(actor, patient_id)` | `bool` | Scope (section 8), for media |
| `registered_count(*, from_day, to_day)` | `int` | Home figures |
| `waiting_in_queue(*, clinic_ids=None)` | `int` | Home figures |

Enums: `AssignmentPurpose` (diagnosis, treatment), `Sex`. Patient alerts are not here:
`GET /patients/{id}/` reads `DiagnosisFacade.medical_alerts`.
Uses: diagnosis (alerts), workcards (`transfer_open_cases`), academics (scope), setup.

## diagnosis

`DiagnosisFacade` · fake `InMemoryDiagnosisFacade`

| Function | Returns | Notes |
| --- | --- | --- |
| `get_diagnosis_summary(diagnosis_id)` | `DiagnosisSummaryDTO` | Without the F1 sections |
| `approved_plan_items(diagnosis_id)` | `Sequence[PlanItemDTO]` | `diagnosis_not_approved` (BR-04) |
| `get_plan_items(plan_item_ids)` | `Sequence[PlanItemDTO]` | |
| `mark_plan_items(plan_item_ids, status)` | `Sequence[PlanItemDTO]` | planned → referred → done; referred → planned on reject; `plan_item_status` |
| `medical_alerts(patient_id)` | `Sequence[MedicalAlertDTO]` | The red banner (US-12) |
| `submitted_for(actor)` | `Sequence[DiagnosisSummaryDTO]` | Approvals queue in scope |
| `can_read_diagnosis(actor, diagnosis_id)` | `bool` | For media |

Enums: `DiagnosisStatus`, `PlanItemStatus`.
Uses: patients (assignment), academics (scope), setup (lists), media (X-rays), core `Notifier`.

## referrals

`ReferralsFacade` · fake `InMemoryReferralsFacade`

| Function | Returns | Notes |
| --- | --- | --- |
| `get_referral(referral_id)` | `ReferralDTO` | With `plan_item_ids`, `assigned_student_id` |
| `mark_in_treatment(referral_id)` | `ReferralDTO` | assigned → in treatment on the first step submit |
| `complete_referral(referral_id)` | `ReferralDTO` | Called by `CompleteCase` (BR-08); `referral_not_in_treatment` |
| `open_referrals_count(*, clinic_ids=None)` | `int` | Home figures |

Enums: `ReferralStatus`, `OPEN_STATUSES` (BR-04).
Uses: diagnosis, setup, academics (`eligible_students`, scope), workcards
(`create_case_from_referral`), patients (`ensure_assignment`), core `Notifier`.

## workcards

`WorkcardsFacade` · fake `InMemoryWorkcardsFacade` (set `referrals[id] = CaseRequest(...)`)

| Function | Returns | Notes |
| --- | --- | --- |
| `create_work_card(enrollment_id)` | `WorkCardDTO` | One per enrollment; safe to call twice |
| `create_case_from_referral(referral_id, student_id)` | `CaseDTO` | Steps from the templates; `no_work_card`; same case on a second call |
| `transfer_open_cases(patient_id, from_student_id, to_student_id)` | `Sequence[CaseDTO]` | BR-09: approved steps stay credited |
| `progress_of(enrollment_id)` | `WorkCardProgressDTO` | Per case type, done / required |
| `get_case(case_id)` | `CaseDTO` | |
| `can_read_case(actor, case_id)` | `bool` | For media |
| `steps_waiting_count(actor)` | `int` | Home figures |

DTOs: `WorkCardDTO`, `CaseDTO`, `StepDTO`, `ProgressDTO`, `WorkCardProgressDTO`.
Enums: `CaseStatus`, `StepStatus`.
Uses: academics, referrals, diagnosis, patients, media, setup, core `Notifier`.

## media

`MediaFacade` · fake `InMemoryMediaFacade`

| Function | Returns | Notes |
| --- | --- | --- |
| `get_media(media_ids)` | `Sequence[MediaDTO]` | To check a step has its photo or X-ray |
| `attach(media_ids, owner)` | `Sequence[MediaDTO]` | `owner = MediaOwner(OwnerKind.STEP, id, patient_id)`; `media_already_attached` |
| `media_of(owner)` | `Sequence[MediaDTO]` | |
| `signed_url(media_id)` | `SignedUrlDTO` | Expires after 10 minutes; caller checks scope |

Enums: `MediaKind` (photo, xray), `OwnerKind` (diagnosis, case, step, ticket).
Uses: core `FileStorage`; patients, diagnosis, workcards, maintenance (`can_read_*` for scope);
setup (size limit).

## scheduling

`SchedulingFacade` · fake `InMemorySchedulingFacade`

| Function | Returns | Notes |
| --- | --- | --- |
| `assignments_on(clinic_id, day)` | `Sequence[ChairAssignmentDTO]` | Distribution and attendance (F8) |
| `affected_assignments(chair_id, *, from_day)` | `Sequence[ChairAssignmentDTO]` | When a chair goes out of service |

Uses: setup (chairs in service, sessions), academics (enrollments, students per chair, scope).

## maintenance

`MaintenanceFacade` · fake `InMemoryMaintenanceFacade`

| Function | Returns | Notes |
| --- | --- | --- |
| `rounds_on(clinic_id, day)` | `Sequence[RoundDTO]` | F6/F18 |
| `open_tickets(*, clinic_id=None)` | `Sequence[TicketDTO]` | Oldest first |
| `can_read_ticket(actor, ticket_id)` | `bool` | For fault photos |

Enums: `RoundKind`, `TicketStatus`.
Uses: setup (`set_chair_status`, chairs, checklist, fault categories), media, academics
(scope), core `Notifier`.

## notifications

`NotificationsFacade` (extends core's `Notifier`) · fake `InMemoryNotificationsFacade`
(core's `FakeNotifier` plus the unread count)

| Function | Returns | Notes |
| --- | --- | --- |
| `notify(recipient_ids, type, title_key, body_key, params=None, target=None)` | `None` | Core's `Notifier` port; P1.10 makes it the real adapter |
| `unread_count(user_id)` | `int` | |

DTO: `NotificationDTO`. Uses: accounts device tokens through a `DeviceTokenReader` port
(P1.10 adds the accounts service it calls).

## reports

`ReportsFacade` · fake `InMemoryReportsFacade` · no tables

| Function | Returns | Notes |
| --- | --- | --- |
| `home_figures(actor)` | `HomeFiguresDTO` | A figure outside the role is `None` (DB-16) |

Uses: every facade above, read with the actor's scope.

## API outline (Release 1)

Every endpoint below is routed and in the schema at `/api/v1/schema/` (browse it at
`/api/v1/docs/`). Until its module is built it checks the role, then answers **501** in the
standard error format: `{"code": "not_implemented", "message": "…", "details": {"planned_in":
"P1.x"}}`. Roles come from `apps.accounts.api.permissions`. Auth and `/me/` (P0.3) are built.

| Module | Method and path | Roles | Built in |
| --- | --- | --- | --- |
| setup | `GET /lookups/` | All | P1.1 |
| setup | `GET /clinics/` (`?type=`, `?with=chair_status`) | All | P1.1 |
| patients | `GET /patients/` · `GET /patients/{id}/` | Student, Supervisor | P1.3 |
| patients | `POST /patients/{id}/transfer/` | Supervisor | P1.3 |
| patients | `GET /diagnosis-queue/` · `POST /diagnosis-queue/{id}/assign/` | Supervisor | P1.3 |
| diagnosis | `POST /diagnoses/` · `PATCH /diagnoses/{id}/` · `POST /diagnoses/{id}/submit/` | Student | P1.4 |
| diagnosis | `GET /diagnoses/{id}/` | Student, Supervisor | P1.4 |
| diagnosis | `POST /diagnoses/{id}/approve/` · `/return/` | Supervisor | P1.4 |
| media | `POST /media/` · `GET /media/{id}/` | Student, Supervisor, Technician | P1.5 |
| workcards | `GET /workcards/` · `GET /workcards/{id}/` · `GET /cases/{id}/` | Student, Supervisor | P1.6 |
| workcards | `POST /steps/{id}/submit/` | Student | P1.6 |
| workcards | `POST /steps/{id}/approve/` · `/return/` · `POST /cases/{id}/complete/` · `GET /approvals/` | Supervisor | P1.6 |
| referrals | `GET /referrals/` · `POST /referrals/` · `POST /referrals/{id}/accept/` · `/reject/` · `/assign/` · `GET /referrals/{id}/eligible-students/` | Supervisor | P1.7 |
| scheduling | `GET /schedule/` | Student, Supervisor | P1.8 |
| scheduling | `GET /clinics/{id}/today/` · `POST /attendance/` | Supervisor | P1.8 |
| maintenance | `POST /rounds/` · `POST /tickets/{id}/start/` · `/external/` · `/resolve/` · `POST /chairs/{id}/status/` · `GET /chairs/{id}/history/` | Technician | P1.9 |
| maintenance | `GET /tickets/` · `POST /tickets/` | Technician, Supervisor | P1.9 |
| notifications | `GET /notifications/` · `POST /notifications/read/` | All | P1.10 |

Not planned (deferred, build-prompts section 1): `POST /cases/` (lab cases), `GET /logbook/`,
`GET /case-finder/`. `GET /clinics/?with=chair_status` is served by setup (chair status is
setup data), not by maintenance. Academics and reports have no app endpoints in Release 1.

**Building an endpoint.** Replace its `planned_view(...)` in `api/views.py` with the real view
under the same URL name, keeping the same roles; its placeholder test in
`backend/tests/test_api_outline.py` then drops out on its own, and the module's own API tests
take over.
