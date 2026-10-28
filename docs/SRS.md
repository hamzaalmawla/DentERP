# SPU Dental Clinic System — Software Requirements Specification

Oct 23, 2026 · @Zainab

This specification defines what the system must do. It is written for approval by the dean of the Faculty of Dentistry and as the build input for the development team.

## 1. Introduction

**Purpose.** This document states the requirements for the SPU Dental Clinic System, which replaces the paper forms of the Faculty of Dentistry clinics and labs at Syrian Private University. It has three readers. The dean approves it. The development team builds from it. Claude Code uses its requirement IDs and acceptance criteria as build instructions.

**Scope.** The system has:

- one mobile app (iOS and Android) with three interfaces: Student, Supervisor and Maintenance
- one web dashboard for the super admin and management
- one Django backend that serves both

It covers patient records, diagnosis, referrals, clinical and lab work cards with grading, chair and session distribution, chair checks and maintenance, photos and reports. It does not cover fees or payments, the university's academic system, or the X-ray imaging software.

**Definitions**

| Term | Meaning |
| --- | --- |
| Course (مقرر) | A clinical or lab course a student is enrolled in for a term. It defines the required cases and the steps of each case |
| Work card (بطاقة الأعمال) | The electronic version of F2 (lab) or F3 (clinical): one per student per course per term |
| Case | One unit of work on a work card, for example one filling on tooth 36 or one lab exercise |
| Step | One stage of a case (for example Preparation), approved and graded by a supervisor |
| Diagnosis | The electronic version of F1: history, dental chart, examination, diagnosis and treatment plan |
| Plan item | One treatment in the diagnosis plan, for example a root canal on tooth 46 |
| Referral (إحالة) | Sends one or more plan items to a department clinic for treatment |
| Clinic | A room with chairs (clinical) or benches (lab). Its type is diagnosis, treatment or lab |
| Session | A time slot in the clinic day, for example 8:00–9:40 |
| Round | A morning or afternoon chair check (F6, F18) |
| Ticket | A fault report on a chair, followed until it is repaired |
| Super admin | The dashboard user who manages the whole system and registers patients |
| FDI | The two-digit tooth numbering used on F1 (quadrant 1–4, tooth 1–8) |

**References**

- SPU Dental Clinic System — System Analysis (team document)
- SPU Dental Clinic System — Project Plan (team document)
- SPU/AQM forms M-09-Den-F1, F2, F3, F6, F7, F8, F9, F18 (issue 00, 01/11/2025)
- Site visit recording, clinics, 18 Oct 2026

## 2. Overall description

The system is new and stands alone. One Django backend holds all data. It serves the mobile app through a REST API and the dashboard directly.

**Product perspective**

- **Backend:** Django, Django REST Framework, PostgreSQL. It holds all records, the rules and the permissions.
- **Dashboard:** Django Unfold, inside the same Django project. Only the super admin and management use it.
- **Mobile app:** Flutter. One app; after login it opens the Student, Supervisor or Maintenance interface according to the user's role. A user with several roles picks one.
- **Storage:** photos and X-ray images in S3-compatible object storage.
- **Notifications:** in-app list for every user, plus push notifications where the device supports them.

**User classes**

| User class | Interface | Typical number | Main need |
| --- | --- | --- | --- |
| Super admin | Dashboard | 1–3 | Set up and run the whole system; register patients; manage users; view everything |
| Management (dean, department heads) | Dashboard, read-only | 5–15 | Reports, statistics, referral and maintenance overview |
| Student | Mobile, Student interface | Hundreds (to confirm) | Diagnose patients, record treatment steps, follow own work cards and grades |
| Supervisor | Mobile, Supervisor interface | Tens (to confirm) | Approve and grade, refer patients, assign patients to students, follow attendance |
| Maintenance technician | Mobile, Maintenance interface | 1–5 | Chair rounds, fault tickets, repairs |

**Operating environment**

- **Mobile:** Android 8.0 or later; iOS 15 or later; phones and tablets.
- **Dashboard:** current versions of Chrome, Edge, Firefox and Safari on desktop.
- **Server:** Linux cloud server with Docker, HTTPS, on the university domain.
- **Time zone:** Asia/Damascus.

