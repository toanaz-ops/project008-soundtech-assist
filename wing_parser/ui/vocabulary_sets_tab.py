"""The Sets tab: a table, Add/Edit/Delete/Reset, and the AI-approved-
looking source column. Each set's own row also shows its fully expanded
kinds (F13) so nesting's effect is visible without opening a second row.

A write that fails validation (unknown kind, unknown set, a cycle -- all
subclasses of ValueError, vocabulary_store.py) is shown to the operator
by re-opening the SAME dialog instance rather than losing what they
typed: `dialog.exec()` is called again on it in `_run_dialog_loop`,
which is safe -- a QDialog's widgets keep their state across repeated
`exec()` calls, only its own accept/reject result resets."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from wing_parser.classifier.matcher import known_kinds
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_set_dialog import VocabularySetDialog

_COLUMNS = ("vocabulary.col.label", "vocabulary.col.kinds",
           "vocabulary.col.nested", "vocabulary.col.source")


class VocabularySetsTab(QWidget):
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
        rows = self._vocabulary.sets()
        self.table.setRowCount(len(rows))
        for r, entry in enumerate(rows):
            expanded = ", ".join(self._vocabulary.expand_set(entry.key))
            nested = ", ".join(entry.sets)
            if entry.sets:
                nested = f"{nested}  ->  {expanded}"
            self.table.setItem(r, 0, QTableWidgetItem(entry.label))
            self.table.setItem(r, 1, QTableWidgetItem(", ".join(entry.kinds)))
            self.table.setItem(r, 2, QTableWidgetItem(nested))
            self.table.setItem(r, 3, QTableWidgetItem(entry.display_origin))

    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self._vocabulary.sets()[row]

    def _add(self) -> None:
        dialog = VocabularySetDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets()),
        )
        if self._run_dialog_loop(dialog, self._apply):
            self._on_changed()

    def _edit(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        dialog = VocabularySetDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets() if s.key != entry.key),
            initial=entry,
        )
        if self._run_dialog_loop(dialog, self._apply):
            self._on_changed()

    def _apply(self, result) -> None:
        key, label, kinds, sets_ = result
        self._vocabulary.put_set(key, label=label, kinds=kinds, sets=sets_)

    def _delete(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        self._vocabulary.delete_set(entry.key)
        self._on_changed()

    def _reset(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        self._vocabulary.reset_set(entry.key)
        self._on_changed()

    def _run_dialog_loop(self, dialog, apply) -> bool:
        """Keep re-showing `dialog` (same instance, input kept) until the
        write succeeds or the operator cancels. `UnknownKindError`/
        `UnknownSetError`/`CycleError` are all `ValueError` subclasses
        (vocabulary_store.py) -- one `except` covers every save-time
        failure this tab can produce, and `CycleError`'s own message
        already spells out the path (" → "-joined)."""
        while dialog.exec():
            try:
                apply(dialog.result())
            except ValueError as exc:
                QMessageBox.warning(self, text("vocabulary.title"), str(exc))
                continue
            return True
        return False
