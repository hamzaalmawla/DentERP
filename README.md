# SPU Dental Clinic System

A software system that replaces the paper forms used in the clinics and labs of the **Faculty of Dentistry at Syrian Private University (SPU)**.

Today, patient diagnosis, referrals, student work cards, chair schedules and chair maintenance are all recorded on paper (SPU/AQM forms M-09-Den-F1 to F18). There is no patient archive: a patient is often treated for one tooth and the rest of the treatment plan is lost. This project moves the whole flow into one system, so every patient has a complete record, every step a student performs is approved and graded by a supervisor, and the faculty has live reports.

## Project documents

| Document | PDF | Word | Source |
| --- | --- | --- | --- |
| Software Requirements Specification (SRS) | [SPU-Dental-SRS.pdf](docs/SPU-Dental-SRS.pdf) | [.docx](docs/SPU-Dental-SRS.docx) | [SRS.md](docs/SRS.md) |
| System Design Document | [SPU-Dental-System-Design.pdf](docs/SPU-Dental-System-Design.pdf) | [.docx](docs/SPU-Dental-System-Design.docx) | [system-design.md](docs/system-design.md) |

The Markdown files are the working source. The PDF and Word files are generated from them (see [Rebuilding the documents](#rebuilding-the-documents)).

## What the system does

- **Patients and diagnosis** — patient registration, the full diagnosis form (medical history, FDI dental chart, soft tissue, periodontal indices, X-rays, treatment plan).
- **Referrals** — plan items are referred to department clinics and assigned to eligible students.
- **Clinical and lab work cards** — each case is recorded step by step with photos; supervisors approve and grade every step.
- **Chairs and sessions** — distribution of students to chairs and sessions, attendance, daily clinic and lab reports.
- **Maintenance** — morning and afternoon chair rounds, fault tickets, taking chairs out of and back into service.
- **Reports and audit** — statistics for management, a case finder for supervisors, and a full audit log of every change.

Everything the clinic may change (clinics, chairs, sessions, courses, steps, grading, lists) is configured from the dashboard, not hard-coded.

## Users and interfaces

| Interface | Users |
| --- | --- |
| Mobile app — Student | Dental students: diagnosis, treatment steps with photos, work cards, schedule |
| Mobile app — Supervisor | Clinical supervisors: approve and grade, refer, assign patients, attendance |
| Mobile app — Maintenance | Maintenance technicians: chair rounds and fault tickets |
| Web dashboard | Super admin (manages the system, registers patients) and management (dean, department heads; read-only) |

The app is Arabic first (right to left), with English as a second language.

## Architecture

- **Backend:** Python 3.12, Django 5.2 LTS, Django REST Framework, PostgreSQL 16, Celery + Redis
- **Web dashboard:** Django Unfold, inside the same Django project
- **Mobile app:** Flutter (iOS and Android), one app with three role-based interfaces
- **Storage:** S3-compatible object storage for clinical photos and X-rays
- **Deployment:** Docker Compose on a cloud server with HTTPS; CI/CD with GitHub Actions

Full details are in the [System Design Document](docs/SPU-Dental-System-Design.pdf).

## Timeline

| Phase | Dates |
| --- | --- |
| Planning, requirements and design | 24 Oct – 20 Nov 2026 |
| Dean sign-off | 21 Nov 2026 |
| Development (5 one-week sprints) | 21 Nov – 25 Dec 2026 |
| User acceptance testing | 26 Dec 2026 – 6 Jan 2027 |
| Production deployment and training | 7 – 15 Jan 2027 |
| Handover | 18 Jan 2027 |

## Repository layout

```
docs/      SRS and System Design (Markdown source, PDF, Word)
tools/     scripts that generate the PDF and Word documents
```

The `backend/`, `mobile/` and `deploy/` folders will be added during development, as described in section 4 of the System Design.

## Rebuilding the documents

Requires Python with `python-docx` and Microsoft Word on Windows.

```bash
pip install python-docx
python tools/build_docs.py
powershell -ExecutionPolicy Bypass -File tools/export_pdf.ps1
```

## Team

- Hamza Almawla
- Zeannab Alhommsi

Software Engineering, Syrian Private University — 2026/2027
