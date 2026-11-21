"""The dashboard's Django authentication backend (design section 8).

It checks the username and password with ``VerifyCredentials``, the same service the API login
uses: the same lockout after 5 failures, the same refusal of locked accounts and users with no
role, the same audit entries. It also refuses users with no dashboard role (students and
technicians). It is the only backend in ``AUTHENTICATION_BACKENDS``, so no login can skip
these rules.

When a login is refused, the service's error is kept on the request, so the login form can show
the right message (``login_error``).
"""

from django.contrib.auth.backends import BaseBackend
from django.core.exceptions import PermissionDenied

from apps.accounts import container
from apps.accounts.application.services import VerifyCredentialsCommand
from apps.accounts.models import User
from apps.core.domain.errors import DomainError

_ERROR_ATTRIBUTE = "_dashboard_login_error"


class DashboardBackend(BaseBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        try:
            verified = container.verify_credentials().execute(
                VerifyCredentialsCommand(username, password, for_dashboard=True)
            )
        except DomainError as error:
            if request is not None:
                setattr(request, _ERROR_ATTRIBUTE, error)
            raise PermissionDenied from error  # stops authenticate(); no other backend runs
        return User.objects.filter(pk=verified.user_id).first()

    def get_user(self, user_id):
        return User.objects.filter(pk=user_id).first()  # deactivated users are logged out


def login_error(request) -> DomainError | None:
    """Why the last ``authenticate()`` on this request refused the login."""
    return getattr(request, _ERROR_ATTRIBUTE, None)
