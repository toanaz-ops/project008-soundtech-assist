"""The Terms tab: a table, Add/Edit/Delete/Reset, a live search filter
(S1), and two broken-reference actions (S2, fix round 1) for a term
naming a set that no longer exists -- see `vocabulary_broken_ref.py`.
A tombstoned default term shows as its own greyed row, source
"default, deleted" (I1); Reset is the only enabled action there. Edit is
disabled for a row with a genuinely broken reference, closing the old
silent-drop-on-Edit bug; a case/diacritic-variant reference is not
broken (folded identity, same as `vocabulary_checks.check_sets`) and
stays editable via the dialog's own folded pre-select."""

from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext.ingest import keywords
from wing_parser.ui import vocabulary_broken_ref as broken_ref
from wing_parser.ui import vocabulary_tab_support as support
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_term_dialog import VocabularyTermDialog

_COLUMNS = ("vocabulary.col.key", "vocabulary.col.kinds", "vocabulary.col.nested",
           "vocabulary.col.match", "vocabulary.col.source")


class VocabularyTermsTab(QWidget):
    def __init__(self, vocabulary, on_changed) -> None:
        super().__init__()
        self._vocabulary = vocabulary
        self._on_changed = on_changed
        self._row_entries: list[tuple] = []   # (TermEntry, is_deleted)
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
        self.pick_set_button = QPushButton(text("vocabulary.pick_set"))
        self.drop_ref_button = QPushButton(text("vocabulary.drop_reference"))
        self.add_button.clicked.connect(self._add)
        self.edit_button.clicked.connect(self._edit)
        self.delete_button.clicked.connect(self._delete)
        self.reset_button.clicked.connect(self._reset)
        self.pick_set_button.clicked.connect(self._pick_another_set)
        self.drop_ref_button.clicked.connect(self._drop_reference)

        buttons = QHBoxLayout()
        for button in (self.add_button, self.edit_button, self.delete_button,
                      self.reset_button, self.pick_set_button, self.drop_ref_button):
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

    def _set_identities(self) -> set[str]:
        return {keywords.fold(s.key) for s in self._vocabulary.sets()}

    def _broken_sets(self, entry) -> tuple[str, ...]:
        identities = self._set_identities()
        return tuple(s for s in entry.sets if keywords.fold(s) not in identities)

    def _populate(self) -> None:
        rows = tuple((entry, False) for entry in self._vocabulary.terms())
        rows += tuple((entry, True) for entry in self._vocabulary.deleted_terms())
        self._row_entries = list(rows)
        self.table.setRowCount(len(rows))
        self._haystacks = []
        faded = self.palette().color(QPalette.ColorRole.PlaceholderText)
        identities = self._set_identities()
        for r, (entry, is_deleted) in enumerate(rows):
            kinds_text = (text("vocabulary.dialog.ignore") if entry.ignore
                         else ", ".join(entry.kinds))
            nested = ", ".join(
                s if keywords.fold(s) in identities else
                text("vocabulary.broken").format(names=s)
                for s in entry.sets
            )
            source = (text("vocabulary.source.default_deleted") if is_deleted
                     else entry.display_origin)
            values = (entry.key, kinds_text, nested, entry.match, source)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if is_deleted:
                    item.setForeground(faded)
                self.table.setItem(r, column, item)
            self._haystacks.append(support.folded_haystack(entry.key, kinds_text))
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
        broken = self._broken_sets(entry) if has_selection and not is_deleted else ()
        can_reset = has_selection and (
            is_deleted or self._vocabulary.has_default_term(entry.key))
        self.edit_button.setEnabled(has_selection and not is_deleted and not broken)
        self.delete_button.setEnabled(has_selection and not is_deleted)
        self.reset_button.setEnabled(can_reset)
        self.pick_set_button.setEnabled(bool(broken))
        self.drop_ref_button.setEnabled(bool(broken))

    def _add(self) -> None:
        dialog = VocabularyTermDialog(
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
        dialog = VocabularyTermDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets()), initial=entry,
        )
        if support.run_dialog_loop(self, dialog, self._apply):
            self._on_changed()

    def _apply_new(self, result) -> None:
        key, kinds, sets_, ignore, match = result
        existing = {keywords.fold(t.key) for t in self._vocabulary.terms()}
        support.check_new_key(key, existing)
        self._vocabulary.put_term(key, kinds=kinds, sets=sets_, ignore=ignore, match=match)

    def _apply(self, result) -> None:
        key, kinds, sets_, ignore, match = result
        self._vocabulary.put_term(key, kinds=kinds, sets=sets_, ignore=ignore, match=match)

    def _delete(self) -> None:
        selection = self._selected()
        if selection is None or selection[1]:
            return
        entry = selection[0]
        if support.write_or_report(self, lambda: self._vocabulary.delete_term(entry.key)):
            self._on_changed()

    def _reset(self) -> None:
        selection = self._selected()
        if selection is None:
            return
        entry = selection[0]
        if support.write_or_report(self, lambda: self._vocabulary.reset_term(entry.key)):
            self._on_changed()

    def _pick_another_set(self) -> None:
        selection = self._selected()
        if selection is None:
            return
        entry = selection[0]
        broken = self._broken_sets(entry)
        if not broken:
            return
        broken_ref.pick_another_set(self, self._vocabulary, entry, broken[0], self._on_changed)

    def _drop_reference(self) -> None:
        selection = self._selected()
        if selection is None:
            return
        entry = selection[0]
        broken = self._broken_sets(entry)
        if not broken:
            return
        broken_ref.drop_reference(self, self._vocabulary, entry, broken[0], self._on_changed)
