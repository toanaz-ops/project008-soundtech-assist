"""One Terms-step row: an unresolved fragment, taught in one click.

Record writes through vocabulary.put_term (kinds and/or sets picked from
lists built off patterns.yaml's known kinds and the current sets --
never typed, so nothing expects: would refuse can be saved, W6). Ignore
(remember) writes put_term(..., ignore=True). Skip writes nothing --
this import only (design spec §4). The key field prefills with the
WHOLE fragment; "match inside a sentence" auto-ticks the moment the
operator shortens it below the fragment's own length, because a
shortened key almost always means "match this word wherever it
appears", not "this exact sentence, verbatim" -- the operator can still
tick it by hand for an unshortened key (e.g. to make a single word like
"trống" match inside a longer sibling fragment too).

A failed Record/Ignore (an empty picker with no ignore, an unknown kind
or set that slipped in, or the write itself hitting disk trouble) is
reported through vocabulary_tab_support.write_or_report -- same wording
the Vocabulary window's own tabs use -- and leaves the row's input and
state untouched so the operator can fix and retry (controller
requirement on top of the brief).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
)

from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_tab_support import write_or_report


class TermsRow(QGroupBox):
    def __init__(self, fragment: str, *, vocabulary, known_kinds, known_sets,
                 context_lines: tuple[str, ...] = (), on_written: Callable[[], None]) -> None:
        super().__init__(fragment)
        self.fragment = fragment
        self._vocabulary = vocabulary
        self._on_written = on_written
        self.state = "pending"

        self.key_edit = QLineEdit(fragment)
        self.key_edit.textChanged.connect(self._auto_check_word_match)
        self.word_match_check = QCheckBox(text("import.terms.match_word"))

        self.kinds_list = QListWidget()
        self.kinds_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for kind in known_kinds:
            self.kinds_list.addItem(QListWidgetItem(kind))

        self.sets_list = QListWidget()
        self.sets_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for key in known_sets:
            self.sets_list.addItem(QListWidgetItem(key))

        self.record_button = QPushButton(text("import.record"))
        self.record_button.clicked.connect(self._record)
        self.ignore_button = QPushButton(text("import.terms.ignore_remember"))
        self.ignore_button.clicked.connect(self._ignore)
        self.skip_button = QPushButton(text("import.skip"))
        self.skip_button.clicked.connect(self._skip)

        top = QHBoxLayout()
        top.addWidget(QLabel(text("import.terms.key")))
        top.addWidget(self.key_edit, 1)
        top.addWidget(self.word_match_check)

        context_label = QLabel("\n".join(context_lines))
        context_label.setWordWrap(True)

        pickers = QHBoxLayout()
        pickers.addWidget(self.kinds_list)
        pickers.addWidget(self.sets_list)

        buttons = QHBoxLayout()
        buttons.addWidget(self.record_button)
        buttons.addWidget(self.ignore_button)
        buttons.addWidget(self.skip_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(context_label)
        layout.addLayout(pickers)
        layout.addLayout(buttons)

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary

    def mark_resolved(self) -> None:
        """A sibling row's Record/Ignore made this fragment resolve too
        (design spec §4: 're-resolved immediately, so one keyword can
        clear several rows below it'). Disable, do not remove -- the
        operator can still see what happened to it."""
        self.state = "resolved"
        self.setEnabled(False)

    def _picked_kinds(self) -> tuple[str, ...]:
        return tuple(item.text() for item in self.kinds_list.selectedItems())

    def _picked_sets(self) -> tuple[str, ...]:
        return tuple(item.text() for item in self.sets_list.selectedItems())

    def _match_mode(self) -> str:
        return "word" if self.word_match_check.isChecked() else "exact"

    def _auto_check_word_match(self, current_text: str) -> None:
        if len(current_text.strip()) < len(self.fragment):
            self.word_match_check.setChecked(True)

    def _record(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            return
        kinds, sets_ = self._picked_kinds(), self._picked_sets()
        ok = write_or_report(
            self, lambda: self._vocabulary.put_term(
                key, kinds=kinds, sets=sets_,
                match=self._match_mode(), origin="manual",
            ))
        if not ok:
            return
        self.state = "recorded"
        self.setEnabled(False)
        self._on_written()

    def _ignore(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            return
        ok = write_or_report(
            self, lambda: self._vocabulary.put_term(
                key, ignore=True, match=self._match_mode(), origin="manual"))
        if not ok:
            return
        self.state = "recorded"
        self.setEnabled(False)
        self._on_written()

    def _skip(self) -> None:
        self.state = "skipped"
        self.setEnabled(False)
