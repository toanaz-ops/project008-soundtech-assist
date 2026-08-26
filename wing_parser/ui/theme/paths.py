"""Bundle-safe resource lookup.

In a frozen build sys._MEIPASS is the bundle root and the spec maps
wing_parser/ui/resources to the SAME relative position, so one lookup
serves both. Dev root = parents[2] of this file (repo root).

Moved verbatim out of wing_parser/ui/theme.py, which is being split
into this package; the module stays on disk only until the split
finishes and is shadowed by the package meanwhile.
"""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
    return root / "wing_parser" / "ui" / "resources" / name
