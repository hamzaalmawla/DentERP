from dataclasses import dataclass, field

import pytest
from django.conf import settings
from django.test import Client

from apps.accounts.models import Role, User, UserRole
from apps.accounts.testing.api import bearer, login
from apps.core.testing import FakeUnitOfWork, FixedClock, InMemoryAuditLogger
from apps.setup.application.facade import SetupFacadeService
from apps.setup.application.services import (
    AddChairs,
    Reorder,
    SaveRecord,
    SaveRecordCommand,
    SetChairStatus,
    SetRecordActive,
    UpdateSettings,
)
from apps.setup.domain.records import Table
from apps.setup.testing import InMemorySetupStore

from .helpers import ADMIN, PASSWORD

# --- Service tests: every port is an in-memory fake -----------------------------------


@dataclass
class Fakes:
    store: InMemorySetupStore = field(default_factory=InMemorySetupStore)
    audit: InMemoryAuditLogger = field(default_factory=InMemoryAuditLogger)
    uow: FakeUnitOfWork = field(default_factory=FakeUnitOfWork)
    clock: FixedClock = field(default_factory=FixedClock)

    def save_record(self) -> SaveRecord:
        s = self.store
        return SaveRecord(s.records, s.terms, s.settings, self.audit, self.uow)

    def set_record_active(self) -> SetRecordActive:
        return SetRecordActive(self.store.records, self.store.settings, self.audit, self.uow)

    def reorder(self) -> Reorder:
        s = self.store
        return Reorder(s.records, s.terms, s.settings, self.audit, self.uow)

    def add_chairs(self) -> AddChairs:
        s = self.store
        return AddChairs(s.records, s.chairs, s.terms, s.settings, self.audit, self.uow)

    def set_chair_status(self) -> SetChairStatus:
        return SetChairStatus(self.store.chairs, self.clock, self.audit, self.uow)

    def update_settings(self) -> UpdateSettings:
        return UpdateSettings(self.store.settings, self.audit, self.uow)

    def facade(self) -> SetupFacadeService:
        s = self.store
        return SetupFacadeService(
            terms=s.terms,
            clinics=s.clinics,
            chairs=s.chairs,
            lookups=s.lookups,
            settings=s.settings,
            set_chair_status=self.set_chair_status(),
        )

    def save(self, table: Table, record_id: int | None = None, **values) -> int:
        """Save through the service as the administrator; returns the id."""
        return self.save_record().execute(ADMIN, SaveRecordCommand(table, values, record_id)).id


@pytest.fixture
def fakes() -> Fakes:
    return Fakes()


# --- Database, API and dashboard tests -----------------------------------------------------


@pytest.fixture
def make_user(db):
    def make(username: str, *roles: str) -> User:
        user = User.objects.create_user(username, PASSWORD, full_name_ar=f"مستخدم {username}")
        for code in roles:
            UserRole.objects.create(user=user, role=Role.objects.get(code=code))
        return user

    return make


@pytest.fixture
def api(make_user):
    """An API client logged in with real tokens: ``api("student", language="ar")``."""

    def make(role: str, language: str = "en"):
        user = make_user(f"api_{role}", role)
        response = login(user.username, PASSWORD)
        assert response.status_code == 200, response.json()
        return bearer(response.json()["access"], language=language)

    return make


@pytest.fixture
def dashboard(make_user):
    """A dashboard session in English: ``dashboard("super_admin")`` → client."""

    def make(role: str = "super_admin") -> Client:
        user = make_user(f"dash_{role}", role)
        client = Client()
        client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        client.force_login(user)
        client.user = user
        return client

    return make
