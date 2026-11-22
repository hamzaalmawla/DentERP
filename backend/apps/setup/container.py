"""Builds the setup services with their real adapters (design section 5)."""

from .application.facade import SetupFacade, SetupFacadeService


def facade() -> SetupFacade:
    """What other modules' containers pass to their services as the setup port."""
    return SetupFacadeService()
