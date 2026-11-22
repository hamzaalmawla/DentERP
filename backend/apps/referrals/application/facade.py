"""The referrals module's public functions (P0.5 contract, docs/contracts.md).

Other modules call these, never referrals' models or repositories. Every function takes and
returns ids and DTOs. A missing referral raises ``NotFoundError``.
"""

from collections.abc import Sequence
from typing import Protocol, runtime_checkable

from .dtos import ReferralDTO


@runtime_checkable
class ReferralsFacade(Protocol):
    def get_referral(self, referral_id: int) -> ReferralDTO: ...

    def mark_in_treatment(self, referral_id: int) -> ReferralDTO:
        """assigned → in treatment, when the first step of its case is submitted. A referral
        already in treatment is returned unchanged."""
        ...

    def complete_referral(self, referral_id: int) -> ReferralDTO:
        """→ completed, called by ``CompleteCase`` (BR-08); notifies the referring clinic.
        ``DomainError("referral_not_in_treatment")`` from any state but assigned or in
        treatment."""
        ...

    def open_referrals_count(self, *, clinic_ids: Sequence[int] | None = None) -> int:
        """Open referrals sent to these clinics, or to all (home figures, DB-16)."""
        ...


class ReferralsFacadeService:
    """The referrals facade the container hands out. Built in P1.7."""

    def get_referral(self, referral_id: int) -> ReferralDTO:
        raise NotImplementedError

    def mark_in_treatment(self, referral_id: int) -> ReferralDTO:
        raise NotImplementedError

    def complete_referral(self, referral_id: int) -> ReferralDTO:
        raise NotImplementedError

    def open_referrals_count(self, *, clinic_ids: Sequence[int] | None = None) -> int:
        raise NotImplementedError
