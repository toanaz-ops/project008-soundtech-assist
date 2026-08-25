"""Bundle-safe resources and the one stylesheet application point.

In a frozen build sys._MEIPASS is the bundle root and the spec maps
wing_parser/ui/resources to the SAME relative position, so one lookup
serves both. Dev root = parents[2] of this file (repo root).
"""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(name: str) -> Path:
    root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return root / "wing_parser" / "ui" / "resources" / name


def load_stylesheet() -> str:
    return resource_path("theme.qss").read_text(encoding="utf-8")


def apply(app) -> None:
    app.setStyle("Fusion")
    app.setStyleSheet(load_stylesheet())
