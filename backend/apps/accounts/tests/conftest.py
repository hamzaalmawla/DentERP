from dataclasses import dataclass, field

import pytest
from django.conf import settings
from django.test import Client

from apps.accounts.models import Role, User, UserRole
from apps.accounts.testing import (
    FakePasswordHasher,
    FakePasswordPolicy,
    FakeTokenIssuer,
    FixedPasswordGenerator,
    InMemoryAccountRepository,
    InMemoryDeviceTokenRepository,
    InMemoryRoleRepository,
)
from apps.accounts.testing.api import login
from apps.core.testing import FakeUnitOfWork, FixedClock, InMemoryAuditLogger
from apps.setup.testing import InMemorySetupFacade

PASSWORD = "Strong-Pass-2026"


# --- Service tests: every port is an in-memory fake -----------------------------------


@dataclass
class Fakes:
    accounts: InMemoryAccountRepository = field(default_factory=InMemoryAccountRepository)
    roles: InMemoryRoleRepository = field(default_factory=InMemoryRoleRepository)
    setup: InMemorySetupFacade = field(default_factory=InMemorySetupFacade)
    devices: InMemoryDeviceTokenRepository = field(default_factory=InMemoryDeviceTokenRepository)
    hasher: FakePasswordHasher = field(default_factory=FakePasswordHasher)
    policy: FakePasswordPolicy = field(default_factory=FakePasswordPolicy)
    passwords: FixedPasswordGenerator = field(default_factory=FixedPasswordGenerator)
    tokens: FakeTokenIssuer = field(default_factory=FakeTokenIssuer)
    clock: FixedClock = field(default_factory=FixedClock)
    audit: InMemoryAuditLogger = field(default_factory=InMemoryAuditLogger)
    uow: FakeUnitOfWork = field(default_factory=FakeUnitOfWork)


@pytest.fixture
def fakes() -> Fakes:
    return Fakes()


# --- Database and API tests ------------------------------------------------------------


@pytest.fixture
def make_user(db):
    """A user with the given roles (codes), saved through the ORM."""

    def make(username: str = "user", *roles: str, password: str = PASSWORD, **fields) -> User:
        fields.setdefault("full_name_ar", f"مستخدم {username}")
        user = User.objects.create_user(username, password, **fields)
        for code in roles:
            UserRole.objects.create(user=user, role=Role.objects.get(code=code))
        return user

    return make


@pytest.fixture
def logged_in(make_user):
    """Log a new user in with real tokens: ``logged_in("student")`` → (user, tokens)."""

    def make(*roles: str, username: str | None = None, **fields):
        user = make_user(username or "_".join(roles) or "nobody", *roles, **fields)
        response = login(user.username, PASSWORD)
        assert response.status_code == 200, response.json()
        return user, response.json()

    return make


# --- Dashboard tests --------------------------------------------------------------------


def english_client() -> Client:
    """A browser that picked English with the language switch (messages are asserted in
    English; Arabic is the default and is tested on its own)."""
    client = Client()
    client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
    return client


@pytest.fixture
def dashboard(make_user):
    """A dashboard session for a new user: ``dashboard("supervisor")`` → client (with
    ``client.user``). The session is opened with ``force_login``; the login form itself is
    tested in test_dashboard_login.py."""

    def make(*roles: str, username: str | None = None, **fields) -> Client:
        user = make_user(username or "_".join(roles) or "nobody", *roles, **fields)
        client = english_client()
        client.force_login(user)
        client.user = user
        return client

    return make
