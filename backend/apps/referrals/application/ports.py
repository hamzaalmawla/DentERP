"""Ports of the referrals module (P0.5 outline; P1.7 may refine them inside the module).

Repository ports return DTOs; the ORM adapters live in ``infrastructure/``. Other modules are
reached through their facades only.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from apps.academics.application.facade import AcademicsFacade
from apps.core.application.ports import AuditLogger, Clock, Notifier, UnitOfWork
from apps.diagnosis.application.facade import DiagnosisFacade
from apps.patients.application.facade import PatientsFacade
from apps.setup.application.facade import SetupFacade
from apps.workcards.application.facade import WorkcardsFacade

from .dtos import ReferralDTO

__all__ = [
    "AcademicsFacade",  # eligible students (BR-05), supervisor scope (BR-07)
    "AuditLogger",
    "Clock",
    "DiagnosisFacade",  # approved plan items, plan item status
    "Notifier",
    "PatientsFacade",  # assignment for treatment
    "ReferralRepository",
    "SetupFacade",  # target clinic and treatment type departments
    "UnitOfWork",
    "WorkcardsFacade",  # create_case_from_referral
]


@runtime_checkable
class ReferralRepository(Protocol):
    def get(self, referral_id: int, *, for_update: bool = False) -> ReferralDTO | None: ...

    def open_referral_of(self, plan_item_id: int) -> ReferralDTO | None:
        """BR-04: the open referral that holds this plan item, if any."""
        ...

    def open_count(self, clinic_ids: Sequence[int] | None) -> int: ...
