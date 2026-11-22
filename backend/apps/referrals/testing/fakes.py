"""In-memory fake of the referrals facade, for other modules' service tests.

referrals = InMemoryReferralsFacade()
referrals.add_referral(ReferralDTO(12, patient_id=3, from_clinic_id=1, to_clinic_id=2,
                                   referred_by_id=30, status=ReferralStatus.ASSIGNED,
                                   plan_item_ids=(9,), sent_at=now, assigned_student_id=40))
"""

from collections.abc import Sequence
from dataclasses import replace
from datetime import UTC, datetime

from apps.core.domain.errors import DomainError, NotFoundError
from apps.core.domain.i18n import _
from apps.referrals.application.dtos import ReferralDTO, ReferralStatus


class InMemoryReferralsFacade:
    def __init__(self, now: datetime | None = None) -> None:
        self.now = now or datetime(2026, 12, 1, 9, 0, tzinfo=UTC)
        self.referrals: dict[int, ReferralDTO] = {}

    def add_referral(self, referral: ReferralDTO) -> ReferralDTO:
        self.referrals[referral.id] = referral
        return referral

    # --- ReferralsFacade ----------------------------------------------------------------

    def get_referral(self, referral_id: int) -> ReferralDTO:
        try:
            return self.referrals[referral_id]
        except KeyError:
            raise NotFoundError() from None

    def mark_in_treatment(self, referral_id: int) -> ReferralDTO:
        referral = self.get_referral(referral_id)
        if referral.status == ReferralStatus.ASSIGNED:
            referral = self.referrals[referral_id] = replace(
                referral, status=ReferralStatus.IN_TREATMENT
            )
        return referral

    def complete_referral(self, referral_id: int) -> ReferralDTO:
        referral = self.get_referral(referral_id)
        if referral.status not in (ReferralStatus.ASSIGNED, ReferralStatus.IN_TREATMENT):
            raise DomainError("referral_not_in_treatment", _("The referral is not being treated."))
        referral = self.referrals[referral_id] = replace(
            referral, status=ReferralStatus.COMPLETED, completed_at=self.now
        )
        return referral

    def open_referrals_count(self, *, clinic_ids: Sequence[int] | None = None) -> int:
        return sum(
            1
            for r in self.referrals.values()
            if r.is_open and (clinic_ids is None or r.to_clinic_id in clinic_ids)
        )