**Constraints**

- Arabic first, written right to left. English is available as a second language.
- Nothing about clinics, chairs, courses, steps or sessions may be fixed in code. All of it is configured in the dashboard (section 4).
- There are no fees or payments.
- The content of every SPU/AQM paper form must be covered by a screen.
- Fixed handover date: 18 Jan 2027.

**Assumptions and dependencies**

- Student, course and enrollment lists come from the academic system as Excel files.
- The app is published from developer accounts held outside Syria.
- The university provides a subdomain for the server.
- An electronic approval by a logged-in supervisor replaces the handwritten signature on the forms.

## 3. Roles and permissions

The server checks every action against the user's role and, for students, against ownership. A student only ever sees patients and cases assigned to them.

Key: ✓ allowed · *own* only their own records · *scope* only clinics or courses the supervisor is assigned to · *view* read-only · — not allowed

| Action | Super admin | Management | Supervisor | Student | Technician |
| --- | --- | --- | --- | --- | --- |
| Configure clinics, chairs, sessions, courses, steps, lists | ✓ | — | — | — | — |
| Manage users and import students | ✓ | — | — | — | — |
| Register and edit patients | ✓ | — | — | — | — |
| View a patient record | ✓ | view | scope | own | — |
| Assign a waiting patient to a student for diagnosis | ✓ | — | scope | — | — |
| Fill and submit a diagnosis | — | — | — | own | — |
| Approve or return a diagnosis | — | — | scope | — | — |
| Create a referral | — | — | scope | — | — |
| Accept or reject a referral, assign to a student | ✓ | — | scope | — | — |
| Record a step and upload photos | — | — | — | own | — |
| Create a lab case | — | — | — | own | — |
| Approve, grade or return a step | — | — | scope | — | — |
| Transfer a patient between students | ✓ | — | scope | — | — |
| Distribute students to chairs and sessions | ✓ | — | scope | view own | — |
| Mark attendance | — | — | scope | — | — |
| Do a chair round | — | — | — | — | ✓ |
| Report a chair fault | ✓ | — | scope | — | ✓ |
| Work and close a ticket; set a chair in or out of service | ✓ | — | — | — | ✓ |
| View reports and statistics | ✓ | view | scope | own | own tickets |
| View the audit log | ✓ | — | — | — | — |

A user can hold several roles, for example a supervisor who is also a department head (Management). Permissions add up across roles.

## 4. Dynamic configuration

Everything the clinic may change is data that the super admin edits in the dashboard, never code. New clinics, chairs, courses or steps take effect without a new release of the app.

| Item | Fields the admin sets | Used by |
| --- | --- | --- |
| Academic term | Name (for example 2026–2027 Fall), start and end dates, active flag | Courses, enrollments, work cards |
| Department | Name (AR and EN), head (user) | Clinics, courses, referrals, reports |
| Clinic | Number, name, building and floor, type (diagnosis / treatment / lab), department, active flag | Distribution, referrals, rounds, reports |
| Chair or bench | Clinic, number, status (in service / out of service) | Distribution, rounds, tickets |
| Session | Clinic type or clinic, name, start and end time, order | Distribution (F7), daily reports (F8, F9) |
| Course | Code, name (AR and EN), type (clinical / lab), department, term, clinics where it runs, students per chair (1–3) | Work cards, assignment, distribution |
| Case requirement | Course, case type, number required | Work card progress, case finder |
| Step template | Course, case type (optional), order, name, grading type, photo required (yes / no) | Cases, approvals |
| Grading type | Numeric score with a range (for example 0–100), a code list (for example A/B/C), or pass / fail | Step approval |
| Course supervisors | Course or clinic, supervisors | Supervisor scope (section 3) |
| Enrollment | Student, course, term (usually imported from Excel) | Work cards, eligibility |
| Tooth codes | Letter, meaning (AR and EN), colour on the chart. Default: D, M, F, N, R, E, C, I, U, P | Dental chart |
| Medical history items | Question (AR and EN), type (yes/no, yes/no + details, text), alert flag, order. Default: the 15 conditions on F1, plus smoking, pregnancy, medications and past surgeries | Diagnosis, patient alerts |
| Soft tissue sites | Name (AR and EN), order. Default: the sites on the F1 oral map | Diagnosis |
| Periodontal index set | Index name (calculus / plaque), teeth and surfaces (default 16, 11, 26 buccal; 36, 31, 46 lingual), score range (default 0–3) | Diagnosis |
| Treatment types | Name (AR and EN), department it is referred to, case type it becomes | Treatment plan, referrals |
| Chair checklist | Item name (AR and EN), order. Default: cleanliness, handpiece connections, chair movements, lighting | Rounds |
| Round times | Morning and afternoon windows. Default: 8:30–9:30 and 14:00–15:00 | Rounds, reminders |
| Fault categories | Name, blocks the chair (yes / no) | Tickets |
| System settings | University and faculty names, logo, default language, photo size limit, notification switches | Everywhere |

