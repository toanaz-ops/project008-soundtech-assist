"""Lint an existing show-context file from the Pick step (design spec
§6). Reads exactly what `wing showcontext lint` reads
(`load_show_context`, `context.anomalies`) -- no second lint
implementation. Fix writes `<file>.bak` (overwriting an older one, W2)
before `apply_repairs`, which itself keeps no backup of its own, then
re-lints and shows what changed and what remains. A failed backup write
(a full disk, a read-only file) must stop before `apply_repairs` ever
runs -- writing repairs into a file this dialog could not first protect
would defeat the whole point of W2.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QTextEdit,
    QVBoxLayout,
)

from wing_parser.showcontext import load_show_context
from wing_parser.showcontext.rewrite import apply_repairs
from wing_parser.ui.texts import text


class LintDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("import.lint.title"))
        self.setMinimumSize(560, 400)
        self._path: Path | None = None

        self.open_button = QPushButton(text("import.lint.open"))
        self.open_button.clicked.connect(self._open)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.fix_button = QPushButton(text("import.lint.fix"))
        self.fix_button.setEnabled(False)
        self.fix_button.clicked.connect(self._fix)
        close_button = QPushButton(text("import.lint.close"))
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.fix_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.output, 1)
        layout.addLayout(buttons)

    def open_path(self, path: str) -> None:
        self._path = Path(path)
        self._lint()

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, text("import.lint.open"), "", text("import.yaml_filter"))
        if path:
            self.open_path(path)

    def _lint(self) -> None:
        try:
            context = load_show_context(self._path)
        except ValueError as exc:
            self.output.setPlainText(str(exc))
            self.fix_button.setEnabled(False)
            return
        if not context.anomalies:
            self.output.setPlainText(
                text("import.lint.clean").format(count=len(context.segments)))
            self.fix_button.setEnabled(False)
            return
        self.output.setPlainText("\n".join(context.anomalies))
        self.fix_button.setEnabled(True)

    def _fix(self) -> None:
        answer = QMessageBox.question(
            self, text("import.lint.title"), text("import.lint.confirm"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        backup = Path(str(self._path) + ".bak")
        try:
            shutil.copyfile(self._path, backup)
        except OSError as exc:
            self.output.setPlainText(text("import.lint.backup_failed").format(error=exc))
            return
        repairs = apply_repairs(self._path)
        fixed_lines = [text("import.lint.fixed").format(n=len(repairs)), *repairs]
        self._lint()   # sets fix_button's new state and its own text first
        self.output.setPlainText(
            "\n".join(fixed_lines) + "\n\n" + self.output.toPlainText())
