"""What the Console page's signals do to the window.

`window_state.py`'s job, for the one scene that arrives from a desk
rather than from a file -- kept out of `main_window.py`, which is at
190 lines and would not survive a fourth responsibility, and out of
`live_snapshot.py`, which must not import the window it talks to.

The adopt path here is deliberately **not** `window_state.adopt_session`
(`window_state.py:94-98`): it opens with `switch_to("doctor")`, and D16 says a
pull leaves the view where it is. The operator is mid-console-workflow
-- start a watch, rerun a short discovery, export what he just pulled --
and all of that is on this page; yanking the view away costs him the
place he was working in, where staying costs one click on Open Doctor.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PySide6.QtCore import QObject, Signal

from wing_parser.ui import live_write, window_state
from wing_parser.ui.apply_level import ArmState
from wing_parser.ui.live_state import allowed_actions
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner
from wing_parser.ui.write_queue import WriteQueue


def adopt_pulled_session(window, session) -> None:
    """Everything a freshly *pulled* scene needs, minus the page switch.

    `window_state.adopt_session` without its `switch_to("doctor")` (D16),
    and without `remember_recent` (D4): the session's path is a bare
    suggested filename naming nothing on disk, so a recent-menu entry
    would later pop "File is gone" and self-heal itself away
    (`window_state.py:76-89`). `SnapshotPanel.exported` is what puts a
    real path in that menu, once one exists.
    """
    window.session = session
    window._show_finding(None)
    window._refresh()


def wire_console(window, page) -> None:
    """Connect the Console page to the window, if the page is built yet.

    **The contract is all three signals or none of them.** A Console
    page offers `session_pulled`, `exported` and `doctor_requested`, or
    it offers nothing and this is a no-op -- task 13's `ConsolePage`
    re-emits all three from its `SnapshotPanel`, and this function is
    also handed that panel directly by several tests. The `hasattr` is
    the same idiom `MainWindow._refresh` uses for `set_session`
    (`main_window.py:176-178`), and existed for the same reason: the
    Console page arrived over several tasks, and until task 13 the slot
    held task 8's `EmptyState`, which has none of the three. The branch
    is still live and still pinned -- any widget without them reaches
    here. Deliberately only the first signal is guarded: a page carrying
    `session_pulled` but missing one of the other two is a half-built
    contract and raises `AttributeError` here, at construction, rather
    than silently dropping Export or Open Doctor at a venue. Both
    branches are pinned in `tests/test_ui_console.py`.
    """
    if not hasattr(page, "session_pulled"):
        return
    page.session_pulled.connect(
        lambda session: adopt_pulled_session(window, session))
    page.exported.connect(
        lambda path: window_state.remember_recent(window, path))
    page.doctor_requested.connect(lambda: window.switch_to("doctor"))
    # The fourth is outside that contract and carries its own guard: it
    # is a whole-page signal (the address a handshake landed on, for
    # `window_state` to remember), and `SnapshotPanel` -- which this
    # function is handed directly by several tests, and which owns the
    # three above -- does not have it.
    if hasattr(page, "host_connected"):
        page.host_connected.connect(
            lambda host: window_state.remember_console(window, host))


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

    # -- the one wire -------------------------------------------------------

    def submit(self, job: WriteJob) -> None:
        self._queue.enqueue(job)

    def close(self) -> None:
        """Every DISCONNECTED / LOST / ERROR lands here (F4)."""
        self.arm.disarm()
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
        if not started:
            # The runner is busy with something the queue does not know
            # about. Requeue rather than drop: W10 says neither of two rapid
            # Immediate repairs is lost.
            self._queue.settle()
            self._queue.enqueue(job)

    def _settle_then(self, callback, payload) -> None:
        """Exactly one terminal path per write, and the queue hears it
        BEFORE the callback -- a callback that enqueues the next revert
        (Revert all, §7.2) must find the wire free."""
        self._queue.settle()
        callback(payload)


def install_write_gate(window, page, *, transport=None, timeout=None) -> WriteGate:
    """Build the gate, publish it on the window, wire every dropout to it.

    The three sources are the page's EXISTING signals: `console_page.py` is
    at 199 of the 200-line ceiling and may not grow a state signal (W7),
    and these are exactly the transitions into DISCONNECTED, ERROR and LOST
    (`console_page.py:117-138`).
    """
    gate = WriteGate(page, transport=transport, timeout=timeout, parent=window)
    window.write_gate = gate
    page.connect_bar.disconnected.connect(gate.close)
    page.events.lost.connect(lambda _exc: gate.close())
    for panel in (page.connect_bar, page.discovery, page.snapshot):
        panel.failed.connect(lambda _exc: gate.close())
    changes = getattr(window, "changes_panel", None)
    if changes is not None:
        changes.attach_gate(gate)          # task 12 gives ChangesPanel this
    return gate
