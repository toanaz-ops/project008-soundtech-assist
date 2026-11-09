"""Has the live Watch seen the desk being played in the last 30 seconds?

Wave 6 (2026-11-09, owner-delegated decision Q3). The Arm dialog's
"This desk is NOT running a show" latch stays the ONLY gate; this is a
soft hint beside it. Qt-free so it is unit-testable with an injected clock.

What counts as motion (exact match, on the watch event's address
`/<family>/<n>/<leaf>` as `net/watch/events.py` produces it):

  * family in `ch`, `bus`, `main`
  * leaf in `$fdr`, `$mute` (the effective values the watch list polls;
    the bare `fdr` / `mute` spellings are accepted too)

Solo, names, DCAs and matrices are NOT motion. Times are caller-supplied
(use `time.monotonic()`), never read here. A change exactly `window_s`
old is outside the window.
"""

from __future__ import annotations

from collections import deque

FAMILIES = frozenset({"ch", "bus", "main"})
LEAVES = frozenset({"$fdr", "$mute", "fdr", "mute"})
WINDOW_S = 30.0


def is_motion(path: str) -> bool:
    parts = path.split("/")
    return (len(parts) == 4 and parts[0] == ""
            and parts[1] in FAMILIES and parts[3] in LEAVES)


class DeskActivity:
    def __init__(self) -> None:
        self._times: deque[float] = deque()

    def record(self, path: str, at: float) -> None:
        if is_motion(path):
            self._times.append(at)
            while at - self._times[0] >= WINDOW_S:      # bound memory
                self._times.popleft()

    def recent_motion(self, now: float, window_s: float = WINDOW_S) -> int:
        return sum(1 for t in self._times if now - t < window_s)
