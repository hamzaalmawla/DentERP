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
