# SPU Dental Clinic System — Build Prompts (Release 1)

Nov 20, 2026

This file holds the prompts used to build Release 1 with Claude Code. Run them in order. Each prompt is one task: one Claude Code session, one branch, one pull request. The prompts point to [SRS.md](SRS.md) and [system-design.md](system-design.md) and do not repeat what those documents already say.

## 1. Release 1 scope

Release 1 builds the base of the system and two clinics only: **Diagnosis (التشخيص)** and **Endodontics (اللبية)**. The rest is built later on top of this base without changing it.

| In Release 1 | Deferred to later releases |
| --- | --- |
| Base: repository, Docker, `core`, `accounts`, CI | Labs: lab work cards and lab cases (ST-10, BR-10, US-05, US-06) |
| Login and roles on mobile and dashboard (all 6 roles) | Other department clinics (prosthodontics, periodontics, surgery, …) and their courses |
| Diagnosis clinic: reception → waiting queue → student diagnosis (F1) → supervisor approval | Case finder (SV-10), logbook (ST-13), student progress screen (SV-12) |
| Endodontics clinic: referral from diagnosis → accept and assign → clinical work card (F3) → steps with photos and X-rays → grading → case complete | PDF printouts (SYS-08), F9 lab report, full statistics reports |
| Chairs on mobile: chair distribution, my schedule, clinic today and attendance (F7, F8) | Merge duplicate patients (DB-19), round reminders (MT-09), stale referral alerts |
| Chairs on mobile: maintenance rounds, fault tickets, chairs in and out of service (F6, F18) | App store release, production deployment |
| Dashboard main screens: users, setup, lists, courses, patients and reception, referral board, chair and maintenance boards, home figures, F8 and chair status reports with Excel export, audit log | |

**Two clinics is a data decision, not a code decision.** The SRS forbids fixing clinics in code (section 4, NFR-13). The two clinics, their departments, the Endodontics course and its steps are seed data the super admin can change. Nothing in the code may check for "diagnosis" or "endo" by name. The code uses only the clinic `type` (diagnosis, treatment, lab) and configuration tables. A later release adds a department by adding data, not code.

**Seed data to confirm with the clinic** (the prompts load these as defaults, editable in the dashboard):

| Item | Default |
| --- | --- |
| Departments | Oral Diagnosis (التشخيص) · Endodontics (مداواة الأسنان اللبية) |
| Clinics | One diagnosis clinic and one treatment clinic for Endodontics; number of chairs to confirm (use 12 until confirmed) |
| Sessions | 5 sessions a day; times to confirm from F7 |
| Endodontics course | Clinical, current term, students per chair 1, steps in order |
| Endodontics case types | Anterior root canal (معالجة لبية أمامية) · Premolar root canal (معالجة لبية ضاحك) · Molar root canal (معالجة لبية رحى) · Retreatment (إعادة معالجة) |
| Endodontics steps | 1 Pre-operative X-ray and diagnosis confirmation (X-ray required) · 2 Access cavity (photo required) · 3 Working length (X-ray required) · 4 Cleaning and shaping · 5 Master cone (X-ray required) · 6 Obturation (X-ray required) · 7 Coronal seal and final X-ray (X-ray required) |
| Grading | Numeric 0–100 |
| Treatment types | One per case type above, referred to the Endodontics department |

## 2. How to run the prompts

1. Start a new Claude Code session for each prompt, from the latest `main`.
2. Paste the prompt, then paste the **standard footer** (section 3) under it.
3. Review the pull request: read the diff, run the tests, check the screens in Arabic. Merge, then start the next prompt.
4. Prompts marked **Track A** and **Track B** in the same phase can run in parallel by the two developers. They touch different modules. Prompts with no track run alone, in order.
5. If a prompt is too large for one session, ask Claude Code to split it and do the first half. Never merge a half-done module without its tests.

| Phase | Prompts | Who |
| --- | --- | --- |
| 0. Base | P0.1 → P0.5 | Both developers together, in order |
| 1. Backend and dashboard | P1.1 → P1.2, then Track A (P1.3 → P1.7) and Track B (P1.8 → P1.11) in parallel, then P1.12 | Two tracks |
| 2. Mobile | P2.1 → P2.3, then Track A (P2.4 → P2.5) and Track B (P2.6 → P2.9) in parallel | Two tracks |
| 3. Integration | P3.1 → P3.2 | Both |

## 3. Standard footer

Paste this under every prompt.

```
Rules for this task:
- Read CLAUDE.md, docs/decisions.md, and the sections of docs/SRS.md and docs/system-design.md named above before writing code.
- Release 1 scope is in docs/build-prompts.md section 1. Do not build anything listed there as deferred.
- Never hard-code clinic names, department names, course names or step names. Use configuration tables and the clinic type only.
- Work only in the modules and folders this prompt names. If you need another module, call its application service or port; if the port is missing, stop and tell me.
- Create a branch named after the prompt id (for example p1-3-patients), commit there, and open a draft pull request.
- Tests are part of the task, not a later step. Write them in the same pull request as the code:
  - Backend: pytest for every service — the allowed path, each guard failure (by its error code) and the
    permission scope (a row outside scope returns 404), using the in-memory fakes of the ports. API tests for
    every endpoint with each allowed role and one forbidden role. Repository tests against PostgreSQL.
  - Mobile: unit tests for every ViewModel with fake repositories (loading, data, error, each action);
    repository tests with a mocked dio; widget tests for every key widget and screen state.
  - One test per acceptance criterion of the stories named in the prompt, named after the story (test_us09_...).
- Run ruff + pytest (backend) or flutter analyze + flutter test (mobile). All must pass before you finish.
  Paste the test summary in the pull request description.
- Every user-facing string is translatable, with the Arabic translation added.
- Update README.md in the same pull request: set this prompt's row in the Status table, and change
  "Running everything" for anything you added or changed (a service, port, command or make target,
  environment variable, seed or demo command, URL or folder). README.md is the one place that says
  how to run the project.
- Module boundaries: call other modules only through their facades (docs/contracts.md). If you change
  a facade, change its Protocol, service, fake and docs/contracts.md together.
- End with: what you built, the requirement and US ids covered, how you tested it, and anything left open.
```

