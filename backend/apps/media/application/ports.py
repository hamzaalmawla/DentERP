"""Ports of the media module (P0.5 outline; P1.5 may refine them inside the module).

Files are stored through core's ``FileStorage`` port. Scope checks ask the module that owns
the record (patients, diagnosis, workcards, maintenance) through its facade.

Media is called by diagnosis, workcards and maintenance, and asks them about scope; to keep
the facades free of import cycles, ``ports.py`` imports facades, and facades import only their
own DTOs and core.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from apps.core.application.ports import AuditLogger, Clock, FileStorage, UnitOfWork
from apps.diagnosis.application.facade import DiagnosisFacade
from apps.maintenance.application.facade import MaintenanceFacade
from apps.patients.application.facade import PatientsFacade
from apps.setup.application.facade import SetupFacade
from apps.workcards.application.facade import WorkcardsFacade

from .dtos import MediaDTO, MediaOwner

__all__ = [
    "AuditLogger",
    "Clock",
    "DiagnosisFacade",  # may the user see this diagnosis
    "FileStorage",
    "MaintenanceFacade",  # may the user see this ticket
    "MediaRepository",
    "PatientsFacade",  # may the user see this patient
    "SetupFacade",  # upload size limit (SystemSetting)
    "ThumbnailQueue",
    "UnitOfWork",
    "WorkcardsFacade",  # may the user see this case
]


@runtime_checkable
class MediaRepository(Protocol):
    def get_many(self, media_ids: Sequence[int]) -> Sequence[MediaDTO]: ...

    def by_idempotency_key(self, key: str) -> MediaDTO | None: ...

    def of_owner(self, owner: MediaOwner) -> Sequence[MediaDTO]: ...

    def attach(self, media_ids: Sequence[int], owner: MediaOwner) -> Sequence[MediaDTO]: ...


@runtime_checkable
class ThumbnailQueue(Protocol):
    def make_thumbnail(self, media_id: int) -> None:
        """Queue the thumbnail (a Celery task) after the upload commits."""
        ...
