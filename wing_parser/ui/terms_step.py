"""The terms step widget: one row per unresolved term.

The G2b invariant lives here: loading guesses only prefills the kind
editors -- nothing touches classifier.yaml until an explicit Record
click on that term's row. A blank kind is refused too: never write a
blank verdict. The page hands in the provider factory, a failure
reporter and the write target directory; this widget does the rest.
Guessing runs on the page's shared cancellable worker (task C).
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wing_parser.classifier.matcher import Classification
from wing_parser.ui import import_controller as ic
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner


class TermsStep(QWidget):
    def __init__(self, provider_factory, fail, runner=None,
                 report=None) -> None:
        super().__init__()
        self._provider_factory = provider_factory
        self._fail = fail
        self._rows: dict[str, dict] = {}
        self._result = None
        self._rows_data: tuple = ()
        # Where ic.record_term writes; None means the cache default.
        self.directory = None

        self.load_guesses_button = QPushButton(text("import.load_guesses"))
        self.load_guesses_button.clicked.connect(self.load_guesses)
        self.cancel_button = QPushButton(text("import.cancel"))
        self.cancel_button.setVisible(False)
        self._calls = ButtonRunner(
            runner=runner or CallRunner(self),
            primary=self.load_guesses_button, cancel=self.cancel_button,
            report=report or (lambda message: None),
            running=text("import.guessing"),
            cancelled=text("import.cancelled"),
            timeout_text=text("import.timeout"),
            busy_text=text("import.busy"), on_error=fail,
        )
        self.cancel_button.clicked.connect(self._calls.cancel)

        self.grid = QGridLayout()
        self.grid.setColumnStretch(1, 1)
        layout = QVBoxLayout(self)
        layout.addWidget(self.load_guesses_button)
        layout.addWidget(self.cancel_button)
        layout.addLayout(self.grid)
        layout.addStretch()

    # -- building ---------------------------------------------------------

    def populate(self, result) -> None:
        """One row per unresolved term; rebuilt fresh for every result."""
        while self.grid.count():
            self.grid.takeAt(0).widget().deleteLater()
        self._rows.clear()
        self._result = result
        terms = ic.unresolved(result)
        context_by_term = ic.context_for(terms, self._rows_data)
        for position, term in enumerate(terms):
            kind_edit = QLineEdit()
            record = QPushButton(text("import.record"))
            record.clicked.connect(lambda _=False, t=term: self.record(t))
            skip = QPushButton(text("import.skip"))
            skip.clicked.connect(lambda _=False, t=term: self.mark(t, "skipped"))
            context = QLabel("\n".join(context_by_term.get(term, [])))
            context.setWordWrap(True)

            self.grid.addWidget(QLabel(term), position * 2, 0)
            self.grid.addWidget(kind_edit, position * 2, 1)
            self.grid.addWidget(record, position * 2, 2)
            self.grid.addWidget(skip, position * 2, 3)
            self.grid.addWidget(context, position * 2 + 1, 1)
            self._rows[term] = {
                "kind": kind_edit,
                "record": record,
                "skip": skip,
                "state": "pending",
            }

    def set_rows(self, rows: tuple) -> None:
        self._rows_data = rows

    # -- actions ------------------------------------------------------------

    def load_guesses(self) -> None:
        """Prefill proposed kinds only -- never a write.

        One remote call per term, so this runs on the shared worker
        under its "guesses" timeout; `_apply_guesses` is today's
        continuation, arriving from the worker thread instead.
        """
        if not self._rows:
            return
        terms = tuple(self._rows)
        self._calls.run(
            "guesses", ic.guesses_for, terms,
            ic.context_for(terms, self._rows_data), self._provider_factory,
            on_success=self._apply_guesses,
        )

    def _apply_guesses(self, pairs) -> None:
        for term, classification in pairs:
            if classification is not None and term in self._rows:
                self.kind_editor_for(term).setText(classification.kind)

    def record(self, term: str) -> None:
        """The only write path: an explicit click on this term's row."""
        kind = self.kind_editor_for(term).text().strip()
        if not kind:
            self._fail(ValueError(text("import.needs_kind")))
            return
        try:
            ic.record_term(
                term,
                Classification(kind=kind, confidence=1.0, origin="manual"),
                directory=self.directory,
            )
        except (OSError, ValueError) as exc:
            self._fail(exc)
            return
        self.mark(term, "recorded")

    def mark(self, term: str, state: str) -> None:
        self._rows[term]["state"] = state

    # -- test seams -----------------------------------------------------------

    def record_button_for(self, term: str) -> QPushButton:
        return self._rows[term]["record"]

    def skip_button_for(self, term: str) -> QPushButton:
        return self._rows[term]["skip"]

    def kind_editor_for(self, term: str) -> QLineEdit:
        return self._rows[term]["kind"]

    def term_row_state(self, term: str) -> str:
        return self._rows[term]["state"]
