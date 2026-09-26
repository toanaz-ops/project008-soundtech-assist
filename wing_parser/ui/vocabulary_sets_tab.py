"""The Sets tab: a table, Add/Edit/Delete/Reset, a live search filter
(S1), and the AI-approved-looking source column. Each set's own row also
shows its fully expanded kinds (F13) so nesting's effect is visible
without opening a second row. A tombstoned default appears as its own
greyed row at the bottom, source "default, deleted" (fix round 1, I1) --
Reset is the only enabled action on such a row, since Edit/Delete have
nothing left to act on.

Save-time and delete/reset failures go through `vocabulary_tab_support`
-- see that module's docstring for which exceptions it treats as one
class of "tell the operator, do not crash"."""

from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext.ingest import keywords
from wing_parser.ui import vocabulary_tab_support as support
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_set_dialog import VocabularySetDialog

_COLUMNS = ("vocabulary.col.label", "vocabulary.col.kinds",
           "vocabulary.col.nested", "vocabulary.col.source")


class VocabularySetsTab(QWidget):
    def __init__(self, vocabulary, on_changed) -> None:
        super().__init__()
        self._vocabulary = vocabulary
        self._on_changed = on_changed
        self._row_entries: list[tuple] = []   # (SetEntry, is_deleted)
        self._haystacks: list[str] = []

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText(text("vocabulary.search_placeholder"))
        self.search_edit.textChanged.connect(self._apply_filter)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([text(key) for key in _COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self._refresh_buttons)

        self.add_button = QPushButton(text("vocabulary.add"))
        self.edit_button = QPushButton(text("vocabulary.edit"))
        self.delete_button = QPushButton(text("vocabulary.delete"))
        self.reset_button = QPushButton(text("vocabulary.reset"))
        self.add_button.clicked.connect(self._add)
        self.edit_button.clicked.connect(self._edit)
        self.delete_button.clicked.connect(self._delete)
        self.reset_button.clicked.connect(self._reset)

        buttons = QHBoxLayout()
        for button in (self.add_button, self.edit_button, self.delete_button, self.reset_button):
            buttons.addWidget(button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        self._populate()

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary
        self._populate()

    def _populate(self) -> None:
        rows = tuple((entry, False) for entry in self._vocabulary.sets())
        rows += tuple((entry, True) for entry in self._vocabulary.deleted_sets())
        self._row_entries = list(rows)
        self.table.setRowCount(len(rows))
        self._haystacks = []
        faded = self.palette().color(QPalette.ColorRole.PlaceholderText)
        for r, (entry, is_deleted) in enumerate(rows):
            label_text = entry.key if is_deleted else entry.label
            expanded = ", ".join(self._vocabulary.expand_set(entry.key))
            nested = ", ".join(entry.sets)
            if entry.sets:
                nested = f"{nested}  ->  {expanded}"
            source = (text("vocabulary.source.default_deleted") if is_deleted
                     else entry.display_origin)
            values = (label_text, ", ".join(entry.kinds), nested, source)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if is_deleted:
                    item.setForeground(faded)
                self.table.setItem(r, column, item)
            self._haystacks.append(
                support.folded_haystack(label_text, entry.label, ", ".join(entry.kinds)))
        self._apply_filter(self.search_edit.text())
        self._refresh_buttons()

    def _apply_filter(self, query: str) -> None:
        support.apply_search_filter(self.table, self._haystacks, query)

    def _selected(self):
        row = self.table.currentRow()
        if row < 0 or row >= len(self._row_entries):
            return None
        return self._row_entries[row]

    def _refresh_buttons(self) -> None:
        selection = self._selected()
        entry, is_deleted = selection if selection else (None, False)
        has_selection = selection is not None
        can_reset = has_selection and (
            is_deleted or self._vocabulary.has_default_set(entry.key))
        self.edit_button.setEnabled(has_selection and not is_deleted)
        self.delete_button.setEnabled(has_selection and not is_deleted)
        self.reset_button.setEnabled(can_reset)

    def _add(self) -> None:
        dialog = VocabularySetDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets()),
        )
        if support.run_dialog_loop(self, dialog, self._apply_new):
            self._on_changed()

    def _edit(self) -> None:
        selection = self._selected()
        if selection is None or selection[1]:
            return
        entry = selection[0]
        dialog = VocabularySetDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets() if s.key != entry.key),
            initial=entry,
        )
        if support.run_dialog_loop(self, dialog, self._apply):
            self._on_changed()

    def _apply_new(self, result) -> None:
        key, label, kinds, sets_ = result
        existing = {keywords.fold(s.key) for s in self._vocabulary.sets()}
        support.check_new_key(key, existing)
        self._vocabulary.put_set(key, label=label, kinds=kinds, sets=sets_)

    def _apply(self, result) -> None:
        key, label, kinds, sets_ = result
        self._vocabulary.put_set(key, label=label, kinds=kinds, sets=sets_)

    def _delete(self) -> None:
        selection = self._selected()
        if selection is None or selection[1]:
            return
        entry = selection[0]
        if support.write_or_report(self, lambda: self._vocabulary.delete_set(entry.key)):
            self._on_changed()

    def _reset(self) -> None:
        selection = self._selected()
        if selection is None:
            return
        entry = selection[0]
        if support.write_or_report(self, lambda: self._vocabulary.reset_set(entry.key)):
            self._on_changed()
