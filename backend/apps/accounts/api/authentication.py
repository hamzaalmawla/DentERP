"""API authentication: JWT bearer tokens, then the two checks every request goes through
(design section 8):

1. ``X-Active-Role``: the role the user picked must be one they hold (``role_not_held``).
2. The first-login gate: while the user still has a temporary password, every endpoint
   returns ``password_change_required``, except the views that set
   ``password_change_allowed = True`` (``GET /me/`` and ``POST /me/password/``).

The checks run here, not in a Django middleware, because the JWT user is only known once DRF
has authenticated the request inside the view.
"""

from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.accounts.domain.errors import PasswordChangeRequiredError

from .context import request_auth


class AccountJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is None:
            return None
        user, token = result
        auth = request_auth(request, user)
        if auth is not None and auth.must_change_password and not _allows_pending_change(request):
            raise PasswordChangeRequiredError()
        return user, token


def _allows_pending_change(request) -> bool:
    view = (getattr(request, "parser_context", None) or {}).get("view")
    return bool(getattr(view, "password_change_allowed", False))
