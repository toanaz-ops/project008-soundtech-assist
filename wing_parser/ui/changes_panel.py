"""The journal, shown before it is saved.

"What have I changed?" must be answerable without diffing two files.
Each row names what was there and what it becomes -- the `before`
captured when the edit was made, not recomputed now.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QListWidget, QPushButton, QVBoxLayout, QWidget

from wing_parser.edit.journal import Patch
from wing_parser.ui.texts import text


class ChangesPanel(QWidget):
    undo_requested = Signal()

    def __init__(self) -> None:
        super().__init__()
        self.list = QListWidget()
        self.undo_button = QPushButton(text("changes.undo"))
        self.undo_button.clicked.connect(self.undo_requested.emit)

        layout = QVBoxLayout(self)
        layout.addWidget(self.list)
        layout.addWidget(self.undo_button)
        self.set_changes(())

    def set_changes(self, patches: tuple[Patch, ...]) -> None:
        self.list.clear()
        for patch in patches:
            self.list.addItem(
                f"{patch.label}  —  {patch.path}: {patch.before!r} → {patch.after!r}"
            )
        self.undo_button.setEnabled(bool(patches))
