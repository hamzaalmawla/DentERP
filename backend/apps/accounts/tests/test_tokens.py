"""RefreshToken and Logout services."""

import pytest

from apps.accounts.application.services import Logout, RefreshToken
from apps.core.domain.errors import DomainError


def refresh(f, token: str):
    return RefreshToken(f.accounts, f.tokens, f.uow).execute(token)


def logout(f, token: str):
    return Logout(f.tokens, f.audit, f.uow).execute(token)


class TestRefresh:
    def test_rotates_the_refresh_token(self, fakes):
        user = fakes.accounts.add("sara")
        first = fakes.tokens.issue(user.id)

        pair = refresh(fakes, first.refresh)

        assert pair.refresh != first.refresh
        assert fakes.tokens.open_tokens(user.id) == {pair.refresh}

    def test_an_old_refresh_token_cannot_be_used_again(self, fakes):
        user = fakes.accounts.add("sara")
        first = fakes.tokens.issue(user.id)
        refresh(fakes, first.refresh)

        with pytest.raises(DomainError, match="token_invalid"):
            refresh(fakes, first.refresh)

    def test_an_unknown_token_is_invalid(self, fakes):
        with pytest.raises(DomainError, match="token_invalid"):
            refresh(fakes, "forged")

    def test_a_deactivated_user_cannot_refresh(self, fakes):
        user = fakes.accounts.add("sara")
        token = fakes.tokens.issue(user.id).refresh
        fakes.accounts.users[user.id].is_active = False

        with pytest.raises(DomainError, match="token_invalid"):
            refresh(fakes, token)


class TestLogout:
    def test_revokes_the_refresh_token_and_audits(self, fakes):
        user = fakes.accounts.add("sara")
        token = fakes.tokens.issue(user.id).refresh

        logout(fakes, token)

        assert fakes.tokens.open_tokens(user.id) == set()
        assert fakes.audit.actions() == ["logout"]
        assert fakes.audit.entries[0].user_id == user.id

    def test_a_revoked_token_cannot_log_out_again(self, fakes):
        user = fakes.accounts.add("sara")
        token = fakes.tokens.issue(user.id).refresh
        logout(fakes, token)

        with pytest.raises(DomainError, match="token_invalid"):
            logout(fakes, token)
