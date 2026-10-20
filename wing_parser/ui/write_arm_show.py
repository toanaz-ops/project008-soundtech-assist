"""The "which show is this?" half of the Arm dialog (wave 5, W9/W12).

A show code names the write-log file, so it is validated with
`writelog.normalize_code` before Arm can enable. Name and venue are free
text, at most 80 characters, and only decorate the report.
"""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QCheckBox, QLabel, QLineEdit, QVBoxLayout, QWidget

from wing_parser import writelog
from wing_parser.ui.state_store import MAX_SHOW_TEXT
from wing_parser.ui.texts import text


class ShowFields(QWidget):
    changed = Signal()

    def __init__(self, last_show: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.code_edit = QLineEdit()
        self.adhoc = QCheckBox(text("console.write.arm_adhoc"))
        self.code_hint = QLabel("")
        self.code_hint.setWordWrap(True)
        self.name_edit = QLineEdit()
        self.venue_edit = QLineEdit()
        for edit in (self.name_edit, self.venue_edit):
            edit.setMaxLength(MAX_SHOW_TEXT)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(QLabel(text("console.write.arm_code_label")))
        layout.addWidget(self.code_edit)
        layout.addWidget(self.adhoc)
        layout.addWidget(self.code_hint)
        layout.addWidget(QLabel(text("console.write.arm_name_label")))
        layout.addWidget(self.name_edit)
        layout.addWidget(QLabel(text("console.write.arm_venue_label")))
        layout.addWidget(self.venue_edit)

        if last_show:
            self.code_edit.setText(last_show.get("code", ""))
            self.name_edit.setText(last_show.get("name", ""))
            self.venue_edit.setText(last_show.get("venue", ""))
        self._code_before_adhoc = ""
        self.code_edit.textChanged.connect(self._code_changed)
        self.adhoc.toggled.connect(self._adhoc_toggled)

    def code(self) -> str | None:
        """The normalised code, or `None` while the field is not valid."""
        return writelog.normalize_code(self.code_edit.text())

    def show_dict(self) -> dict:
        return {"code": self.code() or "",
                "name": self.name_edit.text().strip(),
                "venue": self.venue_edit.text().strip()}

    def _code_changed(self, _typed: str) -> None:
        shown = self.code_edit.text().strip()
        self.code_hint.setText(
            text("console.write.arm_code_hint") if shown and self.code() is None
            else "")
        self.changed.emit()

    def _adhoc_toggled(self, on: bool) -> None:
        if on:
            self._code_before_adhoc = self.code_edit.text()
            self.code_edit.setText(writelog.adhoc_code(datetime.now()))
        else:
            self.code_edit.setText(self._code_before_adhoc)
        self.code_edit.setEnabled(not on)
