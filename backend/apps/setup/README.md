# setup

Terms, departments, clinics and chairs, sessions, the lookup lists and the system settings
(DB-04, DB-06, DB-18, SYS-07, SYS-10; US-01). Design:
[system-design.md](../../../docs/system-design.md) sections 5–7 and 11; SRS section 4. The
layout is the one in [core's README](../core/README.md). Setup uses no other module.

## Endpoints

| Endpoint | Answer | Notes |
| --- | --- | --- |
| `GET /api/v1/lookups/` | Every lookup list, the `version` and the app's settings | Every role. Names in the request language (`Accept-Language`). `ETag: "lookups-<version>-<language>"`; send it in `If-None-Match` and the answer is 304 while nothing changed |
| `GET /api/v1/clinics/` | Active clinics by number | Every role. `?type=diagnosis\|treatment\|lab`; `?with=chair_status` adds each clinic's active chairs and the counts in and out of service |

## Records and their rules

Every record the super admin edits is described once in `domain/records.py` (`Table`): its
values and how each is checked, which values are unique (checked against deactivated records
too, so one can be activated again), and which records it points to (they must be active).
Two services apply those rules to every table: `SaveRecord` (create or change) and
`SetRecordActive` (deactivate or activate; nothing is deleted). Lists are ordered by
dragging their rows (`Reorder`). `AddChairs` adds numbered chairs to a clinic;
`SetChairStatus` puts a chair in or out of service with a reason and writes its history
(`ChairStatusChange`). `UpdateSettings` stores the settings of `domain/settings.py`.

Any change to a list sent to the app (`LOOKUP_TABLES`, and the photo size and round times)
adds one to the lookups version, so the app downloads `/lookups/` again.

## Other modules

Call the facade (`SetupFacade`, [docs/contracts.md](../../../docs/contracts.md)); in service
tests use `apps.setup.testing.InMemorySetupFacade`. Setup's own service tests use
`InMemorySetupStore`, the in-memory fakes of its repository ports.

## Default data

`python manage.py seed_defaults` (`make seed`) loads `seed/defaults.json` through the same
rules as the dashboard. A record already there (found by the values in `SEED_KEYS`, active or
deactivated) is left as it is, and a setting already set keeps its value, so it is safe to run
again. A term is made current only when no term is current. Tests never load it unless a test
calls the command.
