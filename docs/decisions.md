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

## 2026-11-21 — Accounts module details (P0.3)

**Decision.**

1. `AUTH_USER_MODEL` is `accounts.User`. `User` inherits `core.BaseModel` (abstract, so no
   migration dependency on core), `AbstractBaseUser` and `PermissionsMixin`. `accounts.0001`
   depends only on `auth`; `core.0001` runs after it. A developer database migrated before
   P0.3 must be recreated with `make clean` then `make migrate`.
2. Usernames are stored in lower case and matched without case or surrounding spaces, because
   phone keyboards capitalise the first letter. A username is never reused, even after the
   user is deactivated.
3. The API authenticates with JWT bearer tokens only; session authentication is removed from
   the API (the dashboard keeps Django sessions, P0.4). A request without credentials now gets
   401 `not_authenticated` instead of 403. The public schema and docs ignore any token sent.
4. The `X-Active-Role` check and the first-login gate run in the DRF authentication class
   (`apps/accounts/api/authentication.py`), not in a Django middleware: the JWT user is only
   known once DRF authenticates the request inside the view. A view stays open during the
   gate by setting `password_change_allowed = True` (only `/me/` and `/me/password/`). Login,
   refresh and logout take no authentication, so they work during the gate too.
5. The active role is the `X-Active-Role` header, or the user's only role. A user with several
   roles and no header has no active role, and endpoints that check a role answer
   `active_role_required` (403). The permission classes check the active role, not any role the
   user holds, so each interface reaches only its own endpoints.
6. The permission classes (`IsStudent`, …, `HasAnyRole`) and `request_actor` live in
   `apps.accounts.api`, not in core as section 5 lists, because they read the roles that
   accounts owns and core may not import accounts. Other modules' `api/` import them.
7. Status codes: `invalid_credentials` and `token_invalid` are 400, not 401, so the app's
   "access token expired → refresh" handling never fires on a wrong password; `account_locked`,
   `no_role`, `role_not_held`, `active_role_required` and `password_change_required` are 403.
8. Lockout (SYS-01): the 5th failure in a row locks the account for 15 minutes and already
   answers `account_locked`. While locked, the right password is refused and attempts are not
   counted. When a lock runs out the count starts again. Unknown and deactivated users get
   `invalid_credentials` after the same hashing time as a real user. A user with no role cannot
   log in (`no_role`).
9. Changing the password revokes every token issued before (simplejwt `CHECK_REVOKE_TOKEN` for
   access tokens, the blacklist for refresh tokens) and returns a new pair. Resetting a
   password gives a new temporary password, unlocks the account and revokes every token.
10. `JWT_SIGNING_KEY` is a new secret, required in staging and production; in development it
    falls back to `DJANGO_SECRET_KEY`.
11. The rate limits are DRF throttles kept in the Redis cache. A root `conftest.py` empties the
    cache before each test so limits never carry over between tests.
12. User administration services refuse unless the actor is acting as `super_admin` and still
    holds it. The administrator cannot remove their own `super_admin` role. `createsuperuser`
    also gives the `super_admin` role.
13. A push token registered by another user moves to the user who registers it now (the phone
    changed hands).
14. `create_demo_users` runs only where `DEMO_USERS_ALLOWED` is on (development settings). Demo
    users are `demo_<role>` with the password `Spu-Demo-2026` unless `--password` is given.
15. Assigning a department to a user (DB-02) waits for the `Department` table of the setup
    module (P1.x); it is added to `CreateUser` and the user screens once that table exists.

**Reason.** Follow the security design (section 8) on every endpoint while keeping JWT
authentication inside DRF; give the app stable codes for each login state; keep core free of
accounts so the dependency between them runs one way.
