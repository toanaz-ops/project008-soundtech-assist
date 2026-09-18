"""Gate 2 (§8.2): nothing writes until this dialog has been satisfied.

Three conditions, all of them, once per connection (F4): a FRESH identity
re-query, the show latch ticked, and the console's exact name typed.

Identity is never reused from the earlier connect.
`net_commands._echo_identity_before_write` (`net_commands.py:79-85`) does
exactly this before every CLI write, and `identity.py:10-14` says why: the
caller is about to trust "this is the console I meant to write to".

The latch reads "This desk is NOT running a show right now." and starts
UNTICKED. Wave 2's sketch had it the other way round -- "this desk is in a
show", default on -- and a ticked box meaning "danger" reads backwards at
2 a.m., when every other checkbox in this app means "yes, do this".

While the identity read is still in flight, the typed name cannot yet be
judged right or wrong -- there is nothing to compare it against. The hint
shows `console.write.name_pending` instead of `.name_wrong` until the read
settles (review fix round 1, item 1); judging it early would tell an
operator who typed correctly that they had typed the wrong thing.

**Its own `CallRunner`, not the Console page's** (W5). W1 allows writing
while the page is WATCHING, the page's runner is then legitimately busy,
and `CallRunner.start` returns False when it is (`workers.py:112-113`) --
a shared runner would refuse every identity read made during a watch, so
this dialog could not even show which desk it is about to arm.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QHBoxLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout,
)

from wing_parser.ui import live_write
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner


class ArmWriteDialog(QDialog):
    armed = Signal(object)          # the WingIdentity this arming is for

    def __init__(self, gate, parent=None, *, transport=None, timeout=None) -> None:
        super().__init__(parent)
        self._gate = gate
        self._transport = transport or live_write.REAL
        self._identity = None
        self._identity_pending = True
        self.setWindowTitle(text("console.write.arm_title"))
        self.setWindowModality(Qt.WindowModality.ApplicationModal)     # W11

        self.status_label = QLabel(text("console.write.reading"))
        self.status_label.setWordWrap(True)
        self.latch = QCheckBox(text("console.write.latch"))
        self.latch_why = QLabel(text("console.write.latch_why"))
        self.latch_why.setWordWrap(True)
        self.name_edit = QLineEdit()
        self.name_hint = QLabel("")
        self.arm_button = QPushButton(text("console.write.arm"))
        self.arm_button.setEnabled(False)
        self.cancel_button = QPushButton(text("console.write.cancel"))

        layout = QVBoxLayout(self)
        layout.addWidget(self.status_label)
        layout.addWidget(self.latch)
        layout.addWidget(self.latch_why)
        layout.addWidget(QLabel(text("console.write.name_prompt")))
        layout.addWidget(self.name_edit)
        layout.addWidget(self.name_hint)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.cancel_button)
        buttons.addWidget(self.arm_button)
        layout.addLayout(buttons)

        self.latch.toggled.connect(self._refresh)
        self.name_edit.textChanged.connect(self._refresh)
        self.arm_button.clicked.connect(self._arm)
        self.cancel_button.clicked.connect(self.reject)

        self._runner = CallRunner(self)
        self._runner.start(
            "connect", self._transport.identity, gate.host(),
            on_success=self._identified, on_failure=self._identity_failed,
            timeout=timeout,
        )

    # -- the fresh read ----------------------------------------------------

    def _identified(self, identity) -> None:
        self._identity = identity
        self._identity_pending = False
        self.status_label.setText(text("console.write.desk").format(
            name=identity.name, model=identity.model, serial=identity.serial))
        self._refresh()

    def _identity_failed(self, exc) -> None:
        """Dead for this dialog's life, deliberately. A desk that would not
        say who it is is not a desk to arm against, and a Retry button here
        would invite exactly that -- close it and connect again."""
        self.status_label.setText(text("console.write.identity_failed").format(
            host=self._gate.host(), error=exc))
        self._identity = None
        self._identity_pending = False
        self._refresh()

    # -- the three conditions ----------------------------------------------

    def _refresh(self) -> None:
        typed = self.name_edit.text()
        if self._identity_pending:
            # Nothing to judge the typed name against yet -- a correct
            # guess must not be told it is wrong (review fix round 1, #1).
            self.name_hint.setText(
                text("console.write.name_pending") if typed else "")
            self.arm_button.setEnabled(False)
            return
        matches = self._identity is not None and typed == self._identity.name
        self.name_hint.setText(
            "" if matches or not typed else text("console.write.name_wrong"))
        self.arm_button.setEnabled(bool(self.latch.isChecked() and matches))

    def _arm(self) -> None:
        if self._identity is None:
            return
        self._gate.arm.arm(self._identity)
        self._gate.changed.emit()
        self.armed.emit(self._identity)
        self.accept()

    def reject(self) -> None:
        """Cancel/Esc/X: settle the pre-flight runner before anything else.

        `CallRunner.cancel()` marks the in-flight call settled RIGHT NOW,
        from the UI's side -- a late `finished`/`failed` signal that was
        already queued across the thread boundary is then a no-op, because
        `CallRunner._settle` refuses to fire a callback twice (review fix
        round 1, #2). Without this, closing the dialog mid-read could still
        run `_identified`/`_identity_failed` on a widget the operator just
        dismissed.
        """
        self._runner.cancel()
        super().reject()


def arm_now(gate, parent=None, **kwargs) -> bool:
    """Open the dialog modally; True once the gate really is armed.

    THE single entrance. Manual's own Send button and the countdown both
    call this when unarmed, so Manual has one button that always means the
    same thing and the arming step appears only when it is needed (§2.2).
    """
    if gate.arm.armed():
        return True
    ArmWriteDialog(gate, parent, **kwargs).exec()
    return gate.arm.armed()
