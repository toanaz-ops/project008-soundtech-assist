"""Bundle-safe resource lookup.

In a frozen build sys._MEIPASS is the bundle root and the spec maps
wing_parser/ui/resources to the SAME relative position, so one lookup
serves both. Dev root = parents[3] of this file (repo root: theme/
paths.py sits four levels below it).
"""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    return root / "wing_parser" / "ui" / "resources" / name
