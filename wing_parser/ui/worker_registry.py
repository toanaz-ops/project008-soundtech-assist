"""Keep-alive registry for model/console worker threads (D-58).

PySide6 6.12 aborts the process when a running QThread is destroyed.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QCoreApplication

#: Every worker that was ever started and may still be running. PySide6
#: 6.12 aborts the process when a running QThread is destroyed, so a worker
#: stays referenced here until it has really stopped -- whatever happens to
#: the CallRunner or the window that owned it (D-58).
_LIVE: set = set()
_HOOKED = False


def _running(worker) -> bool:
    try:
        return worker.isRunning()
    except RuntimeError:        # C++ object already gone: nothing to keep alive
        return False


def _prune() -> None:
    _LIVE.difference_update([w for w in _LIVE if not _running(w)])


def wait_all(workers, timeout_ms: int) -> None:
    """Wait for `workers` up to a total of `timeout_ms`; never longer."""
    deadline = time.monotonic() + timeout_ms / 1000
    for worker in list(workers):
        left = int((deadline - time.monotonic()) * 1000)
        if left <= 0:
            break
        worker.wait(left)


def shutdown_all(timeout_ms: int = 2000) -> None:
    """Cancel every live worker and wait a bounded time for them to stop.

    Stragglers (a hung HTTP call) stay in the keep-alive set, so they are
    never destroyed while running.
    """
    for worker in list(_LIVE):
        worker.cancel()
    wait_all(_LIVE, timeout_ms)
    _prune()


def register(worker) -> None:
    global _HOOKED
    _prune()
    _LIVE.add(worker)
    app = QCoreApplication.instance()
    if app is not None and not _HOOKED:
        _HOOKED = True
        app.aboutToQuit.connect(lambda: shutdown_all(2000))
