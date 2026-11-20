"""Ports shared by every module.

Services receive these through their constructor (built in each module's ``container.py``).
Core's adapters live in ``core/infrastructure``; the in-memory fakes used by service tests live
in ``core/testing``. Every port is ``runtime_checkable`` so a test can check that a fake or an
adapter fits it.
"""

from collections.abc import Callable, Mapping, Sequence
from datetime import date, datetime
from types import TracebackType
from typing import Any, BinaryIO, Protocol, Self, runtime_checkable

from .dtos import NotificationTarget


@runtime_checkable
class Clock(Protocol):
    """The current time. Services never call ``datetime.now()`` themselves."""

    def now(self) -> datetime:
        """The current moment, timezone-aware."""
        ...

    def today(self) -> date:
        """Today's date in the clinic's time zone (Asia/Damascus)."""
        ...


@runtime_checkable
class Notifier(Protocol):
    """Sends an in-app notification, and a push where the user has a device (SYS-03).

    ``title_key`` and ``body_key`` name translatable messages; ``params`` fill their
    placeholders, so each recipient sees the text in their own language.
    """

    def notify(
        self,
        recipient_ids: Sequence[int],
        type: str,
        title_key: str,
        body_key: str,
        params: Mapping[str, Any] | None = None,
        target: NotificationTarget | None = None,
    ) -> None: ...


@runtime_checkable
class FileStorage(Protocol):
    """Private file storage (photos, X-rays). Files are reached only through signed links."""

    def save(self, name: str, content: BinaryIO | bytes, content_type: str) -> str:
        """Store the file and return the name it was stored under (it may differ from ``name``)."""
        ...

    def open(self, name: str) -> bytes: ...

    def exists(self, name: str) -> bool: ...

    def signed_url(self, name: str, expires_in_seconds: int) -> str:
        """A link that gives read access to the file until it expires."""
        ...


@runtime_checkable
class UnitOfWork(Protocol):
    """Runs a service's writes in one transaction.

    ``with uow:`` commits on success and rolls back on an exception. ``on_commit`` runs a
    callback (for example sending a push notification) only after the transaction commits.
    """

    def __enter__(self) -> Self: ...

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None: ...

    def on_commit(self, callback: Callable[[], None]) -> None: ...


@runtime_checkable
class AuditLogger(Protocol):
    """Writes one audit log row (SYS-04).

    ``model`` is ``"app_label.ModelName"``; ``changes`` is the diff from
    ``apps.core.domain.audit.diff``. When ``user_id`` is not given, the adapter uses the user of
    the current request or ``acting_as`` block; the client IP is taken from the request.
    """

    def log(
        self,
        action: str,
        *,
        model: str = "",
        object_id: int | str | None = None,
        changes: Mapping[str, Any] | None = None,
        user_id: int | None = None,
    ) -> None: ...
