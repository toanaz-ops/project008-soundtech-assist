"""The Vocabulary window's Assistant tab: propose, validate, tick, Apply.

Two ways in (design spec §8.2) share this class: the instruction box
below, and the Terms step's "AI: propose for unread rows" button (Task
7), which calls `propose_for_fragments` on a `VocabularyWindow` opened
with `initial_fragments` set (see vocabulary_window.py). Neither writes
anything before Apply (F11) -- `_show_proposal` only ever populates the
table; `_apply` (via `vocabulary_assistant_support.apply_ticked`) is the
sole path to `vocab_changes.apply`.

Grey-out has two independent triggers (fix round 1, I0 added the first):

- **Proactive:** `_update_key_status`, run at construction and on every
  `showEvent` (same idiom as `key_status.KeyStatusLine`, and it recovers
  the same way -- re-showing this tab, or the window reopening after
  Settings changes, re-checks), disables `propose_button`/
  `instruction_edit` and says why BEFORE any call is attempted, using
  `key_status.key_configured()`. `propose_for_fragments`/`_propose` both
  also refuse outright.
- **Reactive:** `_failed` classifies every call failure through
  `provider_errors.classify` and, for `vocabulary_assistant_support.
  UNRECOVERABLE` classes, disables the same two widgets on top of
  reporting the message.

The rest of the Vocabulary window (Sets/Terms tabs) is a separate widget
and is never touched by either trigger. The worker-thread plumbing
(`propose_via_factory`, so a bad `provider.yaml` fails inside the worker
rather than the GUI thread -- fix round 1, I1) and the row/apply
mechanics live in `vocabulary_assistant_support.py`, split out to stay
under this project's 200-line UI-file ceiling.
"""

from __future__ import annotations

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QTableWidget, QVBoxLayout, QWidget,
)

from wing_parser.classifier import provider_errors, vocab_changes
from wing_parser.classifier.matcher import known_kinds
from wing_parser.ui import key_status
from wing_parser.ui import vocabulary_assistant_support as support
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner


class VocabularyAssistant(QWidget):
    def __init__(self, vocabulary, provider_factory, on_applied) -> None:
        super().__init__()
        self._vocabulary = vocabulary
        self._provider_factory = provider_factory
        self._on_applied = on_applied
        self._validated: list[vocab_changes.Validated] = []
        self._checks: list[QCheckBox] = []
        self._key_ok = True

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

        self.table = QTableWidget(0, len(support.COLUMNS))
        self.table.setHorizontalHeaderLabels([text(key) for key in support.COLUMNS])
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

        self._update_key_status()

    def showEvent(self, event) -> None:  # noqa: N802 - Qt naming
        super().showEvent(event)
        self._update_key_status()

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary

    def propose_for_fragments(self, fragments: tuple[str, ...]) -> bool:
        if not self._key_ok:
            return False
        return self._start(fragments=fragments, instruction="")

    def _propose(self) -> None:
        if not self._key_ok:
            return
        self._start(fragments=(), instruction=self.instruction_edit.toPlainText().strip())

    def _start(self, *, fragments, instruction) -> bool:
        call = partial(
            support.propose_via_factory, instruction=instruction, fragments=fragments,
            vocabulary=self._vocabulary, known_kinds=known_kinds("channels"),
        )
        return self._call.run("guesses", call, self._provider_factory, on_success=self._show_proposal)

    def _show_proposal(self, changes) -> None:
        """Populate the table only -- nothing here writes."""
        self._validated = [vocab_changes.validate(c, self._vocabulary) for c in changes]
        self._checks = []
        self.table.setRowCount(len(self._validated))
        for row, validated in enumerate(self._validated):
            check = support.populate_row(self.table, row, validated, self._vocabulary)
            self._checks.append(check)

    def _apply(self) -> None:
        """The sole path to `vocab_changes.apply` -- and the sole point
        anything is written (F11). Nothing ticked-and-valid is a no-op
        (leaves the table for a still-undecided operator); otherwise the
        table is cleared and the tally shown, so a second click with
        nothing left ticked is also a no-op (fix round 1 minor: never
        re-write)."""
        applied, failed = support.apply_ticked(self, self._checks, self._validated, self._vocabulary)
        if applied or failed:
            self.status_label.setText(
                text("vocabulary.assistant.apply_result").format(applied=applied, failed=failed))
            self.table.setRowCount(0)
            self._checks = []
            self._validated = []
        if applied:
            self._on_applied()

    def _update_key_status(self) -> None:
        """Proactive grey-out (fix round 1, I0): before any call is
        attempted, not only after one fails. Fix round 2 (important):
        this runs on every `showEvent` -- the window reopening with
        `initial_fragments` set, or a tab switch away and back -- which
        can land WHILE a call is genuinely in flight; re-enabling the
        button then would break `ButtonRunner`'s own disabled-while-
        running rule. `self._runner.busy` (workers.CallRunner) is the
        same flag `ButtonRunner.run` itself checks before starting a new
        call, so this can never disagree with it."""
        self._key_ok = key_status.key_configured()
        enabled = self._key_ok and not self._runner.busy
        self.propose_button.setEnabled(enabled)
        self.instruction_edit.setEnabled(enabled)
        if self._runner.busy:
            return   # a running call owns the status line; leave it alone
        no_key_text = text("vocabulary.assistant.no_key")
        if not self._key_ok:
            self.status_label.setText(no_key_text)
        elif self.status_label.text() == no_key_text:
            self.status_label.setText("")

    def _failed(self, exc: Exception) -> None:
        code, message = provider_errors.classify(exc)
        self.status_label.setText(message)
        if code in support.UNRECOVERABLE:
            self.propose_button.setEnabled(False)
            self.instruction_edit.setEnabled(False)
