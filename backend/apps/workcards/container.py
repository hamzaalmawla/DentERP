"""Builds the workcards services with their real adapters (design section 5)."""

from .application.facade import WorkcardsFacade, WorkcardsFacadeService


def facade() -> WorkcardsFacade:
    """What other modules' containers pass to their services as the workcards port."""
    return WorkcardsFacadeService()
