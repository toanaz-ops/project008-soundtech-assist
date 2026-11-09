"""Revision history of one entry: who changed what, and a way back.

Selecting a revision shows its unified diff against the one before it
(additions and removals coloured from the theme). **Restore this version**
writes that snapshot as a NEW revision -- history is never rewritten.
"""

from __future__ import annotations

import html

from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QHBoxLayout, QMessageBox, QPushButton, QTableWidget,
    QTableWidgetItem, QTextBrowser, QVBoxLayout, QWidget,
)

from wing_parser.library import ValidationFailed
from wing_parser.library.store import LibraryStore
from wing_parser.ui.library_edit_dialog import remembered_author, warn
from wing_parser.ui.texts import text
from wing_parser.ui.theme import tokens

COLUMNS = ("rev", "when", "who", "action", "note")


def confirm(parent, title: str, body: str) -> bool:
    answer = QMessageBox.question(parent, title, body)
    return answer == QMessageBox.StandardButton.Yes


def diff_html(diff: str) -> str:
    """A unified diff as `<pre>` HTML: + in `ok`, - in `danger`, headers dim."""
    colours = {"+": tokens.hex_str("ok"), "-": tokens.hex_str("danger"),
               "@": tokens.hex_str("accent")}
    dim = tokens.hex_str("dim")
    rows = []
    for line in diff.splitlines():
        head = line[:3] in ("+++", "---")
        colour = dim if head else colours.get(line[:1], tokens.hex_str("text"))
        rows.append(f'<span style="color:{colour}">{html.escape(line)}</span>')
    return "<pre>" + "\n".join(rows) + "</pre>"


class HistoryDialog(QDialog):
    def __init__(self, store: LibraryStore, entry_id: str, parent: QWidget | None = None,
                 state_dir=None) -> None:
        super().__init__(parent)
        self._store, self._id, self._state_dir = store, entry_id, state_dir
        self.restored = False
        self.setWindowTitle(text("library.history.title").format(id=entry_id))
        self.resize(900, 640)
        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels([text(f"library.hcol.{c}") for c in COLUMNS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.diff_view = QTextBrowser()
        self.restore_button = QPushButton(text("library.history.restore"))
        self.close_button = QPushButton(text("library.close"))
        self.restore_button.clicked.connect(self.restore_selected)
        self.close_button.clicked.connect(self.accept)
        self.table.itemSelectionChanged.connect(self._show_diff)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(self.restore_button)
        buttons.addWidget(self.close_button)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table, stretch=1)
        layout.addWidget(self.diff_view, stretch=2)
        layout.addLayout(buttons)
        self.reload()

    def reload(self) -> None:
        self._revisions = list(reversed(self._store.history(self._id)))
        self.table.setRowCount(len(self._revisions))
        for row, rev in enumerate(self._revisions):
            action = text(f"library.action.{rev.action}") if rev.action in (
                "create", "edit", "retire", "restore", "shipped") else rev.action
            for col, value in enumerate((rev.rev, rev.at, rev.author, action, rev.note)):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))
        if self._revisions:
            self.table.selectRow(0)
        else:
            self.diff_view.setPlainText(text("library.history.none"))
        self._sync_restore()

    def selected_rev(self) -> int | None:
        row = self.table.currentRow()
        return self._revisions[row].rev if 0 <= row < len(self._revisions) else None

    def _sync_restore(self) -> None:
        rev = self.selected_rev()
        latest = self._revisions[0].rev if self._revisions else None
        self.restore_button.setEnabled(rev is not None and rev != latest)

    def _show_diff(self) -> None:
        row = self.table.currentRow()
        self._sync_restore()
        if not 0 <= row < len(self._revisions):
            return
        if row + 1 >= len(self._revisions):
            self.diff_view.setPlainText(text("library.history.first"))
            return
        before, after = self._revisions[row + 1].rev, self._revisions[row].rev
        self.diff_view.setHtml(diff_html(self._store.diff(self._id, before, after)))

    def restore_selected(self) -> None:
        rev = self.selected_rev()
        if rev is None:
            return
        if not confirm(self, text("library.history.restore"),
                       text("library.history.restore_confirm").format(rev=rev)):
            return
        try:
            self._store.restore(self._id, rev, author=remembered_author(self._state_dir))
        except ValidationFailed as exc:
            warn(self, text("library.history.restore"), text("library.save_failed").format(error=exc))
            return
        self.restored = True
        self.reload()