---

## Phase 0 — Base

### P0.1 Repository, Docker and conventions

```
Set up the repository for development, following docs/system-design.md sections 3, 4, 12 and 13.

1. Create backend/ as a Django 5.2 project on Python 3.13 with the folder layout in section 4:
   config/ with settings split into base, dev, staging and prod; urls; celery; wsgi; asgi.
   Settings: LANGUAGE_CODE "ar", LANGUAGES ar and en, TIME_ZONE "Asia/Damascus", USE_TZ True,
   PostgreSQL from environment variables, Redis for Celery and cache, all secrets from environment variables.
2. pyproject.toml with exact pinned versions of every backend library in section 3
   (Django, DRF, simplejwt, drf-spectacular, django-filter, django-unfold, django-import-export, openpyxl,
   django-simple-history, django-storages, boto3, Pillow, celery, django-celery-beat, firebase-admin,
   pytest, pytest-django, factory-boy, ruff). Leave WeasyPrint out for now (PDF is deferred).
3. deploy/docker-compose.yml for development: web (runserver), worker, beat, db (postgres:18),
   redis (redis:8), storage (Garage, with a bucket created on start). A .env.example with every variable.
4. A /health/ endpoint that checks the database and Redis.
5. ruff config, pytest config, and a Makefile or scripts for: up, migrate, test, lint, makemessages.
6. .github/workflows/backend-ci.yml: ruff, pytest against a PostgreSQL service, "makemigrations --check", and the OpenAPI schema build.
7. CLAUDE.md at the repository root containing the "Conventions for Claude Code" from section 13
   (backend, mobile and process rules), plus a short "Release 1 scope" paragraph pointing to docs/build-prompts.md.
8. docs/decisions.md with its first entry, dated today: "Release 1 is limited to the Diagnosis and
   Endodontics clinics, the chairs system (distribution, attendance, maintenance) on mobile, login and roles,
   and the main dashboard screens. Labs and other departments are deferred. Clinics stay configuration data."
9. Update README.md "Repository layout" for backend/ and deploy/.

Tests: settings load for dev, staging and prod; /health/ returns 200 when the database and Redis are up and 503
when one is down; CI runs and passes on the pull request.

Done when: `docker compose up` starts every service, /health/ returns 200, CI passes on the pull request.
```

### P0.2 Core module

```
Build the core module (backend/apps/core) — docs/system-design.md sections 5, 6, 7 (conventions) and 8.
Requirements: SYS-02, SYS-04, SYS-10.

1. Module layout from section 5 (domain/, application/, infrastructure/, api/, admin.py, models.py, container.py).
   Make a template of this layout (a short README in apps/core describing it) so every module copies it.
2. BaseModel (abstract): id, created_at, created_by, updated_at, updated_by, is_active. A default manager that
   hides inactive rows and an all_objects manager. No hard delete: delete() raises an error; deactivate() sets is_active False.
   A mechanism that fills created_by / updated_by from the current user (request middleware + service context).
3. AuditLog model and an AuditLogger port with an ORM adapter: user, action (create, update, approve, return,
   login, login_failed, …), model, object_id, changes (JSON diff), ip, at. Indexes from section 6.
4. django-simple-history set up so any module can register a model for full history in one line.
5. DomainError(code, message, details) and one DRF exception handler that returns
   {"code", "message", "details"} with the message in the request language (Accept-Language), and maps
   Django/DRF validation, 404 and permission errors to the same format.
6. API conventions: /api/v1/ router, pagination (page, page_size default 20 max 100), django-filter and ordering
   defaults, drf-spectacular schema at /api/v1/schema/ and Swagger UI at /api/v1/docs/ (SYS-09).
7. Shared ports in core/application/ports.py as typing.Protocol: Clock, Notifier (notify(recipient_ids, type, title_key,
   body_key, params, target)), FileStorage, UnitOfWork if useful. In-memory fakes for each in core/testing/.
8. A base for scope-aware query services (section 8): a helper so a query service returns 404 for rows outside scope.

Tests: soft delete (delete() raises, deactivate() hides the row, all_objects still sees it); created_by / updated_by
filled; audit diff; history row on change; the error format in Arabic and English for DomainError, validation, 404
and 403; pagination limits (default 20, maximum 100); the scope helper returns 404; the schema builds.
```

### P0.3 Accounts: login and roles (backend)

```
Build the accounts module — docs/system-design.md sections 5, 6, 7 (Auth endpoints) and 8.
Requirements: DB-01, DB-02, ST-01, SV-01, MT-01, SYS-01, SYS-02. Story: US-04 (backend part).

1. Models: custom User (username, full_name_ar, full_name_en, phone, university_id, must_change_password,
   failed_logins, locked_until), Role with codes super_admin, management, reception, supervisor, student,
   technician (loaded by a data migration), UserRole, DeviceToken. Set AUTH_USER_MODEL.
2. Domain rules: lock for 15 minutes after 5 failed logins; temporary password forces a change;
   password rules from Django validators.
3. Application services: Login, RefreshToken (rotate), Logout (blacklist), ChangePassword, RegisterDevice,
   CreateUser (with temporary password), AssignRoles, ResetPassword, UnlockAccount. All write AuditLog
   (login, login_failed, password change).
4. API: POST /api/v1/auth/login/ (returns access, refresh, must_change_password, roles),
   /auth/refresh/, /auth/logout/, GET /me/, POST /me/password/, POST /me/devices/.
   Access token 15 minutes, refresh 30 days rotated.
5. Permissions: X-Active-Role header middleware that checks the user holds the role (error code
   "role_not_held"); DRF permission classes IsStudent, IsSupervisor, IsTechnician, IsReception,
   IsSuperAdmin, IsManagement, and a HasAnyRole(...) helper. When the user must change the password,
   every endpoint except /me/ and /me/password/ returns code "password_change_required".
6. Rate limit: login 10 per minute per IP, others 120 per minute per user (DRF throttles).
7. A management command create_demo_users that creates one user per role for development.

Tests: login success, wrong password, lockout and unlock, first-login password change gate,
refresh rotation, logout blacklist, X-Active-Role with a role not held, each permission class.
```

### P0.4 Dashboard shell and users

