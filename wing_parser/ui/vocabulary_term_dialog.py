"""Add or edit one term. A term is `ignore: true` OR kinds/sets, never
both (vocabulary.put_term already refuses that combination) -- the
Ignore checkbox disables both list widgets while it is ticked so the
dialog cannot even try to send both.

Combo default (adapted from the plan's draft, which left a brand-new
term at "word"): `vocabulary.put_term`'s own keyword default is
`match="exact"` (vocabulary.py), so a term created here with the combo
untouched writes the same value the API would have chosen on its own.
An edited term keeps whatever match its entry already has.

Pre-selecting an edited entry's own sets/kinds by FOLDED identity, not
exact string equality (fix round 1 minor) -- see `vocabulary_set_dialog`'s
docstring for why: a case/diacritic-variant set reference is valid, not
broken, and must not be silently dropped just because the dialog's own
pre-select missed it."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout,
)

from wing_parser.showcontext.ingest import keywords
from wing_parser.ui.texts import text


class VocabularyTermDialog(QDialog):
    def __init__(self, parent=None, *, known_kinds=(), known_sets=(), initial=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("vocabulary.title"))
        self._initial = initial

        self.name_edit = QLineEdit(initial.key if initial else "")
        self.name_edit.setEnabled(initial is None)

        self.match_box = QComboBox()
        self.match_box.addItem(text("vocabulary.dialog.match.word"), "word")
        self.match_box.addItem(text("vocabulary.dialog.match.exact"), "exact")
        initial_match = initial.match if initial else "exact"
        self.match_box.setCurrentIndex(0 if initial_match == "word" else 1)

        self.ignore_check = QCheckBox(text("vocabulary.dialog.ignore"))
        self.ignore_check.setChecked(bool(initial and initial.ignore))
        self.ignore_check.toggled.connect(self._apply_ignore_state)

        initial_kind_identities = {keywords.fold(k) for k in initial.kinds} if initial else set()
        self.kinds_list = QListWidget()
        self.kinds_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for kind in known_kinds:
            item = QListWidgetItem(kind)
            self.kinds_list.addItem(item)
            if keywords.fold(kind) in initial_kind_identities:
                item.setSelected(True)

        initial_set_identities = {keywords.fold(s) for s in initial.sets} if initial else set()
        self.sets_list = QListWidget()
        self.sets_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for key in known_sets:
            item = QListWidgetItem(key)
            self.sets_list.addItem(item)
            if keywords.fold(key) in initial_set_identities:
                item.setSelected(True)

        self._apply_ignore_state(self.ignore_check.isChecked())

        form = QFormLayout()
        form.addRow(text("vocabulary.dialog.name"), self.name_edit)
        form.addRow(text("vocabulary.dialog.match"), self.match_box)
        form.addRow("", self.ignore_check)
        form.addRow(text("vocabulary.dialog.kinds"), self.kinds_list)
        form.addRow(text("vocabulary.dialog.sets"), self.sets_list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _apply_ignore_state(self, ignored: bool) -> None:
        self.kinds_list.setEnabled(not ignored)
        self.sets_list.setEnabled(not ignored)

    def result(self) -> tuple[str, tuple[str, ...], tuple[str, ...], bool, str]:
        key = self.name_edit.text().strip() or (self._initial.key if self._initial else "")
        ignore = self.ignore_check.isChecked()
        kinds = () if ignore else tuple(item.text() for item in self.kinds_list.selectedItems())
        sets_ = () if ignore else tuple(item.text() for item in self.sets_list.selectedItems())
        match = self.match_box.currentData()
        return key, kinds, sets_, ignore, match
