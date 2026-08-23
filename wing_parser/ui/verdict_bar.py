"""Record a verdict on the selected finding.

Today this costs him typing
`wing feedback G8:ch.8.send.8 --verdict false-positive --scene ...`
with the finding id copied by eye. Two clicks instead is the single
highest-value thing this window does, because the verdict log is how
his judgement enters the rule set at all.

The wording is deliberate. `advisory/feedback.py` says plainly that
there is no machine learning here: the log exists so that, read across
many shows, a pattern becomes visible -- and a human writes the
resulting principle. So this records a verdict; it does not teach
anything, and the interface must not suggest otherwise.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from wing_parser.advisory import feedback
from wing_parser.advisory.models import Finding

LABELS = {
    "correct": "Correct",
    "false-positive": "False positive",
    "irrelevant": "Irrelevant",
}


class VerdictBar(QWidget):
    recorded = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._finding: Finding | None = None
        self._session = None

        self.tally = QLabel("")
        self.note = QLineEdit()
        self.note.setPlaceholderText("Note (optional)")

        buttons = QHBoxLayout()
        self.buttons: dict[str, QPushButton] = {}
        for verdict in feedback.VERDICTS:
            button = QPushButton(LABELS.get(verdict, verdict))
            button.clicked.connect(
                lambda _checked=False, chosen=verdict: self.record(chosen)
            )
            buttons.addWidget(button)
            self.buttons[verdict] = button
        buttons.addStretch()

        layout = QVBoxLayout(self)
        layout.addWidget(self.tally)
        layout.addLayout(buttons)
        layout.addWidget(self.note)
        self.show_finding(None, None)

    def show_finding(self, finding: Finding | None, session) -> None:
        self._finding, self._session = finding, session
        for button in self.buttons.values():
            button.setEnabled(finding is not None)
        self.tally.setText(self._tally_text(finding))

    def _tally_text(self, finding: Finding | None) -> str:
        """The running count for this rule.

        Shown because it is the evidence that a standing principle
        should be written -- seven rejections of one rule is a signal,
        and it is invisible everywhere else today.
        """
        if finding is None:
            return ""
        counts = feedback.summarise().get(finding.rule_id, {})
        if not counts:
            return f"{finding.rule_id}: no verdict recorded yet"
        parts = ", ".join(f"{number} {verdict}" for verdict, number in sorted(counts.items()))
        return f"{finding.rule_id}: {parts}"

    def record(self, verdict: str) -> None:
        if self._finding is None:
            return
        feedback.record(
            self._finding,
            verdict,
            self.note.text(),
            scene=str(self._session.path) if self._session else "",
        )
        self.note.clear()
        self.tally.setText(self._tally_text(self._finding))
        self.recorded.emit()
