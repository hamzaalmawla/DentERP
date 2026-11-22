"""Values of the referrals module that other modules read through its DTOs."""

from enum import StrEnum


class ReferralStatus(StrEnum):
    SENT = "sent"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    ASSIGNED = "assigned"
    IN_TREATMENT = "in_treatment"
    COMPLETED = "completed"


# A plan item may be in only one open referral at a time (BR-04).
OPEN_STATUSES: frozenset[ReferralStatus] = frozenset(
    {
        ReferralStatus.SENT,
        ReferralStatus.ACCEPTED,
        ReferralStatus.ASSIGNED,
        ReferralStatus.IN_TREATMENT,
    }
)