```
Set up the web dashboard with Django Unfold — docs/system-design.md sections 8 and 11.
Requirements: DB-01, DB-02, DB-17, DB-21 (access part). Story: US-04 (dashboard part).

1. Unfold admin mounted at /dashboard/. Arabic by default with dir="rtl" in the base template,
   language switch Arabic / English. Check the sidebar, header, filters, lists, forms and actions in RTL,
   and fix layout problems with a small CSS override. Write what you checked in docs/decisions.md.
2. Theme: SPU colours and logo as settings (placeholders until the identity files arrive), one place to change them.
3. Login: only super_admin, management, reception and supervisor can log in; students and technicians get a
   clear message. Session idle timeout 2 hours. Failed dashboard logins use the same lockout service as the API.
4. Role-based sidebar: build the sidebar from a single map of role → groups (section 11 table), so each later
   module only registers its screens in that map. Hide groups the role does not have, and check the role on
   every admin view, not only in the menu.
5. A ReadOnlyForManagement mixin (has_add/change/delete_permission false for management-only users) that every
   later admin class uses.
6. Users screens (super admin): list, search, create with roles and department and a temporary password,
   deactivate, reset password, unlock account. Roles screen. Audit log viewer, read-only, filtered by user,
   model, action and date (DB-17).
7. An empty Home page placeholder (filled in P1.11).

Tests: each role sees only its own groups; a supervisor cannot open the users screen by URL;
management cannot save; a student cannot log in.
```

### P0.5 Module skeletons and contracts

```
Create the skeletons and the contracts for every Release 1 module, so the two tracks can work in parallel —
docs/system-design.md section 5 (Modules) and section 13 (Build order, phase 0).

Modules: setup, academics, patients, diagnosis, referrals, workcards, media, scheduling, maintenance,
notifications, reports.

For each module:
1. The folder layout from section 5 with empty files, registered in INSTALLED_APPS.
2. application/ports.py: the repository ports and the cross-module ports this module needs, as typing.Protocol.
3. application/dtos.py: the DTOs other modules will read (frozen dataclasses), for example PatientSummaryDTO,
   ClinicDTO, ChairDTO, EnrollmentDTO, PlanItemDTO, CaseDTO, StepDTO.
4. application/facade.py: the public service functions other modules may call, with signatures and docstrings,
   raising NotImplementedError for now. Key ones:
   - setup: get_clinic, list_chairs(clinic, in_service_only), set_chair_status, get_lookups_version
   - academics: current_term, supervisor_scope(user), eligible_students(clinic), students_per_chair(course)
   - patients: get_patient_summary, ensure_assignment, end_assignments, patient_alerts (via diagnosis)
   - diagnosis: approved_plan_items(diagnosis), mark_plan_items(items, status), medical_alerts(patient)
   - workcards: create_case_from_referral(referral, student), transfer_open_cases(patient, from, to)
   - media: attach(media_ids, owner), signed_url(media_id)
   - notifications: notify(...)
5. An in-memory fake of each facade in <module>/testing/fakes.py.

Write docs/contracts.md: one table per module listing its facade functions and DTOs. This is the agreement
between Track A and Track B. Generate the OpenAPI outline of the planned endpoints in section 7 (Release 1 only),
even if the views return 501 for now.

Tests: every fake satisfies its Protocol; every module imports and is registered; the OpenAPI schema builds; an
import-rule test that fails if a module imports another module's models.py or infrastructure/ (keep it for the
whole project).
```

---

## Phase 1 — Backend and dashboard

### P1.1 Setup: clinics, chairs, sessions, lists

```
Build the setup module — SRS section 4, docs/system-design.md sections 5, 6 (setup tables), 7 (Lookups), 11.
Requirements: DB-04, DB-06, DB-18, SYS-07, SYS-10. Story: US-01.

1. Models: Term, Department, Clinic (type diagnosis / treatment / lab), Chair (status in_service / out_of_service),
   Session, CaseType, ToothCode, MedicalHistoryItem, SoftTissueSite, IndexDefinition, TreatmentType,
   ChecklistItem, FaultCategory, SystemSetting. Constraints from section 6. Names in Arabic and English.
2. Services: CRUD through services; SetChairStatus (with reason, writes history); a lookups version number that
   changes whenever any list changes.
3. API: GET /api/v1/lookups/ returning every list in one call in the request language, with the version and an
   ETag; GET /api/v1/clinics/ (filter by type).
4. Dashboard: Facilities group (Departments, Clinics with inline Chairs, Sessions, Terms), Lists group
   (sortable order), Settings (single record). Super admin only.
5. Seed command `seed_defaults` (idempotent): the default lists from SRS section 4 (tooth codes D M F N R E C I U P,
   F1 medical history items, soft tissue sites, index set 16/11/26 buccal and 36/31/46 lingual 0–3, checklist,
   fault categories, round times), plus the Release 1 seed from docs/build-prompts.md section 1:
   two departments, one diagnosis clinic, one Endodontics treatment clinic with 12 chairs, 5 sessions,
   Endodontics case types and treatment types.

Acceptance (US-01): create a clinic with 12 chairs and 5 sessions; deactivating a chair hides it from
list_chairs(in_service_only) but keeps its history.

Tests: US-01 criteria; unique constraints (clinic number, chair number per clinic, tooth code letter, one current
term); SetChairStatus writes history and needs a reason; /lookups/ in Arabic and English, version changes after an
edit, ETag returns 304; seed_defaults run twice creates no duplicates; only the super admin can open these screens.
```

### P1.2 Academics: courses, steps, enrollments, supervisor scope

