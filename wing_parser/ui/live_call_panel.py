"""Shared chrome for every Console-page widget that runs one live call.

`ConnectBar` (task 9) and `DiscoveryPanel` (task 10) turned out identical
in everything except the call itself: both hold a `Transport` and an
optional `timeout` override, own one `CallRunner`, start their call
through the same `ButtonRunner` dance (primary button disabled, Cancel
shown, a running/cancelled/timeout/busy line, `on_timeout` always
`_fail`), and settle on Cancel the same way. `CallPanel` is that shell,
extracted after review flagged the duplication rather than hoisted in
advance -- neither panel changes shape or behaviour from this refactor.

What stays OUT, by design: any widget (`QComboBox`, `QLabel`, a lamp, a
banner), any `texts.py` string, and any `net`-shaped call
(`live_controller.connect` vs `.discover`). Panel-specific STATE also
stays out -- `_cancel_fallback` is a hook, not a table, because the two
panels answer "what does Cancel revert to" from different busy states
(`CONNECTING` -> `DISCONNECTED` vs `WALKING` -> `CONNECTED`) and there is
no shared row to hoist. This module imports `live_controller` (for the
transport default) but never `net` itself, the same rule every other
`ui/` module follows.
"""

from __future__ import annotations

from PySide6.QtWidgets import QWidget

from wing_parser.ui import live_controller
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.live_state import LiveState
from wing_parser.ui.workers import CallRunner


class CallPanel(QWidget):
    """Owns the transport, the timeout override, the state and the runner.

    Not useful on its own -- a subclass supplies its widgets, wires them
    to `cancel()` and its own call-starting method, and ends its own
    `__init__` with `self.set_state(LiveState.DISCONNECTED)` once those
    widgets exist (this base cannot call it: nothing here is built yet
    when `CallPanel.__init__` runs).
    """

    def __init__(self, parent=None, *, transport=None, timeout=None) -> None:
        super().__init__(parent)
        self._transport = transport or live_controller.REAL
        self._timeout = timeout
        self._state = LiveState.DISCONNECTED
        self._runner = CallRunner(self)

    def set_state(self, state: LiveState) -> None:
        """Wear `state`. Subclasses override, call `super()` first, then
        refresh whatever chrome (lamp, buttons) their own state drives."""
        self._state = state

    def cancel(self) -> None:
        """Settle a running call now; its late answer is discarded."""
        self._runner.cancel()
        fallback = self._cancel_fallback()
        if fallback is not None:
            self.set_state(fallback)

    def _cancel_fallback(self) -> LiveState | None:
        """Which state `cancel()` reverts to, or `None` to stay put.

        Overridden by every subclass: each one only reverts from its own
        busy state, to its own idle state, so there is nothing generic to
        default this to.
        """
        return None

    def _fail(self, exc) -> None:
        """The common tail of every failure path: state -> error.

        A caller that also needs to report a line writes it first
        (a `_refused`-shaped method), then calls this; a timeout arrives
        from `ButtonRunner.on_timeout` with its line already reported
        (`call_button.py:82-89`) and needs nothing more here. A subclass
        with its own signal to emit (`ConnectBar.failed`) overrides this,
        calls `super()._fail(exc)`, then emits.
        """
        self.set_state(LiveState.ERROR)

    def _run_call(self, kind, function, *args, primary, cancel_button,
                   status, running, cancelled, timeout_text, busy_text,
                   on_success, on_error, busy_state) -> bool:
        """Build the ButtonRunner + CallRunner dance once for every panel.

        `on_timeout` is always `self._fail`: every call site here wants
        the same thing on a timeout (state -> error, line already
        reported by `ButtonRunner` itself), which is the property that
        made this worth extracting rather than just the busy-line prose.
        """
        call = ButtonRunner(
            runner=self._runner, primary=primary, cancel=cancel_button,
            report=status.setText, running=running, cancelled=cancelled,
            timeout_text=timeout_text, busy_text=busy_text,
            on_error=on_error, on_timeout=self._fail, parent=self,
        )
        started = call.run(
            kind, function, *args, on_success=on_success,
            timeout=self._timeout,
        )
        if started:
            self.set_state(busy_state)
        return started
