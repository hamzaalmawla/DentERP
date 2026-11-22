"""The module boundary rule (design section 5, CLAUDE.md). Kept for the whole project.

A module never imports another module's ``models.py``, ``infrastructure/`` or anything else
inside it; it calls that module's facade. Allowed across modules:

- ``apps.core`` from any module: the base every module builds on (``BaseModel``, the shared
  ports, the error format, ``acting_as``, …). Core itself imports no other module.
- ``apps.<other>.application.facade`` and ``apps.<other>.application.dtos`` from anywhere.
- ``apps.<other>.container`` from the module's own ``container.py`` only, to pass the other
  module's facade to its services.
- ``apps.accounts.api`` (permission classes, ``request_actor``) from the module's ``api/``.
- ``apps.accounts.dashboard.navigation`` (``register_screen``) from the module's ``admin.py``.

Tests (``tests/``) and migrations are not checked: tests may use other modules' fakes in
``testing/``.
"""

import ast
from pathlib import Path

import pytest
from django.conf import settings

from .modules import ALL_MODULES

APPS_DIR = settings.BASE_DIR / "apps"
SKIPPED_FOLDERS = {"tests", "migrations"}


def _allowed(module: str, file: str, imported: str) -> bool:
    parts = imported.split(".")
    if parts[0] != "apps":
        return True  # not one of our modules
    if len(parts) < 2:
        return False  # "from apps import diagnosis" is checked as apps.diagnosis
    target, inside = parts[1], parts[2:]
    if target == module:
        return True
    if module == "core":
        return False  # core is the base: it knows no other module
    if target == "core":
        return True
    if inside[:2] in (["application", "facade"], ["application", "dtos"]):
        return True
    if inside[:1] == ["container"]:
        return file == "container.py"
    if target == "accounts" and inside[:1] == ["api"]:
        return file.startswith("api/")
    if target == "accounts" and inside[:2] == ["dashboard", "navigation"]:
        return file == "admin.py"
    return False


def _imported_names(tree: ast.AST, package: str) -> list[tuple[int, list[str]]]:
    """Each import as the names it could mean: ``from a.b import c`` is ``a.b`` or ``a.b.c``."""
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found += [(node.lineno, [alias.name]) for alias in node.names]
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                anchor = package.split(".")[: len(package.split(".")) - node.level + 1]
                base = ".".join([*anchor, base] if base else anchor)
            found += [(node.lineno, [base, f"{base}.{alias.name}"]) for alias in node.names]
    return found


def violations(module: str, file: str, source: str) -> list[str]:
    """The imports of ``apps/<module>/<file>`` that break the rule."""
    package = ".".join(["apps", module, *Path(file).with_suffix("").parts[:-1]])
    if Path(file).name == "__init__.py":
        package = ".".join(["apps", module, *Path(file).parent.parts])
    return [
        f"apps/{module}/{file}:{line} imports {names[-1]}"
        for line, names in _imported_names(ast.parse(source), package)
        if not any(_allowed(module, file, name) for name in names)
    ]


def _source_files(module: str):
    root = APPS_DIR / module
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if not SKIPPED_FOLDERS & set(relative.parts):
            yield relative.as_posix(), path.read_text(encoding="utf-8")


@pytest.mark.parametrize("module", ALL_MODULES)
def test_modules_only_import_each_others_facades(module):
    found = [v for file, source in _source_files(module) for v in violations(module, file, source)]

    assert found == []


class TestTheRuleItself:
    @pytest.mark.parametrize(
        ("module", "file", "source"),
        [
            ("workcards", "application/services.py", "from apps.referrals.models import Referral"),
            ("workcards", "application/services.py", "import apps.referrals.models"),
            ("workcards", "infrastructure/repositories.py", "from apps.setup import models"),
            ("workcards", "api/views.py", "from apps.diagnosis.infrastructure.repos import X"),
            ("workcards", "application/services.py", "from apps.diagnosis.domain import rules"),
            ("workcards", "application/services.py", "from apps import diagnosis"),
            ("workcards", "application/ports.py", "from apps.setup.application.services import A"),
            ("workcards", "application/services.py", "from apps.setup.container import facade"),
            ("workcards", "application/services.py", "from apps.accounts.api import permissions"),
            ("workcards", "admin.py", "from apps.accounts.models import User"),
            ("workcards", "api/views.py", "from apps.accounts.dashboard.navigation import Group"),
            ("core", "models.py", "from apps.accounts.application.facade import X"),
        ],
    )
    def test_refused(self, module, file, source):
        assert violations(module, file, source)

    @pytest.mark.parametrize(
        ("module", "file", "source"),
        [
            ("workcards", "application/ports.py", "from apps.setup.application.facade import S"),
            ("workcards", "application/services.py", "from apps.setup.application import dtos"),
            ("workcards", "container.py", "from apps.setup import container as setup"),
            ("workcards", "api/views.py", "from apps.accounts.api.permissions import IsStudent"),
            ("workcards", "admin.py", "from apps.accounts.dashboard.navigation import Group"),
            ("workcards", "admin.py", "from apps.core.dashboard import DashboardModelAdmin"),
            ("workcards", "models.py", "from apps.core.models import BaseModel"),
            ("workcards", "application/services.py", "from .ports import CaseRepository"),
            ("workcards", "api/views.py", "from ..application import facade"),
            ("workcards", "application/services.py", "from django.db import models"),
        ],
    )
    def test_allowed(self, module, file, source):
        assert violations(module, file, source) == []

    def test_a_relative_import_cannot_leave_the_module(self):
        assert violations("workcards", "api/views.py", "from ...referrals import models")
