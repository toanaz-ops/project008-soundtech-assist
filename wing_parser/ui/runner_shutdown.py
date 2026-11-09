"""Close-time shutdown for every owner of a CallRunner (D-58).

PySide6 6.12 aborts when a running QThread is destroyed. The worker
registry parks every started worker, but an owner that closes while a
call hangs should still cancel it and wait a bounded time, once, for all
its runners together -- never one wait per runner.
"""

from __future__ import annotations

from wing_parser.ui.worker_registry import wait_all
from wing_parser.ui.workers import CallRunner

CLOSE_WAIT_MS = 1000


def shutdown_runners(owner, timeout_ms: int = CLOSE_WAIT_MS) -> None:
    """Cancel + bounded-wait every CallRunner under `owner` (recursive).

    A worker still running after the bound stays in the registry's
    keep-alive set; it is never destroyed while running.
    """
    runners = owner.findChildren(CallRunner)
    workers = [worker for runner in runners for worker in runner.drain()]
    wait_all(workers, timeout_ms)
    for runner in runners:
        runner.prune()


class ShutdownOnDone:
    """Mixin for a QDialog: accept/reject/close all end in `done`."""

    def done(self, result) -> None:
        shutdown_runners(self)
        super().done(result)
