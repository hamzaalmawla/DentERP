"""What the referrals module gives other modules (P0.5 contract). Frozen dataclasses only."""

from dataclasses import dataclass
from datetime import datetime

from apps.referrals.domain.values import OPEN_STATUSES, ReferralStatus

__all__ = ["OPEN_STATUSES", "ReferralDTO", "ReferralStatus"]


@dataclass(frozen=True, slots=True)
class ReferralDTO:
    id: int
    patient_id: int
    from_clinic_id: int
    to_clinic_id: int
    referred_by_id: int
    status: ReferralStatus
    plan_item_ids: tuple[int, ...]
    sent_at: datetime
    assigned_student_id: int | None = None
    accepted_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def is_open(self) -> bool:
        return self.status in OPEN_STATUSES
