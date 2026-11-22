"""In-memory fakes of the setup facade, for service tests in any module."""

from .fakes import ChairStatusChange, InMemorySetupFacade

__all__ = ["ChairStatusChange", "InMemorySetupFacade"]
