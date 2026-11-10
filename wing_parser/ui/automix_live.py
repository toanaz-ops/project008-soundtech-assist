"""Tools > Automix > Full auto... (wave 12 phase 2, spec section 7).

A non-modal panel that drives the pure loop (`automix.live_loop`) on a
timer and one `CallRunner` (D-58). Every real write goes through
`live_write.send` under the gate's arm, and each is recorded in the Sent
ledger and the write log with the show code from the arm (AM-1, AM-22).
Simulate (default ON) reads the live desk and only lists would-write rows.
"""

from __future__ import annotations

import copy
import threading

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QDialog, QVBoxLayout

from wing_parser.ui import automix_live_guard as guard
from wing_parser.ui import automix_live_records as records
from wing_parser.ui import automix_live_worker as work
from wing_parser.ui.automix_live_consent import ConsentMixin
from wing_parser.ui.automix_live_panel_revert import RevertMixin
from wing_parser.ui.automix_live_settle import SettleMixin
from wing_parser.ui.automix_live_view import LiveControls
from wing_parser.ui.runner_shutdown import ShutdownOnDone
from wing_parser.ui.texts import text
from wing_parser.ui.workers import TIMEOUTS, CallRunner

PUMP_MS = 250
BUDGET_SHARE = 0.6           # a tick stops writing after this share of its timeout (AM-53)


class AutomixLivePanel(ConsentMixin, SettleMixin, RevertMixin, ShutdownOnDone, QDialog):
    def __init__(self, window, *, gate=None, client_factory=None, limits=None,
                 clock=None, timeout=None) -> None:
        super().__init__(window)
        self._window = window
        self._gate = gate or window.write_gate
        self._factory = client_factory
        self._limits, self._clock, self._timeout = limits, clock, timeout
        self._loop = self._worker = self._ctx = None
        self._ticks = self._rows = self._pending = 0
        self._armed_by_me = self._silent = False
        self.setWindowTitle(text("automix.live.title"))
        self.resize(900, 700)
        self.view = LiveControls()
        QVBoxLayout(self).addWidget(self.view)
        self._runner = CallRunner(self)
        self._timer = QTimer(self, interval=PUMP_MS, timeout=self._pump)
        self._settle_timer = QTimer(self, interval=PUMP_MS, timeout=self._settle)
        self.view.start_btn.clicked.connect(self.start)
        self.view.stop_btn.clicked.connect(self.stop)
        self.view.revert_btn.clicked.connect(self.revert)
        self._gate.changed.connect(self._gate_changed)

    def _say(self, message: str) -> None:
        self.view.status.setText(message)

    # -- start / stop -------------------------------------------------------

    def start(self) -> bool:
        window, gate, view = self._window, self._gate, self.view
        reason = guard.refusal(self)
        if reason:
            self._say(text(reason))
            return False
        simulate = view.simulate.isChecked()
        if not simulate and not self._fresh_arm():
            return False
        if self._factory is None:
            from wing_parser.ui import live_controller
            self._factory = live_controller.REAL.client
        budget = BUDGET_SHARE * (TIMEOUTS["tick"] if self._timeout is None else self._timeout)
        self._ctx = work.LiveContext(
            gate.host(), gate.arm.identity, gate.arm.show, gate.transport,
            self._factory, simulate, threading.Event(), threading.Event(),
            budget or None)
        from wing_parser import WingScene
        from wing_parser.core.loader import parse_raw

        session = window.session
        path, options = session.path, view.options_panel.options()
        self._worker = work.TickRunner(
            self._ctx, copy.deepcopy(session._document()),
            lambda doc: WingScene(parse_raw(doc, path)), options)
        self._loop = work.make_loop(self._worker, options, self._limits, self._clock)
        self._ticks = self._rows = self._pending = 0
        view.writes_model.removeRows(0, view.writes_model.rowCount())
        view.set_locked(())
        self._lock_ui(True)
        self._timer.start()
        self._refresh_status()
        return True

    def stop(self) -> None:
        if self._loop is not None:
            self._loop.stop()
            self._ctx.stop.set()
            self._ctx.abort.set()
        self._finish_run()
        self._release_arm()                          # a new run needs a new arm

    def done(self, result) -> None:
        self.stop()
        super().done(result)

    def _halt(self) -> None:
        """Stop writing at once, whatever thread is still out there (AM-52)."""
        self._ctx.abort.set()
        self._ctx.stop.set()
        self._loop.stop()
        self._finish_run()
        self._release_arm()

    def _failed(self, exc) -> None:
        """A tick or revert failed or timed out: its thread may still run."""
        self._say(text("automix.live.error").format(error=exc))
        if self._loop is not None:
            self._halt()

    def _gate_ok(self) -> bool:
        return self._gate.can_write() if self._ctx.simulate else self._gate.ready()

    def _gate_changed(self) -> None:
        if self._loop is None or self._silent:
            return
        if self._gate_ok() or not self._active():
            self.view.set_running(self._active(), self._can_revert())
            return
        self._halt()
        self._say(text("automix.live.gate_closed"))

    # -- the tick loop ------------------------------------------------------

    def _pump(self) -> None:
        loop = self._loop
        if loop is None or not loop.due() or self._runner.busy or self._worker_busy():
            return
        if not self._gate_ok():
            self._gate_changed()
            return
        if not self._gate.idle():                    # a manual write appeared (W10)
            self._halt()
            self._say(text("automix.live.gate_busy"))
            return
        self._worker.begin()
        if not self._runner.start("tick", self._worker.tick_once, loop,
                                  on_success=self._ticked, on_failure=self._failed,
                                  timeout=self._timeout):
            self._worker.busy.clear()

    def _ticked(self, result) -> None:
        report, fatal = result
        self._ticks += 1
        self._pending = report.pending
        self._drain()
        self.view.set_locked(self._loop.locked_paths)
        if fatal or report.state.value != "running":
            self._ctx.stop.set()
            self._finish_run()
            self._release_arm()
        self._refresh_status()
        if report.errors:
            self._say(text("automix.live.error").format(error=report.errors[-1][1]))

    def _add_rows(self, rows) -> None:
        genre = self.view.options_panel.options().genre
        self._rows += len(rows)
        self.view.add_rows(records.record_rows(self._window, self._ctx, genre, rows))

    def _refresh_status(self) -> None:
        if self._loop is not None:
            self._say(records.status_line(
                self._loop, self._ticks, self._rows, self._pending))

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self._timer.isActive():
            self.stop()
            return
        super().keyPressEvent(event)


def open_live(window) -> None:
    """One panel per window: a second call raises the one already open (AM-60)."""
    panel = getattr(window, "_automix_live", None)
    try:
        if panel is not None:
            panel.show()
            panel.raise_()
            panel.activateWindow()
            return
    except RuntimeError:                             # its C++ side is gone
        pass
    panel = AutomixLivePanel(window)
    panel.show()
    window._automix_live = panel
