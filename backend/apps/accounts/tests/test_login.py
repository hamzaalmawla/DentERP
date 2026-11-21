"""Login service (SYS-01, ST-01) with in-memory fakes."""

from datetime import timedelta

import pytest

from apps.accounts.application.services import Login, LoginCommand
from apps.core.domain.errors import DomainError


def service(f) -> Login:
    return Login(f.accounts, f.hasher, f.tokens, f.clock, f.audit, f.uow)


def attempt(f, username="sara", password="Old-Pass-2026"):
    return service(f).execute(LoginCommand(username, password))


def test_login_returns_tokens_roles_and_the_password_gate(fakes):
    user = fakes.accounts.add("sara", roles=("supervisor", "student"))

    result = attempt(fakes)

    assert result.access == "access-1"
    assert result.refresh == "refresh-1"
    assert result.roles == ("student", "supervisor")
    assert result.must_change_password is False
    assert fakes.tokens.open_tokens(user.id) == {"refresh-1"}
    assert fakes.audit.actions() == ["login"]
    assert fakes.audit.entries[0].user_id == user.id


def test_login_records_the_time_and_clears_failures(fakes):
    user = fakes.accounts.add("sara", failed_logins=3)

    attempt(fakes)

    stored = fakes.accounts.stored(user.id)
    assert stored.last_login == fakes.clock.now()
    assert stored.failed_logins == 0


def test_username_is_case_insensitive(fakes):
    fakes.accounts.add("sara")

    assert attempt(fakes, username="  Sara ").access


def test_a_temporary_password_is_reported(fakes):
    fakes.accounts.add("sara", must_change_password=True)

    assert attempt(fakes).must_change_password is True


def test_wrong_password_counts_a_failure_and_audits_it(fakes):
    user = fakes.accounts.add("sara")

    with pytest.raises(DomainError) as error:
        attempt(fakes, password="wrong")

    assert error.value.code == "invalid_credentials"
    assert fakes.accounts.stored(user.id).failed_logins == 1
    assert fakes.uow.commits == 1  # the failure is saved before the error is raised
    entry = fakes.audit.entries[0]
    assert (entry.action, entry.user_id) == ("login_failed", user.id)
    assert entry.changes == {"username": "sara", "reason": "wrong_password"}


def test_unknown_user_gets_the_same_error_and_spends_hashing_time(fakes):
    with pytest.raises(DomainError) as error:
        attempt(fakes, username="nobody")

    assert error.value.code == "invalid_credentials"
    assert fakes.hasher.time_spent == 1
    assert fakes.audit.entries[0].changes == {"username": "nobody", "reason": "unknown_user"}


def test_a_deactivated_user_cannot_log_in(fakes):
    fakes.accounts.add("sara", is_active=False)

    with pytest.raises(DomainError, match="invalid_credentials"):
        attempt(fakes)


def test_the_fifth_failure_locks_the_account(fakes):
    user = fakes.accounts.add("sara")
    for _ in range(4):
        with pytest.raises(DomainError, match="invalid_credentials"):
            attempt(fakes, password="wrong")

    with pytest.raises(DomainError) as error:
        attempt(fakes, password="wrong")

    assert error.value.code == "account_locked"
    locked_until = fakes.clock.now() + timedelta(minutes=15)
    assert error.value.details == {"locked_until": locked_until.isoformat()}
    assert fakes.accounts.stored(user.id).locked_until == locked_until


def test_a_locked_account_is_refused_even_with_the_right_password(fakes):
    user = fakes.accounts.add(
        "sara", failed_logins=5, locked_until=fakes.clock.now() + timedelta(minutes=10)
    )

    with pytest.raises(DomainError, match="account_locked"):
        attempt(fakes)

    assert fakes.tokens.open_tokens(user.id) == set()
    assert fakes.audit.entries[-1].changes["reason"] == "locked"


def test_the_lock_ends_after_15_minutes(fakes):
    fakes.accounts.add("sara")
    for _ in range(5):
        with pytest.raises(DomainError):
            attempt(fakes, password="wrong")

    fakes.clock.advance(minutes=15)

    assert attempt(fakes).access


def test_a_user_without_a_role_cannot_log_in(fakes):
    user = fakes.accounts.add("sara", roles=())

    with pytest.raises(DomainError) as error:
        attempt(fakes)

    assert error.value.code == "no_role"
    assert fakes.tokens.open_tokens(user.id) == set()
