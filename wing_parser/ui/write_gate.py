"""Gates 1 and 2, and the single wire (spec §8.1-8.2).

Split out of `live_wiring.py` by Task 11's escape hatch: that module was
at 195 of its 200-line ceiling, and Task 11 adds routing on top of it.
`install_write_gate` -- the one function that actually needs a `window`
-- stays in `live_wiring.py`; everything here needs only a `page`, so it
moved whole. `live_wiring.py` re-exports all three names, so every
existing `from wing_parser.ui.live_wiring import WriteGate` (and
`GateClosed`, `WriteJob`) keeps working unchanged.

This module names nothing under `wing_parser.net.write` (§8.4's
allow-list of one is `live_write.py`, not this file): `WriteGate` reaches
the write path only through `live_write.send`, a plain function call.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, Signal

from wing_parser.ui import live_write
from wing_parser.ui.apply_level import ArmState
from wing_parser.ui.live_state import allowed_actions
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner
from wing_parser.ui.write_queue import WriteQueue


class GateClosed(RuntimeError):
    """Gate 4 refused a write between the operator's click and the packet.

    A countdown can run for a minute and the desk can go LOST underneath
    it -- `RoundGuard` raises `DeskLost` after three silent rounds
    (`live_guard.py:44-52`) -- without the dialog knowing. Checking a
    live-state gate once, at paint time, is the classic form of this bug,
    so every path re-asks immediately before the confirmation is built.
    """


@dataclass(frozen=True)
class WriteJob:
    """One queued write, with the two ways it can end already bound."""

    confirmation: object                        # live_write.WriteConfirmation
    on_result: Callable[[object], None]
    on_error: Callable[[Exception], None]


class WriteGate(QObject):
    """Gates 1 and 2, and the single wire, in one object the window publishes.

    Built HERE rather than on the Console page (§8.1): the Doctor page and
    the Changes dock read it and neither may import `console_page`, so a
    page that failed to build would otherwise leave a write button enabled.
    It holds the page only to READ `page.state`, live, every time -- a
    cached answer is exactly what gate 4 exists to distrust.

    W10: one `CallRunner` and one `WriteQueue`, so "one parameter on the
    wire" is a property of the transport rather than of the UI happening
    not to offer a second button.
    """

    changed = Signal()

    def __init__(self, page, *, transport=None, timeout=None, parent=None) -> None:
        super().__init__(parent)
        self._page = page
        self._transport = transport or live_write.REAL
        self._timeout = timeout
        self.arm = ArmState()
        self._runner = CallRunner(self)
        self._queue = WriteQueue(self._start)

    # -- what everything asks it -------------------------------------------

    def can_write(self) -> bool:
        """Gate 1: `_ACTIONS` offers `"write"` in two states only (§6)."""
        return "write" in allowed_actions(self._page.state)

    def ready(self) -> bool:
        """Gates 1 and 2 together. Re-asked before every send (§8.4)."""
        return self.can_write() and self.arm.armed()

    def host(self) -> str:
        return self._page.connect_bar.host()

    @property
    def transport(self):
        """The transport this gate was built with (REAL in production, a
        `FakeDesk`'s in tests) -- so a caller building its OWN dialog
        (`changes_send.SendRow`) reaches the same desk the gate does,
        rather than defaulting past it to `live_write.REAL`."""
        return self._transport

    # -- the one wire -------------------------------------------------------

    def submit(self, job: WriteJob) -> None:
        self._queue.enqueue(job)

    def close(self) -> None:
        """Every DISCONNECTED / LOST / ERROR lands here (F4).

        Queued writes are dropped and TOLD: the connection every one of
        them needs is gone, `_start` would refuse them one by one anyway,
        and a job whose callbacks never run freezes whatever was waiting
        on it -- a Revert-all run stalls on the row that died. The
        in-flight one is left alone; nothing can un-send a packet."""
        self.arm.disarm()
        for job in self._queue.clear():
            job.on_error(GateClosed(text("console.write.gate_closed")))
        self.changed.emit()

    def _start(self, job: WriteJob) -> None:
        if not self.ready():
            self._settle_then(job.on_error,
                              GateClosed(text("console.write.gate_closed")))
            return
        started = self._runner.start(
            "write", live_write.send, job.confirmation, self._transport,
            on_success=lambda result: self._settle_then(job.on_result, result),
            on_failure=lambda exc: self._settle_then(job.on_error, exc),
            on_cancel=lambda: self._settle_then(
                job.on_error, GateClosed(text("console.write.gate_closed"))),
            timeout=self._timeout,
        )
        # D-52 #5: `started` is always True here. `WriteQueue._pump` calls
        # `_start` only when its own `_in_flight` slot is empty, and that
        # slot is cleared by `_settle_then` -> `_queue.settle()`, which
        # runs from `CallRunner._settle` only AFTER `_settle` has already
        # cleared `self._runner._active`. So `self._runner.busy` is always
        # False the moment `_pump` calls back in here -- this `WriteGate`
        # is the runner's only caller. An old requeue-on-False branch lived
        # here (removed 2026-09-25); besides being unreachable, it was
        # also wrong -- `settle()` then `enqueue()` re-enters `_start`
        # synchronously while the same runner would still be busy, which
        # recurses rather than actually waiting. Fail loudly instead of
        # reintroducing that: if this assumption is ever wrong, something
        # now lets two writes past `WriteQueue`'s single in-flight
        # guarantee (W10), and that is worse to hide than to crash on.
        if not started:
            raise RuntimeError("WriteGate's own CallRunner was busy at _start")

    def _settle_then(self, callback, payload) -> None:
        """Exactly one terminal path per write, and the queue hears it
        BEFORE the callback -- a callback that enqueues the next revert
        (Revert all, §7.2) must find the wire free."""
        self._queue.settle()
        callback(payload)
