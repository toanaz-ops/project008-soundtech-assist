"""How eagerly a repair reaches the desk, and what may be undone on it.

Qt-free on purpose (spec §4): these are the rules that decide whether a
packet leaves at all, and a rule a plain pytest can exhaust is worth more
than one that needs a window to observe.

This module names nothing under `wing_parser.net`. `ArmState.identity` is
a `net.identity.WingIdentity` and `RevertQueue`'s records are
`live_write.SentWrite`, but neither type is imported: the first would make
this module part of the net import graph for one annotation, and the second
would be a cycle (`live_write` is a `ui/` module too).
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Sequence


class ApplyLevel(str, Enum):
    """F3. Remembered for the current connection only; never persisted."""

    MANUAL = "manual"
    DELAYED = "delayed"
    IMMEDIATE = "immediate"


class ArmState:
    """F4: one arming per connection, and what it was armed FOR.

    The identity is kept, not just a boolean, because gate 5
    (`net/write.py:93-100`) re-queries it on every write and a reviewer
    must be able to ask "armed for which desk?" without guessing.
    """

    def __init__(self) -> None:
        self.identity: Any | None = None
        self.level: ApplyLevel = ApplyLevel.MANUAL

    def arm(self, identity: Any) -> None:
        self.identity = identity

    def armed(self) -> bool:
        return self.identity is not None

    def disarm(self) -> None:
        """Every DISCONNECTED / LOST / ERROR lands here (F4).

        The level falls back with the identity, so the selector an
        operator looks up at after a dropout reads Manual and tells him
        the truth rather than the level he picked before the cable went.
        """
        self.identity = None
        self.level = ApplyLevel.MANUAL


class RevertQueue:
    """F7: the sent ledger walked backwards, one record at a time.

    Last written, first undone -- and `next()` hands out exactly one, so
    "one parameter per transmission" (F1) is a property of this object
    rather than of the UI happening not to offer a second button.
    """

    def __init__(self, records: Sequence[Any]) -> None:
        self._pending = list(reversed(list(records)))
        self._total = len(self._pending)
        self._done = 0
        self._stopped = False

    def next(self) -> Any | None:
        """The next record, or `None` when exhausted **or** stopped."""
        if self._stopped or not self._pending:
            return None
        self._done += 1
        return self._pending.pop(0)

    def stop(self) -> None:
        """W12/W15: end the run between parameters. The one already on the
        wire completes -- nothing can un-send a packet."""
        self._stopped = True

    @property
    def progress(self) -> tuple[int, int]:
        """`(done, total)`, counted as records are handed OUT: the line
        reads `Reverting 3/7` while the third is going, not after it."""
        return self._done, self._total

    @property
    def remaining(self) -> tuple[Any, ...]:
        """What a stopped run left alone, still in reverse order."""
        return tuple(self._pending)
