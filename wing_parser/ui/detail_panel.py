"""Everything known about the selected finding, plus its repair.

The rule's rationale sits on screen rather than behind a tooltip
because it is the argument the operator is being asked to accept or
reject, and the verdict buttons below are meaningless without it.

A rule with no repair descriptor shows no button and says why. Offering
a fix the descriptor table cannot justify is the one failure mode this
whole feature was designed against.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QGroupBox,
    QLabel,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from wing_parser.advisory.models import Finding
from wing_parser.edit import repairs

NO_REPAIR = (
    "No one-click repair for this rule: it states a window or a count, "
    "so no single value follows from it. Adjust it by hand on the console."
)


def _wrapped(text: str = "") -> QLabel:
    label = QLabel(text)
    label.setWordWrap(True)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return label


def _boxed(title: str, label: QLabel) -> QGroupBox:
    box = QGroupBox(title)
    layout = QVBoxLayout(box)
    layout.addWidget(label)
    return box


class DetailPanel(QWidget):
    repaired = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._finding: Finding | None = None
        self._session = None

        self.message_label = _wrapped()
        self.title_label = _wrapped()
        self.rationale_label = _wrapped()
        self.source_label = _wrapped()
        self.evidence_label = _wrapped()
        self.no_repair_label = _wrapped()

        self.repair_button = QPushButton("")
        self.repair_button.clicked.connect(self._repair)

        inner = QWidget()
        layout = QVBoxLayout(inner)
        layout.addWidget(self.title_label)
        layout.addWidget(self.message_label)
        layout.addWidget(self.repair_button)
        layout.addWidget(self.no_repair_label)
        layout.addWidget(_boxed("Why this rule exists", self.rationale_label))
        layout.addWidget(_boxed("Source", self.source_label))
        layout.addWidget(_boxed("Evidence", self.evidence_label))
        layout.addStretch()

        area = QScrollArea()
        area.setWidget(inner)
        area.setWidgetResizable(True)

        outer = QVBoxLayout(self)
        outer.addWidget(area)

        self.show_finding(None, None)

    def show_finding(self, finding: Finding | None, session) -> None:
        self._finding, self._session = finding, session
        if finding is None or session is None:
            self._clear()
            return

        rule = session.rule(finding.rule_id)
        self.title_label.setText(
            f"{finding.rule_id} — {rule.title if rule else ''}"
            f"   [{finding.severity} · {finding.layer}]"
        )
        self.message_label.setText(finding.message)
        self.rationale_label.setText(rule.rationale.strip() if rule else "")
        self.source_label.setText(rule.source.strip() if rule else "")
        self.evidence_label.setText(
            "\n".join(f"{key} = {value!r}" for key, value in sorted(finding.evidence.items()))
            or "none recorded"
        )

        repair = repairs.load_repairs().get(finding.rule_id)
        self.repair_button.setVisible(repair is not None)
        self.repair_button.setEnabled(repair is not None)
        self.repair_button.setText(repair.label if repair else "")
        self.repair_button.setToolTip(repair.rationale.strip() if repair else "")
        self.no_repair_label.setText("" if repair else NO_REPAIR)

    def _clear(self) -> None:
        for label in (
            self.title_label,
            self.message_label,
            self.rationale_label,
            self.source_label,
            self.evidence_label,
            self.no_repair_label,
        ):
            label.setText("")
        self.repair_button.setVisible(False)
        self.repair_button.setEnabled(False)
        self.repair_button.setText("")

    def _repair(self) -> None:
        if self._finding is None or self._session is None:
            return
        if self._session.repair(self._finding):
            self.repaired.emit()
