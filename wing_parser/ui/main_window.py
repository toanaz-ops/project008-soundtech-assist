"""The window shell: menus, file dialogs, layout and the title.

Behaviour lives in Session. This file turns clicks into Session calls
and Session state into widgets, and holds no rule knowledge of its own.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from wing_parser.ui.changes_panel import ChangesPanel
from wing_parser.ui.detail_panel import DetailPanel
from wing_parser.ui.findings_view import FindingsView
from wing_parser.ui.session import Session
from wing_parser.ui.verdict_bar import VerdictBar

FILTER = "WING scene (*.snap);;All files (*)"


class MainWindow(QMainWindow):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__()
        self.session = session
        self._build_menus()
        self._build_body()
        self._build_changes_dock()
        self.resize(1280, 760)
        self._refresh()

    # -- construction ---------------------------------------------------

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu("&File")
        file_menu.addAction("&Open...", self.open_file)
        self._save_action = file_menu.addAction("Save &As...", self.save_as)
        edit_menu = self.menuBar().addMenu("&Edit")
        self._undo_action = edit_menu.addAction("&Undo", self.undo)

    def _build_body(self) -> None:
        self.findings_view = FindingsView()
        self.detail_panel = DetailPanel()
        self.verdict_bar = VerdictBar()

        self.findings_view.selected.connect(self._show_finding)
        self.detail_panel.repaired.connect(self._refresh)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.addWidget(self.detail_panel, stretch=1)
        right_layout.addWidget(self.verdict_bar)

        body = QSplitter(Qt.Orientation.Horizontal)
        body.addWidget(self.findings_view)
        body.addWidget(right)
        body.setStretchFactor(0, 3)
        body.setStretchFactor(1, 2)
        self.setCentralWidget(body)

    def _build_changes_dock(self) -> None:
        self.changes_panel = ChangesPanel()
        self.changes_panel.undo_requested.connect(self.undo)
        self._changes_dock = QDockWidget("Changes", self)
        self._changes_dock.setWidget(self.changes_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._changes_dock)
        self._changes_dock.setVisible(False)

    # -- actions --------------------------------------------------------

    def open_file(self) -> None:
        name, _ = QFileDialog.getOpenFileName(self, "Open a WING scene", "", FILTER)
        if not name:
            return
        try:
            self.session = Session.open(name)
        except (ValueError, OSError) as exc:
            # Stay on the scene already loaded. A failed Open must never
            # leave the operator with an empty window and a lost session.
            QMessageBox.critical(self, "Cannot open that file", str(exc))
            return
        self._show_finding(None)
        self._refresh()

    def save_as(self) -> None:
        if self.session is None:
            return
        suggested = str(
            self.session.path.with_name(self.session.path.stem + "-edited.snap")
        )
        name, _ = QFileDialog.getSaveFileName(
            self, "Save the edited scene", suggested, FILTER
        )
        if not name:
            return
        try:
            self.session.save_as(name)
        except OSError as exc:
            # The journal is untouched and the window stays dirty.
            QMessageBox.critical(self, "Cannot save", str(exc))
            return
        QMessageBox.information(self, "Saved", f"Wrote {name}")

    def undo(self) -> None:
        if self.session is not None and self.session.undo():
            self._refresh()

    # -- state ----------------------------------------------------------

    def _show_finding(self, finding) -> None:
        self.detail_panel.show_finding(finding, self.session)
        self.verdict_bar.show_finding(finding, self.session)

    def _refresh(self) -> None:
        loaded = self.session is not None
        self._save_action.setEnabled(loaded)
        self._undo_action.setEnabled(loaded and self.session.dirty)

        self.findings_view.set_findings(self.session.findings() if loaded else [])
        self.changes_panel.set_changes(self.session.changes() if loaded else ())
        self._changes_dock.setVisible(loaded and self.session.dirty)

        if not loaded:
            self.setWindowTitle("wing")
            self._show_finding(None)
            return
        mark = " *" if self.session.dirty else ""
        profile = f"  [{self.session.profile}]" if self.session.profile else ""
        self.setWindowTitle(f"wing — {self.session.path.name}{profile}{mark}")
