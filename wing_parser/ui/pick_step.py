"""The pick step widget: choose a workbook, see what is inside it."""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtWidgets import (
    QFileDialog,
    QGroupBox,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from wing_parser.ui.lint_dialog import LintDialog
from wing_parser.ui.texts import text


class PickStep(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.choose_button = QPushButton(text("import.pick"))
        self.choose_button.setIcon(qta.icon("fa5s.file-excel"))
        self.lint_button = QPushButton(text("import.lint.open"))
        self.lint_button.clicked.connect(self._open_lint)

        self.sample_pane = QTextEdit()
        self.sample_pane.setReadOnly(True)
        self.sample_pane.setPlainText(text("import.resting"))
        group = QGroupBox(text("import.sample_pane"))
        inner = QVBoxLayout(group)
        inner.addWidget(self.sample_pane)

        layout = QVBoxLayout(self)
        layout.addWidget(self.choose_button)
        layout.addWidget(self.lint_button)
        layout.addWidget(group, stretch=1)

    def _open_lint(self) -> None:
        """UX fix (Task 9 fix round 1): go straight to the file chooser --
        an operator clicking this button already means to pick a file, so
        landing on an empty dialog whose OWN "Check an existing show-
        context file..." button (same label) has to be clicked a second
        time was a real double-click-the-same-thing bug, not a feature."""
        path, _ = QFileDialog.getOpenFileName(
            self, text("import.lint.open"), "", text("import.yaml_filter"))
        if not path:
            return
        dialog = LintDialog(self)
        dialog.open_path(path)
        dialog.exec()

    def show_samples(self, samples) -> None:
        """Each sheet's name and first lines, as a what-is-in-here pane."""
        self.sample_pane.setPlainText("\n\n".join(
            f"SHEET {sample.name}\n" + "\n".join(sample.lines)
            for sample in samples
        ))
