"""The theme package: tokens, generated QSS, palette, install.

Public surface (kept stable for existing imports):
  resource_path(name)  -- bundle-safe resource lookup (paths.py)
  load_stylesheet()    -- the fully substituted stylesheet (qss.py)
  apply(app)           -- fonts + palette + icons + stylesheet (install.py)
"""

from __future__ import annotations

from wing_parser.ui.theme.install import apply
from wing_parser.ui.theme.paths import resource_path
from wing_parser.ui.theme.qss import build

_SUBSTITUTED = None


def load_stylesheet() -> str:
    """Cached so repeated calls do not re-substitute the template."""
    global _SUBSTITUTED
    if _SUBSTITUTED is None:
        _SUBSTITUTED = build()
    return _SUBSTITUTED


__all__ = ["resource_path", "load_stylesheet", "apply"]
