"""The pick step widget: choose a workbook, see what is inside it."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtWidgets import (
    QGroupBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from wing_parser.ui.texts import text


class PickStep(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.choose_button = QPushButton(text("import.pick"))
        self.choose_button.setIcon(qta.icon("fa5s.file-excel"))

        self.sample_pane = QTextEdit()
        self.sample_pane.setReadOnly(True)
        self.sample_pane.setPlainText(text("import.resting"))
        group = QGroupBox(text("import.sample_pane"))
        inner = QVBoxLayout(group)
        inner.addWidget(self.sample_pane)

        layout = QVBoxLayout(self)
        layout.addWidget(self.choose_button)
        layout.addWidget(group, stretch=1)

    def show_samples(self, samples) -> None:
        """Each sheet's name and first lines, as a what-is-in-here pane."""
        self.sample_pane.setPlainText("\n\n".join(
            f"SHEET {sample.name}\n" + "\n".join(sample.lines)
            for sample in samples
        ))
