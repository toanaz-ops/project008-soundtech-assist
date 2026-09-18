"""The journal, shown before it is saved.

"What have I changed?" must be answerable without diffing two files.
Each row names what was there and what it becomes -- the `before`
captured when the edit was made, not recomputed now, and now carries its
own Send button (S2.2): `SendRow` in `changes_send.py`.

`self.ledger` is a minimal stand-in for Task 13's `SentLedger`
(`changes_ledger.py`) -- `records()`, `add()` and `row_widget()` only, no
Revert-all/Stop. Task 13 replaces this class with an import from its own
module; nothing here depends on the stand-in beyond that shape.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget,
)

from wing_parser.edit.journal import Patch
from wing_parser.ui import write_router
from wing_parser.ui.changes_send import SendRow
from wing_parser.ui.texts import text


class _LedgerRow(QWidget):
    """The one thing Task 12's own tests need off a sent row: a Revert
    button that exists and is enabled. Task 13's `LedgerRow` replaces
    this; wiring the click to `write_router.route_revert` is its job."""

    def __init__(self, record, parent=None) -> None:
        super().__init__(parent)
        self.record = record
        self.revert_button = QPushButton(text("console.write.revert"))
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(f"{record.address}"), 1)
        layout.addWidget(self.revert_button)


class SentLedger(QWidget):
    """Stand-in for `changes_ledger.SentLedger` until Task 13 lands it."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._records: list = []
        self.list = QListWidget()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(text("console.write.sent_heading")))
        layout.addWidget(self.list)

    def add(self, record) -> None:
        self._records.append(record)
        row = _LedgerRow(record)
        item = QListWidgetItem()
        item.setSizeHint(row.sizeHint())
        self.list.addItem(item)
        self.list.setItemWidget(item, row)

    def records(self) -> tuple:
        return tuple(self._records)

    def row_widget(self, index: int) -> QWidget:
        return self.list.itemWidget(self.list.item(index))


class ChangesPanel(QWidget):
    undo_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._gate = None
        self._window = None
        self.list = QListWidget()
        self.status_label = QLabel("")
        self.ledger = SentLedger()
        self.undo_button = QPushButton(text("changes.undo"))
        self.undo_button.clicked.connect(self.undo_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addWidget(self.status_label)
        layout.addWidget(self.ledger)
        layout.addWidget(self.undo_button)
        self.set_changes(())

    def attach_gate(self, gate) -> None:
        self._gate = gate
        gate.changed.connect(self._refresh_rows)

    def attach_window(self, window) -> None:
        self._window = window

    def set_changes(self, patches: tuple[Patch, ...]) -> None:
        self.list.clear()
        for patch in patches:
            item = QListWidgetItem()
            row = SendRow(patch, self._gate,
                          getattr(self._window, "_apply_delay", 5))
            row.sent.connect(self.record_sent)
            row.send_error.connect(self.report_write_error)
            item.setSizeHint(row.sizeHint())
            self.list.addItem(item)
            self.list.setItemWidget(item, row)
        self.undo_button.setEnabled(bool(patches))

    def record_sent(self, patch, record) -> None:
        """One result: the badge, the scene (F8) and one ledger row."""
        write_router.apply_result(self._window, patch, record)
        self.ledger.add(record)
        self._badge(patch, record)

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
                return
