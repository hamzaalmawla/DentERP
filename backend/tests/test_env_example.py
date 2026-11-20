"""deploy/.env.example lists every environment variable the settings read."""

import re
from pathlib import Path

import pytest

BACKEND_DIR = Path(__file__).resolve().parent.parent
SETTINGS_DIR = BACKEND_DIR / "config" / "settings"
ENV_EXAMPLE = BACKEND_DIR.parent / "deploy" / ".env.example"

ENV_CALL = re.compile(r"""\benv(?:_bool|_int|_list)?\(\s*["']([A-Z0-9_]+)["']""")


def variables_read_by_settings() -> set[str]:
    names: set[str] = set()
    for path in SETTINGS_DIR.glob("*.py"):
        names.update(ENV_CALL.findall(path.read_text()))
    return names


def variables_in_env_example() -> set[str]:
    names = set()
    for line in ENV_EXAMPLE.read_text().splitlines():
        line = line.strip().lstrip("#").strip()
        if "=" in line and re.fullmatch(r"[A-Z0-9_]+", line.split("=", 1)[0]):
            names.add(line.split("=", 1)[0])
    return names


@pytest.mark.skipif(not ENV_EXAMPLE.exists(), reason="deploy/ is not mounted in this container")
def test_env_example_lists_every_variable_the_settings_read():
    read = variables_read_by_settings()

    assert "DJANGO_SECRET_KEY" in read  # the pattern finds the calls
    assert read - variables_in_env_example() == set()
