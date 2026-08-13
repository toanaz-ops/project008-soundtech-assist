"""Load descriptor YAML files.

Descriptors say what a value means. Schema says where a value is and
whether it is well formed. Keeping them apart is what lets a user add a
new EQ model or tap point without touching Python.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

DATA_DIR = Path(__file__).resolve().parent / "data"


@lru_cache(maxsize=None)
def load(name: str) -> dict[str, Any]:
    path = DATA_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"no descriptor named {name!r} in {DATA_DIR}")
    return yaml.safe_load(path.read_text(encoding="utf-8"))
