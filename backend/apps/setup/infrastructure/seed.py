"""The default records for ``seed_defaults``, read from ``apps/setup/seed/defaults.json``.

The file is data, not code: the clinic can correct a name or a time there (or later in the
dashboard) without a code change.
"""

import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

DEFAULTS_FILE = Path(__file__).resolve().parent.parent / "seed" / "defaults.json"


class JsonSeedSource:
    def __init__(self, path: Path = DEFAULTS_FILE) -> None:
        self._path = path

    def load(self) -> Mapping[str, Any]:
        return json.loads(self._path.read_text(encoding="utf-8"))
