"""Adapter of the ``UnitOfWork`` port over a database transaction."""

from collections.abc import Callable
from types import TracebackType
from typing import Self

from django.db import transaction


class DjangoUnitOfWork:
    def __init__(self) -> None:
        self._atomic = None

    def __enter__(self) -> Self:
        self._atomic = transaction.atomic()
        self._atomic.__enter__()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        atomic, self._atomic = self._atomic, None
        atomic.__exit__(exc_type, exc, traceback)

    def on_commit(self, callback: Callable[[], None]) -> None:
        transaction.on_commit(callback)
