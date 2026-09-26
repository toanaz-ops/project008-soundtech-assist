"""The Vocabulary window's Assistant tab: propose, validate, tick, Apply.

Two ways in (design spec §8.2) share this class: the instruction box
below, and the Terms step's "AI: propose for unread rows" button (Task
7), which calls `propose_for_fragments` on a `VocabularyWindow` opened
with `initial_fragments` set (see vocabulary_window.py). Neither writes
anything before Apply (F11) -- `_show_proposal` only ever populates the
table; `_apply` is the sole call to `vocab_changes.apply`.

Greying out on failure (design spec §8.1: "the window works fully with
no key and no network; only the assistant greys out, saying why"):
`_failed` classifies every call failure through `provider_errors.classify`
(same classifier Settings' Test connection and Task 9's Try AI use) and,
for the classes that mean nothing will succeed until something OUTSIDE
this window changes (a bad/missing key, no network, a missing SDK in a
frozen exe), disables `propose_button`/`instruction_edit` on top of
reporting the message -- the rest of the Vocabulary window (Sets/Terms
tabs) is a separate widget and is never touched.

One honest limitation, worth knowing before reading `_UNRECOVERABLE`:
`propose_changes` (vocab_changes.py) calls into `provider.py`'s shared
`complete_json`, which wraps ANY raw exception a Provider raises into a
bare `ProviderError(str(exc))` before it ever reaches `_failed` --
discarding a real SDK error's `.status_code` and its type. That strips
exactly what `provider_errors.classify` uses to tell BAD_KEY/QUOTA/
NO_NETWORK apart (see that module's own docstring), so through THIS
call path only SDK_MISSING is genuinely reachable today (its check is a
text match on the wrapped message, not the exception's type -- see
`provider_anthropic.py`'s own ImportError handler). This predates this
task (`llm.py`/`guess.py`/`suggest.py` hit the same wrapper) and is not
this task's to fix; `_UNRECOVERABLE` still lists all three classes so
this widget starts telling them apart for real the moment that wrapper
is changed to preserve a raw exception's identity.
"""

from __future__ import annotations

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from wing_parser.classifier import provider_errors, vocab_changes
from wing_parser.classifier.matcher import known_kinds
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_tab_support import write_or_report
from wing_parser.ui.workers import CallRunner

_COLUMNS = (
    "vocabulary.assistant.col.apply", "vocabulary.assistant.col.before",
    "vocabulary.assistant.col.after", "vocabulary.assistant.col.reason",
)

_UNRECOVERABLE = (provider_errors.BAD_KEY, provider_errors.NO_NETWORK, provider_errors.SDK_MISSING)


class VocabularyAssistant(QWidget):
    def __init__(self, vocabulary, provider_factory, on_applied) -> None:
        super().__init__()
        self._vocabulary = vocabulary
        self._provider_factory = provider_factory
        self._on_applied = on_applied
        self._validated: list[vocab_changes.Validated] = []
        self._checks: list[QCheckBox] = []

        self.instruction_edit = QPlainTextEdit()
        self.instruction_edit.setPlaceholderText(text("vocabulary.assistant.placeholder"))
        self.propose_button = QPushButton(text("vocabulary.assistant.propose"))
        self.propose_button.clicked.connect(self._propose)
        self.cancel_button = QPushButton(text("vocabulary.assistant.cancel"))
        self.cancel_button.setVisible(False)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self._runner = CallRunner(self)
        self._call = ButtonRunner(
            runner=self._runner, primary=self.propose_button, cancel=self.cancel_button,
            report=self.status_label.setText,
            running=text("vocabulary.assistant.running"),
            cancelled=text("vocabulary.assistant.cancelled"),
            timeout_text=text("vocabulary.assistant.timeout"),
            busy_text=text("vocabulary.assistant.busy"), on_error=self._failed,
        )
        self.cancel_button.clicked.connect(self._call.cancel)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([text(key) for key in _COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.apply_button = QPushButton(text("vocabulary.assistant.apply"))
        self.apply_button.clicked.connect(self._apply)

        buttons = QHBoxLayout()
        buttons.addWidget(self.propose_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.instruction_edit)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)
        layout.addWidget(self.apply_button)

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary

    def propose_for_fragments(self, fragments: tuple[str, ...]) -> bool:
        return self._start(fragments=fragments, instruction="")

    def _propose(self) -> None:
        self._start(fragments=(), instruction=self.instruction_edit.toPlainText().strip())

    def _start(self, *, fragments, instruction) -> bool:
        provider = self._provider_factory()
        call = partial(
            vocab_changes.propose_changes, instruction=instruction, fragments=fragments,
            vocabulary=self._vocabulary, known_kinds=known_kinds("channels"),
        )
        return self._call.run("guesses", call, provider, on_success=self._show_proposal)

    def _show_proposal(self, changes) -> None:
        """Populate the table only -- nothing here writes. A row's
        checkbox starts ticked and enabled exactly when `validate` found
        no problem; an invalid row's reason column names why, appended
        to the model's own stated reason."""
        self._validated = [vocab_changes.validate(c, self._vocabulary) for c in changes]
        self._checks = []
        self.table.setRowCount(len(self._validated))
        for row, validated in enumerate(self._validated):
            change = validated.change
            reason = change.reason if validated.valid else (
                f"{change.reason} — {'; '.join(validated.problems)}"
            )
            check = QCheckBox()
            check.setEnabled(validated.valid)
            check.setChecked(validated.valid)
            self.table.setCellWidget(row, 0, check)
            self.table.setItem(row, 1, QTableWidgetItem("" if change.before is None else str(change.before)))
            self.table.setItem(row, 2, QTableWidgetItem("" if change.after is None else str(change.after)))
            self.table.setItem(row, 3, QTableWidgetItem(reason))
            self._checks.append(check)

    def _apply(self) -> None:
        """The sole call to `vocab_changes.apply` in this class -- and
        the sole point anything is written (F11). A row ticked-and-valid
        at proposal time is re-checked here for real: `apply` calls
        straight into `vocabulary.put_set`/`put_term`, which validate
        again immediately before writing -- catching the case a batch of
        several changes can create (an earlier applied change altering
        what a later one's cycle/kind/set check sees, see vocab_changes.py's
        own docstring for why this module does not chain-validate the
        whole batch up front instead). `write_or_report` (shared with the
        Sets/Terms tabs) reports any such failure with the house
        QMessageBox and lets the rest of the ticked rows proceed."""
        applied = 0
        for check, validated in zip(self._checks, self._validated):
            if not (check.isChecked() and validated.valid):
                continue
            change = validated.change
            if write_or_report(self, partial(vocab_changes.apply, change, self._vocabulary)):
                applied += 1
        if applied:
            self._on_applied()

    def _failed(self, exc: Exception) -> None:
        code, message = provider_errors.classify(exc)
        self.status_label.setText(message)
        if code in _UNRECOVERABLE:
            self.propose_button.setEnabled(False)
            self.instruction_edit.setEnabled(False)