The defaults listed come from the SPU/AQM forms. They are loaded on first install, and the admin can change them.

## 5. Functional requirements

There are 67 requirements across the dashboard (DB), the Student (ST), Supervisor (SV) and Maintenance (MT) interfaces, and the system as a whole (SYS). Priority uses MoSCoW: **Must** for the handover, **Should** if time allows, **Could** later. The sprint column matches the Project Plan.

### 5.1 Web dashboard (super admin and management)

| ID | Requirement | Priority | Sprint |
| --- | --- | --- | --- |
| DB-01 | Log in with username and password; management users get read-only menus | Must | S1 |
| DB-02 | Create, edit and deactivate users; assign one or more roles and a department; reset passwords | Must | S1 |
| DB-03 | Import students and enrollments from an Excel template, with a validation report of rejected rows | Must | S1 |
| DB-04 | Manage terms, departments, clinics, chairs, sessions and courses (section 4) | Must | S1 |
| DB-05 | Manage case requirements, step templates and grading types per course | Must | S1 |
| DB-06 | Manage lookup lists: tooth codes, medical history items, soft tissue sites, index set, treatment types, checklist items, fault categories | Must | S1 |
| DB-07 | Assign supervisors to courses and clinics | Must | S1 |
| DB-08 | Register a patient: full name, national ID, date of birth, sex, job, phone, address. The system generates a unique file number and warns about duplicates by national ID or by name plus phone | Must | S3 |
| DB-09 | Send a registered patient to a diagnosis clinic's waiting queue | Must | S3 |
| DB-10 | Search patients by file number, national ID, name or phone; open the full record (read-only for clinical parts) | Must | S3 |
| DB-11 | Edit patient details, with a change history | Must | S3 |
| DB-12 | Distribute students to chairs and sessions for a clinic and a date range (F7), with an auto-suggest that respects students per chair and skips out-of-service chairs | Should | S4 |
| DB-13 | Referral board: all referrals with status, age in days and filters by clinic, department and status | Must | S4 |
| DB-14 | Maintenance board: chair status per clinic, open tickets, repair history | Must | S4 |
| DB-15 | Reports: daily clinic report (F8), daily lab report (F9), chair status (F6/F18), student logbook, course progress, patients with pending plan items, referral and maintenance statistics; export to Excel and PDF | Must | S5 |
| DB-16 | Home page with key figures: patients registered, open referrals, approvals waiting, chairs out of service | Should | S5 |
| DB-17 | Audit log viewer with filters by user, record and date | Must | S5 |
| DB-18 | System settings (section 4) | Must | S1 |
| DB-19 | Merge duplicate patient records | Could | — |

### 5.2 Student interface (mobile)

