"""An ordered record of edits, held instead of applied.

The application never mutates the document it loaded. It keeps the
original and this list, and re-derives everything after every change.
Three things follow, and they are why the shape was chosen over
mutating in place:

  1. Undo is dropping the last patch and re-deriving.
  2. "What have I changed?" is this list, reviewable before saving,
     rather than a diff the operator must compute against a file.
  3. It is the bridge to the live-console work. Writing
     ae_data.ch.1.send.8.mode = "PRE" into a file and sending the
     equivalent OSC message to a running WING are the same patch
     leaving through two different doors.

`before` is captured by the caller when the patch is made, never
recomputed at save time, so the journal stays a truthful record of what
the operator was looking at when they decided.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Patch:
    path: str
    before: Any
    after: Any
    because: str
    label: str


class EditJournal:
    def __init__(self) -> None:
        self._patches: list[Patch] = []

    def append(self, patch: Patch) -> None:
        self._patches.append(patch)

    def undo(self) -> Patch | None:
        """None on an empty journal: Undo is always present in the menu,
        and an empty journal is a normal state rather than an error."""
        return self._patches.pop() if self._patches else None

    def patches(self) -> tuple[Patch, ...]:
        return tuple(self._patches)

    def __len__(self) -> int:
        return len(self._patches)

    def __bool__(self) -> bool:
        return bool(self._patches)
