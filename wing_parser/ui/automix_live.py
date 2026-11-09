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

from wing_parser.ui import automix_live_records as records
from wing_parser.ui import automix_live_worker as work
from wing_parser.ui.automix_live_view import LiveControls
from wing_parser.ui.runner_shutdown import ShutdownOnDone
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner
from wing_parser.ui.write_arm_dialog import arm_now

PUMP_MS = 250


class AutomixLivePanel(ShutdownOnDone, QDialog):
    def __init__(self, window, *, gate=None, client_factory=None, limits=None,
                 clock=None, timeout=None) -> None:
        super().__init__(window)
        self._window = window
        self._gate = gate or window.write_gate
        self._factory = client_factory
        self._limits, self._clock, self._timeout = limits, clock, timeout
        self._loop = self._worker = self._ctx = None
        self._ticks = self._rows = self._pending = 0
        self.setWindowTitle(text("automix.live.title"))
        self.resize(900, 700)
        self.view = LiveControls()
        QVBoxLayout(self).addWidget(self.view)
        self._runner = CallRunner(self)
        self._timer = QTimer(self, interval=PUMP_MS, timeout=self._pump)
        self.view.start_btn.clicked.connect(self.start)
        self.view.stop_btn.clicked.connect(self.stop)
        self.view.revert_btn.clicked.connect(self.revert)
        self._gate.changed.connect(self._gate_changed)

    # -- start / stop -------------------------------------------------------

    def _say(self, message: str) -> None:
        self.view.status.setText(message)

    def _error(self, exc) -> None:
        self._say(text("automix.live.error").format(error=exc))
    def start(self) -> bool:
        window, gate, view = self._window, self._gate, self.view
        session = getattr(window, "session", None)
        if session is None:
            self._say(text("automix.live.need_scene"))
            return False
        if not gate.can_write():
            self._say(text("automix.live.need_connection"))
            return False
        simulate = view.simulate.isChecked()
        if not simulate and not arm_now(gate, self):
            return False
        if self._runner.busy:
            self._say(text("automix.live.busy"))
            return False
        if self._factory is None:
            from wing_parser.ui import live_controller
            self._factory = live_controller.REAL.client
        self._ctx = work.LiveContext(
            gate.host(), gate.arm.identity, gate.arm.show, gate.transport,
            self._factory, simulate, threading.Event(), threading.Event())
        from wing_parser import WingScene
        from wing_parser.core.loader import parse_raw

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
        self._finish_run()

    def done(self, result) -> None:
        self.stop()
        super().done(result)

    def _gate_ok(self) -> bool:
        return self._gate.can_write() if self._ctx.simulate else self._gate.ready()

    def _gate_changed(self) -> None:
        if self._loop is None or not self._timer.isActive() or self._gate_ok():
            return
        self._ctx.abort.set()
        self._ctx.stop.set()
        self._loop.stop()
        self._finish_run()
        self._say(text("automix.live.gate_closed"))

    def _lock_ui(self, running: bool) -> None:
        self.view.set_running(running, self._can_revert())
        records.lock_other_writers(self._window, running)    # one writer (W10)

    def _can_revert(self) -> bool:
        return bool(self._worker and self._worker.originals and self._gate.ready())

    def _finish_run(self) -> None:
        was_running = self._timer.isActive()
        self._timer.stop()
        self._lock_ui(False)
        if was_running:
            self._refresh_status()

    # -- the tick loop ------------------------------------------------------

    def _pump(self) -> None:
        loop = self._loop
        if loop is None or not loop.due() or self._runner.busy:
            return
        if not self._gate_ok():
            self._gate_changed()
            return
        self._runner.start("tick", self._worker.tick_once, loop,
                           on_success=self._ticked, on_failure=self._error,
                           timeout=self._timeout)

    def _ticked(self, result) -> None:
        report, rows, fatal = result
        self._ticks += 1
        self._pending = report.pending
        self._add_rows(rows)
        self.view.set_locked(self._loop.locked_paths)
        if fatal or report.state.value != "running":
            self._ctx.stop.set()
            self._finish_run()
        self._refresh_status()
        if report.errors:
            self._error(report.errors[-1][1])

    def _add_rows(self, rows) -> None:
        genre = self.view.options_panel.options().genre
        self._rows += len(rows)
        self.view.add_rows(records.record_rows(self._window, self._ctx, genre, rows))

    def _refresh_status(self) -> None:
        if self._loop is not None:
            self._say(records.status_line(
                self._loop, self._ticks, self._rows, self._pending))

    # -- revert -------------------------------------------------------------

    def revert(self) -> bool:
        if not self._can_revert():
            self._say(text("automix.live.nothing_to_revert"))
            return False
        self._ctx.abort.clear()
        started = self._runner.start(
            "tick", self._worker.revert, on_success=self._reverted,
            on_failure=self._error,
            timeout=self._timeout or max(60, 6 * len(self._worker.originals)))
        if started:
            self.view.revert_btn.setEnabled(False)
        return started

    def _reverted(self, rows) -> None:
        self.view.add_rows(records.record_reverts(self._window, self._ctx, rows))
        for row in rows:
            self._worker.originals.pop(row.path, None)
        self._say(text("automix.live.reverted").format(count=len(rows)))
        self.view.set_running(False, self._can_revert())

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self._timer.isActive():
            self.stop()
            return
        super().keyPressEvent(event)


def open_live(window) -> None:
    panel = AutomixLivePanel(window)
    panel.show()
    window._automix_live = panel