| ID | Requirement | Priority | Sprint |
| --- | --- | --- | --- |
| ST-01 | Log in; change password on first login; stay logged in until logout or 30 days of inactivity | Must | S1 |
| ST-02 | Home: today's clinic, chair and sessions; returned items to fix; items waiting for approval; latest notifications | Must | S4 |
| ST-03 | My patients: patients assigned to me for diagnosis or treatment, with medical alerts shown first | Must | S3 |
| ST-04 | Patient record (own patients only): details, alerts, diagnoses, plan and its status, referrals, photos and X-rays | Must | S3 |
| ST-05 | Fill a diagnosis (F1) as a step-by-step form: complaint; medical history; dental chart (tap a tooth, pick codes); soft tissue sites; calculus and plaque indices; X-ray findings with images; diagnosis; treatment plan items (treatment type, teeth). Saves a draft automatically | Must | S3 |
| ST-06 | Submit the diagnosis to a supervisor of that clinic; see a returned diagnosis with the comment, fix it and resubmit | Must | S3 |
| ST-07 | My work cards: one card per course and term, showing cases done against required, and grades | Must | S2 |
| ST-08 | Case view: patient, tooth, case type and the list of steps with status, grade and supervisor | Must | S2 |
| ST-09 | Record a step: mark it done, add a note, attach photos from the camera or gallery, and send it to a supervisor for approval | Must | S2 |
| ST-10 | Create a lab case on a lab work card: case type and exercise or model number | Must | S2 |
| ST-11 | Upload photos compressed, with a queue that retries when the network returns | Must | S2 |
| ST-12 | My schedule: chair and session distribution for the coming days | Should | S4 |
| ST-13 | Logbook: all my cases by course and case type, with grades | Should | S5 |
| ST-14 | Notifications list; tap to open the related item | Must | S5 |
| ST-15 | Profile, Arabic / English switch, logout | Must | S1 |

### 5.3 Supervisor interface (mobile)

| ID | Requirement | Priority | Sprint |
| --- | --- | --- | --- |
| SV-01 | Log in, same as ST-01 | Must | S1 |
| SV-02 | Home: approvals waiting, by type; my clinics today; new referrals; patients waiting for diagnosis | Must | S4 |
| SV-03 | Diagnosis queue: assign a waiting patient to a student in my clinic | Must | S3 |
| SV-04 | Review a diagnosis (all sections, photos, X-rays), then approve it or return it with a comment | Must | S3 |
| SV-05 | From an approved diagnosis, select plan items and create a referral to a department clinic, with the procedure and a note | Must | S3 |
| SV-06 | Referral inbox for my clinics: accept or reject with a reason; assign the patient to an eligible student (enrolled in a course run in that clinic this term), with the student's progress shown | Must | S4 |
| SV-07 | Approval queue for steps: see the photos and the student's note; enter a grade according to the course's grading type; approve or return with a comment. Two taps for a normal approval | Must | S2 |
| SV-08 | When the last step is approved, confirm the case as complete. The referral then closes and the referring clinic is notified | Must | S4 |
| SV-09 | Transfer a patient (and their open cases) to another student, with a reason | Must | S4 |
| SV-10 | Case finder: search patients with pending plan items by treatment type, department or tooth, to give students the cases they need | Should | S4 |
| SV-11 | Clinic today: chair × session grid of students; mark attendance; adjust the distribution | Should | S4 |
| SV-12 | View a student's work cards and progress (students in my scope) | Should | S5 |
| SV-13 | Report a chair fault with a photo and a note; it opens a ticket | Must | S4 |
| SV-14 | Notifications list | Must | S5 |

### 5.4 Maintenance interface (mobile)

| ID | Requirement | Priority | Sprint |
| --- | --- | --- | --- |
| MT-01 | Log in, same as ST-01 | Must | S1 |
| MT-02 | Home: clinics with counts of chairs in and out of service; open tickets by age | Must | S4 |
| MT-03 | Do a round: pick a clinic and the morning or afternoon round, then check each chair against the checklist. "All OK" in one tap; a fault takes a note and an optional photo | Must | S4 |
| MT-04 | A failed check opens a ticket automatically, linked to the chair and the round | Must | S4 |
| MT-05 | Work a ticket: Open → In progress → (External repair) → Resolved; mark it internal or external; add repair notes and photos | Must | S4 |
| MT-06 | A ticket in a blocking fault category takes the chair out of service. Resolving it returns the chair to service | Must | S4 |
| MT-07 | Set a chair in or out of service by hand, with a reason | Must | S4 |
| MT-08 | Chair history: past rounds, tickets and repairs | Should | S5 |
| MT-09 | Reminder notification when a round has not been done by the end of its window | Could | S5 |

### 5.5 System-wide

