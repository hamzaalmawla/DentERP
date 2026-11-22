"""Ports of the diagnosis module (P0.5 outline; P1.4 may refine them inside the module).

Repository ports return DTOs; the ORM adapters live in ``infrastructure/``. Other modules are
reached through their facades only.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from apps.academics.application.facade import AcademicsFacade
from apps.core.application.ports import AuditLogger, Clock, Notifier, UnitOfWork
from apps.media.application.facade import MediaFacade
from apps.patients.application.facade import PatientsFacade
from apps.setup.application.facade import SetupFacade

from .dtos import DiagnosisSummaryDTO, MedicalAlertDTO, PlanItemDTO, PlanItemStatus

__all__ = [
    "AcademicsFacade",  # supervisor scope (BR-07)
    "AuditLogger",
    "Clock",
    "DiagnosisRepository",
    "MediaFacade",  # X-rays attached to the diagnosis
    "Notifier",
    "PatientsFacade",  # the patient is assigned to the student (BR-03)
    "PlanItemRepository",
    "SetupFacade",  # lookup lists, treatment type → department
    "UnitOfWork",
]


@runtime_checkable
class DiagnosisRepository(Protocol):
    """The diagnosis aggregate with its F1 sections."""

    def get_summary(self, diagnosis_id: int) -> DiagnosisSummaryDTO | None: ...

    def in_progress_for(self, patient_id: int) -> DiagnosisSummaryDTO | None:
        """BR-02: at most one diagnosis in progress per patient."""
        ...

    def alerts_of(self, patient_id: int) -> Sequence[MedicalAlertDTO]: ...


@runtime_checkable
class PlanItemRepository(Protocol):
    def get_many(self, plan_item_ids: Sequence[int]) -> Sequence[PlanItemDTO]: ...

    def of_diagnosis(self, diagnosis_id: int) -> Sequence[PlanItemDTO]: ...

    def set_status(
        self, plan_item_ids: Sequence[int], status: PlanItemStatus
    ) -> Sequence[PlanItemDTO]: ...
