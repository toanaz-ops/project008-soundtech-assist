"""The Terms tab: a table, Add/Edit/Delete/Reset, a live search filter
(S1), and two broken-reference actions (S2) for a term naming a set that
no longer exists -- see `vocabulary_broken_ref.py`. A tombstoned default
term shows as its own greyed row, source "default, deleted" (I1); Reset
is the only enabled action there. Edit is disabled for a row with a
genuinely broken reference, closing the old silent-drop-on-Edit bug; a
case/diacritic-variant reference is not broken (folded identity) and
stays editable via the dialog's own folded pre-select.

Fix round 2 also confirms before an edit would drop a hand-edited kind
the dialog cannot even show, and confirms Delete by name -- see
`vocabulary_tab_support.py` for both, and for the widget-construction
helpers used below."""

from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QTableWidgetItem, QVBoxLayout, QWidget

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext.ingest import keywords
from wing_parser.ui import token_labels
from wing_parser.ui import vocabulary_broken_ref as broken_ref
from wing_parser.ui import vocabulary_tab_support as support
from wing_parser.ui import vocabulary_tab_widgets as widgets
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

        self.search_edit = widgets.build_search_edit(self._apply_filter)
        self.table = widgets.build_table(_COLUMNS, self._refresh_buttons)
        buttons_layout, (
            self.add_button, self.edit_button, self.delete_button, self.reset_button,
            self.pick_set_button, self.drop_ref_button,
        ) = widgets.build_toolbar(
            ("vocabulary.add", self._add), ("vocabulary.edit", self._edit),
            ("vocabulary.delete", self._delete), ("vocabulary.reset", self._reset),
            ("vocabulary.pick_set", self._pick_another_set),
            ("vocabulary.drop_reference", self._drop_reference),
        )

        layout = QVBoxLayout(self)
        layout.addWidget(self.search_edit)
        layout.addWidget(self.table)
        layout.addLayout(buttons_layout)
        self._populate()

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary
        self._populate()

    def _identities(self) -> set[str]:
        return widgets.set_identities(self._vocabulary)

    def _broken(self, entry) -> tuple[str, ...]:
        return widgets.broken_set_names(entry.sets, self._identities())

    def _populate(self) -> None:
        widgets.clear_selection(self.table)

        rows = tuple((entry, False) for entry in self._vocabulary.terms())
        rows += tuple((entry, True) for entry in self._vocabulary.deleted_terms())
        self._row_entries = list(rows)
        self.table.setRowCount(len(rows))
        self._haystacks = []
        faded = self.palette().color(QPalette.ColorRole.PlaceholderText)
        identities = self._identities()
        for r, (entry, is_deleted) in enumerate(rows):
            kinds_text = (text("vocabulary.dialog.ignore") if entry.ignore
                         else ", ".join(entry.kinds))
            nested = widgets.render_nested_sets(entry.sets, identities)
            source = (text("vocabulary.source.default_deleted") if is_deleted
                     else token_labels.label("origin", entry.display_origin))
            values = (entry.key, kinds_text, nested,
                      token_labels.label("match", entry.match), source)
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if is_deleted:
                    item.setForeground(faded)
                self.table.setItem(r, column, item)
            self._haystacks.append(widgets.folded_haystack(entry.key, kinds_text))
        self._apply_filter(self.search_edit.text())
        self._refresh_buttons()

    def _apply_filter(self, query: str) -> None:
        widgets.apply_search_filter(self.table, self._haystacks, query)

    def _selected(self):
        return widgets.selected_row(self.table, self._row_entries)

    def _refresh_buttons(self) -> None:
        selection = self._selected()
        entry, is_deleted = selection if selection else (None, False)
        has_selection = selection is not None
        broken = self._broken(entry) if has_selection and not is_deleted else ()
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
        known = known_kinds("channels")
        dialog = VocabularyTermDialog(
            self, known_kinds=known,
            known_sets=tuple(s.key for s in self._vocabulary.sets()), initial=entry,
        )
        apply_edit = lambda result: self._apply_edit(entry, known, result)  # noqa: E731
        if support.run_dialog_loop(self, dialog, apply_edit):
            self._on_changed()

    def _apply_new(self, result) -> None:
        key, kinds, sets_, ignore, match = result
        existing = {keywords.fold(t.key) for t in self._vocabulary.terms()}
        support.check_new_key(key, existing)
        self._vocabulary.put_term(key, kinds=kinds, sets=sets_, ignore=ignore, match=match)

    def _apply_edit(self, entry, known, result) -> None:
        key, kinds, sets_, ignore, match = result
        support.confirm_kind_drop(self, tuple(k for k in entry.kinds if k not in known))
        self._vocabulary.put_term(key, kinds=kinds, sets=sets_, ignore=ignore, match=match)

    def _delete(self) -> None:
        selection = self._selected()
        if selection is None or selection[1]:
            return
        entry = selection[0]
        if not support.confirm_delete(self, entry.key):
            return
        if support.write_or_report(self, lambda: self._vocabulary.delete_term(entry.key)):
            self._on_changed()

    def _reset(self) -> None:
        selection = self._selected()
        if selection is None:
            return
        entry = selection[0]
        if support.write_or_report(self, lambda: self._vocabulary.reset_term(entry.key)):
            self._on_changed()

    def _write_term(self, entry):
        return lambda new_sets: self._vocabulary.put_term(
            entry.key, kinds=entry.kinds, sets=new_sets,
            ignore=entry.ignore, match=entry.match)

    def _pick_another_set(self) -> None:
        selection = self._selected()
        entry = selection[0] if selection else None
        broken = self._broken(entry) if entry else ()
        if not broken:
            return
        broken_ref.pick_another_set(self, self._vocabulary, entry.sets, broken[0],
                                    self._write_term(entry), self._on_changed)

    def _drop_reference(self) -> None:
        selection = self._selected()
        entry = selection[0] if selection else None
        broken = self._broken(entry) if entry else ()
        if not broken:
            return
        broken_ref.drop_reference(self, entry.sets, broken[0],
                                  self._write_term(entry), self._on_changed)
