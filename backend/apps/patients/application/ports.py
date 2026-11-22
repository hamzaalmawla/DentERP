"""Ports of the patients module (P0.5 outline; P1.3 may refine them inside the module).

Repository ports return DTOs; the ORM adapters live in ``infrastructure/``. Other modules are
reached through their facades only.
"""

from collections.abc import Sequence
from datetime import datetime
from typing import Protocol, runtime_checkable

from apps.academics.application.facade import AcademicsFacade
from apps.core.application.ports import AuditLogger, Clock, Notifier, UnitOfWork
from apps.diagnosis.application.facade import DiagnosisFacade
from apps.setup.application.facade import SetupFacade
from apps.workcards.application.facade import WorkcardsFacade

from .dtos import AssignmentDTO, AssignmentPurpose, PatientSummaryDTO

__all__ = [
    "AcademicsFacade",  # supervisor scope for the diagnosis queue and transfers
    "AssignmentRepository",
    "AuditLogger",
    "Clock",
    "DiagnosisFacade",  # medical alerts on the patient record
    "DiagnosisQueueRepository",
    "FileNumberGenerator",
    "Notifier",
    "PatientRepository",
    "SetupFacade",  # diagnosis clinics
    "UnitOfWork",
    "WorkcardsFacade",  # transfer_open_cases
]


@runtime_checkable
class PatientRepository(Protocol):
    def get(self, patient_id: int) -> PatientSummaryDTO | None: ...

    def national_id_exists(self, national_id: str) -> bool: ...

    def same_name_and_phone(self, full_name: str, phone: str) -> Sequence[PatientSummaryDTO]: ...


@runtime_checkable
class FileNumberGenerator(Protocol):
    def next_file_no(self, year: int) -> str:
        """The next file number of the year, e.g. ``2026-000123``; safe under concurrency."""
        ...


@runtime_checkable
class AssignmentRepository(Protocol):
    def active_for(self, patient_id: int) -> Sequence[AssignmentDTO]: ...

    def create(
        self,
        patient_id: int,
        student_id: int,
        purpose: AssignmentPurpose,
        case_id: int | None,
        at: datetime,
    ) -> AssignmentDTO: ...

    def end(self, assignment_id: int, at: datetime) -> AssignmentDTO: ...


@runtime_checkable
class DiagnosisQueueRepository(Protocol):
    def has_waiting_entry(self, patient_id: int) -> bool: ...

    def waiting_count(self, clinic_ids: Sequence[int] | None) -> int: ...
