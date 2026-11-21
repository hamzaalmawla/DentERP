# accounts

Login, roles and the user's own account (DB-01, DB-02, ST-01, SV-01, MT-01, SYS-01, SYS-02).
Design: [system-design.md](../../../docs/system-design.md) sections 5–8. The layout is the one
in [core's README](../core/README.md).

## Endpoints

| Endpoint | Body → answer | Notes |
| --- | --- | --- |
| `POST /api/v1/auth/login/` | `username`, `password` → `access`, `refresh`, `must_change_password`, `roles` | 10 a minute per IP. 5 failures in a row lock the account for 15 minutes |
| `POST /api/v1/auth/refresh/` | `refresh` → `access`, `refresh` | The refresh token is rotated; the old one stops working |
| `POST /api/v1/auth/logout/` | `refresh` → 204 | Revokes the refresh token |
| `GET /api/v1/me/` | → profile, `roles`, `active_role` | Open while the password must change |
| `POST /api/v1/me/password/` | `current_password`, `new_password` → `access`, `refresh` | Revokes every older token; open while the password must change |
| `POST /api/v1/me/devices/` | `platform` (`android`, `ios`), `token` → device | Push token for notifications |

Access tokens last 15 minutes, refresh tokens 30 days. Every other endpoint allows 120 requests
a minute per user.

## Using roles in another module

```python
from apps.accounts.api.context import request_actor
from apps.accounts.api.permissions import HasAnyRole, IsSupervisor
from apps.accounts.domain.roles import RoleCode


class ApprovalsView(APIView):
    permission_classes = [IsSupervisor]  # or HasAnyRole(RoleCode.STUDENT, RoleCode.SUPERVISOR)

    def get(self, request):
        actor = request_actor(request)  # Actor(user_id, role) for services and query services
        ...
```

- The permission classes check the role the user is **acting in now**: the `X-Active-Role`
  header, or the user's only role. A user with several roles who sends no header gets
  `active_role_required` (403) on role-checked endpoints; a header naming a role the user
  does not hold gets `role_not_held` (403) on every endpoint.
- While the password is temporary, every authenticated endpoint returns
  `password_change_required` (403). A view that must stay open sets
  `password_change_allowed = True` (only `/me/` and `/me/password/` do).
- API tests log in with real tokens through `apps.accounts.testing.api` (`login`, `bearer`).
  Service tests use the fakes in `apps.accounts.testing`.

## The dashboard (`dashboard/`, P0.4)

The web dashboard is Django's admin styled with Unfold, at `/dashboard/`. Its shell lives in
`dashboard/` (a driving adapter, like `api/`), because who sees what depends on the roles this
module owns:

- `site.py`: the admin site. Only super admin, management, reception and supervisor log in
  (`DashboardBackend` checks the password with `VerifyCredentials`, the API's rules). A
  temporary password must be changed first; a user with several dashboard roles chooses one
  (`/dashboard/role/`, "Switch role" in the account menu).
- `navigation.py`: `ROLE_GROUPS`, the single role → sidebar groups map (design section 11),
  and `register_screen()`. The same map decides the sidebar and the role check of every admin
  view, so a hidden screen is also refused by URL.
- `permissions.py`: `ReadOnlyForManagement`. The site adds it to every screen.

A module adds a screen in its `admin.py`:

```python
from apps.accounts.dashboard import Group, ReadOnlyForManagement, dashboard_actor, register_screen
from apps.core.dashboard import DashboardModelAdmin


@admin.register(Clinic)
class ClinicAdmin(ReadOnlyForManagement, DashboardModelAdmin):
    # Forms and actions call services with dashboard_actor(request).
    list_display = ("name_ar", "type")


register_screen(Group.FACILITIES, model=Clinic, title=_("Clinics"), icon="apartment")
```

Every screen inherits `apps.core.dashboard.DashboardModelAdmin` (the site refuses other
classes): nothing is deleted, and Django's own admin log is not written (`AuditLog` is the
record). Screens of installed libraries (auth groups, Celery beat, token blacklist) are not
part of the dashboard.

## Services

`container.py` builds them. The dashboard uses the administration ones; each refuses unless the
actor is acting as `super_admin`.

| Service | What it does |
| --- | --- |
| `VerifyCredentials` | The password check with the lockout, shared by `Login` and the dashboard login; audit `login`, `login_failed`. For the dashboard it also refuses students and technicians |
| `Login`, `RefreshToken`, `Logout` | Tokens; audit `logout` |
| `ChangePassword`, `RegisterDevice` | The user's own account; audit `password_change` |
| `CreateUser`, `UpdateUser`, `AssignRoles`, `ResetPassword`, `UnlockAccount`, `DeactivateUser` | User administration (DB-02); audit `create`, `update`, `password_reset`, `unlock`, `deactivate`. A deactivated user's tokens are revoked; users are never deleted |
| `CreateDemoUsers` | One user per role, for `python manage.py create_demo_users` (development only) |

## Error codes

| Code | Status | When |
| --- | --- | --- |
| `invalid_credentials` | 400 | Wrong username or password (also for unknown and deactivated users) |
| `account_locked` | 403 | Locked after 5 failures; `details.locked_until` |
| `no_role` | 403 | The account has no role |
| `dashboard_not_allowed` | 403 | Dashboard login of a user who is only a student or technician |
| `token_invalid` | 400 | Refresh token expired, revoked or malformed: log in again |
| `role_not_held`, `active_role_required` | 403 | See above |
| `password_change_required` | 403 | Temporary password not changed yet |
| `wrong_password`, `password_unchanged`, `password_invalid` | 400 | `POST /me/password/`; `password_invalid` lists the rules broken in `details.messages` |
| `username_taken`, `university_id_taken`, `account_not_locked` | 409 | Administration |
| `role_required`, `unknown_role`, `own_admin_role`, `own_account`, `username_invalid`, `full_name_required`, `invalid_device` | 400 | Administration and devices |