| ID | Requirement | Priority | Sprint |
| --- | --- | --- | --- |
| SYS-01 | JWT login with refresh tokens; lock an account for 15 minutes after 5 failed attempts | Must | S1 |
| SYS-02 | Role and ownership checks on every API call (section 3), never only in the app | Must | S1 |
| SYS-03 | In-app notifications for: diagnosis submitted, approved or returned; step submitted, approved or returned; referral received, accepted, rejected or completed; patient assigned or transferred; ticket opened or resolved. Push notifications for the same events where available | Must | S5 |
| SYS-04 | Audit log of every create, change, approval and login: user, action, record, time | Must | S1 |
| SYS-05 | Approved diagnoses and steps are locked. A change after approval creates a new version, and the history is kept | Must | S3 |
| SYS-06 | Photos: JPEG or PNG, compressed on the phone to at most 2 MB, with thumbnails generated on the server; linked to the patient and optionally to a case and step | Must | S2 |
| SYS-07 | Arabic and English for every screen, label and lookup list, right to left in Arabic | Must | S1 |
| SYS-08 | Printable PDF of a diagnosis (F1 layout), a work card (F2/F3) and the daily reports | Should | S5 |
| SYS-09 | API documented with OpenAPI at /api/v1/docs | Must | S1 |
| SYS-10 | Soft delete only: records are deactivated, never removed, so history and grades stay intact | Must | S1 |

## 6. Business rules and record lifecycles

Four records carry the workflow. Each one moves forward only through a named person's action, and the server rejects any change that skips a state.

&#91;embedded content: record lifecycles · diagnosis, referral, step, ticket\]

A return sends the record back to the student to fix and resubmit. A diagnosis can be returned many times before it is approved.

### Business rules

| ID | Rule |
| --- | --- |
| BR-01 | Only the super admin creates patients. Each patient has a unique file number generated by the system and a unique national ID when one is given |
| BR-02 | A patient has at most one diagnosis in progress at a time. A later diagnosis is a new record; the earlier ones stay as history, and the medical history is copied forward to be checked |
| BR-03 | Students see and work only on patients assigned to them, for diagnosis or for treatment. A transfer ends the old student's access to that patient's open cases |
| BR-04 | An approved diagnosis is locked. Only its plan items can be referred, and each item can be in only one open referral at a time |
| BR-05 | A referred patient may be assigned only to a student enrolled, in the current term, in a course that runs in the receiving clinic |
| BR-06 | Steps of a case are approved in their template order unless the course allows any order (configurable) |
| BR-07 | A supervisor approves only within their scope (assigned courses or clinics), and never their own work |
| BR-08 | When the last step of a case is approved and the case is confirmed complete, the case is marked done, its referral is completed, the plan item is marked done, and the referring clinic is notified |
| BR-09 | A case counts toward a work card's required number only when it is complete. Work done on a transferred patient stays credited to the student who did each step |
| BR-10 | A lab work card needs the course's required number of lab cases (default 5, from F2) |
| BR-11 | One round per clinic, round type (morning / afternoon) and day. After submission, only the super admin can change it |
| BR-12 | A failed check opens a ticket. A ticket in a blocking category takes the chair out of service; out-of-service chairs cannot be given to students |
| BR-13 | Nothing is deleted: records are deactivated, and approved records are versioned (SYS-05, SYS-10) |
| BR-14 | Patients pay no fees, and the system records no payments |

## 7. User stories and acceptance criteria

There are 24 user stories, grouped by the sprint that delivers them. Each story is done when every acceptance criterion passes, together with the definition of done in the Project Plan.

### Sprint 1 — Foundation

| ID | Story | Acceptance criteria | Covers |
| --- | --- | --- | --- |
| US-01 | As the super admin, I want to set up a clinic with its chairs and sessions, so that the system matches the real faculty | Create clinic 5 (treatment, 12 chairs) and 5 sessions. The chairs appear in distribution and rounds. Deactivating a chair hides it from new distributions but keeps its history | DB-04 |
| US-02 | As the super admin, I want to define a course with its case requirements and steps, so that work cards follow the course rules | Create a course with 2 case types, a required count for each, 4 steps and a 0–100 grading type. A student enrolled in it gets a work card showing 0 of the required count | DB-04, DB-05 |
| US-03 | As the super admin, I want to import students from Excel, so that I don't type them by hand | A file with 200 rows imports in under 1 minute. Rows with a missing university ID or an unknown course are listed with the reason and not imported. Importing the same file again creates no duplicates | DB-03 |
| US-04 | As any user, I want to log in once and land in my own interface | A student lands in the Student interface, a supervisor in the Supervisor interface, a technician in Maintenance. A user with two roles chooses one. Every screen is in Arabic, right to left, by default | ST-01, SYS-01, SYS-07 |

