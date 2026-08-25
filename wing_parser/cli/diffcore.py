"""Diff rows for the GUI: scene.diff() shaped for a table.

render.changes keeps its text job for the CLI; this module adds the
structured twin so the Diff page needs no subprocess and no parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from wing_parser.cli.render import level


@dataclass(frozen=True)
class DiffRow:
    path: str
    before: str
    after: str
    magnitude: float | None


def _fmt(value) -> str:
    if isinstance(value, float):
        return level(value)
    return str(value)


def _natural(path: str) -> tuple[object, ...]:
    """Sort key that orders ch.2 before ch.10 rather than after it."""
    return tuple(int(part) if part.isdigit() else part
                 for part in re.split(r"(\d+)", path))


def diff_rows(before_scene, after_scene) -> tuple[DiffRow, ...]:
    changes = before_scene.diff(after_scene)
    rows = tuple(
        DiffRow(
            path=change.path,
            before=_fmt(change.before),
            after=_fmt(change.after),
            magnitude=change.magnitude,
        )
        for change in changes
    )
    return tuple(sorted(rows, key=lambda row: _natural(row.path)))
