"""Builds the maintenance services with their real adapters (design section 5)."""

from .application.facade import MaintenanceFacade, MaintenanceFacadeService


def facade() -> MaintenanceFacade:
    """What other modules' containers pass to their services as the maintenance port."""
    return MaintenanceFacadeService()
