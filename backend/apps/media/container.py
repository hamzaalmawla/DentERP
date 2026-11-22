"""Builds the media services with their real adapters (design section 5)."""

from .application.facade import MediaFacade, MediaFacadeService


def facade() -> MediaFacade:
    """What other modules' containers pass to their services as the media port."""
    return MediaFacadeService()
