"""VerifyCredentials (SYS-01): the credential check shared by the API login and the dashboard
login. The lockout rules themselves are tested through Login in test_login.py."""

from datetime import timedelta

import pytest

from apps.accounts.application.services import VerifyCredentials, VerifyCredentialsCommand
from apps.core.domain.errors import AccessDeniedError, DomainError


def verify(f, username="sara", password="Old-Pass-2026", *, for_dashboard=False):
    return VerifyCredentials(f.accounts, f.hasher, f.clock, f.audit, f.uow).execute(
        VerifyCredentialsCommand(username, password, for_dashboard=for_dashboard)
    )


def test_returns_the_user_roles_and_password_gate(fakes):
    user = fakes.accounts.add("sara", roles=("supervisor",), must_change_password=True)

    result = verify(fakes, " Sara ")

    assert result.user_id == user.id
    assert result.roles == frozenset({"supervisor"})
    assert result.must_change_password is True
    assert fakes.accounts.stored(user.id).last_login == fakes.clock.now()
    assert fakes.audit.actions() == ["login"]


@pytest.mark.parametrize("role", ["super_admin", "management", "reception", "supervisor"])
def test_dashboard_roles_may_log_in_to_the_dashboard(fakes, role):
    fakes.accounts.add("sara", roles=(role,))

    assert verify(fakes, for_dashboard=True).roles == frozenset({role})


@pytest.mark.parametrize("role", ["student", "technician"])
def test_students_and_technicians_are_refused_by_the_dashboard(fakes, role):
    user = fakes.accounts.add("sara", roles=(role,), failed_logins=2)

    with pytest.raises(AccessDeniedError) as error:
        verify(fakes, for_dashboard=True)

    assert error.value.code == "dashboard_not_allowed"
    entry = fakes.audit.entries[-1]
    assert (entry.action, entry.user_id) == ("login_failed", user.id)
    assert entry.changes == {"username": "sara", "reason": "dashboard_not_allowed"}
    # The password was right: the refusal is not a failed attempt and the login is not recorded.
    stored = fakes.accounts.stored(user.id)
    assert (stored.failed_logins, stored.last_login) == (2, None)
    assert fakes.uow.commits == 1


def test_a_student_who_is_also_a_supervisor_may_log_in_to_the_dashboard(fakes):
    fakes.accounts.add("sara", roles=("student", "supervisor"))

    assert verify(fakes, for_dashboard=True).roles == frozenset({"student", "supervisor"})


def test_students_still_log_in_to_the_app(fakes):
    fakes.accounts.add("sara", roles=("student",))

    assert verify(fakes).roles == frozenset({"student"})


def test_the_dashboard_uses_the_same_lockout(fakes):
    user = fakes.accounts.add("sara", roles=("supervisor",))
    for _ in range(4):
        with pytest.raises(DomainError, match="invalid_credentials"):
            verify(fakes, password="wrong", for_dashboard=True)

    with pytest.raises(DomainError, match="account_locked"):
        verify(fakes, password="wrong", for_dashboard=True)
    with pytest.raises(DomainError, match="account_locked"):
        verify(fakes, for_dashboard=True)

    assert fakes.accounts.stored(user.id).locked_until == fakes.clock.now() + timedelta(minutes=15)


@pytest.mark.parametrize(
    ("values", "code"),
    [
        ({"roles": ()}, "no_role"),
        ({"is_active": False}, "invalid_credentials"),
    ],
)
def test_guards_apply_to_the_dashboard(fakes, values, code):
    fakes.accounts.add("sara", **values)

    with pytest.raises(DomainError) as error:
        verify(fakes, for_dashboard=True)

    assert error.value.code == code