```
Build the academics module — SRS section 4, docs/system-design.md sections 5, 6 (academics tables), 8 (scope).
Requirements: DB-03, DB-05, DB-07. Stories: US-02, US-03.

1. Models: Course, CourseClinic, CaseRequirement, GradingScheme (numeric / code / pass_fail), StepTemplate
   (order, grading scheme, photo_required, xray_required), Enrollment, SupervisorScope.
2. Services: eligible_students(clinic, term) per BR-05 with each student's progress (from the workcards port);
   supervisor_scope(user) returning clinic ids and course ids; validate_grade(scheme, value) used later by steps.
3. Enrollment created → call workcards facade to create the work card (use the fake until P1.6 is merged).
4. Excel import (django-import-export + openpyxl) for students and enrollments with the columns in SRS section 9,
   downloadable templates, row-by-row validation, a report of rejected rows with reasons, idempotent re-import.
   200 rows in under 1 minute.
5. Dashboard: Academic setup group — Courses with inlines (clinics, case requirements, step templates,
   supervisors), Grading schemes, Enrollments, Import students. Super admin only.
6. Extend `seed_defaults`: the Endodontics course for the current term with its case requirements,
   the 7 step templates and the 0–100 grading scheme from docs/build-prompts.md section 1.

Acceptance: US-02 and US-03 criteria from SRS section 7.1.

Tests: US-02 (an enrolled student gets a card showing 0 of the required count); US-03 (200 rows under 1 minute,
rejected rows with reasons, re-import creates no duplicates); eligible_students includes only students enrolled this
term in a course run in that clinic (BR-05); validate_grade for each scheme type, in and out of range;
supervisor_scope by course, by clinic and both; unique constraints.
```

### P1.3 Patients and reception — Track A

```
Build the patients module — docs/system-design.md sections 5, 6 (patients tables), 7 (Patients, Diagnosis queue,
Transfers), 8 (Reception and Student scope), 11 (Reception role).
Requirements: DB-08, DB-09, DB-10, DB-11, DB-20, ST-03, SV-03, SV-09 (service only). Stories: US-09, US-10.

1. Models: Patient (file_no generated, unique and sequential per year, e.g. 2026-000123), DiagnosisQueueEntry,
   PatientAssignment, PatientTransfer. Patient history with simple-history (DB-11).
2. Services: RegisterPatient (national ID duplicate blocks with code "duplicate_national_id"; name + phone
   match returns a warning the user confirms), EditPatientDetails, SendToDiagnosisQueue (one waiting entry
   per patient), AssignFromQueue (supervisor in scope of that diagnosis clinic → creates PatientAssignment
   purpose diagnosis), TransferPatient (ends old assignment, calls workcards.transfer_open_cases, records reason).
3. Query services with scope: student sees patients with an active assignment; supervisor sees patients in
   their clinics; reception sees details only, never clinical data.
4. API: GET /patients/, GET /patients/{id}/ (with alerts from the diagnosis facade), GET /diagnosis-queue/,
   POST /diagnosis-queue/{id}/assign/, POST /patients/{id}/transfer/.
5. Dashboard: Patients group for reception and super admin — register with duplicate warning, search by file
   number / national ID / name / phone (under 2 seconds on 20,000 rows: add indexes), edit details with history,
   "Send to diagnosis clinic" action, today's queue with status. Supervisors and management see patients read-only
   in their scope. Reception never sees diagnoses, steps, photos or grades.

Acceptance: US-09 and US-10 from SRS section 7.3.

Tests: US-09 (file number generated and unique, also under concurrent registrations; duplicate national ID blocks;
name + phone warns); US-10 (assigned patient appears in the student's list); only one waiting queue entry per patient;
assign refused for a supervisor outside the diagnosis clinic; transfer ends the old assignment and records the reason;
a student gets 404 on a patient not assigned to them; reception's responses contain no clinical fields; editing
details writes a history row; search under 2 seconds on 20,000 patients.
```

### P1.4 Diagnosis (F1) — Track A

```
Build the diagnosis module — docs/system-design.md sections 5, 6 (diagnosis tables), 7 (Diagnosis), 9 (transitions).
Requirements: ST-05, ST-06, SV-04, SYS-05. Business rules: BR-02, BR-04, BR-07. Stories: US-11, US-12, US-13.

1. Models: Diagnosis, MedicalHistoryAnswer, ToothFinding (FDI permanent and primary teeth), SoftTissueFinding,
   IndexScore, PlanItem (teeth as an array, department from the treatment type). simple-history on all.
2. Domain: state machine draft → submitted → approved, submitted → returned → submitted. Value object FdiTooth.
   Index score within the definition's range. One diagnosis in progress per patient (partial unique index).
3. Services: CreateDraft (copies the last approved medical history forward, BR-02), UpdateDraft (one nested body
   with all F1 sections), Submit (patient assigned to the student; required sections filled; chosen supervisor
   in scope), Approve (supervisor in scope, not the owner; locks; plan items → planned), Return (comment required),
   medical_alerts(patient), approved_plan_items, mark_plan_items. A change after approval creates a new version.
4. API: POST /diagnoses/, GET/PATCH /diagnoses/{id}/, POST /diagnoses/{id}/submit/, /approve/, /return/.
   X-ray images are linked by media ids (media module facade).
5. Notifications through the Notifier port after commit: submitted → supervisor; approved / returned → student.
6. Dashboard: Diagnoses read-only for supervisors (scope), management and super admin, with approve / return
   actions for supervisors calling the same services (DB-21).

Acceptance: US-11 (backend part), US-12 (alerts in patient detail), US-13.

Tests: every allowed transition and every refused one (approve a draft, submit an approved diagnosis, …); submit
refused when sections are missing or the patient is not assigned; approve refused for the owner and outside scope;
return without a comment refused; approved record locked (PATCH refused) and a change makes a new version; a second
diagnosis in progress refused (BR-02) and medical history copied forward; index score out of range refused; invalid
FDI tooth refused; several codes per tooth allowed; alerts in patient detail; notifications sent only after commit;
audit log entries for submit, approve and return.
```

### P1.5 Media: photos and X-rays — Track A

```
Build the media module — docs/system-design.md sections 5, 6 (MediaFile), 7 (Media), 8 (Data protection).
Requirements: ST-11 (server side), SYS-06.

1. MediaFile model: kind photo / xray, links to patient and optionally diagnosis, case, step, ticket;
   idempotency_key unique.
2. FileStorage adapter on django-storages + boto3 against Garage (private bucket); signed URLs valid 10 minutes.
3. Upload service: JPEG or PNG only, size limit from SystemSetting (default 2 MB), Idempotency-Key header returns
   the same object on retry; thumbnail made by a Celery task with Pillow.
4. Scope: a user can read a file only if they can read its patient, case or ticket (reuse the other modules'
   query facades). Technicians see ticket photos only.
5. API: POST /media/ (multipart), GET /media/{id}/ (returns signed URLs for file and thumbnail).
6. facade.attach(media_ids, owner) used by diagnosis, workcards and maintenance.

Tests: with a fake FileStorage — wrong type and too large refused; the same Idempotency-Key returns the same object
and stores one file; the thumbnail task creates a thumbnail; signed URL expires after 10 minutes; a student gets 404
on another student's patient photo; a technician gets only ticket photos. One integration test against the Garage
container.
```

