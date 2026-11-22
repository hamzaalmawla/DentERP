"""Builds the reports services with their real adapters (design section 5)."""

from .application.facade import ReportsFacade, ReportsFacadeService


def facade() -> ReportsFacade:
    """What the dashboard home page uses for its figures (P1.11)."""
    return ReportsFacadeService()
