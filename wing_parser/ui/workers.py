"""One cancellable worker path for every model call (ruled 2026-08-26).

A model call is a multi-second network round trip; running it on the
GUI thread freezes the window mid-show and reads as crashed. Every
such call now goes through :class:`FunctionWorker` (a thread) under a
:class:`CallRunner`, which adds the ruled numeric timeout
(:data:`TIMEOUTS`) and lets one owner run one call at a time -- a
second concurrent call is queue-rejected, never interleaved.

Documented limitation: ``cancel()`` cannot reach into an in-flight
HTTP request -- it only makes the result be discarded when the
callable returns. The thread object may outlive the Cancel click
briefly; the runner keeps retired workers referenced so Python cannot
GC a running thread.
"""

from __future__ import annotations

import threading

from PySide6.QtCore import QObject, QTimer, QThread, Signal

#: Ruled per-call budgets in seconds; a call past its budget is failed
#: with :class:`CallTimedOut` while the UI stays responsive.
#:
#: The first three are model calls -- HTTP to a provider. The last three
#: are live-console reads -- UDP to a desk on the local network, so they
#: are ruled from measured desk times, not borrowed (spec S7.2, D14):
#: connect 5 s is a backstop over ``query_identity``'s own 2.0 s socket
#: timeout (``identity.py:68``), walk 60 s is ~60x the measured ~1.00 s
#: clean walk, and snapshot 90 s is 9x the measured ~10 s whole-console
#: read. A watch has no budget at all: it ends on Stop, or when
#: :class:`~wing_parser.ui.live_guard.RoundGuard` declares the desk lost.
TIMEOUTS = {
    "proposal": 120, "guesses": 180, "probe": 30,
    "connect": 5, "walk": 60, "snapshot": 90,
}


class CallTimedOut(Exception):
    """A worker blew past its TIMEOUTS budget; carries kind and seconds."""

    def __init__(self, kind: str, seconds: int) -> None:
        super().__init__(f"{kind} timed out after {seconds}s")
        self.kind = kind
        self.seconds = seconds


class FunctionWorker(QThread):
    """Run one callable off the GUI thread and report how it ended.

    Exactly one terminal signal fires: finished(result), failed(exc)
    or finished_cancelled() -- a cancelled result is discarded, never
    delivered.
    """

    finished = Signal(object)
    failed = Signal(object)
    finished_cancelled = Signal()

    def __init__(self, function, *args, parent=None) -> None:
        super().__init__(parent)
        self._function = function
        self._args = args
        self._cancelled = threading.Event()

    def cancel(self) -> None:
        """Discard the result when the callable returns (see module doc)."""
        self._cancelled.set()

    def run(self) -> None:
        try:
            result = self._function(*self._args)
        except Exception as exc:  # noqa: BLE001 - the failure IS the payload
            if self._cancelled.is_set():
                self.finished_cancelled.emit()
            else:
                self.failed.emit(exc)
            return
        if self._cancelled.is_set():
            self.finished_cancelled.emit()
            return
        self.finished.emit(result)


class CallRunner(QObject):
    """One long call at a time, with a timeout, wired to callbacks.

    start() returns False when a call already runs -- the caller shows
    the busy message instead of corrupting state. cancel() settles the
    call immediately from the UI's side: buttons come back NOW, the
    wire call dies whenever, its result discarded. Callbacks always run
    on the GUI thread (queued across the thread boundary).
    """

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._active: dict | None = None
        self._retired: list[FunctionWorker] = []

    @property
    def busy(self) -> bool:
        return self._active is not None

    def start(self, kind, function, *args, on_success, on_failure,
              on_cancel=None, timeout=None) -> bool:
        """Run function(*args) on a worker; False when already busy.

        `timeout` overrides the TIMEOUTS[kind] budget -- tests pass 0
        so no test ever waits real seconds.
        """
        if self.busy:
            return False
        seconds = TIMEOUTS[kind] if timeout is None else timeout
        worker = FunctionWorker(function, *args)
        timer = QTimer(self)
        timer.setSingleShot(True)
        active: dict = {
            "settled": False, "worker": worker,
            "timer": timer, "on_cancel": on_cancel,
        }
        self._active = active

        def succeeded(result) -> None:
            if self._settle(active):
                on_success(result)

        def failed(exc) -> None:
            if self._settle(active):
                on_failure(exc)

        def cancelled() -> None:
            if self._settle(active) and on_cancel is not None:
                on_cancel()

        def timed_out() -> None:
            if self._settle(active):
                on_failure(CallTimedOut(kind, seconds))

        worker.finished.connect(succeeded)
        worker.failed.connect(failed)
        worker.finished_cancelled.connect(cancelled)
        timer.timeout.connect(timed_out)
        timer.start(seconds * 1000)
        worker.start()
        return True

    def cancel(self) -> None:
        """Settle the running call now; its late result is discarded."""
        active = self._active
        if active is None or not self._settle(active):
            return
        if active["on_cancel"] is not None:
            active["on_cancel"]()

    # -- internals ------------------------------------------------------

    def _settle(self, active: dict) -> bool:
        """End the call exactly once; False when it already ended."""
        if active["settled"]:
            return False
        active["settled"] = True
        active["timer"].stop()
        active["worker"].cancel()     # a late result is discarded
        self._active = None
        # Keep the thread referenced until it really stops, so a
        # cancelled-but-still-on-the-wire worker is never GC'd.
        self._retired.append(active["worker"])
        self._retired[:] = [w for w in self._retired if w.isRunning()]
        return True