### P1.6 Clinical work cards and steps (Endodontics) — Track A

```
Build the workcards module for clinical cards only — docs/system-design.md sections 5, 6 (workcards tables),
7 (Work cards, Cases, Steps, Approvals), 9 (Step and Case transitions).
Requirements: ST-07, ST-08, ST-09, SV-07, SV-08. Rules: BR-06, BR-07, BR-08, BR-09. Stories: US-07, US-08, US-16.
Lab cases (POST /cases/ for labs, ST-10) are deferred: do not build them.

1. Models: WorkCard (one per enrollment, card_no per term), Case (status open / completed / cancelled, referral
   unique), StepRecord (student who did the step, grade_value / grade_code, supervisor, comment). simple-history.
2. Domain: step state machine pending → submitted → approved, submitted → returned → submitted; order rule BR-06
   (unless course allows any order); photo or X-ray required by the template; grade valid for the scheme.
3. Services: CreateWorkCard (on enrollment), create_case_from_referral (steps copied from the course's
   templates for the case type), SubmitStep (attach media), ApproveStep (supervisor in scope, not owner),
   ReturnStep (comment required), CompleteCase (all steps approved → case completed; calls referrals and
   diagnosis facades: referral completed, plan item done; progress +1), transfer_open_cases (completed steps stay
   credited to the old student, BR-09).
4. Query: progress per case type done / required with grades; approvals queue for a supervisor
   (submitted steps in scope).
5. API: GET /workcards/, GET /workcards/{id}/, GET /cases/{id}/, POST /cases/{id}/complete/,
   POST /steps/{id}/submit/, /approve/, /return/, GET /approvals/ (steps here + submitted diagnoses from the
   diagnosis facade, one list, filter by clinic and type).
6. Notifications: step submitted → supervisors in scope; approved / returned → student; case completed →
   referring clinic.
7. Dashboard: Work cards and cases read-only; supervisors get approve / return / complete actions in scope.

Acceptance: US-07 and US-08 criteria applied to clinical steps, US-16.

Tests: step transitions allowed and refused; submit out of order refused unless the course allows any order (BR-06);
submit without a required photo or X-ray refused; approve with a grade outside the scheme refused; approve refused
for the owner and outside scope (BR-07); return without a comment refused; approved step locked; complete refused
while a step is not approved; complete updates referral, plan item and progress (BR-08); progress counts only
completed cases (BR-09); transfer keeps completed steps credited to the old student; the approvals queue shows only
my scope; a notification for each event.
```

### P1.7 Referrals: Diagnosis → Endodontics — Track A

```
Build the referrals module — docs/system-design.md sections 5, 6 (referral tables), 7 (Referrals), 9 (transitions).
Requirements: SV-05, SV-06, DB-13 (data side). Rules: BR-04, BR-05, BR-07. Stories: US-14, US-15.

1. Models: Referral (from_clinic, to_clinic, status sent / accepted / rejected / assigned / in_treatment /
   completed), ReferralItem (a plan item in only one open referral).
2. Services: CreateReferral (plan items from an approved diagnosis, target clinic of type treatment whose
   department matches the treatment type; plan items → referred), Accept, Reject (reason; plan items → planned),
   Assign (student eligible per academics.eligible_students; creates the case via workcards facade and a
   PatientAssignment purpose treatment), automatic → in_treatment on first step submit, complete (called by
   CompleteCase).
3. API: POST /referrals/, GET /referrals/?direction=in|out&status=, POST /referrals/{id}/accept/, /reject/,
   /assign/, GET /referrals/{id}/eligible-students/ (with progress).
4. Notifications: sent → receiving clinic supervisors; accepted / rejected → referrer; assigned → student.
5. Dashboard: Referral board for supervisors (own clinics), management and super admin: status, age in days,
   filters by clinic, department and status; accept / reject / assign actions.

Write one end-to-end service test: approved diagnosis with an Endodontics plan item → referral → accept →
assign → case on the student's card with patient, tooth and case type → all steps approved → complete →
referral completed, plan item done, referring clinic notified.
Acceptance: US-14, US-15, US-16.

Tests (besides the end-to-end one): referring a plan item of a non-approved diagnosis refused; the same plan item in
two open referrals refused (BR-04); a target clinic of the wrong department refused; accept / reject / assign by a
supervisor of another clinic return 404; reject without a reason refused and plan items go back to planned; assign
to an ineligible student refused (BR-05); the first step submit moves the referral to in_treatment; inbox and sent
filters.
```

### P1.8 Chair distribution and attendance — Track B

```
Build the scheduling module — docs/system-design.md sections 5, 6 (scheduling tables), 7 (Scheduling), 11.
Requirements: DB-12, SV-11, ST-12. Rule: BR-12. Stories: US-20, US-21.

1. Models: ChairAssignment (date, session, chair, course, student), Attendance.
2. Services: SuggestDistribution(clinic, course, date range) — fills each in-service chair with up to the course's
   students per chair, only enrolled students, round-robin fair across dates, never out-of-service chairs;
   SaveDistribution (per date and session; validates chair in service and student enrolled);
   MarkAttendance (bulk, supervisor in scope); when a chair goes out of service, list the affected future
   assignments for the supervisor.
3. API: GET /schedule/?date= (student: my chairs and sessions for the coming days),
   GET /clinics/{id}/today/ (supervisor: chair × session grid with students and attendance),
   POST /attendance/ (bulk), and endpoints to move a student to another chair for a session.
4. Dashboard: Scheduling group — a custom Unfold page with the chair × session grid for a clinic and date range,
   an Auto-suggest button, drag or select to change, save. Super admin for all clinics, supervisors for their own.
   Attendance page per clinic and date.

Acceptance: US-20, US-21 (F8 report itself comes in P1.11).

Tests: the suggestion never uses an out-of-service chair and never puts more than students-per-chair on a chair;
only enrolled students are suggested; the same student twice in one date and session refused; attendance by a
supervisor outside scope returns 404; /schedule/ returns only my own chairs; the /clinics/{id}/today/ grid matches
the saved distribution; a chair going out of service lists the affected assignments.
```

