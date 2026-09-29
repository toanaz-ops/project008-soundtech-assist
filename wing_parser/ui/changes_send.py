"""One journal row: what changed, and the button that sends it (§2.2).

The Send button is **disabled only when the gate is closed** -- the Console
page not CONNECTED or WATCHING -- with `console.write.blocked` as its
tooltip. Being unarmed does NOT disable it: clicking while unarmed opens
`ArmWriteDialog` first and the countdown after it, so Manual has one button
that always means the same thing and the arming step appears only when it is
actually needed.

Clicking opens the COUNTDOWN, deliberately, not a bare confirm: Manual
exists so the operator sees the numbers, and that screen is where the
numbers are.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from wing_parser.ui import live_write, write_router
from wing_parser.ui.texts import text
from wing_parser.ui.theme import tokens


def badge_text(record) -> str:
    """The one line §2.4 gives each of the three outcomes."""
    result = record.result
    kind = live_write.outcome(result)
    if kind is live_write.Outcome.SENT:
        return text("console.write.sent").format(readback=result.readback)
    if kind is live_write.Outcome.CLAMPED:
        return text("console.write.clamped").format(
            readback=result.readback, after=record.written)
    return text("console.write.no_reply").format(address=record.address)


class SendRow(QWidget):
    send_requested = Signal(object)     # the Patch this row carries
    dialog_opened = Signal(object)      # the countdown, for tests and for focus
    sent = Signal(object, object)       # (Patch, SentWrite) -- a completed send
    send_error = Signal(object)         # the exception -- gate 4 closing, DeskChanged, ...

    def __init__(self, patch, gate, delay=5, parent=None) -> None:
        super().__init__(parent)
        self.patch = patch
        self._gate = gate
        self._delay = delay
        self.label = QLabel(text("changes.row").format(
            label=patch.label, path=patch.path,
            before=patch.before, after=patch.after))
        self.label.setWordWrap(True)
        # The badge is the outcome of a live write: it sits on its own line
        # under the label, wraps, and is never cut (full text = tooltip).
        self.badge = QLabel("")
        self.badge.setWordWrap(True)
        self.badge.setVisible(False)
        self.send_button = QPushButton(text("console.write.send"))
        self.send_button.clicked.connect(self._send)

        top = QHBoxLayout()
        top.addWidget(self.label, 1)
        top.addWidget(self.send_button)
        layout = QVBoxLayout(self)
        # A gap under each row so a badge reads as its own row's outcome.
        layout.setContentsMargins(0, 0, 0, tokens.METRICS["unit"] * 3)
        layout.addLayout(top)
        layout.addWidget(self.badge)
        self.refresh()

    def refresh(self) -> None:
        """Gate openness only (§2.2) -- being unarmed never disables it.

        No gate yet (a panel built and populated before `attach_gate`,
        as the direct-construction tests in `test_ui_widgets.py` do)
        reads exactly like a closed one: nothing can be sent."""
        enabled = self._gate is not None and self._gate.can_write()
        self.send_button.setEnabled(enabled)
        self.send_button.setToolTip("" if enabled else text("console.write.blocked"))

    def set_badge(self, record) -> None:
        shown = badge_text(record)
        self.badge.setText(shown)
        self.badge.setToolTip(shown)
        self.badge.setVisible(bool(shown))

    def _send(self) -> None:
        self.send_requested.emit(self.patch)
        dialog = write_router.send_manually(
            self._gate, self.patch, self._delay, self.window(),
            transport=self._gate.transport,
            on_sent=self._sent, on_error=self.send_error.emit)
        if dialog is not None:
            self.dialog_opened.emit(dialog)

    def _sent(self, patch, record) -> None:
        """The result reaches the row's badge AND announces itself
        (`sent`) so `ChangesPanel.set_changes` can wire it to
        `record_sent` -- F8's scene correction and the ledger row, not
        just what this row shows."""
        self.set_badge(record)
        self.sent.emit(patch, record)
