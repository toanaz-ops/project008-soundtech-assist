"""The watch loop's thread: one signal per change, and no judgement at all.

A watch is not a call. `FunctionWorker` under a `CallRunner`
(`workers.py`) is one call, one result, one numeric budget -- exactly
wrong for a loop that runs for a whole show, produces a stream, and has
no deadline (spec S7.2: the watch row's budget is **none**). So the
watch gets its own thread, and this is it.

It decides nothing. Whether to stop, and whether the desk is gone, are
both `RoundGuard`'s (`live_guard.py`) -- plain Python, covered by plain
pytest. This class only drains a generator off the GUI thread and turns
what comes out of it into signals: an item into `produced`, a normal end
into `finished`, `Cancelled` into `finished_cancelled`, and anything
else -- `DeskLost` included -- into `failed`. Exactly one of those three
terminal signals fires (the `FunctionWorker` contract, `workers.py:49-83`).

It also names no transport. It is handed a callable that returns an
iterable, so the same worker drains the real `poller.watch` over a live
desk and a two-line generator in a test. Spec S7.3, D5.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

from PySide6.QtCore import QThread, Signal

from wing_parser.ui.live_guard import Cancelled

# Every started worker, pruned of the ones that really stopped. A
# QThread whose last Python reference goes away while it is still
# running is destroyed mid-run; `CallRunner._settle` keeps its retired
# workers for the same reason (`workers.py:166-169`), and a watch -- the
# longest-lived thread in the app -- needs it most.
_RUNNING: list["GeneratorWorker"] = []


def running_workers() -> tuple["GeneratorWorker", ...]:
    """The watch threads this process is still holding a reference to."""
    return tuple(_RUNNING)


def _still_running(worker: "GeneratorWorker") -> bool:
    """`worker.isRunning()`, but a deleted wrapper is simply not running.

    The list below outlives any single caller, so one entry whose C++
    object was destroyed -- a worker given a Qt parent that died first --
    would make the NEXT `start()` raise `RuntimeError: Internal C++
    object (GeneratorWorker) already deleted`, anywhere in the app and
    with a traceback pointing at an unrelated watch. Measured in task 12,
    four tests down. A corpse is dropped instead.
    """
    try:
        return worker.isRunning()
    except RuntimeError:
        return False


@dataclass(frozen=True)
class WatchSummary:
    """How a finished watch went, for the page's closing line.

    `rounds` is every guarded read `RoundGuard` reported, which is one
    more than the loop's own rounds: `poller.watch` reads the strip
    labels once and takes a priming sample before the first round
    (`poller.py:84-86`), and both go through the same guard. Counting
    what the guard actually reported keeps this worker free of a second,
    disagreeing tally.
    """

    rounds: int
    events: int
    seconds: float


class GeneratorWorker(QThread):
    """Drain `function(*args)`'s iterable off the GUI thread, emitting each item.

    Wiring, for the page that owns the watch -- the guard is built inside
    the callable so that it can report its rounds into this worker's own
    signal, and so that nothing touches the desk until the thread runs::

        def run_watch():
            guard = RoundGuard(client, host, cancel,
                               on_round=worker.report_progress)
            return poller.watch(guard, watch_list, interval=0.25)

        worker = GeneratorWorker(run_watch)

    There is no `cancel()` here: Stop sets the `threading.Event` the
    guard already watches, and the guard raises `Cancelled` before its
    next round, so stop latency is bounded by one round and this class
    stays free of the logic.
    """

    produced = Signal(object)
    progress = Signal(int, int)
    finished = Signal(object)
    failed = Signal(object)
    finished_cancelled = Signal()

    def __init__(self, function, *args, parent=None) -> None:
        super().__init__(parent)
        self._function = function
        self._args = args
        self._rounds = 0
        self._events = 0

    def report_progress(self, answered: int, total: int) -> None:
        """`RoundGuard`'s `on_round`, straight onto the `progress` signal."""
        self._rounds += 1
        self.progress.emit(answered, total)

    def start(self, *args, **kwargs) -> None:
        """Start the thread, and keep it referenced until it really stops."""
        super().start(*args, **kwargs)
        _RUNNING.append(self)
        _RUNNING[:] = [w for w in _RUNNING if w is self or _still_running(w)]

    def run(self) -> None:
        started = time.monotonic()
        try:
            for item in self._function(*self._args):
                self._events += 1
                self.produced.emit(item)
        except Cancelled:
            self.finished_cancelled.emit()
            return
        except Exception as exc:  # noqa: BLE001 - the failure IS the payload
            self.failed.emit(exc)
            return
        self.finished.emit(
            WatchSummary(self._rounds, self._events, time.monotonic() - started)
        )