### P1.9 Maintenance: rounds, tickets, chair status — Track B

```
Build the maintenance module — docs/system-design.md sections 5, 6 (maintenance tables), 7 (Maintenance), 9.
Requirements: MT-02 to MT-08, SV-13, DB-14. Rules: BR-11, BR-12. Stories: US-18, US-19.

1. Models: Round (one per clinic, date, kind morning / afternoon), ChairCheck, Ticket (open / in_progress /
   external_repair / resolved, internal or external), TicketEvent.
2. Services: SubmitRound (all chairs in one call; "all OK" fast path; a failed check needs a note and opens a
   ticket linked to the chair and the round; only the super admin can change a submitted round), OpenTicket
   (technician, supervisor in scope, or system; blocking category → chair out of service via setup facade),
   StartTicket, MarkExternal (note required), ResolveTicket (repair note required; chair back in service if no
   other blocking ticket; record who fixed it), SetChairStatus by hand with a reason.
3. Query: clinics with chair counts in / out of service, open tickets by age, chair history (rounds, tickets).
4. API: GET /clinics/?with=chair_status, POST /rounds/, POST /tickets/, GET /tickets/,
   POST /tickets/{id}/start/, /external/, /resolve/, POST /chairs/{id}/status/, GET /chairs/{id}/history/.
   Technicians see no patient data.
5. Notifications: ticket opened → technicians; resolved → whoever reported it.
6. Dashboard: Maintenance group — chair status board per clinic (in / out of service, open tickets),
   tickets list with filters, rounds list. Supervisors can only report a fault.

Acceptance: US-18 (20 chairs all OK in one request), US-19.

Tests: a second round for the same clinic, kind and day refused (BR-11); a failed check without a note refused; a
failed check opens a ticket linked to chair and round; a blocking category takes the chair out of service (BR-12);
resolve returns the chair to service only when no other blocking ticket is open; each ticket transition allowed and
refused; external and resolve need a note; a manual status change needs a reason; ticket responses contain no
patient data; notifications for opened and resolved.
```

### P1.10 Notifications — Track B

```
Build the notifications module — docs/system-design.md section 9 (Notifications), section 7 (Notifications).
Requirements: SYS-03, ST-14, SV-14. Story: US-24.

1. Notification model (recipient, type, title and body in the recipient's language, target like "case:123",
   read_at). Types: every event in SYS-03 that exists in Release 1.
2. Replace the Notifier port's fake with the real adapter: create the row, then a Celery task sends the push
   through firebase-admin to the user's DeviceTokens. Push failures are logged; the row stays. Remove dead tokens.
   Firebase credentials from an environment variable; when missing, push is skipped (development).
3. API: GET /notifications/ (unread count in the response), POST /notifications/read/ (ids or all).
4. Check that every Release 1 event is wired: diagnosis submitted / approved / returned; step submitted /
   approved / returned; referral received / accepted / rejected / completed; patient assigned / transferred;
   ticket opened / resolved. Add a test that lists them.

Acceptance: US-24 (backend part).

Tests: a row is created in the recipient's language; a push failure keeps the row; dead tokens are removed; push is
skipped without credentials; unread count; mark read by ids and all; a user cannot read or mark another user's
notifications.
```

### P1.11 Dashboard main screens and reports — Track B

```
Finish the main dashboard screens — docs/system-design.md section 11, SRS 5.1.
Requirements: DB-13, DB-14, DB-15 (Release 1 part), DB-16, DB-20, DB-21. Story: US-22 (F6/F18 and F8 only).

1. Home (DB-16): Unfold cards for patients registered (today / term), open referrals, approvals waiting,
   chairs out of service, today's diagnosis queue. Each role sees the figures for its scope; reception sees
   only patients and the queue.
2. Supervisor workspace (DB-21): check that a supervisor sees, for their own clinics and courses only, the
   approvals queue (diagnoses and steps with approve / return), the referral board, distribution and attendance,
   and can report a fault. Add an Approvals page if it is not already there.
3. Reports group (reports module, read-only queries with scope): daily clinic report F8 per clinic and date
   (students, chairs, sessions, attendance, steps done), chair status report F6/F18 per clinic and date
   (rounds and faults), referral statistics for the two clinics. On-screen table with filters, Excel export.
   PDF export is deferred.
4. Management: every screen read-only; check every admin class uses ReadOnlyForManagement.
5. Go through every dashboard screen in Arabic RTL and in English; fix untranslated strings.

Write a short checklist in docs/dashboard-checklist.md of each role, its menus and what it can do, and confirm
each line by test or by hand.

Tests: home figures per role and scope; a supervisor's approve action on the dashboard calls the same service as the
API (same guards); management cannot save on any screen (a test that loops over every registered admin class);
opening another role's screen by URL is refused; F8 and chair status report rows for seeded data; the Excel export
has the same rows as the screen; reception sees no clinical data on any screen.
```

### P1.12 Backend acceptance and demo data

```
Close phase 1 for Release 1.

1. A `seed_demo` command (development and staging only): users for every role, 30 fake patients with Arabic
   names, a term, 20 students enrolled in the Endodontics course, supervisors scoped to each clinic, a week of
   chair distribution, some diagnoses in each state, referrals, cases with steps in each state, rounds and tickets.
2. An end-to-end API test (pytest, real database) of the whole Release 1 flow, as HTTP calls with each role's token:
   reception registers → sends to diagnosis queue → supervisor assigns → student fills and submits diagnosis →
   supervisor returns → student resubmits → approves → refers Endodontics item → Endodontics supervisor accepts
   and assigns → student submits steps with photos → supervisor approves each → completes case → notifications
   checked at each step. Plus: technician morning round with one fault → ticket → chair out of service → resolve.
3. Check: every Release 1 Must requirement and US in docs/build-prompts.md section 1 has a test; list any gap.
4. Check the OpenAPI schema at /api/v1/docs/ has every Release 1 endpoint with request and response schemas,
   and export it to docs/openapi.yaml for the mobile track.
5. Coverage report for domain/ and application/ (target 70%+, NFR-12).
```

