"""In-memory fakes of the ports in ``apps.core.application.ports``.

They behave like the real adapters and remember what they were asked to do, so a test can
check it:

    clock = FixedClock(datetime(2026, 12, 1, 9, 0, tzinfo=UTC))
    notifier = FakeNotifier()
    service = SubmitDiagnosis(repo, clock=clock, notifier=notifier, uow=FakeUnitOfWork())
    service.execute(command)
    assert notifier.sent[0].type == "diagnosis_submitted"
"""

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from types import TracebackType
from typing import Any, BinaryIO, Self
from zoneinfo import ZoneInfo

from apps.core.application.dtos import NotificationTarget

CLINIC_TIME_ZONE = ZoneInfo("Asia/Damascus")


class FixedClock:
    """A clock that stands still until the test moves it."""

    def __init__(self, now: datetime | None = None) -> None:
        self._now = now or datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
        if self._now.tzinfo is None:
            raise ValueError("FixedClock needs a timezone-aware datetime.")

    def now(self) -> datetime:
        return self._now

    def today(self) -> date:
        return self._now.astimezone(CLINIC_TIME_ZONE).date()

    def set(self, now: datetime) -> None:
        self._now = now

    def advance(self, **delta: float) -> None:
        self._now += timedelta(**delta)


@dataclass(frozen=True)
class SentNotification:
    recipient_ids: tuple[int, ...]
    type: str
    title_key: str
    body_key: str
    params: Mapping[str, Any]
    target: NotificationTarget | None


class FakeNotifier:
    def __init__(self) -> None:
        self.sent: list[SentNotification] = []

    def notify(
        self,
        recipient_ids: Sequence[int],
        type: str,
        title_key: str,
        body_key: str,
        params: Mapping[str, Any] | None = None,
        target: NotificationTarget | None = None,
    ) -> None:
        self.sent.append(
            SentNotification(
                tuple(recipient_ids), type, title_key, body_key, dict(params or {}), target
            )
        )


@dataclass
class _StoredFile:
    content: bytes
    content_type: str


class InMemoryFileStorage:
    def __init__(self) -> None:
        self.files: dict[str, _StoredFile] = {}

    def save(self, name: str, content: BinaryIO | bytes, content_type: str) -> str:
        data = content if isinstance(content, bytes) else content.read()
        stored_name, suffix = name, 1
        while stored_name in self.files:  # like the real storage, never overwrite
            stem, dot, extension = name.rpartition(".")
            stored_name = f"{stem}_{suffix}{dot}{extension}" if dot else f"{name}_{suffix}"
            suffix += 1
        self.files[stored_name] = _StoredFile(data, content_type)
        return stored_name

    def open(self, name: str) -> bytes:
        try:
            return self.files[name].content
        except KeyError:
            raise FileNotFoundError(name) from None

    def exists(self, name: str) -> bool:
        return name in self.files

    def signed_url(self, name: str, expires_in_seconds: int) -> str:
        return f"memory://{name}?expires_in={expires_in_seconds}"


class FakeUnitOfWork:
    """Counts commits and rollbacks; ``on_commit`` callbacks run only after a commit."""

    def __init__(self) -> None:
        self.commits = 0
        self.rollbacks = 0
        self._pending: list[Callable[[], None]] = []

    def __enter__(self) -> Self:
        self._pending = []
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        pending, self._pending = self._pending, []
        if exc_type is not None:
            self.rollbacks += 1
            return
        self.commits += 1
        for callback in pending:
            callback()

    def on_commit(self, callback: Callable[[], None]) -> None:
        self._pending.append(callback)


@dataclass(frozen=True)
class AuditEntry:
    action: str
    model: str
    object_id: str
    changes: Mapping[str, Any]
    user_id: int | None


@dataclass
class InMemoryAuditLogger:
    entries: list[AuditEntry] = field(default_factory=list)

    def log(
        self,
        action: str,
        *,
        model: str = "",
        object_id: int | str | None = None,
        changes: Mapping[str, Any] | None = None,
        user_id: int | None = None,
    ) -> None:
        self.entries.append(
            AuditEntry(
                str(action),
                model,
                "" if object_id is None else str(object_id),
                dict(changes or {}),
                user_id,
            )
        )

    def actions(self) -> list[str]:
        return [entry.action for entry in self.entries]
