"""Gate 3 (§8.3): the countdown an operator can watch, extend or cancel.

**Expiry is an apply** (F5). The screen is a chance to stop, not a
confirmation to give: the operator has already decided by clicking Repair,
and a dialog that quietly dropped the write on timeout would leave the desk
and the scene disagreeing with nobody told.

**Cancel leaves the scene edit in place.** The Repair already happened, the
journal holds the `Patch`, Doctor already re-derived; Cancel drops only the
transmission, and Undo in the Changes panel drops the file side
(`ui/session.py:71-75`). Different doors, and `console.write.cancelled` says so.

**Gate 4 re-checks at the last moment** (§8.4). This countdown can run for a
minute -- `+5 s` is unbounded -- and `RoundGuard` can declare the desk lost
underneath it in under a second (`live_guard.py:44-52`). So Apply now and
expiry both re-ask `WriteGate.ready()` immediately before the confirmation
is built.

The countdown is a `QTimer` on the GUI thread: it counts seconds and
touches no socket, so `+5 s` cannot block the window. The PRE-FLIGHT read
runs on this dialog's OWN `CallRunner` (W5), never the Console page's,
because that one is legitimately busy during a watch.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from wing_parser.net.address import osc_address
from wing_parser.ui import live_write
from wing_parser.ui.live_wiring import GateClosed, WriteJob
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner

EXTEND_SECONDS = 5


class DelayedWriteDialog(QDialog):
    applied = Signal(object)        # the SetResult
    failed = Signal(object)         # GateClosed, SerialMismatchError, anything
    cancelled = Signal()            # W12: inside a revert run, stop the run

    def __init__(self, gate, patch, seconds, parent=None, *,
                 transport=None, timeout=None, revert_record=None) -> None:
        super().__init__(parent)
        self._gate = gate
        self._patch = patch
        self._record = revert_record
        self._transport = transport or live_write.REAL
        self._address = osc_address(patch.path)
        self._after = revert_record.desk_before if revert_record else patch.after
        #: The pre-flight read, NORMALISED -- kept as a value (the ledger
        #: records it), not scraped back off the label, which loses type.
        self.desk_before = None
        self._settled = False
        self.remaining = int(seconds)
        self._total = int(seconds)

        self.setWindowTitle(text("console.write.delay_title").format(seconds=seconds))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)     # W11

        self.address_label = QLabel(
            text("console.write.address").format(address=self._address))
        self.desk_label = QLabel("")
        self.file_label = QLabel(
            text("console.write.file_value").format(value=patch.before))
        self.after_label = QLabel(
            text("console.write.after").format(value=self._after))
        self.mismatch_label = QLabel("")
        self.mismatch_label.setWordWrap(True)
        self.countdown_label = QLabel(
            text("console.write.countdown").format(remaining=self.remaining))
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, self._total)
        self.bar.setValue(self.remaining)

        self.apply_button = QPushButton(text("console.write.apply_now"))
        self.extend_button = QPushButton(text("console.write.extend"))
        self.cancel_button = QPushButton(text("console.write.cancel"))

        layout = QVBoxLayout(self)
        for widget in (self.address_label, self.desk_label, self.file_label,
                       self.after_label, self.mismatch_label,
                       self.countdown_label, self.bar, self.status_label):
            layout.addWidget(widget)
        buttons = QHBoxLayout()
        buttons.addWidget(self.cancel_button)
        buttons.addStretch(1)
        buttons.addWidget(self.extend_button)
        buttons.addWidget(self.apply_button)
        layout.addLayout(buttons)

        self.apply_button.clicked.connect(self._apply)
        self.extend_button.clicked.connect(self._extend)
        self.cancel_button.clicked.connect(self._cancel)

        self._runner = CallRunner(self)
        self._runner.start(
            "connect", self._transport.read, gate.host(), patch.path,
            on_success=self._read_desk, on_failure=lambda _exc: self._no_read(),
            timeout=timeout,
        )
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    # -- the pre-flight read ------------------------------------------------

    def _read_desk(self, value) -> None:
        if value is None:
            self._no_read()
            return
        self.desk_before = value
        self.desk_label.setText(
            text("console.write.desk_value").format(value=value))
        if value != self._patch.before:
            # Somebody moved the desk after the scene was pulled -- the
            # operator's call, not the app's; both values go on screen.
            self.mismatch_label.setText(text("console.write.mismatch").format(
                desk=value, file=self._patch.before))

    def _no_read(self) -> None:
        self.desk_label.setText(text("console.write.no_read"))

    # -- the countdown -------------------------------------------------------

    def _tick(self) -> None:
        self.remaining -= 1
        self.bar.setValue(max(self.remaining, 0))
        self.countdown_label.setText(text("console.write.countdown").format(
            remaining=max(self.remaining, 0)))
        if self.remaining <= 0:
            self._apply()                  # F5: expiry IS an apply

    def _extend(self) -> None:
        """Adds five to whatever remains, any number of times, no ceiling."""
        self.remaining += EXTEND_SECONDS
        self._total = max(self._total, self.remaining)
        self.bar.setMaximum(self._total)
        self.bar.setValue(self.remaining)
        self.countdown_label.setText(
            text("console.write.countdown").format(remaining=self.remaining))

    # -- the three ways out ---------------------------------------------------

    def _apply(self) -> None:
        if self._settled:
            return
        self._settled = True
        self._timer.stop()
        if not self._gate.ready():                       # GATE 4 (§8.4)
            self.status_label.setText(text("console.write.gate_closed"))
            self.failed.emit(GateClosed(text("console.write.gate_closed")))
            return
        self.status_label.setText(
            text("console.write.sending").format(address=self._address))
        self._gate.submit(WriteJob(
            live_write.WriteConfirmation(
                host=self._gate.host(), address=self._address,
                after=self._after, identity=self._gate.arm.identity,
                desk_before=self.desk_before,
            ),
            self._done, self._failed,
        ))

    def _done(self, result) -> None:
        self.applied.emit(result)
        self.accept()

    def _failed(self, exc) -> None:
        self.status_label.setText(text("console.write.refused").format(error=exc))
        self.failed.emit(exc)

    def _cancel(self) -> None:
        """W12: inside a revert run this stops the WHOLE run, exactly as the
        ledger's Stop does. W15: in Delayed this IS the way out -- a Stop
        button behind a modal dialog is not reachable at all."""
        if self._settled:
            return
        self._settled = True
        self._timer.stop()
        self.status_label.setText(text(
            "console.write.revert_cancelled" if self._record
            else "console.write.cancelled"))
        self.cancelled.emit()
        self.reject()

    def reject(self) -> None:
        """Esc/X-close mirrors `ArmWriteDialog.reject`: settle the
        pre-flight runner and stop the countdown right now, so a late read
        or tick cannot touch a dismissed dialog. Unconditional -- `_cancel`
        also routes here, after already doing its own settling."""
        self._timer.stop()
        self._runner.cancel()
        super().reject()
