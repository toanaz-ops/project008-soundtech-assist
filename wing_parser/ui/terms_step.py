"""The Terms step: one row per unresolved fragment, taught in one click.

Each row (terms_row.TermsRow) owns its own key field, "match inside a
sentence" checkbox, kind/set pickers and Record/Ignore(remember)/Skip
buttons -- moved there so this file stays under the 200-line ceiling
(docs/tech-debt.md#d-29's own reason). Record and Ignore write straight
through vocabulary.py; after either, every remaining PENDING row is
re-resolved against the reloaded vocabulary, because one new keyword can
clear several rows below it (design spec §4). The pre-wave-4
load_guesses/_apply_guesses flow is gone -- "AI: propose for unread
rows" opens the Vocabulary window's Assistant tab (Tasks 5-6)
pre-loaded with every still-pending fragment. The "Vocabulary..." button
opens the same window over this step's own directory and re-resolves on
close, so a term taught there clears rows here too (controller
requirement on top of the brief, spec §8.1).

Fix round 1: `Vocabulary.load` in `populate`/`_reresolve` is guarded --
a hand-edited classifier.yaml broken badly enough to raise (not just an
entry-level problem, which `Vocabulary.load` already swallows into
`.problems`) reports through `self.fail` instead of raising out of a Qt
slot. `self.fail` is a plain public attribute (same pattern as
`directory`), wired by `import_steps._terms` to `page._fail`, so this
widget still needs no constructor args. "AI: propose for unread rows"
disables itself once no row is left pending -- checked after populate,
after every re-resolve, and after a Skip (which does not itself trigger
a re-resolve, since it wrote nothing).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import QPushButton, QScrollArea, QVBoxLayout, QWidget

from wing_parser.classifier import vocabulary as vocab_module
from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext.ingest import build
from wing_parser.ui import import_controller as ic
from wing_parser.ui.terms_row import TermsRow
from wing_parser.ui.texts import text


class TermsStep(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._rows: dict[str, TermsRow] = {}
        self._result = None
        self._rows_data: tuple = ()
        self._vocabulary = None
        # record/ignore's write target; tests point this at tmp_path, None = cache default.
        self.directory = None
        # a broken classifier.yaml reports here instead of raising out of a slot;
        # import_steps._terms wires this to page._fail. Default: swallow (headless use).
        self.fail: Callable[[Exception], None] = lambda exc: None

        self.vocabulary_button = QPushButton(text("vocabulary.open_button"))
        self.vocabulary_button.clicked.connect(self._open_vocabulary)
        self.ai_propose_button = QPushButton(text("import.terms.ai_propose"))
        self.ai_propose_button.clicked.connect(self._ai_propose)

        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._rows_container)

        layout = QVBoxLayout(self)
        layout.addWidget(self.vocabulary_button)
        layout.addWidget(self.ai_propose_button)
        layout.addWidget(scroll, 1)

    # -- building -----------------------------------------------------------

    def populate(self, result) -> None:
        """One row per unresolved fragment; rebuilt fresh for every result."""
        try:
            vocabulary = vocab_module.Vocabulary.load(self.directory)
        except (OSError, ValueError) as exc:
            self.fail(exc)
            return
        for row in self._rows.values():
            row.setParent(None)
        self._rows.clear()
        self._result = result
        self._vocabulary = vocabulary
        kinds = known_kinds("channels")
        sets_ = tuple(s.key for s in self._vocabulary.sets())
        terms = ic.unresolved(result)
        context_by_term = ic.context_for(terms, self._rows_data)
        for fragment in terms:
            row = TermsRow(
                fragment, vocabulary=self._vocabulary, known_kinds=kinds, known_sets=sets_,
                context_lines=tuple(context_by_term.get(fragment, ())),
                on_written=self._reresolve,
            )
            row.skip_button.clicked.connect(self._update_ai_propose_enabled)
            self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
            self._rows[fragment] = row
        self._update_ai_propose_enabled()

    def set_rows(self, rows: tuple) -> None:
        self._rows_data = rows

    # -- re-resolution ----------------------------------------------------

    def _reresolve(self) -> None:
        try:
            vocabulary = vocab_module.Vocabulary.load(self.directory)
        except (OSError, ValueError) as exc:
            self.fail(exc)
            return
        self._vocabulary = vocabulary
        for fragment, row in self._rows.items():
            if row.state != "pending":
                continue
            row.set_vocabulary(self._vocabulary)
            resolution = build.resolve_fragment(fragment, self._vocabulary)
            if resolution.kinds or resolution.ignored:
                row.mark_resolved()
        self._update_ai_propose_enabled()

    def _update_ai_propose_enabled(self) -> None:
        self.ai_propose_button.setEnabled(
            any(row.state == "pending" for row in self._rows.values()))

    # -- AI / Vocabulary entry points --------------------------------------

    def _open_vocabulary(self) -> None:
        from wing_parser.ui.vocabulary_window import open_vocabulary

        open_vocabulary(self, directory=self.directory)
        self._reresolve()

    def _ai_propose(self) -> None:
        from wing_parser.ui.vocabulary_window import open_vocabulary

        pending = tuple(f for f, row in self._rows.items() if row.state == "pending")
        open_vocabulary(self, directory=self.directory, fragments=pending)
        self._reresolve()

    # -- test seams -----------------------------------------------------------

    def record_button_for(self, term: str) -> QPushButton:
        return self._rows[term].record_button

    def skip_button_for(self, term: str) -> QPushButton:
        return self._rows[term].skip_button

    def kind_editor_for(self, term: str):
        return self._rows[term].kinds_list

    def term_row_state(self, term: str) -> str:
        return self._rows[term].state
