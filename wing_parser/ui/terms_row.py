"""One Terms-step row: an unresolved fragment, taught in one click.

Record writes through vocabulary.put_term (kinds and/or sets picked from
lists built off patterns.yaml's known kinds and the current sets --
never typed, so nothing expects: would refuse can be saved, W6). Ignore
(remember) writes put_term(..., ignore=True). Skip writes nothing --
this import only (design spec §4). The key field prefills with the
WHOLE fragment; "match inside a sentence" auto-ticks once the operator
shortens it below the fragment's own length (a shortened key almost
always means "match this word wherever it appears"), and can still be
ticked by hand for an unshortened key (e.g. so "trống" also matches
inside a longer sibling fragment).

A failed Record/Ignore (a blank key, an unknown kind or set that slipped
in, or the write itself hitting disk trouble) is reported by name and
leaves the row's input and state untouched so the operator can fix and
retry (controller requirement on top of the brief). A write that
SUCCEEDS but still leaves this row's own fragment unresolved -- the
usual cause is a shortened key with "match inside a sentence" unticked
by hand after the auto-tick -- warns rather than silently claiming
"recorded"; the term itself stays saved either way (fix round 1,
Important/minor).

`set_vocabulary` rebuilds `sets_list` from the fresh vocabulary's own
`.sets()` on every re-resolve, keeping whichever selected keys still
exist -- a set created or deleted in the Vocabulary window must show up
here too. M3: Record/Ignore confirms first, naming the entry, when the
key folds to one that already exists -- `put_term` would otherwise
replace it with no warning of its own.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QVBoxLayout,
)

from wing_parser.showcontext.ingest import build, keywords
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_tab_support import confirm_overwrite, write_or_report


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
        self._fill_sets_list(known_sets)

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
        self._fill_sets_list(
            tuple(entry.key for entry in vocabulary.sets()), keep=self._picked_sets())

    def mark_resolved(self) -> None:
        """A sibling row's Record/Ignore made this fragment resolve too
        (design spec §4: 're-resolved immediately, so one keyword can
        clear several rows below it'). Disable, do not remove -- the
        operator can still see what happened to it."""
        self.state = "resolved"
        self.setEnabled(False)

    def _fill_sets_list(self, keys: tuple[str, ...], *, keep: tuple[str, ...] = ()) -> None:
        self.sets_list.clear()
        for key in keys:
            item = QListWidgetItem(key)
            self.sets_list.addItem(item)
            if key in keep:
                item.setSelected(True)

    def _picked_kinds(self) -> tuple[str, ...]:
        return tuple(item.text() for item in self.kinds_list.selectedItems())

    def _picked_sets(self) -> tuple[str, ...]:
        return tuple(item.text() for item in self.sets_list.selectedItems())

    def _match_mode(self) -> str:
        return "word" if self.word_match_check.isChecked() else "exact"

    def _auto_check_word_match(self, current_text: str) -> None:
        if len(current_text.strip()) < len(self.fragment):
            self.word_match_check.setChecked(True)

    def _require_key(self) -> str | None:
        key = self.key_edit.text().strip()
        if key:
            return key
        QMessageBox.warning(self, text("vocabulary.title"), text("import.terms.empty_key"))
        return None

    def _existing_term_with_same_key(self, key: str):
        folded = keywords.fold(key)
        for term in self._vocabulary.terms():
            if keywords.fold(term.key) == folded:
                return term
        return None

    def _confirm_overwrite_if_any(self, key: str) -> bool:
        existing = self._existing_term_with_same_key(key)
        return existing is None or confirm_overwrite(self, existing.key)

    def _record(self) -> None:
        key = self._require_key()
        if key is None:
            return
        if not self._confirm_overwrite_if_any(key):
            return
        kinds, sets_ = self._picked_kinds(), self._picked_sets()
        ok = write_or_report(
            self, lambda: self._vocabulary.put_term(
                key, kinds=kinds, sets=sets_,
                match=self._match_mode(), origin="manual",
            ))
        if not ok:
            return
        self._finish_write()

    def _ignore(self) -> None:
        key = self._require_key()
        if key is None:
            return
        if not self._confirm_overwrite_if_any(key):
            return
        ok = write_or_report(
            self, lambda: self._vocabulary.put_term(
                key, ignore=True, match=self._match_mode(), origin="manual"))
        if not ok:
            return
        self._finish_write()

    def _finish_write(self) -> None:
        """The write already landed -- `_on_written` first, so a sibling
        row can clear even when THIS row's own fragment does not (the
        vocabulary re-resolve refreshes `self._vocabulary` too). Only
        THEN check whether this row's own fragment now resolves: if not,
        warn instead of silently claiming "recorded" -- the term stays
        saved, but the row stays pending so the operator can fix the key
        or the checkbox and record again."""
        self._on_written()
        resolution = build.resolve_fragment(self.fragment, self._vocabulary)
        if not (resolution.kinds or resolution.ignored):
            QMessageBox.warning(
                self, text("vocabulary.title"),
                text("import.terms.not_matching").format(fragment=self.fragment))
            return
        self.state = "recorded"
        self.setEnabled(False)

    def _skip(self) -> None:
        self.state = "skipped"
        self.setEnabled(False)
