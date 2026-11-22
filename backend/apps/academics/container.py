"""Builds the academics services with their real adapters (design section 5)."""

from .application.facade import AcademicsFacade, AcademicsFacadeService


def facade() -> AcademicsFacade:
    """What other modules' containers pass to their services as the academics port."""
    return AcademicsFacadeService()
