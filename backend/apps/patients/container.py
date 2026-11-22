"""Builds the patients services with their real adapters (design section 5)."""

from .application.facade import PatientsFacade, PatientsFacadeService


def facade() -> PatientsFacade:
    """What other modules' containers pass to their services as the patients port."""
    return PatientsFacadeService()
