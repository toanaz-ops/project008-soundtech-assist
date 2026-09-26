"""Add or edit one set. The name is fixed once created -- renaming would
leave an orphaned key on disk (put_set writes under whatever key it is
given; it does not delete an old one), so this dialog disables the name
field when editing rather than half-supporting a rename."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QListWidget, QListWidgetItem, QVBoxLayout,
)

from wing_parser.ui.texts import text


class VocabularySetDialog(QDialog):
    def __init__(self, parent=None, *, known_kinds=(), known_sets=(), initial=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("vocabulary.title"))
        self._initial = initial

        self.name_edit = QLineEdit(initial.key if initial else "")
        self.name_edit.setEnabled(initial is None)
        self.label_edit = QLineEdit(initial.label if initial else "")

        self.kinds_list = QListWidget()
        self.kinds_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for kind in known_kinds:
            item = QListWidgetItem(kind)
            self.kinds_list.addItem(item)
            if initial and kind in initial.kinds:
                item.setSelected(True)

        self.sets_list = QListWidget()
        self.sets_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for key in known_sets:
            item = QListWidgetItem(key)
            self.sets_list.addItem(item)
            if initial and key in initial.sets:
                item.setSelected(True)

        form = QFormLayout()
        form.addRow(text("vocabulary.dialog.name"), self.name_edit)
        form.addRow(text("vocabulary.dialog.label"), self.label_edit)
        form.addRow(text("vocabulary.dialog.kinds"), self.kinds_list)
        form.addRow(text("vocabulary.dialog.sets"), self.sets_list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def result(self) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
        key = self.name_edit.text().strip() or (self._initial.key if self._initial else "")
        label = self.label_edit.text().strip() or key
        kinds = tuple(item.text() for item in self.kinds_list.selectedItems())
        sets_ = tuple(item.text() for item in self.sets_list.selectedItems())
        return key, label, kinds, sets_