---

## Phase 2 — Mobile app

### P2.1 Flutter app foundation

```
Create the Flutter app in mobile/ — docs/system-design.md sections 3 (Mobile app), 4 (mobile/ layout), 10.
Requirements: SYS-07, NFR-09, NFR-10 (foundation).

1. Flutter stable, Dart 3, pinned packages from section 3: flutter_riverpod, go_router, dio, freezed,
   json_serializable, flutter_secure_storage, drift, image_picker, flutter_image_compress, firebase_messaging,
   flutter_local_notifications, flutter_localizations, intl, connectivity_plus, mocktail.
2. Folder layout from section 4 and MVVM rules from section 10 and CLAUDE.md.
3. core/: environment config (dev, staging base URL), dio client with auth header, X-Active-Role,
   Accept-Language and a token refresh interceptor (queue requests while refreshing; on refresh failure log out),
   API error → localized message mapping by error code in one place, connectivity watcher.
4. Theme: Arabic font (for example Cairo or Noto Kufi Arabic), RTL by default, SPU colours as tokens in one file
   (placeholders until the identity files arrive), 48 px touch targets, light theme.
5. l10n: app_ar.arb and app_en.arb, Arabic default, language switch persisted.
6. drift database with three tables: diagnosis drafts, upload queue, cached lookups.
7. Shared widgets: loading / error / empty states, patient alert banner, status chip, confirm dialog.
8. .github/workflows/mobile-ci.yml: flutter analyze, flutter test.

Tests: refresh interceptor (an expired token refreshes once and replays queued requests; a refresh failure logs
out); error-code mapping returns Arabic and English messages; headers sent on every request; drift tables open;
widget tests for the shared widgets in RTL and LTR.

Done when the app starts on Android and iOS to an empty login screen in Arabic RTL and CI passes.
```

### P2.2 Login, roles and profile

```
Build login and role routing in the app — docs/system-design.md section 10 (Login and role routing).
Requirements: ST-01, SV-01, MT-01, ST-15, SYS-01. Story: US-04 (mobile part).

1. features/auth with model / viewmodel / view: login screen, forced password change on first login
   (password_change_required), lockout message with the remaining time, logout.
2. Tokens in flutter_secure_storage; stay logged in until logout or 30 days without use.
3. Role routing: one role → its home; several app roles → role picker; switch role from the profile.
   Only student, supervisor and technician open the app; other roles see "use the dashboard".
4. go_router guards for /student/…, /supervisor/…, /maintenance/…; a wrong role goes back to its own home.
5. Bottom navigation shells for the three interfaces with the tabs from section 10 (empty screens for now).
6. Profile: name, roles, switch role, language switch, logout. Register the FCM device token after login
   (POST /me/devices/).

Tests: ViewModel tests with fake repositories for login, password change, role picking and the router guard.
```

### P2.3 Shared: lookups, notifications, upload queue

```
Build the shared app services used by all three interfaces — docs/system-design.md section 10.
Requirements: ST-11, ST-14, SV-14, SYS-03, SYS-06, NFR-10. Story: US-24 (mobile part).

1. Lookups repository: GET /lookups/ cached in drift, refreshed at most once a day or when the version changes.
2. Upload queue: pick from camera or gallery, compress to at most 2 MB, store in app storage (never the gallery),
   enqueue with an idempotency key, background sender with retry and back-off, delete the local file after upload,
   expose per-item state so screens can show "waiting to upload". Camera permission text in both languages
   (NFR-14).
3. Notifications: list screen, unread badge on the home tab, mark read, tap opens the target route
   ("case:123" → case screen, and so on); push messages via firebase_messaging and local notifications,
   tapping a push opens the same target.

Tests: lookups served from cache and refreshed only on a new version; upload queue — compresses to 2 MB or less,
retries with back-off after a network error, sends the same idempotency key on retry, deletes the local file after
success, survives an app restart; notification target routing for each target type; unread badge count.
```

### P2.4 Student — Diagnosis clinic — Track A

```
Build the Student interface for the Diagnosis clinic — docs/system-design.md section 10 (Screens, Key widgets).
Requirements: ST-02, ST-03, ST-04, ST-05, ST-06. Stories: US-11, US-12.

1. Home: today's clinic, chair and sessions (from /schedule/), returned items to fix, items waiting for approval,
   latest notifications.
2. My patients (alerts first) and Patient record: details, alert banner on every patient screen, diagnoses,
   plan with status, referrals, photos and X-rays.
3. Diagnosis wizard, 8 steps: complaint; medical history (from lookups, alert items highlighted); dental chart
   widget (4 × 8 FDI grid, permanent and primary, tap → multi-select code chips with colours from lookups);
   soft tissue sites (normal / finding + note); indices (six teeth × surface, 0–3 segmented, live index);
   X-ray findings with images through the upload queue; diagnosis text and plan items (treatment type, teeth);
   review and submit with the supervisor choice.
4. Draft saved to drift on every change and synced to the server draft when online; survives closing the app.
5. Returned diagnosis shows the supervisor comment and opens for editing and resubmission.

Tests: ViewModel tests for home, patients and the wizard (each step's validation, submit, resubmit after return);
the draft is saved locally on change, restored after a restart, then synced; widget tests for the dental chart (FDI
order, multi-select codes, primary teeth), the indices (only 0–3 accepted) and the alert banner on each patient screen.
```

### P2.5 Student — Endodontics work cards and schedule — Track A

```
Build the Student work card screens for Endodontics and the schedule — docs/system-design.md section 10.
Requirements: ST-07, ST-08, ST-09, ST-11, ST-12. Stories: US-06 (clinical), US-08.

1. Work cards list (one per course and term, done / required) and Work card detail (progress per case type, grades).
2. Case screen: patient (with alert banner), tooth, case type, steps with status, grade and supervisor.
3. Step submit: note, camera / gallery photos and X-rays through the upload queue; photo required when the
   template says so; "waiting to upload" until all photos are sent, then submit; status "Waiting for approval".
   Returned steps show the comment and can be resubmitted.
4. My schedule: chair and session distribution for the coming days (GET /schedule/).
No lab case creation (deferred).

Tests: progress shows done / required per case type; submit is disabled and shows "waiting to upload" until required
photos are uploaded; a returned step shows the comment and resubmits; the schedule shows only my chairs; ViewModel
tests with fake repositories for every screen.
```

