"""Builds the referrals services with their real adapters (design section 5)."""

from .application.facade import ReferralsFacade, ReferralsFacadeService


def facade() -> ReferralsFacade:
    """What other modules' containers pass to their services as the referrals port."""
    return ReferralsFacadeService()
