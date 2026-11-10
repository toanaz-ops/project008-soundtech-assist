"""Widgets of the Full auto panel (wave 12 phase 2): display and enable state only."""

from __future__ import annotations

from PySide6.QtGui import QStandardItem
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QListWidget, QMessageBox, QPushButton,
    QVBoxLayout, QWidget,
)

from wing_parser.ui import automix_tables as tables
from wing_parser.ui.automix_controls import OptionsPanel
from wing_parser.ui.texts import text

LIVE_COLS = ("path", "before", "after", "stage", "mode")
MAX_ROWS = 500


def mode_text(row, kind: str) -> str:
    """`kind` is "revert" or an Outcome value; a simulated row has no result."""
    if row.result is None:
        return text("automix.live.mode.simulated")
    return text(f"automix.live.mode.{kind}")


class LiveControls(QWidget):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        banner = QLabel(text("automix.live.banner"))
        banner.setWordWrap(True)
        self.options_panel = OptionsPanel()
        self.ack = QCheckBox(text("automix.live.ack"))
        self.simulate = QCheckBox(text("automix.live.simulate"))
        self.simulate.setChecked(True)
        self.start_btn = QPushButton(text("automix.live.start"))
        self.stop_btn = QPushButton(text("automix.live.stop"))
        self.revert_btn = QPushButton(text("automix.live.revert"))
        self.status = QLabel(text("automix.live.state.idle"))
        self.status.setWordWrap(True)
        self.writes, self.writes_model = tables.make_table(
            LIVE_COLS, {1, 2}, {0, 1, 2})
        self.locked = QListWidget()
        self.locked.setMaximumHeight(90)
        buttons = QHBoxLayout()
        for part in (self.start_btn, self.stop_btn, self.revert_btn):
            buttons.addWidget(part)
        buttons.addStretch(1)
        layout = QVBoxLayout(self)
        for part in (banner, self.options_panel, self.ack, self.simulate):
            layout.addWidget(part)
        layout.addLayout(buttons)
        layout.addWidget(self.status)
        layout.addWidget(self.writes, 1)
        layout.addWidget(QLabel(text("automix.live.locked")))
        layout.addWidget(self.locked)
        self.simulate.clicked.connect(self._simulate_clicked)
        self.ack.toggled.connect(lambda on: self.start_btn.setEnabled(
            on and not self.stop_btn.isEnabled()))
        self.set_running(False, False)

    def _simulate_clicked(self, checked: bool) -> None:
        """Only a click (never a programmatic change) asks before going live."""
        if not checked and QMessageBox.question(
                self, text("automix.live.title"),
                text("automix.live.confirm_real")) != QMessageBox.StandardButton.Yes:
            self.simulate.setChecked(True)

    def set_running(self, running: bool, can_revert: bool) -> None:
        self.start_btn.setEnabled(not running and self.ack.isChecked())
        self.stop_btn.setEnabled(running)
        self.revert_btn.setEnabled(not running and can_revert)
        self.options_panel.setEnabled(not running)
        self.ack.setEnabled(not running)
        self.simulate.setEnabled(not running)

    def add_rows(self, cells) -> None:
        for row in cells:
            self.writes_model.appendRow([QStandardItem(str(c)) for c in row])
        extra = self.writes_model.rowCount() - MAX_ROWS
        if extra > 0:
            self.writes_model.removeRows(0, extra)
        self.writes.scrollToBottom()

    def set_locked(self, paths) -> None:
        self.locked.clear()
        self.locked.addItems(sorted(paths))