### P2.6 Supervisor — approvals — Track B

```
Build the Supervisor approvals screens — docs/system-design.md section 10 (Supervisor row, Grade input widget).
Requirements: SV-02, SV-04, SV-07, SV-08. Stories: US-07, US-13, US-16.

1. Home: approvals waiting by type, my clinics today, new referrals, patients waiting for diagnosis.
2. Approvals queue (diagnoses and steps, filter by clinic).
3. Diagnosis review: all sections read-only (dental chart in read mode, X-rays full screen), approve or return
   with a required comment.
4. Step review: photos full screen with zoom, student note, grade input built from the grading scheme
   (number pad / code chips / pass-fail), approve or return. A normal approval is 2 taps after opening.
5. Case: when all steps are approved, a "Confirm case complete" action.

Tests: widget tests for the grade input in each scheme type (numeric range, codes, pass / fail); return blocked
without a comment; a normal approval takes 2 taps after opening (a widget test that counts the taps); complete shown
only when all steps are approved; API error codes shown as localized messages.
```

### P2.7 Supervisor — queue, referrals, assignment, transfer — Track B

```
Build the Supervisor patient flow screens — docs/system-design.md section 10.
Requirements: SV-03, SV-05, SV-06, SV-09. Stories: US-10, US-14, US-15, US-17.

1. Diagnosis queue: patients waiting in my diagnosis clinics; assign to a student.
2. Create referral from an approved diagnosis: select plan items not in an open referral, target clinic
   (filtered by the treatment type's department), note.
3. Referral inbox and sent list with status and age; accept, reject with a reason; assign to an eligible
   student with their progress shown.
4. Transfer patient to another student with a reason.

Tests: ViewModel tests for assign, create referral (items already in an open referral cannot be selected), accept,
reject (reason required), assign (only eligible students listed) and transfer (reason required).
```

### P2.8 Chairs — Clinic today and fault report — Track B

```
Build the chair screens for supervisors — docs/system-design.md section 10 (Clinic today, Report fault).
Requirements: SV-11, SV-13. Story: US-21.

1. Clinic today: chair × session grid for a chosen clinic and date, student names per chair, chairs out of
   service shown and disabled; mark attendance present / absent per student in bulk; move a student to another
   chair for a session.
2. Report fault: pick a chair, category, note and optional photo → opens a ticket.

Tests: the grid shows the saved distribution; out-of-service chairs are disabled; bulk attendance sends one request;
the fault report requires a note and queues the photo.
```

### P2.9 Maintenance interface — Track B

```
Build the Maintenance interface — docs/system-design.md section 10 (Maintenance row).
Requirements: MT-02 to MT-08. Stories: US-18, US-19.

1. Clinics list: chairs in and out of service per clinic; open tickets by age.
2. Round screen: choose clinic and morning / afternoon; one row per chair with the checklist; an "All OK" button
   for the whole round; a fault needs a note and takes an optional photo; submit once. A full round of 20 chairs
   all OK must take under 1 minute. Show a clear message if the round was already submitted.
3. Ticket list and ticket detail: start, mark external with a note, resolve with a repair note and photos;
   event history.
4. Chair detail: status, history of rounds and tickets, set in or out of service with a reason.

Tests: "All OK" marks every chair in one tap and submits one request; a fault row needs a note; a second round shows
the already-submitted message; ticket actions shown only in allowed states; external and resolve need a note; a
status change needs a reason.
```

---

## Phase 3 — Integration

### P3.1 Staging deployment

```
Deploy Release 1 to staging — docs/system-design.md section 12.

1. deploy/docker-compose.prod.yml with nginx (HTTPS with Let's Encrypt, static files, upload size limit),
   web (gunicorn), worker, beat, db, redis, storage (Garage), backup (nightly encrypted dump, 30 days).
2. Backend Dockerfile (multi-stage, non-root), collectstatic, migrations on deploy.
3. .github/workflows/deploy-staging.yml on merge to main: build and push the image, SSH to the server,
   compose pull and up, migrate. Secrets in GitHub environments only.
4. /privacy/ page, Sentry for backend and app, uptime check on /health/.
5. Staging loaded with `seed_demo`; a staging build of the app pointing to staging.
Write the runbook in deploy/README.md.

Checks: the full backend test suite passes inside the production image; after deploy, /health/ returns 200 over
HTTPS and HTTP redirects to HTTPS; a photo URL without a signature is refused; a backup is made and restored once to
a scratch database (NFR-04).
```

### P3.2 Release 1 acceptance

```
Run the Release 1 acceptance on staging.

1. Write docs/acceptance-r1.md: for every story in scope (US-01, US-02, US-03, US-04, US-07 (clinical), US-08,
   US-09 to US-21, US-24, and US-22 for F6/F18 and F8), the steps to run it on staging with the demo users,
   in the app and the dashboard, and the expected result from SRS section 7.
2. Add Flutter integration tests for the main paths that can run against staging: login per role, diagnosis
   submit, step approve, morning round.
3. List every failure as a separate issue with steps to reproduce. Fix them one per branch.
4. Check Arabic RTL on every screen of the app and the dashboard, and the 2-tap approval and 1-minute round targets.
```

---

## After Release 1

The next releases reuse the same base. Each one is mostly new data and a few new screens:

- **Labs:** lab work cards and lab cases (ST-10, US-05, US-06), the F9 report.
- **More departments:** add the department, clinics, course, case types, step templates and treatment types in the dashboard; check that referrals and work cards work with no code change.
- **Supervisor tools:** case finder (SV-10), student progress (SV-12), logbook (ST-13).
- **Reports and printouts:** PDF for F1, F2/F3 and daily reports (SYS-08), full statistics.
- **Operations:** round reminders (MT-09), stale referral alerts, production deployment, store release.
