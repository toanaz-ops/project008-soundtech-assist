"""The doctor page: findings on the left, detail and verdict on the right.

This is the window's original body, extracted verbatim when the main
window became a sidebar shell. The rules for what a finding means live
elsewhere; this page only shows them and passes clicks back out.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSplitter, QVBoxLayout, QWidget

from wing_parser.ui.detail_panel import DetailPanel
from wing_parser.ui.findings_view import FindingsView
from wing_parser.ui.session import Session
from wing_parser.ui.verdict_bar import VerdictBar


class DoctorPage(QWidget):
    selected = Signal(object)
    repaired = Signal()

    def __init__(self) -> None:
        super().__init__()
        self._session: Session | None = None

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

    def set_session(self, session: Session | None) -> None:
        self._session = session
        loaded = session is not None
        self.findings_view.set_findings(session.findings() if loaded else [])
        if not loaded:
            self.show_finding(None)

    def _on_view_selected(self, finding) -> None:
        """The user-driven path: announce, then show."""
        self.selected.emit(finding)
        self.show_finding(finding)

    def show_finding(self, finding) -> None:
        """The programmatic path: update the panes without announcing."""
        self.detail_panel.show_finding(finding, self._session)
        self.verdict_bar.show_finding(finding, self._session)
