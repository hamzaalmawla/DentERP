"""Shared ports: every fake and every adapter fits its Protocol and behaves like the other."""

import io
from datetime import UTC, date, datetime

import pytest
from django.core.files.storage import InMemoryStorage

from apps.core import container
from apps.core.application.dtos import NotificationTarget
from apps.core.application.ports import AuditLogger, Clock, FileStorage, Notifier, UnitOfWork
from apps.core.infrastructure.clock import SystemClock
from apps.core.infrastructure.storage import DjangoFileStorage
from apps.core.infrastructure.unit_of_work import DjangoUnitOfWork
from apps.core.testing import (
    FakeNotifier,
    FakeUnitOfWork,
    FixedClock,
    InMemoryAuditLogger,
    InMemoryFileStorage,
)
from tests.testapp.models import Note


@pytest.mark.parametrize(
    ("implementation", "port"),
    [
        (FixedClock(), Clock),
        (SystemClock(), Clock),
        (FakeNotifier(), Notifier),
        (InMemoryFileStorage(), FileStorage),
        (DjangoFileStorage(InMemoryStorage()), FileStorage),
        (FakeUnitOfWork(), UnitOfWork),
        (DjangoUnitOfWork(), UnitOfWork),
        (InMemoryAuditLogger(), AuditLogger),
    ],
)
def test_fits_the_port(implementation, port):
    assert isinstance(implementation, port)


def test_container_builds_the_adapters():
    assert isinstance(container.clock(), Clock)
    assert isinstance(container.audit_logger(), AuditLogger)
    assert isinstance(container.file_storage(), FileStorage)
    assert isinstance(container.unit_of_work(), UnitOfWork)


class TestClocks:
    def test_fixed_clock_today_is_the_damascus_date(self):
        clock = FixedClock(datetime(2026, 12, 1, 22, 30, tzinfo=UTC))  # 01:30 in Damascus

        assert clock.today() == date(2026, 12, 2)

    def test_fixed_clock_moves_only_when_told(self):
        clock = FixedClock(datetime(2026, 12, 1, 9, tzinfo=UTC))
        clock.advance(minutes=15)

        assert clock.now() == datetime(2026, 12, 1, 9, 15, tzinfo=UTC)

    def test_fixed_clock_needs_a_time_zone(self):
        with pytest.raises(ValueError, match="timezone-aware"):
            FixedClock(datetime(2026, 12, 1, 9))

    def test_system_clock_is_aware(self):
        assert SystemClock().now().tzinfo is not None


def test_fake_notifier_records_what_was_sent():
    notifier = FakeNotifier()

    notifier.notify(
        [1, 2],
        "diagnosis_submitted",
        "diagnosis_submitted_title",
        "diagnosis_submitted_body",
        {"patient": "P-1"},
        NotificationTarget("diagnosis", 7),
    )

    sent = notifier.sent[0]
    assert sent.recipient_ids == (1, 2)
    assert sent.params == {"patient": "P-1"}
    assert sent.target == NotificationTarget("diagnosis", 7)


@pytest.mark.parametrize(
    "make_storage", [InMemoryFileStorage, lambda: DjangoFileStorage(InMemoryStorage())]
)
class TestFileStorage:
    def test_save_and_open(self, make_storage):
        storage = make_storage()

        name = storage.save("photos/a.jpg", b"jpeg-bytes", "image/jpeg")

        assert storage.exists(name)
        assert storage.open(name) == b"jpeg-bytes"

    def test_save_a_file_object(self, make_storage):
        storage = make_storage()

        name = storage.save("photos/b.png", io.BytesIO(b"png-bytes"), "image/png")

        assert storage.open(name) == b"png-bytes"

    def test_never_overwrites(self, make_storage):
        storage = make_storage()

        first = storage.save("photos/a.jpg", b"one", "image/jpeg")
        second = storage.save("photos/a.jpg", b"two", "image/jpeg")

        assert first != second
        assert storage.open(first) == b"one"

    def test_missing_file(self, make_storage):
        assert not make_storage().exists("photos/none.jpg")

    def test_signed_url_names_the_file(self, make_storage):
        storage = make_storage()
        name = storage.save("photos/a.jpg", b"x", "image/jpeg")

        assert name in storage.signed_url(name, 600)


class TestFakeUnitOfWork:
    def test_on_commit_runs_after_success(self):
        uow, calls = FakeUnitOfWork(), []

        with uow:
            uow.on_commit(lambda: calls.append("sent"))
            assert calls == []

        assert calls == ["sent"]
        assert uow.commits == 1

    def test_rollback_drops_callbacks(self):
        uow, calls = FakeUnitOfWork(), []

        def fail() -> None:
            with uow:
                uow.on_commit(lambda: calls.append("sent"))
                raise RuntimeError

        with pytest.raises(RuntimeError):
            fail()

        assert calls == []
        assert uow.rollbacks == 1


@pytest.mark.django_db(transaction=True)
class TestDjangoUnitOfWork:
    def test_commits(self):
        calls = []

        with DjangoUnitOfWork() as uow:
            Note.objects.create(title="a")
            uow.on_commit(lambda: calls.append("sent"))

        assert Note.objects.count() == 1
        assert calls == ["sent"]

    def test_rolls_back_on_error(self):
        calls = []

        def fail() -> None:
            with DjangoUnitOfWork() as uow:
                Note.objects.create(title="a")
                uow.on_commit(lambda: calls.append("sent"))
                raise RuntimeError

        with pytest.raises(RuntimeError):
            fail()

        assert Note.objects.count() == 0
        assert calls == []


def test_in_memory_audit_logger_records_entries():
    logger = InMemoryAuditLogger()

    logger.log("approve", model="testapp.Note", object_id=3, user_id=9)

    assert logger.actions() == ["approve"]
    assert logger.entries[0].object_id == "3"
