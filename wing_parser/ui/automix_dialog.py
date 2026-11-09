"""Tools > Automix (wave 12, phase 1): a draft channel-strip proposal.

Draft only. Propose runs the deterministic engine synchronously (no
worker thread, D-58) and lists what it would change; Apply records every
change in the session journal -- the same door Repair uses -- so the
operator reviews it on the Doctor page and saves with Save as.... This
module never writes a file and never touches a desk. The engine is
imported inside the handlers, never at module import (AM-20).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication, QDialog, QHBoxLayout, QLabel, QMessageBox, QPlainTextEdit,
    QPushButton, QTabWidget, QVBoxLayout,
)

from wing_parser.ui import automix_tables as tables
from wing_parser.ui.automix_controls import OptionsPanel
from wing_parser.ui.texts import text


class AutomixDialog(QDialog):
    def __init__(self, window, directory=None) -> None:
        super().__init__(window)
        self._window = window
        self._directory = directory
        self._proposal = None
        self._sources: dict = {}
        self.setWindowTitle(text("automix.title"))
        self.resize(1000, 700)

        banner = QLabel(text("automix.banner"))
        banner.setWordWrap(True)
        self.options_panel = OptionsPanel()
        self.propose_btn = QPushButton(text("automix.propose"))
        self.propose_btn.clicked.connect(self.propose)
        self.apply_btn = QPushButton(text("automix.apply"))
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply)
        self.summary = QLabel("")
        self.summary.setWordWrap(True)
        self.changes, self.changes_model = tables.make_table(
            tables.CHANGE_COLS, {4, 5}, {0, 4, 5})
        self.suggestions, self.suggestions_model = tables.make_table(
            tables.SUGGESTION_COLS)
        self.skipped, self.skipped_model = tables.make_table(
            tables.SKIPPED_COLS)
        self.warnings, self.warnings_model = tables.make_table(
            tables.WARNING_COLS)
        self.tabs = QTabWidget()
        for table, key in ((self.changes, "changes"),
                           (self.suggestions, "suggestions"),
                           (self.skipped, "skipped"),
                           (self.warnings, "warnings")):
            self.tabs.addTab(table, text(f"automix.tab.{key}"))
        self.detail = QPlainTextEdit()
        self.detail.setReadOnly(True)
        self.detail.setMaximumHeight(120)
        self.changes.selectionModel().selectionChanged.connect(self._show_detail)

        buttons = QHBoxLayout()
        buttons.addWidget(self.propose_btn)
        buttons.addWidget(self.apply_btn)
        buttons.addStretch(1)
        buttons.addWidget(QPushButton(text("settings.close"), clicked=self.reject))
        layout = QVBoxLayout(self)
        for part in (banner, self.options_panel):
            layout.addWidget(part)
        layout.addLayout(buttons)
        layout.addWidget(self.summary)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.detail)

    def _names(self) -> dict:
        names = {}
        for channel in self._window.session.scene.channels():
            number = channel.data.number
            names[f"ch.{number}"] = (
                f"{number} {(channel.data.name or '').strip()}".strip(),
                channel.source_type.kind)
        return names

    def propose(self) -> None:
        session = self._window.session
        if session is None:
            return
        from wing_parser.automix import knowledge, propose

        options = self.options_panel.options()
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self._proposal = propose(session.scene, session._document(),
                                     options, self._directory)
            self._sources = knowledge.load(self._directory).sources
        finally:
            QApplication.restoreOverrideCursor()
        found = self._proposal
        tables.fill_changes(self.changes_model, found.changes, self._names())
        tables.fill_suggestions(self.suggestions_model, found.suggestions)
        tables.fill_skipped(self.skipped_model, found.skipped)
        tables.fill_warnings(self.warnings_model, found.warnings)
        self.detail.setPlainText("")
        self.summary.setText(text("automix.summary").format(
            changes=len(found.changes), suggestions=len(found.suggestions),
            skipped=len(found.skipped), trim=found.headroom_trim_db,
            warnings=len(found.warnings)))
        self.apply_btn.setEnabled(bool(found.changes))

    def _show_detail(self, *_args) -> None:
        rows = self.changes.selectionModel().selectedRows()
        if rows and self._proposal is not None:
            change = self._proposal.changes[rows[0].row()]
            self.detail.setPlainText(tables.detail_text(change, self._sources))

    def apply(self, confirm: bool = True) -> int:
        """Record every change in the session journal; the count recorded."""
        found, session = self._proposal, self._window.session
        if not found or not found.changes or session is None:
            return 0
        if confirm and QMessageBox.question(
                self, text("automix.title"), text("automix.confirm").format(
                    count=len(found.changes))) != QMessageBox.StandardButton.Yes:
            return 0
        genre = found.options.genre
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            session.record_many(
                (c.path, c.after, c.label, f"automix:{genre}:{c.stage}")
                for c in found.changes)
            self._window._refresh()
        finally:
            QApplication.restoreOverrideCursor()
        self.accept()
        return len(found.changes)


def open_automix(window) -> None:
    if getattr(window, "session", None) is not None:
        AutomixDialog(window).exec()
