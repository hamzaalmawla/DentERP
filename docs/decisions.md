# Decisions

Every decision that changes the [System Design](system-design.md) or the [SRS](SRS.md), newest
last. Each entry gives the date, the decision and the reason.

## 2026-11-20 — Release 1 scope

**Decision.** Release 1 is limited to the Diagnosis and Endodontics clinics, the chairs system
(distribution, attendance, maintenance) on mobile, login and roles, and the main dashboard
screens. Labs and other departments are deferred. Clinics stay configuration data.

**Reason.** The development window (21 Nov – 25 Dec 2026) is too short to build and test every
clinic and lab well. Building two clinics end to end on a complete base proves the whole flow;
the other departments are then added as data, not code. The full scope is in
[build-prompts.md](build-prompts.md), section 1.

## 2026-11-20 — Development environment details (P0.1)

**Decision.**

1. Python dependencies are managed with [uv](https://docs.astral.sh/uv/): exact pins in
   `backend/pyproject.toml` and a committed `backend/uv.lock`. The Docker image and CI install
   from the lock file.
2. Garage is pinned to v2.5.0. A one-off `storage-init` service creates the node layout, the
   access key and the bucket through Garage's admin API on every `docker compose up`; it is safe
   to run again.
3. A `test` settings module is added next to dev, staging and prod (fast password hashing,
   in-memory file storage, Celery tasks run in-process).
4. Production sets HSTS `includeSubDomains` (it covers only subdomains of the system's own host)
   and does not request HSTS preload, which would bind the university's whole domain. The Django
   check `security.W021` is silenced for that reason.
5. `django.contrib.admin`, Unfold, simple-history and import-export are installed as libraries
   but added to `INSTALLED_APPS` only by the prompts that use them (P0.2, P0.4 and later). No
   migration that refers to the user model exists yet, so P0.3 can still set `AUTH_USER_MODEL`.
6. `sentry-sdk` is not added yet; it is added with the staging deployment.

**Reason.** Reproducible installs on both developers' machines and in CI; a storage service that
works with one command; settings that fail fast when a secret is missing.

## 2026-11-20 — Core module details (P0.2)

**Decision.**

1. Domain messages are marked with `_` from `apps.core.domain.i18n`, a no-op marker that
   `makemessages` collects, so `domain/` stays plain Python. The API exception handler
   translates the message into the request's language. Placeholders use `%(name)s` and are filled
   from the error's `details`.
2. The HTTP status of a `DomainError` is chosen by its subclass: `NotFoundError` 404,
   `AccessDeniedError` 403, `ConflictError` 409, any other `DomainError` 400. Django's `Http404`
   returns the same `not_found` message as `NotFoundError` and never names the model.
3. `AuditLog` inherits `BaseModel` like every table, and its rows are append-only: `save()` on an
   existing row raises and `delete()` raises as for every model.
4. `created_by`, `updated_by`, the history user and the audit user come from one place:
   `CurrentRequestMiddleware` keeps the request (the user is read at save time, so JWT logins that
   DRF authenticates inside the view are seen), and `acting_as(user_id)` sets the user for Celery
   tasks, commands and imports. `updated_by` is empty when the system made the last change.
5. The client IP comes from `REMOTE_ADDR`, or from `X-Forwarded-For` behind `DJANGO_NUM_PROXIES`
   proxies (0 in development, 1 for nginx in staging and production), the same rule DRF's
   throttles use.
6. `core.0001` and the test app's migration refer to `settings.AUTH_USER_MODEL` as a swappable
   dependency, so P0.3 can still set `AUTH_USER_MODEL` to the custom user. A developer database
   migrated before P0.3 must be recreated with `make clean` then `make migrate` (nothing is
   deployed yet).
7. Until P0.3 adds JWT, the API authenticates with the Django session only; Basic auth is off.
   The API renders JSON only. Every endpoint requires a logged-in user unless it says otherwise;
   the schema and docs at `/api/v1/schema/` and `/api/v1/docs/` are public (SYS-09).
8. Tests of core use `tests/testapp`, an app installed only by `config.settings.test`, with its
   own committed migration.
9. Ruff's `RUF012` (mutable class attributes) is turned off: Django's `Meta`, serializer and admin
   options are lists by design.

**Reason.** Keep the domain free of Django while every message is still translatable; give the
mobile app one stable error format; record the acting user the same way in the API, the dashboard
and background jobs; and test core the way real modules will use it.
