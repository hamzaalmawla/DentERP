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

## Services

`container.py` builds them. The dashboard (P0.4) uses the administration ones; each refuses
unless the actor is acting as `super_admin`.

| Service | What it does |
| --- | --- |
| `Login`, `RefreshToken`, `Logout` | Tokens; lockout; audit `login`, `login_failed`, `logout` |
| `ChangePassword`, `RegisterDevice` | The user's own account; audit `password_change` |
| `CreateUser`, `AssignRoles`, `ResetPassword`, `UnlockAccount` | User administration (DB-02); audit `create`, `update`, `password_reset`, `unlock` |
| `CreateDemoUsers` | One user per role, for `python manage.py create_demo_users` (development only) |

## Error codes

| Code | Status | When |
| --- | --- | --- |
| `invalid_credentials` | 400 | Wrong username or password (also for unknown and deactivated users) |
| `account_locked` | 403 | Locked after 5 failures; `details.locked_until` |
| `no_role` | 403 | The account has no role |
| `token_invalid` | 400 | Refresh token expired, revoked or malformed: log in again |
| `role_not_held`, `active_role_required` | 403 | See above |
| `password_change_required` | 403 | Temporary password not changed yet |
| `wrong_password`, `password_unchanged`, `password_invalid` | 400 | `POST /me/password/`; `password_invalid` lists the rules broken in `details.messages` |
| `username_taken`, `university_id_taken`, `account_not_locked` | 409 | Administration |
| `role_required`, `unknown_role`, `own_admin_role`, `username_invalid`, `full_name_required`, `invalid_device` | 400 | Administration and devices |
