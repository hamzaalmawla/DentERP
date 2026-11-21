# core

The base every other module builds on (SYS-02, SYS-04, SYS-09, SYS-10): `BaseModel` with soft
delete, the audit log, full history, the error format, the API conventions, the shared ports
and the scope helper. Design: [system-design.md](../../../docs/system-design.md) sections 5–8.

## Module layout (copy this for every module)

Every module in `backend/apps/` has the same folders. Ports and adapters is the only pattern
(design section 5): business rules in the centre, Django at the edges.

```
apps/<module>/
├── domain/            # Business rules, state machines, value objects. Plain Python only.
│                      # Messages are marked with `from apps.core.domain.i18n import _`.
├── application/
│   ├── ports.py       # typing.Protocol interfaces the services need (repositories, …)
│   ├── dtos.py        # Frozen dataclasses returned to callers; never model instances
│   ├── services.py    # One class per use case: __init__(ports) + execute(command) -> DTO
│   └── queries.py     # Query services: reads that depend on the user go through the scope
├── infrastructure/    # Adapters that implement the ports: ORM repositories, S3, FCM, …
├── api/               # DRF serializers, views and urls.py; a view calls one service
├── testing/           # In-memory fakes of this module's ports, for its service tests
├── tests/             # pytest: services with fakes; repositories and API against PostgreSQL
├── migrations/
├── admin.py           # Dashboard screens (DashboardModelAdmin); forms and actions call services
├── apps.py
├── container.py       # Builds the services, passing the real adapters to their constructors
└── models.py          # Django models (part of the persistence adapter; services never import it)
```

| Layer | May import |
| --- | --- |
| `domain/` | Python only (and `apps.core.domain`) |
| `application/` | its own `domain/`, `apps.core.domain`, `apps.core.application` |
| `infrastructure/`, `models.py` | `application/` and `domain/`, Django, outside libraries |
| `api/`, `admin.py` | `application/`, `container.py`, `apps.core.api`, `apps.core.dashboard`, `apps.accounts.dashboard` (not core) |

A module never imports another module's `models.py` or `infrastructure/`; it calls that
module's application services. Register the API with one line in `config/api_v1.py`.

## What core gives every module

| Need | Use |
| --- | --- |
| A model | `class Patient(BaseModel)` from `apps.core.models`. `objects` hides inactive rows, `all_objects` shows all. `delete()` raises `HardDeleteError`; call `deactivate()` (SYS-10) |
| Who made a change | `created_by` / `updated_by` are filled on `save()` from the request user. Outside a request (Celery task, command, import) wrap the work in `acting_as(user_id)` from `apps.core.infrastructure.request_context` |
| Full history of a clinical record | One line in the model: `history = track_history()` (`apps.core.infrastructure.history`), then `make makemigrations` |
| Audit log (SYS-04) | Inject the `AuditLogger` port (`container.audit_logger()`); call `log(action, model=…, object_id=…, changes=diff(before, after))`. `snapshot(instance)` gives `before` / `after`. User and IP are filled in |
| A business rule refuses | `raise DomainError("step_out_of_order", _("Approve the earlier steps first."), details)`. `NotFoundError` → 404, `AccessDeniedError` → 403, `ConflictError` → 409, any other `DomainError` → 400 |
| Time, notifications, files, transactions | Ports `Clock`, `Notifier`, `FileStorage`, `UnitOfWork` in `application/ports.py`; fakes in `apps.core.testing` |
| Rows the user may see (section 8) | ORM: a `RoleScope({role: rule})` per repository (a role without a rule sees nothing). Application: subclass `ScopedQueryService` so a row outside scope is a 404 |
| API lists | Pagination (`?page=`, `?page_size=`, 20 by default, 100 at most), django-filter (`filterset_fields`) and `?ordering=` are on by default. Serializers extend `BaseModelSerializer` so date-times go out in UTC |
| Errors in the schema | `extend_schema(responses={400: ErrorSerializer})` with `apps.core.api.serializers.ErrorSerializer` |
| A dashboard screen | Inherit `apps.core.dashboard.DashboardModelAdmin` and register it with `register_screen()` (see [accounts' README](../accounts/README.md#the-dashboard-dashboard-p04)). Show a service error on a form with `apps.core.api.errors.localized_message(error)` |
| The audit log viewer (DB-17) | `/dashboard/core/auditlog/`, read-only, filtered by user, record type, action and date |

## The error format

Every API error is `{"code": "...", "message": "...", "details": {...}}`, with the message in the
language of `Accept-Language` (Arabic by default). Validation errors use the code
`validation_error` and list the fields in `details`. Unknown and out-of-scope rows both return
`not_found`, so a user cannot tell them apart.

## Tests

`tests/testapp` is a small app installed only under `config.settings.test`. Its `Note` model and
endpoints exercise `BaseModel`, history, the error handler, pagination and the scope helper the
way a real module would.
