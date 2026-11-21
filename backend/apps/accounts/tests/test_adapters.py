"""Adapters of the outside services: JWT tokens and Django's password machinery."""

import pytest
from django.conf import settings
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.tokens import RefreshToken as JwtRefreshToken

from apps.accounts.application import ports
from apps.accounts.domain.accounts import Account
from apps.accounts.domain.errors import InvalidTokenError
from apps.accounts.infrastructure.passwords import (
    DjangoPasswordHasher,
    DjangoPasswordPolicy,
    SecretsPasswordGenerator,
)
from apps.accounts.infrastructure.repositories import (
    OrmAccountRepository,
    OrmAuthContextReader,
    OrmDeviceTokenRepository,
    OrmRoleRepository,
)
from apps.accounts.infrastructure.tokens import SimpleJwtTokenIssuer
from apps.accounts.testing import (
    FakePasswordHasher,
    FakePasswordPolicy,
    FakeTokenIssuer,
    FixedPasswordGenerator,
    InMemoryAccountRepository,
    InMemoryAuthContextReader,
    InMemoryDeviceTokenRepository,
    InMemoryRoleRepository,
)


@pytest.mark.parametrize(
    ("implementations", "port"),
    [
        ((OrmAccountRepository(), InMemoryAccountRepository()), ports.AccountRepository),
        ((OrmRoleRepository(), InMemoryRoleRepository()), ports.RoleRepository),
        (
            (OrmAuthContextReader(), InMemoryAuthContextReader(InMemoryAccountRepository())),
            ports.AuthContextReader,
        ),
        (
            (OrmDeviceTokenRepository(), InMemoryDeviceTokenRepository()),
            ports.DeviceTokenRepository,
        ),
        ((DjangoPasswordHasher(), FakePasswordHasher()), ports.PasswordHasher),
        ((DjangoPasswordPolicy(), FakePasswordPolicy()), ports.PasswordPolicy),
        (
            (SecretsPasswordGenerator(), FixedPasswordGenerator()),
            ports.TemporaryPasswordGenerator,
        ),
        ((SimpleJwtTokenIssuer(), FakeTokenIssuer()), ports.TokenIssuer),
    ],
)
def test_adapter_and_fake_fit_the_port(implementations, port):
    for implementation in implementations:
        assert isinstance(implementation, port)


class TestTokenIssuer:
    issuer = SimpleJwtTokenIssuer()

    def test_lifetimes_15_minutes_and_30_days(self, make_user):
        pair = self.issuer.issue(make_user("sara").pk)

        access, refresh = AccessToken(pair.access), JwtRefreshToken(pair.refresh)
        # Both expiries count from the refresh token's creation time; the access token's own
        # "iat" is stamped a moment later and may fall in the next second.
        assert access["exp"] - refresh["iat"] == 15 * 60
        assert refresh["exp"] - refresh["iat"] == 30 * 24 * 60 * 60
        assert settings.SIMPLE_JWT["ROTATE_REFRESH_TOKENS"] is True

    def test_rotate_revokes_the_old_token(self, make_user):
        user = make_user("sara")
        pair = self.issuer.issue(user.pk)

        new = self.issuer.rotate(pair.refresh)

        assert self.issuer.user_of(new.refresh) == user.pk
        with pytest.raises(InvalidTokenError):
            self.issuer.user_of(pair.refresh)
        with pytest.raises(InvalidTokenError):
            self.issuer.rotate(pair.refresh)

    def test_revoke(self, make_user):
        user = make_user("sara")
        pair = self.issuer.issue(user.pk)

        assert self.issuer.revoke(pair.refresh) == user.pk
        with pytest.raises(InvalidTokenError):
            self.issuer.revoke(pair.refresh)

    def test_revoke_all(self, make_user):
        user, other = make_user("sara"), make_user("omar")
        first, second = self.issuer.issue(user.pk), self.issuer.issue(user.pk)
        others = self.issuer.issue(other.pk)
        self.issuer.revoke(first.refresh)

        self.issuer.revoke_all(user.pk)

        for token in (first.refresh, second.refresh):
            with pytest.raises(InvalidTokenError):
                self.issuer.user_of(token)
        assert self.issuer.user_of(others.refresh) == other.pk

    @pytest.mark.parametrize("token", ["", "garbage", "a.b.c"])
    def test_invalid_tokens(self, token):
        with pytest.raises(InvalidTokenError):
            self.issuer.user_of(token)


class TestPasswords:
    def test_hasher(self):
        hasher = DjangoPasswordHasher()
        encoded = hasher.hash("Strong-Pass-2026")

        assert hasher.verify("Strong-Pass-2026", encoded)
        assert not hasher.verify("wrong", encoded)
        assert not hasher.verify("Strong-Pass-2026", "")
        hasher.spend_time("anything")

    def test_policy_uses_the_django_validators(self):
        account = Account(id=1, username="sara.ali", password_hash="", full_name_en="Sara Ali")
        policy = DjangoPasswordPolicy()

        assert policy.problems("Strong-Pass-2026", account) == []
        assert len(policy.problems("1234", account)) == 3  # short, common, numeric
        assert policy.problems("sara.ali.2", account)  # too similar to the username

    def test_generated_passwords_pass_the_policy_and_differ(self):
        generator = SecretsPasswordGenerator()
        account = Account(id=1, username="sara", password_hash="")

        passwords = {generator.generate() for _ in range(20)}

        assert len(passwords) == 20
        for password in passwords:
            assert len(password) == 12
            assert DjangoPasswordPolicy().problems(password, account) == []
