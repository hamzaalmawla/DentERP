"""The reports module's public functions (P0.5 contract, docs/contracts.md).

Reports has no tables: it reads the other modules through their facades and applies the
actor's scope. The dashboard home page (accounts' dashboard shell) shows ``home_figures``.
"""

from typing import Protocol, runtime_checkable

from apps.core.application.dtos import Actor

from .dtos import HomeFiguresDTO


@runtime_checkable
class ReportsFacade(Protocol):
    def home_figures(self, actor: Actor) -> HomeFiguresDTO:
        """The key figures for the actor's role and scope (DB-16)."""
        ...


class ReportsFacadeService:
    """The reports facade the container hands out. Built in P1.11."""

    def home_figures(self, actor: Actor) -> HomeFiguresDTO:
        raise NotImplementedError