### Sprint 2 — Labs

| ID | Story | Acceptance criteria | Covers |
| --- | --- | --- | --- |
| US-05 | As a student, I want to add a lab case to my lab work card | The case type is chosen from the course's list, and the exercise or model number is entered. The case shows the course's steps, all pending | ST-10 |
| US-06 | As a student, I want to finish a lab step and send it with photos | At least 1 photo is required when the step template says so. Upload works on a slow network and retries after loss. The step shows as "Waiting for approval" | ST-09, ST-11 |
| US-07 | As a supervisor, I want to grade lab work from photos on my phone | The queue lists waiting steps for my courses only. An approval with a grade takes 2 taps after opening. A return needs a comment. The student is notified within 1 minute | SV-07, SYS-03 |
| US-08 | As a student, I want to see my progress on each work card | The card shows each case type as done / required, plus the grades. A case counts as done only when its last step is approved | ST-07, ST-08 |

### Sprint 3 — Patients and diagnosis

| ID | Story | Acceptance criteria | Covers |
| --- | --- | --- | --- |
| US-09 | As the super admin, I want to register a patient once | The file number is generated and unique. A matching national ID blocks saving; a matching name plus phone shows a warning. The patient can be sent to a diagnosis clinic's queue | DB-08, DB-09 |
| US-10 | As a supervisor, I want to give a waiting patient to a student for diagnosis | The queue shows the patients waiting in my diagnosis clinics. After assignment, the patient appears in the student's "My patients" list | SV-03 |
| US-11 | As a student, I want to fill the diagnosis on my phone | All F1 sections are present. Tapping a tooth opens its codes, and several codes per tooth are allowed. Index scores accept only the configured range. A draft survives closing the app | ST-05 |
| US-12 | As a student, I want the patient's medical risks shown clearly | Any medical history item flagged as an alert (for example anticoagulants or allergy) shows as a red banner on every screen of that patient | ST-03, ST-04 |
| US-13 | As a supervisor, I want to approve or return a diagnosis | Approval locks it. A return needs a comment and sends it back to the student as editable. Both actions are logged with name and time | SV-04, SYS-05 |
| US-14 | As a supervisor, I want to refer plan items to departments | Only items of an approved diagnosis can be referred, and each item can be in only one open referral. The receiving clinic sees the referral at once | SV-05 |

### Sprint 4 — Clinical cards and maintenance

| ID | Story | Acceptance criteria | Covers |
| --- | --- | --- | --- |
| US-15 | As a supervisor in a department clinic, I want to accept a referral and assign the patient to a student | Only eligible students are offered (enrolled in a course run in this clinic this term), with their progress shown. The case appears on the student's clinical work card with the patient, tooth and case type filled in | SV-06 |
| US-16 | As a supervisor, I want closing the last step to close the referral | Approving the last step and confirming completion marks the case done, the referral completed and the plan item done. The referring clinic is notified | SV-08 |
| US-17 | As a supervisor, I want to move a patient to another student | The open cases move to the new student's card, and completed steps stay credited to the old student. The reason and the date are recorded | SV-09 |
| US-18 | As a technician, I want to do the morning round quickly | Marking 20 chairs "All OK" takes under 1 minute. Only one round per clinic, round type and day is allowed. A fault requires a note | MT-03 |
| US-19 | As a technician, I want a fault to become a ticket that I follow until it is repaired | The ticket is created from the failed check. A blocking category takes the chair out of service. Resolving it puts the chair back and records who fixed it and how | MT-04, MT-05, MT-06 |
| US-20 | As the super admin, I want to distribute students to chairs | The suggestion fills each chair with up to the course's students per chair and never uses out-of-service chairs. Changes are saved per date and session | DB-12 |
| US-21 | As a supervisor, I want to mark attendance on the chair grid | Each student in each session is marked present or absent. The daily clinic report (F8) shows it | SV-11 |

