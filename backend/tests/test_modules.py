"""Every module has the layout of design section 5, is installed, and is routed (P0.5)."""

from importlib import import_module

import pytest
from django.apps import apps
from django.conf import settings

from config import api_v1

from .modules import MODULES, contract_of

APPS_DIR = settings.BASE_DIR / "apps"

FOLDERS = ("domain", "application", "infrastructure", "api", "testing", "tests", "migrations")
FILES = (
    "apps.py",
    "models.py",
    "admin.py",
    "container.py",
    "application/ports.py",
    "application/dtos.py",
    "application/facade.py",
    "application/services.py",
    "application/queries.py",
    "api/urls.py",
    "api/views.py",
    "testing/fakes.py",
)
SUBMODULES = (
    "domain",
    "application.ports",
    "application.dtos",
    "application.facade",
    "application.services",
    "application.queries",
    "infrastructure",
    "api.urls",
    "api.views",
    "testing",
    "admin",
    "container",
    "models",
)


def test_the_modules_folder_holds_exactly_the_planned_modules():
    found = {path.name for path in APPS_DIR.iterdir() if (path / "apps.py").exists()}

    assert found == {"core", "accounts", *MODULES}


@pytest.mark.parametrize("module", MODULES)
class TestModule:
    def test_has_the_layout(self, module):
        root = APPS_DIR / module

        missing = [f for f in FOLDERS if not (root / f / "__init__.py").exists()]
        missing += [f for f in FILES if not (root / f).exists()]
        assert missing == []

    def test_is_installed(self, module):
        config = apps.get_app_config(module)

        assert config.name == f"apps.{module}"
        assert f"apps.{module}" in settings.INSTALLED_APPS

    @pytest.mark.parametrize("submodule", SUBMODULES)
    def test_imports(self, module, submodule):
        import_module(f"apps.{module}.{submodule}")

    def test_its_routes_are_included(self, module):
        included = {getattr(p.urlconf_name, "__name__", p.urlconf_name) for p in api_v1.urlpatterns}

        assert f"apps.{module}.api.urls" in included

    def test_the_container_builds_the_facade(self, module):
        contract = contract_of(module)

        facade = import_module(f"apps.{module}.container").facade()

        assert isinstance(facade, contract.protocol)
