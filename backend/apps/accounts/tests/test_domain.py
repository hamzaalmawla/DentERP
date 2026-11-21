"""Accounts domain rules, plain Python."""

from datetime import UTC, datetime, timedelta

import pytest

from apps.accounts.domain.accounts import (
    LOCK_DURATION,
    MAX_FAILED_LOGINS,
    Account,
    normalize_username,
)
from apps.accounts.domain.devices import validate_device
from apps.accounts.domain.errors import AccountLockedError
from apps.accounts.domain.roles import RoleCode, require_active_role, resolve_active_role
from apps.accounts.domain.users import validate_full_name, validate_username
from apps.core.domain.errors import DomainError

NOW = datetime(2026, 12, 1, 9, 0, tzinfo=UTC)


def account(**values) -> Account:
    return Account(id=1, username="sara", password_hash="x", **values)


class TestLockout:
    def test_the_policy_is_5_failures_and_15_minutes(self):
        assert MAX_FAILED_LOGINS == 5
        assert timedelta(minutes=15) == LOCK_DURATION

    def test_four_failures_do_not_lock(self):
        state = account()
        for _ in range(4):
            state = state.after_failed_login(NOW)

        assert state.failed_logins == 4
        assert not state.is_locked(NOW)

    def test_the_fifth_failure_locks_for_15_minutes(self):
        state = account(failed_logins=4)

        state = state.after_failed_login(NOW)

        assert state.locked_until == NOW + timedelta(minutes=15)
        assert state.is_locked(NOW + timedelta(minutes=14, seconds=59))
        assert not state.is_locked(NOW + timedelta(minutes=15))

    def test_ensure_not_locked_raises_account_locked(self):
        state = account(failed_logins=5, locked_until=NOW + timedelta(minutes=1))

        with pytest.raises(AccountLockedError) as error:
            state.ensure_not_locked(NOW)

        assert error.value.code == "account_locked"
        assert error.value.details["locked_until"] == (NOW + timedelta(minutes=1)).isoformat()

    def test_failures_before_an_expired_lock_are_forgotten(self):
        state = account(failed_logins=5, locked_until=NOW - timedelta(minutes=1))

        state = state.after_failed_login(NOW)

        assert state.failed_logins == 1
        assert state.locked_until is None

    def test_a_successful_login_clears_the_count(self):
        state = account(failed_logins=3).after_successful_login(NOW)

        assert state.failed_logins == 0
        assert state.last_login == NOW

    def test_unlocked_clears_the_lock(self):
        state = account(failed_logins=5, locked_until=NOW + LOCK_DURATION).unlocked()

        assert (state.failed_logins, state.locked_until) == (0, None)

    def test_a_temporary_password_must_be_changed(self):
        assert account().with_password("h", temporary=True).must_change_password is True
        assert (
            account(must_change_password=True)
            .with_password("h", temporary=False)
            .must_change_password
            is False
        )


class TestActiveRole:
    def test_a_requested_role_must_be_held(self):
        with pytest.raises(DomainError) as error:
            resolve_active_role({"student"}, "supervisor")

        assert error.value.code == "role_not_held"
        assert error.value.details == {"role": "supervisor"}

    def test_an_unknown_role_is_not_held(self):
        with pytest.raises(DomainError, match="role_not_held"):
            resolve_active_role({"student"}, "dean")

    def test_a_held_role_is_used(self):
        assert resolve_active_role({"student", "supervisor"}, "supervisor") == "supervisor"

    def test_a_single_role_is_used_without_asking(self):
        assert resolve_active_role({"technician"}, None) == "technician"

    def test_several_roles_without_a_choice_have_no_active_role(self):
        assert resolve_active_role({"student", "supervisor"}, None) is None

        with pytest.raises(DomainError) as error:
            require_active_role(None)
        assert error.value.code == "active_role_required"

    def test_there_are_six_roles(self):
        assert {role.value for role in RoleCode} == {
            "super_admin",
            "management",
            "reception",
            "supervisor",
            "student",
            "technician",
        }


class TestUsersAndDevices:
    def test_usernames_ignore_case_and_spaces(self):
        assert normalize_username("  Sara.Ali ") == "sara.ali"

    @pytest.mark.parametrize("username", ["", "has space", "x" * 151, "semi;colon"])
    def test_invalid_usernames(self, username):
        with pytest.raises(DomainError, match="username_invalid"):
            validate_username(username)

    def test_arabic_letters_and_digits_are_allowed_in_usernames(self):
        assert validate_username("سارة_2026") == "سارة_2026"

    def test_the_arabic_full_name_is_required(self):
        with pytest.raises(DomainError, match="full_name_required"):
            validate_full_name("   ")

    @pytest.mark.parametrize(
        ("platform", "token"), [("windows", "abc"), ("android", "  "), ("ios", "x" * 513)]
    )
    def test_invalid_devices(self, platform, token):
        with pytest.raises(DomainError, match="invalid_device"):
            validate_device(platform, token)

    def test_a_valid_device(self):
        assert validate_device("ios", " tok ") == ("ios", "tok")
