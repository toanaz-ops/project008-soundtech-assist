"""Gate 3 (§8.3): the countdown an operator can watch, extend or cancel.

**Expiry is an apply** (F5) -- once the pre-flight read has landed. Apply
(button or expiry) needs a real desk value to send against: it starts
disabled, expiry HOLDS at 0 until `PreflightRead.landed` fires (split out
to `write_delay_support.py`, D-50), and a failed read disables it for
good -- dropping it silently, or applying blind, is worse.

**Cancel leaves the scene edit in place** -- Undo (`ui/session.py:71-75`)
is the other door, for the file side; `console.write.cancelled` says so.

**Gate 4 re-checks at the last moment** (§8.4): `RoundGuard` can declare
the desk lost mid-countdown (`live_guard.py:44-52`), so Apply now and
expiry both re-ask `WriteGate.ready()` before the confirmation is built.

**A write on the wire cannot be un-sent**: `reject()` and `_cancel` are
no-ops while `_sent`, and every button stays disabled from `_apply`'s submit
until `WriteOutcome` (also `write_delay_support.py`) reports the outcome.
Every OTHER ending CLOSES this dialog -- gate 4 refusing, and a refused
write -- because it is application-modal: one that settles without
closing takes the app with it. A `QTimer` counts seconds on the GUI
thread, no socket; the pre-flight read runs on this dialog's OWN
`CallRunner` (W5), never the busy Console page's.

**Must not import `live_wiring`** (an import cycle bit this module once)
-- `GateClosed`/`WriteJob` come from `write_gate` directly.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QProgressBar, QPushButton, QVBoxLayout,
)

from wing_parser.ui import live_write
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner
from wing_parser.ui.write_delay_support import PreflightRead, WriteOutcome, cancel
from wing_parser.ui.write_gate import GateClosed, WriteJob

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
        self._address, self._after = live_write.plan_write(patch, revert_record)
        self.desk_before = None     #: the pre-flight read, NORMALISED (kept as a value)
        self._settled = self._sent = self._expired = False
        self.remaining = self._total = int(seconds)

        self.setWindowTitle(text("console.write.delay_title").format(seconds=seconds))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)     # W11

        self.address_label = QLabel(text("console.write.address").format(address=self._address))
        self.desk_label = QLabel("")
        self.file_label = QLabel(text("console.write.file_value").format(value=patch.before))
        self.after_label = QLabel(text("console.write.after").format(value=self._after))
        self.mismatch_label = QLabel("")
        self.mismatch_label.setWordWrap(True)
        self.countdown_label = QLabel(text("console.write.countdown").format(remaining=self.remaining))
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)
        self.bar = QProgressBar()
        self.bar.setRange(0, self._total)
        self.bar.setValue(self.remaining)

        self.apply_button = QPushButton(text("console.write.apply_now"))
        self.apply_button.setEnabled(False)              # needs a landed read
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

        self._preflight = PreflightRead(self)
        self._outcome = WriteOutcome(self)
        self._runner = CallRunner(self)
        self._runner.start(
            "connect", self._transport.read, gate.host(), patch.path,
            on_success=self._preflight.landed,
            on_failure=lambda _exc: self._preflight.failed(),
            timeout=timeout,
        )
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(1000)

    # -- the countdown ----------------------------------------------------
    def _tick(self) -> None:
        self.remaining -= 1
        self.bar.setValue(max(self.remaining, 0))
        self.countdown_label.setText(text("console.write.countdown").format(
            remaining=max(self.remaining, 0)))
        if self.remaining > 0:
            return
        self._timer.stop()
        if self.apply_button.isEnabled():
            self._apply()                  # F5: expiry IS an apply
        else:
            self._expired = True           # hold at 0 until the read lands
            self.status_label.setText(text("console.write.reading"))

    def _extend(self) -> None:
        """Adds five to whatever remains, any number of times, no ceiling.

        D-52 #8: also resumes a countdown HELD at 0 awaiting the pre-flight
        read (`_expired`, set by `_tick`, which stops `_timer` on the way
        there) -- adding seconds alone would be inert against a stopped
        timer, and the read landing straight after would still trigger
        `PreflightRead.landed`'s immediate apply with no time bought at all.
        """
        self.remaining += EXTEND_SECONDS
        self._total = max(self._total, self.remaining)
        self.bar.setMaximum(self._total)
        self.bar.setValue(self.remaining)
        self.countdown_label.setText(
            text("console.write.countdown").format(remaining=self.remaining))
        if self._expired:
            self._expired = False
            self.status_label.setText("")
            self._timer.start(1000)

    # -- the three ways out -----------------------------------------------
    def _apply(self) -> None:
        if self._settled or not self.apply_button.isEnabled():
            return
        self._settled = True
        self._timer.stop()
        if not self._gate.ready():                       # GATE 4 (§8.4)
            self.status_label.setText(text("console.write.gate_closed"))
            self.failed.emit(GateClosed(text("console.write.gate_closed")))
            self.reject()
            return
        self.status_label.setText(text("console.write.sending").format(address=self._address))
        self._sent = True
        for button in (self.apply_button, self.extend_button, self.cancel_button):
            button.setEnabled(False)
        self._gate.submit(WriteJob(
            live_write.confirmation_for(
                self._gate.host(), self._address, self._after,
                self._gate.arm.identity, self.desk_before),
            self._outcome.done, self._outcome.failed,
        ))

    def _cancel(self) -> None:
        cancel(self)               # W12/W15, split to write_delay_support.py

    def reject(self) -> None:
        """Esc/X: refused outright while `_sent` (a packet on the wire cannot
        be un-sent); else settles the runner and stops the countdown."""
        if self._sent:
            return
        self._timer.stop()
        self._runner.cancel()
        super().reject()
