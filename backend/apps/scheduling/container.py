"""Builds the scheduling services with their real adapters (design section 5)."""

from .application.facade import SchedulingFacade, SchedulingFacadeService


def facade() -> SchedulingFacade:
    """What other modules' containers pass to their services as the scheduling port."""
    return SchedulingFacadeService()
