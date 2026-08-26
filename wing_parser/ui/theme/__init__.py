"""Minimal theme package shim.

Task 1b-16 turns the single-module theme into a package so
`wing_parser.ui.theme.paths` and `...fonts` can exist while the rest of
the split (tokens, qss, palette, install) is still the NEXT task.
The old `wing_parser/ui/theme.py` stays on disk untouched but is
shadowed by this package; its two remaining functions are carried here
verbatim and it is deleted by the token-package task.
"""

from __future__ import annotations

from wing_parser.ui.theme.paths import resource_path


def load_stylesheet() -> str:
    return resource_path("theme.qss").read_text(encoding="utf-8")


def apply(app) -> None:
    app.setStyle("Fusion")
    from wing_parser.ui.theme import fonts

    fonts.load()
    app.setStyleSheet(load_stylesheet())
