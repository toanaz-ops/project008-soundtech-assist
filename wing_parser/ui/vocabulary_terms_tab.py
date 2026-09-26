"""The Terms tab: a table, Add/Edit/Delete/Reset. A term whose set no
longer exists is shown with the set name plus '(broken)' rather than
crashing the row (design spec §3.2/§8.1). The check is by FOLDED
identity (`keywords.fold`, same as `vocabulary_checks.check_sets`/
`Vocabulary.expand_set`) rather than exact string equality, so a
reference that only differs in case or diacritics from the set's own
authored key -- which `Vocabulary` itself treats as the same set -- is
not wrongly flagged as broken here (adapted from the plan's draft, which
compared raw strings).

Save-time failures are handled exactly like the Sets tab's
`_run_dialog_loop` -- see that module's docstring."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext.ingest import keywords
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_term_dialog import VocabularyTermDialog

_COLUMNS = ("vocabulary.col.key", "vocabulary.col.kinds", "vocabulary.col.nested",
           "vocabulary.col.match", "vocabulary.col.source")


class VocabularyTermsTab(QWidget):
    def __init__(self, vocabulary, on_changed) -> None:
        super().__init__()
        self._vocabulary = vocabulary
        self._on_changed = on_changed

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([text(key) for key in _COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

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
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        self._populate()

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary
        self._populate()

    def _populate(self) -> None:
        set_identities = {keywords.fold(s.key) for s in self._vocabulary.sets()}
        rows = self._vocabulary.terms()
        self.table.setRowCount(len(rows))
        for r, entry in enumerate(rows):
            if entry.ignore:
                kinds_text = text("vocabulary.dialog.ignore")
            else:
                kinds_text = ", ".join(entry.kinds)
            nested = ", ".join(
                s if keywords.fold(s) in set_identities else
                text("vocabulary.broken").format(names=s)
                for s in entry.sets
            )
            self.table.setItem(r, 0, QTableWidgetItem(entry.key))
            self.table.setItem(r, 1, QTableWidgetItem(kinds_text))
            self.table.setItem(r, 2, QTableWidgetItem(nested))
            self.table.setItem(r, 3, QTableWidgetItem(entry.match))
            self.table.setItem(r, 4, QTableWidgetItem(entry.display_origin))

    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self._vocabulary.terms()[row]

    def _add(self) -> None:
        dialog = VocabularyTermDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets()),
        )
        if self._run_dialog_loop(dialog, self._apply):
            self._on_changed()

    def _edit(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        dialog = VocabularyTermDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets()), initial=entry,
        )
        if self._run_dialog_loop(dialog, self._apply):
            self._on_changed()

    def _apply(self, result) -> None:
        key, kinds, sets_, ignore, match = result
        self._vocabulary.put_term(key, kinds=kinds, sets=sets_, ignore=ignore, match=match)

    def _delete(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        self._vocabulary.delete_term(entry.key)
        self._on_changed()

    def _reset(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        self._vocabulary.reset_term(entry.key)
        self._on_changed()

    def _run_dialog_loop(self, dialog, apply) -> bool:
        """See VocabularySetsTab._run_dialog_loop. `put_term` also raises a
        plain `ValueError` (not a named subclass) when neither ignore nor
        kinds/sets is given -- the same broad `except ValueError` covers
        that case too, so an empty term never crashes this tab."""
        while dialog.exec():
            try:
                apply(dialog.result())
            except ValueError as exc:
                QMessageBox.warning(self, text("vocabulary.title"), str(exc))
                continue
            return True
        return False
