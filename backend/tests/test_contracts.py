"""The facades are the contract between the tracks (P0.5, docs/contracts.md).

The in-memory fake and the service of each facade must fit its Protocol exactly: the same
public functions, with the same parameters, defaults and types. A track that changes a facade
changes all three, and docs/contracts.md.
"""

import inspect
from dataclasses import fields, is_dataclass
from importlib import import_module

import pytest

from .modules import BUILT_MODULES, MODULES, contract_of

CONTRACTS = [contract_of(module) for module in MODULES]


def _functions(protocol: type) -> list[str]:
    return sorted(
        name
        for name in dir(protocol)
        if not name.startswith("_") and inspect.isfunction(getattr(protocol, name))
    )


def _ids(contract) -> str:
    return contract.module


@pytest.mark.parametrize("contract", CONTRACTS, ids=_ids)
class TestFacadeContract:
    def test_the_protocol_has_functions(self, contract):
        assert _functions(contract.protocol)

    def test_the_fake_satisfies_the_protocol(self, contract):
        assert isinstance(contract.fake(), contract.protocol)

    def test_the_container_builds_the_service(self, contract):
        service = contract.build()

        assert isinstance(service, contract.service)
        assert isinstance(service, contract.protocol)

    @pytest.mark.parametrize("implementation", ["fake", "service"])
    def test_signatures_match_the_protocol(self, contract, implementation):
        cls = getattr(contract, implementation)
        for name in _functions(contract.protocol):
            expected = inspect.signature(getattr(contract.protocol, name))
            actual = inspect.signature(getattr(cls, name))
            assert actual == expected, f"{cls.__name__}.{name}{actual} != {expected}"


@pytest.mark.parametrize(
    "contract", [c for c in CONTRACTS if c.module not in BUILT_MODULES], ids=_ids
)
def test_a_service_not_built_yet_says_so(contract):
    """Until its build prompt, every function of a facade raises ``NotImplementedError``
    (built modules test their facade themselves)."""
    service = contract.build()
    for name in _functions(contract.protocol):
        parameters = list(inspect.signature(getattr(service, name)).parameters.values())
        arguments = [None] * sum(
            p.kind is p.POSITIONAL_OR_KEYWORD and p.default is p.empty for p in parameters
        )
        keywords = {
            p.name: None for p in parameters if p.kind is p.KEYWORD_ONLY and p.default is p.empty
        }
        with pytest.raises(NotImplementedError):
            getattr(service, name)(*arguments, **keywords)


@pytest.mark.parametrize("module", MODULES)
def test_dtos_are_frozen_dataclasses(module):
    dtos = import_module(f"apps.{module}.application.dtos")
    classes = [
        value
        for name in dtos.__all__
        if inspect.isclass(value := getattr(dtos, name)) and is_dataclass(value)
    ]

    assert classes, "a module gives at least one DTO"
    for cls in classes:
        assert cls.__dataclass_params__.frozen, f"{cls.__name__} is not frozen"
        for field in fields(cls):
            assert "Model" not in str(field.type), f"{cls.__name__}.{field.name} is a model"
