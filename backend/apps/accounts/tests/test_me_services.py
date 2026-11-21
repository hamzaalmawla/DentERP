"""The user's own account: ChangePassword, RegisterDevice, GetProfile and GetAuthContext."""

from datetime import timedelta

import pytest

from apps.accounts.application.queries import GetAuthContext, GetProfile
from apps.accounts.application.services import (
    ChangePassword,
    ChangePasswordCommand,
    RegisterDevice,
    RegisterDeviceCommand,
)
from apps.accounts.testing import InMemoryAuthContextReader
from apps.core.domain.errors import DomainError, NotFoundError


def change(f, user_id, current="Old-Pass-2026", new="New-Pass-2026"):
    return ChangePassword(f.accounts, f.hasher, f.policy, f.tokens, f.audit, f.uow).execute(
        ChangePasswordCommand(user_id, current, new)
    )


class TestChangePassword:
    def test_sets_the_password_and_lifts_the_first_login_gate(self, fakes):
        user = fakes.accounts.add("sara", must_change_password=True)

        change(fakes, user.id)

        stored = fakes.accounts.stored(user.id)
        assert stored.password_hash == "hashed:New-Pass-2026"
        assert stored.must_change_password is False
        assert fakes.audit.actions() == ["password_change"]
        assert fakes.audit.entries[0].changes == {
            "must_change_password": {"old": True, "new": False}
        }

    def test_revokes_old_tokens_and_returns_a_new_pair(self, fakes):
        user = fakes.accounts.add("sara")
        old = fakes.tokens.issue(user.id)

        pair = change(fakes, user.id)

        assert fakes.tokens.open_tokens(user.id) == {pair.refresh}
        assert old.refresh in fakes.tokens.revoked

    def test_wrong_current_password(self, fakes):
        user = fakes.accounts.add("sara")

        with pytest.raises(DomainError) as error:
            change(fakes, user.id, current="nope")

        assert error.value.code == "wrong_password"
        assert fakes.accounts.stored(user.id).password_hash == "hashed:Old-Pass-2026"

    def test_the_same_password_is_refused(self, fakes):
        user = fakes.accounts.add("sara")

        with pytest.raises(DomainError, match="password_unchanged"):
            change(fakes, user.id, new="Old-Pass-2026")

    def test_the_password_rules_apply(self, fakes):
        user = fakes.accounts.add("sara")
        fakes.policy.refused.add("Password123")

        with pytest.raises(DomainError) as error:
            change(fakes, user.id, new="Password123")

        assert error.value.code == "password_invalid"
        assert error.value.details == {"messages": ["too common"]}
        assert fakes.audit.entries == []

    def test_only_the_users_own_active_account(self, fakes):
        user = fakes.accounts.add("sara", is_active=False)

        with pytest.raises(NotFoundError):
            change(fakes, user.id)


class TestRegisterDevice:
    def register(self, f, user_id, token="fcm-token", platform="android"):
        return RegisterDevice(f.accounts, f.devices, f.clock, f.uow).execute(
            RegisterDeviceCommand(user_id, platform, token)
        )

    def test_registers_a_device(self, fakes):
        user = fakes.accounts.add("sara")

        device = self.register(fakes, user.id)

        assert device.platform == "android"
        assert device.last_seen == fakes.clock.now()
        assert fakes.devices.devices["fcm-token"].user_id == user.id

    def test_registering_again_updates_last_seen(self, fakes):
        user = fakes.accounts.add("sara")
        first = self.register(fakes, user.id)
        fakes.clock.advance(days=1)

        again = self.register(fakes, user.id)

        assert again.id == first.id
        assert again.last_seen == fakes.clock.now()

    def test_a_token_moves_to_the_new_user_of_the_phone(self, fakes):
        sara = fakes.accounts.add("sara")
        omar = fakes.accounts.add("omar")
        self.register(fakes, sara.id)

        self.register(fakes, omar.id, platform="ios")

        assert fakes.devices.devices["fcm-token"].user_id == omar.id
        assert len(fakes.devices.devices) == 1

    def test_invalid_device(self, fakes):
        user = fakes.accounts.add("sara")

        with pytest.raises(DomainError, match="invalid_device"):
            self.register(fakes, user.id, platform="symbian")

    def test_unknown_user(self, fakes):
        with pytest.raises(NotFoundError):
            self.register(fakes, 99)


class TestQueries:
    def test_profile(self, fakes):
        user = fakes.accounts.add(
            "sara", full_name_ar="سارة", roles=("student",), phone="0999", university_id="U1"
        )

        profile = GetProfile(fakes.accounts).execute(user.id)

        assert (profile.username, profile.full_name_ar, profile.phone) == ("sara", "سارة", "0999")
        assert profile.roles == ("student",)
        assert profile.university_id == "U1"

    def test_profile_of_a_deactivated_user_is_not_found(self, fakes):
        user = fakes.accounts.add("sara", is_active=False)

        with pytest.raises(NotFoundError):
            GetProfile(fakes.accounts).execute(user.id)

    def test_auth_context(self, fakes):
        user = fakes.accounts.add(
            "sara",
            roles=("student", "supervisor"),
            must_change_password=True,
            locked_until=fakes.clock.now() + timedelta(minutes=1),
        )
        reader = InMemoryAuthContextReader(fakes.accounts)

        context = GetAuthContext(reader).execute(user.id)

        assert context.roles == {"student", "supervisor"}
        assert context.must_change_password is True
        assert GetAuthContext(reader).execute(999) is None
