"""The save step widget: a read-only preview and one Save As button."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtWidgets import (
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from wing_parser.ui.texts import text


class SaveStep(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.preview_pane = QTextEdit()
        self.preview_pane.setReadOnly(True)
        self.save_button = QPushButton(text("import.save_as"))
        self.save_button.setIcon(qta.icon("fa5s.save"))

        layout = QVBoxLayout(self)
        layout.addWidget(self.preview_pane, stretch=1)
        layout.addWidget(self.save_button)
