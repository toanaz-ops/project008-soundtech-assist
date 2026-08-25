"""The window shell: menus, file dialogs, the sidebar and the title.

Behaviour lives in Session. This file turns clicks into Session calls
and Session state into widgets, and holds no rule knowledge of its own.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QStackedWidget,
    QWidget,
)

from wing_parser import config
from wing_parser.ui.changes_panel import ChangesPanel
from wing_parser.ui.channels_page import ChannelsPage
from wing_parser.ui.diff_page import DiffPage
from wing_parser.ui.doctor_page import DoctorPage
from wing_parser.ui.import_page import ImportPage
from wing_parser.ui.overview_page import OverviewPage
from wing_parser.ui.routing_page import RoutingPage
from wing_parser.ui.session import Session
from wing_parser.ui.settings_dialog import SettingsDialog
from wing_parser.ui.texts import text

FILTER = "WING scene (*.snap);;All files (*)"

PAGE_ORDER = ["doctor", "overview", "channels", "routing", "diff", "import_"]

PAGE_ICONS = {
    "doctor": "fa5s.stethoscope",
    "overview": "fa5s.chart-bar",
    "channels": "fa5s.sliders-h",
    "routing": "fa5s.project-diagram",
    "diff": "fa5s.code-branch",
    "import_": "fa5s.file-import",
}


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
        tools_menu = self.menuBar().addMenu("&Tools")
        tools_menu.addAction(text("menu.settings"), self.open_settings)
        help_menu = self.menuBar().addMenu("&Help")
        help_menu.addAction("Where my judgements are stored...", self.show_knowledge_dir)

    def open_settings(self) -> None:
        """Modal: the operator finishes or cancels the key edit in one go."""
        SettingsDialog(self).exec()

    def show_knowledge_dir(self) -> None:
        """Name the directory holding the verdict log and the principles.

        Worth a menu item because in a packaged build it is not where
        anyone would guess: the app runs from one place and keeps his
        work in another, since a frozen bundle is deleted on exit.
        """
        directory = config.knowledge_dir()
        QMessageBox.information(
            self,
            "Knowledge directory",
            f"Verdicts, principles and show profiles live in:\n\n{directory}\n\n"
            f"feedback.jsonl holds every verdict recorded here.\n"
            f"principles.yaml and shows/ are yours to edit.",
        )

    def _build_body(self) -> None:
        self.pages: dict[str, QWidget] = {"doctor": DoctorPage()}
        self.pages["doctor"].repaired.connect(self._refresh)
        self.pages["overview"] = OverviewPage()
        self.pages["channels"] = ChannelsPage()
        self.pages["routing"] = RoutingPage()
        self.pages["diff"] = DiffPage()
        self.pages["import_"] = ImportPage()

        self.stack = QStackedWidget()
        for key in PAGE_ORDER:
            self.stack.addWidget(self.pages[key])

        self.sidebar = QListWidget()
        for key in PAGE_ORDER:
            label = text(f"page.{key.removesuffix('_')}")
            item = QListWidgetItem(qta.icon(PAGE_ICONS[key]), label)
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        body = QHBoxLayout()
        body.addWidget(self.sidebar)
        body.addWidget(self.stack, stretch=1)
        central = QWidget()
        central.setLayout(body)
        self.setCentralWidget(central)

    def switch_to(self, key: str) -> None:
        self.sidebar.setCurrentRow(PAGE_ORDER.index(key))

    def _build_changes_dock(self) -> None:
        self.changes_panel = ChangesPanel()
        self.changes_panel.undo_requested.connect(self.undo)
        self._changes_dock = QDockWidget("Changes", self)
        self._changes_dock.setWidget(self.changes_panel)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._changes_dock)
        self._changes_dock.setVisible(False)

    # -- delegating attributes -------------------------------------------

    @property
    def findings_view(self):
        return self.pages["doctor"].findings_view

    @property
    def detail_panel(self):
        return self.pages["doctor"].detail_panel

    @property
    def verdict_bar(self):
        return self.pages["doctor"].verdict_bar

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
        self.switch_to("doctor")
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
        self.pages["doctor"].show_finding(finding)

    def _refresh(self) -> None:
        loaded = self.session is not None
        self._save_action.setEnabled(loaded)
        self._undo_action.setEnabled(loaded and self.session.dirty)

        for page in self.pages.values():
            if hasattr(page, "set_session"):
                page.set_session(self.session)

        self.changes_panel.set_changes(self.session.changes() if loaded else ())
        self._changes_dock.setVisible(loaded and self.session.dirty)

        if not loaded:
            self.setWindowTitle(text("app.title"))
            return
        mark = " *" if self.session.dirty else ""
        profile = f"  [{self.session.profile}]" if self.session.profile else ""
        self.setWindowTitle(f"wing — {self.session.path.name}{profile}{mark}")
