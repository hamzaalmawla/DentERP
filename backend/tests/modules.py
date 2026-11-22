"""The modules of the system and their P0.5 contracts, shared by the project-level tests."""

from dataclasses import dataclass
from importlib import import_module

# Every module of design section 5 except core and accounts (phase 0), in build order.
MODULES = (
    "setup",
    "academics",
    "patients",
    "diagnosis",
    "referrals",
    "workcards",
    "media",
    "scheduling",
    "maintenance",
    "notifications",
    "reports",
)

ALL_MODULES = ("core", "accounts", *MODULES)


@dataclass(frozen=True)
class Contract:
    module: str
    protocol: type
    service: type
    fake: type


def _title(module: str) -> str:
    return module.capitalize()


def contract_of(module: str) -> Contract:
    """``SetupFacade``, ``SetupFacadeService`` and ``InMemorySetupFacade`` for ``"setup"``."""
    facade = import_module(f"apps.{module}.application.facade")
    fakes = import_module(f"apps.{module}.testing")
    name = _title(module)
    return Contract(
        module=module,
        protocol=getattr(facade, f"{name}Facade"),
        service=getattr(facade, f"{name}FacadeService"),
        fake=getattr(fakes, f"InMemory{name}Facade"),
    )
