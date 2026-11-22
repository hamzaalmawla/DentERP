# SPU Dental Clinic System

A software system that replaces the paper forms used in the clinics and labs of the **Faculty of Dentistry at Syrian Private University (SPU)**.

Today, patient diagnosis, referrals, student work cards, chair schedules and chair maintenance are all recorded on paper (SPU/AQM forms M-09-Den-F1 to F18). There is no patient archive: a patient is often treated for one tooth and the rest of the treatment plan is lost. This project moves the whole flow into one system, so every patient has a complete record, every step a student performs is approved and graded by a supervisor, and the faculty has live reports.

## Status

What is built, prompt by prompt ([build-prompts.md](docs/build-prompts.md)). The API endpoints
of modules not built yet already exist and answer **501 `not_implemented`**; the contract each
module will honour is in [docs/contracts.md](docs/contracts.md).

| Prompt | What | State |
| --- | --- | --- |
| P0.1 | Repository, Docker, CI, conventions | Done |
| P0.2 | `core`: base model, soft delete, audit log, history, error format, shared ports | Done |
| P0.3 | `accounts`: login (JWT), roles, lockout, password change, push tokens | Done |
| P0.4 | Web dashboard shell (Unfold, Arabic RTL), users, roles, audit log viewer | Done |
| P0.5 | Skeletons and facades of the 11 other modules, API outline, import rule | Done |
| P1.1 – P1.12 | Backend modules and dashboard screens (setup and academics first, then tracks A and B) | Not started |
| P2.x | Flutter app (`mobile/`) | Not started |

## Running everything

Everything runs in Docker; only **Docker with Docker Compose** and **make** are needed on your
machine. Run every command from the repository root. `make help` lists them all.

### First run

```bash
make up
```

This creates `deploy/.env` from `deploy/.env.example` (change values there, never in the
example), builds the backend image, then starts PostgreSQL 18, Redis 8, Garage storage (and
creates its bucket), applies the migrations, compiles the Arabic translations, and starts the
web server, the Celery worker and Celery beat. It returns when the web server is healthy.

Then create users to log in with:

```bash
docker compose -f deploy/docker-compose.yml run --rm web python manage.py create_demo_users
```

This creates one user per role, `demo_super_admin`, `demo_management`, `demo_reception`,
`demo_supervisor`, `demo_student` and `demo_technician`, all with the password
`Spu-Demo-2026`. (For your own administrator: `make shell` is a Django shell, or run
`python manage.py createsuperuser` the same way as above.)

### What is running

| What | Where |
| --- | --- |
| Web dashboard (super admin, management, reception, supervisor) | http://localhost:8000/dashboard/ |
| REST API for the mobile app | http://localhost:8000/api/v1/ |
| API documentation (Swagger) and schema | http://localhost:8000/api/v1/docs/ · http://localhost:8000/api/v1/schema/ |
| Health check (200 when the database and Redis are up) | http://localhost:8000/health/ |
| PostgreSQL | `localhost:5432` (user, password and database `spu_dental`) |
| Garage S3 storage | http://localhost:3900 |

Ports can be changed with `WEB_PORT`, `DB_PORT` and `STORAGE_PORT` in your shell. The code in
`backend/` is mounted into the containers and the server reloads on save.

To try the API: log in with `POST /api/v1/auth/login/` (`{"username": "demo_student",
"password": "Spu-Demo-2026"}`), then press **Authorize** in the docs page and paste the
`access` token. A user with several roles also sends the `X-Active-Role` header.

### Everyday commands

| Command | What it does |
| --- | --- |
| `make up` / `make down` | Start (rebuilding if needed) / stop every service; data is kept |
| `make ps` / `make logs` | Service health / follow the logs |
| `make test` | Run all backend tests against PostgreSQL and Redis; `make test ARGS="-k lookups -x"` for some |
| `make lint` / `make format` | Check / fix code style (ruff) |
| `make makemigrations` / `make migrate` | Create migrations after a model change / apply them (and compile translations) |
| `make makemessages` | Collect new texts into `backend/locale/ar/LC_MESSAGES/django.po`; then write the Arabic `msgstr` and run `make migrate` (or `make compilemessages`) |
| `make schema` | Build and validate the OpenAPI schema into `backend/schema.yml` |
| `make shell` | Django shell |
| `make clean` | Stop everything and **delete all data** (database, storage) |

