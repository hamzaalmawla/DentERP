"""Dashboard forms. They hold no rules: each calls an accounts service and shows the service's
error on the field it concerns."""

from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from unfold.forms import AuthenticationForm
from unfold.widgets import INPUT_CLASSES

from apps.accounts import container
from apps.accounts.application.services import ChangePasswordCommand
from apps.core.api.errors import localized_message
from apps.core.domain.errors import DomainError

from .backends import login_error


def error_messages(error: DomainError) -> list[str]:
    """The service error as form messages: its own message, then any detailed messages (the
    password rules a new password breaks)."""
    return [localized_message(error), *error.details.get("messages", [])]


def add_service_error(form: forms.Form, error: DomainError, fields: dict[str, str]) -> None:
    """Show ``error`` on the field named for its code in ``fields``, or above the form."""
    field = fields.get(error.code)
    form.add_error(field if field in form.fields else None, error_messages(error))


class DashboardLoginForm(AuthenticationForm):
    """Logs in through ``DashboardBackend`` and shows why a login was refused: wrong
    credentials, a locked account, no role, or a role that does not use the dashboard."""

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if username is not None and password:
            self.user_cache = authenticate(self.request, username=username, password=password)
            if self.user_cache is None:
                error = login_error(self.request)
                raise ValidationError(
                    localized_message(error) if error else self.error_messages["invalid_login"],
                    code=error.code if error else "invalid_login",
                )
        return self.cleaned_data

    def confirm_login_allowed(self, user):
        """``VerifyCredentials`` already decided; roles, not ``is_staff``, open the dashboard."""


def _password_input(autocomplete: str) -> forms.PasswordInput:
    return forms.PasswordInput(
        attrs={"autocomplete": autocomplete, "class": " ".join(INPUT_CLASSES)}
    )


class DashboardPasswordChangeForm(forms.Form):
    """The user's own password, through the ``ChangePassword`` service (it also lifts the
    first-login gate and logs the user out of the app on other phones)."""

    old_password = forms.CharField(
        label=_("Current password"), strip=False, widget=_password_input("current-password")
    )
    new_password1 = forms.CharField(
        label=_("New password"), strip=False, widget=_password_input("new-password")
    )
    new_password2 = forms.CharField(
        label=_("New password again"), strip=False, widget=_password_input("new-password")
    )

    _ERROR_FIELDS = {
        "wrong_password": "old_password",
        "password_unchanged": "new_password1",
        "password_invalid": "new_password1",
    }

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        new1, new2 = cleaned.get("new_password1"), cleaned.get("new_password2")
        if new1 and new2 and new1 != new2:
            self.add_error("new_password2", _("The two new passwords are not the same."))
        if self.errors:
            return cleaned
        try:
            container.change_password().execute(
                ChangePasswordCommand(self.user.pk, cleaned["old_password"], new1)
            )
        except DomainError as error:
            add_service_error(self, error, self._ERROR_FIELDS)
        return cleaned

    def save(self, commit=True):
        """The service has changed the password; reload the user so the session follows the
        new password hash."""
        self.user.refresh_from_db()
        return self.user
