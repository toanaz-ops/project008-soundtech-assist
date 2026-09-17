"""One packet on the wire at a time (W10), enforced below the UI.

Every write in this app -- an Immediate Repair, a countdown's Apply, a
single Revert, each step of Revert all -- is enqueued here, and the next
starts only when the previous read-back returns or times out. Two rapid
Immediate Repairs queue; neither is dropped.

Qt-free, so the ordering rule is covered by plain pytest. The `start`
callback is what actually launches a write (the `WriteGate`'s single
`CallRunner`, `live_wiring.py`), and every terminal path of that call --
success, failure, timeout, cancel -- must call `settle()` exactly once, or
the queue stalls with a phantom write in flight.
"""

from __future__ import annotations

from collections import deque
from typing import Any, Callable


class WriteQueue:
    def __init__(self, start: Callable[[Any], None]) -> None:
        self._start = start
        self._pending: deque = deque()
        self._in_flight: Any | None = None

    @property
    def in_flight(self) -> Any | None:
        return self._in_flight

    @property
    def pending(self) -> tuple[Any, ...]:
        return tuple(self._pending)

    def enqueue(self, item: Any) -> None:
        self._pending.append(item)
        self._pump()

    def settle(self) -> None:
        """The in-flight write ended, however it ended. Release the next."""
        self._in_flight = None
        self._pump()

    def clear(self) -> None:
        """Drop everything not yet sent. The in-flight one is NOT dropped:
        its datagram may already have left the socket, and the ledger has
        to hear how it ended."""
        self._pending.clear()

    def _pump(self) -> None:
        if self._in_flight is not None or not self._pending:
            return
        self._in_flight = self._pending.popleft()
        self._start(self._in_flight)
