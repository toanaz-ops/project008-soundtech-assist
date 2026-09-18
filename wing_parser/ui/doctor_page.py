"""The doctor page: findings on the left, detail and verdict on the right.

This is the window's original body, extracted verbatim when the main
window became a sidebar shell. The rules for what a finding means live
elsewhere; this page only shows them and passes clicks back out.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QComboBox, QHBoxLayout, QLabel, QPushButton, QSplitter, QVBoxLayout, QWidget,
)

from wing_parser.ui.apply_level import ApplyLevel
from wing_parser.ui.detail_panel import DetailPanel
from wing_parser.ui.findings_view import FindingsView
from wing_parser.ui.session import Session
from wing_parser.ui.texts import text
from wing_parser.ui.verdict_bar import VerdictBar
from wing_parser.ui.write_arm_dialog import arm_now


class _LevelBox(QComboBox):
    """A `QComboBox` whose `currentData`/`itemData` hand back the real
    `ApplyLevel` member, not PySide6's demoted `str`.

    `ApplyLevel(str, Enum)` round-trips through Qt's item-data QVariant
    marshalling as a plain `str` -- confirmed against this project's
    PySide6 (6.11.2): a value stored via `addItem`/`setItemData` comes
    back `type(...) is str`, so `is ApplyLevel.MANUAL` fails even though
    `== ApplyLevel.MANUAL` still holds. `ApplyLevel(value)` re-interns to
    the canonical singleton (`Enum` caches by value), so wrapping the two
    accessors here is enough -- every caller downstream keeps comparing
    with `is`, exactly as the rest of this codebase already does.
    """

    def currentData(self, role=Qt.ItemDataRole.UserRole):
        value = super().currentData(role)
        return ApplyLevel(value) if isinstance(value, str) else value

    def itemData(self, index, role=Qt.ItemDataRole.UserRole):
        value = super().itemData(index, role)
        return ApplyLevel(value) if isinstance(value, str) else value


class DoctorPage(QWidget):
    selected = Signal(object)
    repaired = Signal()
    send_requested = Signal(object)

    def __init__(self) -> None:
        super().__init__()
        self._session: Session | None = None
        self._gate = None

        self.findings_view = FindingsView()
        self.detail_panel = DetailPanel()
        self.verdict_bar = VerdictBar()

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.detail_panel, stretch=1)
        right_layout.addWidget(self.verdict_bar)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(self.findings_view)
        body.addWidget(right)
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 2)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(body)

        self.findings_view.selected.connect(self._on_view_selected)
        self.detail_panel.repaired.connect(self.repaired)

        self.level_box = _LevelBox()
        for level, key in ((ApplyLevel.MANUAL, "manual"),
                           (ApplyLevel.DELAYED, "delayed"),
                           (ApplyLevel.IMMEDIATE, "immediate")):
            self.level_box.addItem(text(f"console.write.{key}"), level)
        self.arm_button = QPushButton(text("console.write.arm"))
        bar = QHBoxLayout()
        bar.addWidget(QLabel(text("console.write.level")))
        bar.addWidget(self.level_box)
        bar.addWidget(self.arm_button)
        bar.addStretch(1)
        right_layout.insertLayout(0, bar)
        self.detail_panel.send_requested.connect(self.send_requested)

    def set_session(self, session: Session | None) -> None:
        self._session = session
        loaded = session is not None
        findings = session.findings() if loaded else []
        self.findings_view.set_findings(findings)
        if findings:
            # A doctor with a patient shows it: row 0 lights up and the
            # detail pane fills, so the page never reads as broken.
            self.findings_view.select_first()
            self.show_finding(self.findings_view.visible_findings()[0])
        else:
            self.show_finding(None)

    def _on_view_selected(self, finding) -> None:
        """The user-driven path: announce, then show."""
        self.selected.emit(finding)
        self.show_finding(finding)

    def show_finding(self, finding) -> None:
        """The programmatic path: update the panes without announcing."""
        self.detail_panel.show_finding(finding, self._session)
        self.verdict_bar.show_finding(finding, self._session)

    def attach_gate(self, gate) -> None:
        """Bind the selector and Arm to the gate `live_wiring` published.

        The Doctor page NEVER imports `console_page` (§8.1): everything it
        knows about the live connection arrives through this one object.
        """
        self._gate = gate
        gate.changed.connect(self._follow_gate)
        self.level_box.currentIndexChanged.connect(self._level_picked)
        self.arm_button.clicked.connect(
            lambda: arm_now(gate, self.window(), transport=gate.transport))
        self._follow_gate()

    def _follow_gate(self) -> None:
        armed = self._gate.arm.armed()
        model = self.level_box.model()
        for index in range(self.level_box.count()):
            allowed = armed or self.level_box.itemData(index) is ApplyLevel.MANUAL
            model.item(index).setEnabled(allowed)
        if not armed:
            self.level_box.setCurrentIndex(
                self.level_box.findData(ApplyLevel.MANUAL))
        self.arm_button.setText(
            text("console.write.armed").format(name=self._gate.arm.identity.name)
            if armed else text("console.write.arm"))

    def _level_picked(self) -> None:
        self._gate.arm.level = self.level_box.currentData()

    def set_controls_enabled(self, enabled: bool) -> None:
        """W14: dead while a Revert-all run is going, alive again on Stop."""
        self.level_box.setEnabled(enabled)
        self.arm_button.setEnabled(enabled)
