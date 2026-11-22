"""Ports of the workcards module (P0.5 outline; P1.6 may refine them inside the module).

Repository ports return DTOs; the ORM adapters live in ``infrastructure/``. Other modules are
reached through their facades only.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from apps.academics.application.facade import AcademicsFacade
from apps.core.application.ports import AuditLogger, Clock, Notifier, UnitOfWork
from apps.diagnosis.application.facade import DiagnosisFacade
from apps.media.application.facade import MediaFacade
from apps.patients.application.facade import PatientsFacade
from apps.referrals.application.facade import ReferralsFacade
from apps.setup.application.facade import SetupFacade

from .dtos import CaseDTO, StepDTO, WorkCardDTO

__all__ = [
    "AcademicsFacade",  # step templates, grading, requirements, supervisor scope
    "AuditLogger",
    "CaseRepository",
    "Clock",
    "DiagnosisFacade",  # plan item → done; submitted diagnoses for the approvals queue
    "MediaFacade",  # step photos and X-rays
    "Notifier",
    "PatientsFacade",  # assignments on transfer
    "ReferralsFacade",  # referral → in treatment, completed
    "SetupFacade",  # treatment type → case type
    "StepRepository",
    "UnitOfWork",
    "WorkCardRepository",
]


@runtime_checkable
class WorkCardRepository(Protocol):
    def get_for_enrollment(self, enrollment_id: int) -> WorkCardDTO | None: ...

    def create(self, enrollment_id: int, student_id: int, course_id: int) -> WorkCardDTO: ...


@runtime_checkable
class CaseRepository(Protocol):
    def get(self, case_id: int, *, for_update: bool = False) -> CaseDTO | None: ...

    def for_referral(self, referral_id: int) -> CaseDTO | None: ...

    def open_for(self, patient_id: int, student_id: int) -> Sequence[CaseDTO]: ...


@runtime_checkable
class StepRepository(Protocol):
    def get(self, step_id: int, *, for_update: bool = False) -> StepDTO | None: ...

    def of_case(self, case_id: int) -> Sequence[StepDTO]: ...
