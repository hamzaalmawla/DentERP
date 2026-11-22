"""Builds the diagnosis services with their real adapters (design section 5)."""

from .application.facade import DiagnosisFacade, DiagnosisFacadeService


def facade() -> DiagnosisFacade:
    """What other modules' containers pass to their services as the diagnosis port."""
    return DiagnosisFacadeService()