### Sprint 5 — Reports and hardening

| ID | Story | Acceptance criteria | Covers |
| --- | --- | --- | --- |
| US-22 | As management, I want the daily reports without paper | F6/F18, F8 and F9 reports are available per clinic and date, as on-screen tables and as Excel and PDF exports | DB-15 |
| US-23 | As a supervisor, I want to find patients who still need a given treatment | A search by treatment type returns patients with an approved, not yet referred plan item of that type, oldest first | SV-10 |
| US-24 | As any user, I want to be told when something needs me | Every event in SYS-03 creates an in-app notification. Tapping it opens the item. The unread count shows on the home screen | SYS-03, ST-14, SV-14 |

## 8. Non-functional requirements

Each requirement has a number that can be tested. Privacy and audit are mandatory because the system holds medical records.

| ID | Area | Requirement |
| --- | --- | --- |
| NFR-01 | Performance | API responses within 1 second for 95% of requests; patient search under 2 seconds; app start to home screen under 3 seconds on a mid-range phone |
| NFR-02 | Capacity | 300 users at the same time; 20,000 patients and 500,000 photos without redesign |
| NFR-03 | Availability | 99% during clinic hours (Sunday–Thursday, 8:00–16:30 Damascus time); maintenance outside those hours |
| NFR-04 | Backup | Daily encrypted database backup and daily photo storage backup, kept 30 days; a restore tested before go-live |
| NFR-05 | Security | HTTPS only; passwords hashed with Django's default (PBKDF2 or Argon2); tokens expire (access token 15 minutes, refresh token 30 days); permissions checked on the server |
| NFR-06 | Privacy | Students see only their own patients; photos are not saved to the phone's gallery after upload; the dashboard is not reachable by students |
| NFR-07 | Audit | Every approval, change and login is logged and kept for at least 5 years |
| NFR-08 | Usability | A normal step approval takes 2 taps; a full round of 20 chairs under 1 minute when all are OK; touch targets at least 48 px |
| NFR-09 | Localization | Arabic (right to left) and English; dates shown day/month/year; the language can be switched at any time |
| NFR-10 | Network | The app keeps working on a slow connection. Drafts are saved on the phone, and photo uploads queue and retry |
| NFR-11 | Compatibility | Android 8.0 and later; iOS 15 and later; current desktop browsers for the dashboard |
| NFR-12 | Maintainability | One repository; a code style enforced by linters; backend test coverage of at least 70% for the business rules; a CLAUDE.md that documents the conventions |
| NFR-13 | Configurability | Every item in section 4 can be changed in the dashboard without code changes or an app release |
| NFR-14 | Store compliance | Demo accounts for the App Store and Google Play reviewers; a privacy policy page; a permission prompt for camera access that states the reason |

## 9. External interfaces

The system talks to four things outside itself: the mobile app (through its API), Excel files, the push notification services, and file storage. There is no live connection to the academic system or the imaging software.

| Interface | Direction | Format and rules |
| --- | --- | --- |
| REST API | App ↔ backend | JSON over HTTPS under `/api/v1/`; JWT in the `Authorization` header; paginated lists; errors as `{code, message, details}` with messages in the user's language; OpenAPI schema at `/api/v1/schema/` |
| Excel import | File → backend | .xlsx templates downloadable from the dashboard. **Students:** university ID, full name (AR), full name (EN), mobile, study year. **Enrollments:** university ID, course code, term. Validated row by row, with a report of errors |
| Excel and PDF export | Backend → file | Reports and record printouts (DB-15, SYS-08) |
| Push notifications | Backend → phone | Firebase Cloud Messaging for Android and Apple Push Notification service for iOS. If push fails, the in-app notification list still holds every event |
| File storage | Backend ↔ storage | S3-compatible object storage; private files served through short-lived signed links; thumbnails created on upload |
| X-ray images | User → backend | Uploaded as image files (JPEG or PNG) exported from the imaging software. A direct link to that software is not in scope |
