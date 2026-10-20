"""The journal, shown before it is saved.

"What have I changed?" must be answerable without diffing two files.
Each row names what was there and what it becomes -- the `before`
captured when the edit was made, not recomputed now, and now carries its
own Send button (S2.2): `SendRow` in `changes_send.py`.

`self.ledger` is `changes_ledger.SentLedger` (Task 13): the sent ledger,
per-row and sequential Revert, Stop and the progress line.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from wing_parser.edit.journal import Patch
from wing_parser.ui import write_apply
from wing_parser.ui.changes_fit import FitList
from wing_parser.ui.changes_ledger import SentLedger
from wing_parser.ui.changes_send import SendRow
from wing_parser.ui.texts import text


class ChangesPanel(QWidget):
    undo_requested = Signal()
    #: (Patch, SentWrite), emitted at the END of `record_sent` -- after the
    #: badge, the ledger row and the scene correction (wave 5, spec section 4).
    sent = Signal(object, object)

    def __init__(self) -> None:
        super().__init__()
        self._gate = None
        self._window = None
        #: (Patch, SentWrite) for every row whose Send completed, so a rebuilt
        #: list (`set_changes` runs after every Repair, Undo and revert) can
        #: put the badge back instead of showing an unsent-looking Send.
        self._sent_rows: list[tuple[Patch, object]] = []
        self.list = FitList()
        self.status_label = QLabel("")
        self.log_warning_label = QLabel("")
        self.log_warning_label.setWordWrap(True)
        self.log_warning_label.setVisible(False)
        self.ledger = SentLedger()
        self.undo_button = QPushButton(text("changes.undo"))
        self.undo_button.clicked.connect(self.undo_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addWidget(self.status_label)
        layout.addWidget(self.log_warning_label)
        layout.addWidget(self.ledger)
        layout.addWidget(self.undo_button)
        self.set_changes(())

    def attach_gate(self, gate) -> None:
        self._gate = gate
        gate.changed.connect(self._refresh_rows)

    def attach_window(self, window) -> None:
        self._window = window
        self.ledger.attach(self._gate, window)

    def set_changes(self, patches: tuple[Patch, ...]) -> None:
        # A patch that left the journal (Undo) loses its record: re-repairing
        # it builds an equal Patch that has NOT been sent.
        self._sent_rows = [(p, r) for p, r in self._sent_rows if p in patches]
        self.list.clear()
        for patch in patches:
            item = QListWidgetItem()
            row = SendRow(patch, self._gate,
                          getattr(self._window, "_apply_delay", 5))
            row.sent.connect(self.record_sent)
            row.send_error.connect(self.report_write_error)
            for sent_patch, sent_record in self._sent_rows:
                if sent_patch == patch:
                    row.set_badge(sent_record)
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
        self.list.fit_all()
        self.undo_button.setEnabled(bool(patches))

    def record_sent(self, patch, record) -> None:
        """One result: one ledger row, the badge, the scene (F8).

        The ledger row goes first: the packet has left, so a scene
        correction that raises must not also lose the row (and with it
        Revert). `sent` still fires -- the write log owes the line -- and
        the exception then propagates as before."""
        self.ledger.add(record)
        self._sent_rows = [(p, r) for p, r in self._sent_rows if p != patch]
        self._sent_rows.append((patch, record))
        self._badge(patch, record)
        try:
            write_apply.apply_result(self._window, patch, record)
        finally:
            self.sent.emit(patch, record)

    def set_log_warning(self, message: str) -> None:
        """A write-log failure (W3), kept on screen for the session."""
        self.log_warning_label.setText(message)
        self.log_warning_label.setVisible(bool(message))

    def report_write_error(self, exc) -> None:
        self.status_label.setText(text("console.write.refused").format(error=exc))

    def has_ledger(self) -> bool:
        """What keeps the dock open on a clean session with a non-empty
        ledger (`main_window.py:181`, Task 13)."""
        return bool(self.ledger.records())

    def _refresh_rows(self) -> None:
        for index in range(self.list.count()):
            widget = self.list.itemWidget(self.list.item(index))
            if widget is not None:
                widget.refresh()

    def _badge(self, patch, record) -> None:
        for index in range(self.list.count()):
            widget = self.list.itemWidget(self.list.item(index))
            if isinstance(widget, SendRow) and widget.patch == patch:
                widget.set_badge(record)
                self.list.fit_all()
                return