Before you push, the same checks as CI must pass: `make lint`, `make test`, `make schema`, and
`makemigrations --check` (CI runs all of them on every pull request,
`.github/workflows/backend-ci.yml`).

### Without Docker

Needs Python 3.13, [uv](https://docs.astral.sh/uv/), PostgreSQL, Redis and GNU gettext
(`msgfmt`, for the Arabic translations) on your machine.

```bash
cd backend
uv sync
set -a && . ../deploy/.env.example && set +a
export POSTGRES_HOST=localhost REDIS_URL=redis://localhost:6379/0 REDIS_CACHE_URL=redis://localhost:6379/1
unset DJANGO_SETTINGS_MODULE
uv run python manage.py compilemessages --ignore ".venv/*"
uv run pytest
```

`DJANGO_SETTINGS_MODULE` is unset so pytest uses `config.settings.test`. To run the server
instead, keep `config.settings.dev` and run `uv run python manage.py migrate` then
`uv run python manage.py runserver`.

### When something goes wrong

- **A migration error after pulling** (for example a table that changed before release): the
  development database is disposable, so `make clean` then `make up`.
- **Arabic texts show in English**: run `make migrate` (it compiles the translations), and check
  the entry in `django.po` is not marked `#, fuzzy`.
- **Port already in use**: stop the other program, or start with `WEB_PORT=8001 make up`.
- **Tests fail with "Model class … isn't in an application in INSTALLED_APPS"** when run
  without Docker: `DJANGO_SETTINGS_MODULE` is still set to the dev settings; unset it.

## Project documents

| Document | Source |
| --- | --- |
| Software Requirements Specification (SRS) | [SRS.md](docs/SRS.md) · [PDF](docs/SPU-Dental-SRS.pdf) · [Word](docs/SPU-Dental-SRS.docx) |
| System Design Document | [system-design.md](docs/system-design.md) · [PDF](docs/SPU-Dental-System-Design.pdf) · [Word](docs/SPU-Dental-System-Design.docx) |
| Release 1 build prompts, in order | [build-prompts.md](docs/build-prompts.md) |
| Module contracts: facades, DTOs, track owners, API outline | [contracts.md](docs/contracts.md) |
| Decisions that change the design | [decisions.md](docs/decisions.md) |
| Conventions every Claude Code session follows | [CLAUDE.md](CLAUDE.md) |
| Graduation report, part 1 (English) | [part1-en.md](docs/report/part1-en.md) · [PDF](docs/report/SPU-Dental-Report-Part1-EN.pdf) · [Word](docs/report/SPU-Dental-Report-Part1-EN.docx) |
| Graduation report, part 1 (Arabic) | [part1-ar.md](docs/report/part1-ar.md) · [PDF](docs/report/SPU-Dental-Report-Part1-AR.pdf) · [Word](docs/report/SPU-Dental-Report-Part1-AR.docx) |

The Markdown files are the working source; the PDF and Word files are generated from them (see
[Rebuilding the documents](#rebuilding-the-documents)). The diagrams are in
[docs/figures](docs/figures).

## What the system does

- **Patients and diagnosis**: registration, the full diagnosis form (medical history, FDI dental chart, soft tissue, periodontal indices, X-rays, treatment plan).
- **Referrals**: plan items are referred to department clinics and assigned to eligible students.
- **Clinical work cards**: each case is recorded step by step with photos; supervisors approve and grade every step.
- **Chairs and sessions**: distribution of students to chairs and sessions, attendance, daily clinic reports.
- **Maintenance**: morning and afternoon chair rounds, fault tickets, taking chairs out of and back into service.
- **Reports and audit**: figures for management and a full audit log of every change.

Everything the clinic may change (clinics, chairs, sessions, courses, steps, grading, lists) is
configured from the dashboard, not hard-coded. Release 1 covers the Diagnosis and Endodontics
clinics; labs and the other departments come later as data
([build-prompts.md](docs/build-prompts.md), section 1).

| Interface | Users |
| --- | --- |
| Mobile app: Student | Diagnosis, treatment steps with photos, work cards, schedule |
| Mobile app: Supervisor | Approve and grade, refer, assign patients, attendance |
| Mobile app: Maintenance | Chair rounds and fault tickets |
| Web dashboard | Super admin, reception, supervisors (their own clinics) and management (read-only) |

The app and the dashboard are Arabic first (right to left), with English as a second language.

## Architecture

- **Backend:** Python 3.13, Django 5.2 LTS, Django REST Framework, PostgreSQL 18, Celery + Redis 8, S3-compatible storage (Garage). A modular monolith: 13 modules, each with ports and adapters inside; modules talk only through each other's facades ([contracts.md](docs/contracts.md)).
- **Web dashboard:** Django Unfold, inside the same Django project, at `/dashboard/`.
- **Mobile app:** Flutter (iOS and Android), one app with three role-based interfaces, MVVM.
- **Deployment:** Docker Compose on a cloud server with HTTPS; CI/CD with GitHub Actions.

## Timeline

| Phase | Dates |
| --- | --- |
| Planning, requirements and design | 24 Oct – 20 Nov 2026 |
| Dean sign-off | 21 Nov 2026 |
| Development: backend first, then mobile, then integration, in two parallel tracks; then hardening | 21 Nov – 25 Dec 2026 |
| User acceptance testing | 26 Dec 2026 – 6 Jan 2027 |
| Production deployment and training | 7 – 15 Jan 2027 |
| Handover | 18 Jan 2027 |

## Repository layout

```
CLAUDE.md          conventions every Claude Code session follows
Makefile           development commands (make help)
backend/           Django project: API, dashboard, Celery jobs
  config/          settings (base, dev, test, staging, prod), urls, celery, wsgi, asgi, /health/
  apps/            one folder per module, layout in System Design section 5
    core/          base model, soft delete, audit log, error format, shared ports
                   (its README is the template every module follows)
    accounts/      users, roles, login, the dashboard shell and its role map
    setup/ academics/ patients/ diagnosis/ referrals/ workcards/ media/
    scheduling/ maintenance/ notifications/ reports/
                   one module each: domain/, application/ (ports, dtos, facade), api/,
                   infrastructure/, testing/ (fakes), tests/, admin.py, container.py
  locale/ar/       Arabic translations
  tests/           project-level tests: module layout, facade contracts, API outline,
                   the import rule; testapp/ exercises core (installed only in tests)
  pyproject.toml   exact library versions (locked in uv.lock)
  Dockerfile       dev and prod images
deploy/            docker-compose.yml for development, .env.example, Garage storage config
docs/              SRS, design, contracts, decisions, build prompts, report, figures
tools/             scripts that generate the PDF and Word documents and the diagrams
.github/workflows/ CI: backend-ci (ruff, migrations check, translations, schema, pytest)
```

The `mobile/` folder and the production compose file are added during development, as described
in section 4 of the System Design.

## Keeping this README up to date

This file is the one place that says how to run the project. **Every build prompt updates it
in the same pull request** when it adds or changes anything here: a service, a port, a command
or `make` target, an environment variable, a seed or demo command, a URL, a new folder, or the
state of a prompt in the [Status](#status) table. The standard footer of
[build-prompts.md](docs/build-prompts.md) and [CLAUDE.md](CLAUDE.md) both say so.

## Rebuilding the documents

Requires Python with `python-docx` and Microsoft Word on Windows.

```bash
pip install python-docx
python tools/figures/make_figures.py
python tools/build_docs.py
powershell -ExecutionPolicy Bypass -File tools/export_pdf.ps1
```

## Team

Supervised by Dr. Mouhib Alnoukari and Amer Khourshed.


- Hamza Almawla
- Zeannab Alhommsi

Software Engineering, Syrian Private University — 2026/2027
