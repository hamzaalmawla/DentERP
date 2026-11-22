# CLAUDE.md

Rules for every Claude Code session in this repository. They come from section 13 of
[docs/system-design.md](docs/system-design.md) ("Conventions for Claude Code"). If a rule here
and the design disagree, stop and ask; record any change to the design in
[docs/decisions.md](docs/decisions.md).

## Project

The SPU Dental Clinic System replaces the paper forms of the Faculty of Dentistry at Syrian
Private University. Requirements: [docs/SRS.md](docs/SRS.md). Design:
[docs/system-design.md](docs/system-design.md). Build prompts, in order:
[docs/build-prompts.md](docs/build-prompts.md).

- `backend/` — Django 5.2 on Python 3.13: REST API, Unfold dashboard, Celery jobs
- `mobile/` — Flutter app (added in phase 2)
- `deploy/` — Docker Compose files, Garage storage config, `.env.example`
- `docs/` — SRS, design, report, decisions log, build prompts

## Release 1 scope

Release 1 builds the base of the system and two clinics only: Diagnosis and Endodontics, plus
login and roles, the chairs system on mobile (distribution, attendance, maintenance) and the main
dashboard screens. Labs, the other department clinics and the items listed as deferred are not
built. The full list is in [docs/build-prompts.md](docs/build-prompts.md), section 1. Clinics,
departments, courses and steps are configuration data: never write their names in code; use the
clinic `type` and the configuration tables.

## Commands

Run from the repository root. Everything runs in Docker (`deploy/docker-compose.yml`).

| Command | What it does |
| --- | --- |
| `make up` | Build and start every service; web on http://localhost:8000, `/health/` |
| `make down` | Stop the services (data is kept); `make clean` also deletes the data |
| `make test ARGS="..."` | pytest against PostgreSQL and Redis |
| `make lint` / `make format` | ruff check and format |
| `make makemigrations` / `make migrate` | Create / apply migrations (migrate also compiles translations) |
| `make makemessages` | Collect strings into `backend/locale/ar/LC_MESSAGES/django.po` |
| `make schema` | Build and validate the OpenAPI schema |

Without Docker: `cd backend && uv sync && uv run pytest` with PostgreSQL and Redis running
locally (see `deploy/.env.example` for the variables). CI (`.github/workflows/backend-ci.yml`)
runs ruff, `makemigrations --check`, `compilemessages`, the schema build and pytest.

Settings: `config.settings.dev` (default), `test` (pytest), `staging`, `prod`. Every secret comes
from an environment variable; add each new variable to `deploy/.env.example` (a test checks it).
Library versions are pinned exactly in `backend/pyproject.toml` and locked in `backend/uv.lock`.

## Backend rules

- Every module follows the layout in section 5: `domain/`, `application/`, `infrastructure/`,
  `api/`, `admin.py`, `models.py`, `container.py`. Ports and adapters is the only architectural
  pattern; do not add others.
- Every model inherits `core.BaseModel`. Records are never hard-deleted; use `is_active=False`.
- Business rules and status changes live only in `domain/` and in the application services.
  Views, serializers, models and admin actions contain no business logic; they call a service.
- One class, one responsibility: one service per use case, one repository per aggregate, one
  adapter per outside service.
- Services receive their ports through the constructor (built in `container.py`) and return DTOs
  (frozen dataclasses), never Django model instances.
- A module never imports another module's `models.py` or `infrastructure/`; it calls that
  module's application services.
- Reads that depend on the user go through query services that apply the scope filter
  (section 8).
- Errors: raise `DomainError(code, message)`; one exception handler turns it into the API error
  format.
- Every user-facing string is wrapped in `gettext`, with Arabic in `locale/ar`.
- Every service gets pytest tests for the allowed path, each guard failure, and the permission
  scope, using in-memory fakes of its ports. Repositories get separate tests against PostgreSQL.
- Migrations are committed. Migrations are never edited after they are merged.

## Mobile rules

- Feature-first folders (`features/<role>/<feature>/`), each with `model/`, `viewmodel/` and
  `view/` (MVVM).
- No API calls or business logic in widgets; views read their ViewModel only, and ViewModels
  reach the API only through repositories.
- Every text comes from the ARB files in Arabic and English. No hard-coded strings.
- Use `EdgeInsetsDirectional` and `AlignmentDirectional` everywhere, so right-to-left layout
  works.
- API error codes are mapped to localized messages in one place.
- After changing the API, regenerate the models from the OpenAPI schema or update the freezed
  models to match it.

## Process rules

- Work is split into small tasks, one per user story or module, never the whole project in one
  step. One branch and one pull request per task. The pull request description lists the US and
  requirement IDs and how they were tested.
- Before merging, a developer reviews the diff, runs it on staging, and checks it in Arabic.
- `docs/decisions.md` records every decision that changes this design, with its date and reason.
- `README.md` says how to run everything. Every task updates it in the same pull request: its
  row in the Status table, and "Running everything" for any service, port, command, `make`
  target, environment variable, seed command, URL or folder it adds or changes.
- Modules call each other only through their facades; [docs/contracts.md](docs/contracts.md)
  lists them and which track owns each module. A facade change updates its Protocol, service,
  fake and contracts.md together (`tests/test_contracts.py` checks they match).
