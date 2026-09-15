"""The window shell: pages, sidebar, dock and title.

Behaviour lives in Session. This file turns clicks into Session calls
and Session state into widgets, and holds no rule knowledge of its
own. The task-C split moved the menus and their actions into
`menus.py`, the persistence wiring into `window_state.py` and the Tab
chain into `focus_chain.py`, keeping every file under the cap.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QScrollArea,
    QStackedWidget,
    QWidget,
)

from wing_parser.ui import live_wiring, menus, state_store, window_state
from wing_parser.ui.changes_panel import ChangesPanel
from wing_parser.ui.channels_page import ChannelsPage
from wing_parser.ui.diff_page import DiffPage
from wing_parser.ui.doctor_page import DoctorPage
from wing_parser.ui.focus_chain import _chain_tab_order, _tab_stops
from wing_parser.ui.import_page import ImportPage
from wing_parser.ui.overview_page import OverviewPage
from wing_parser.ui.page_base import EmptyState
from wing_parser.ui.routing_page import RoutingPage
from wing_parser.ui.session import Session
from wing_parser.ui.theme.widgets import caption_font
from wing_parser.ui.texts import text

PAGE_ORDER = list(state_store.PAGE_KEYS)

PAGE_ICONS = {
    "doctor": "fa5s.stethoscope",
    "overview": "fa5s.chart-bar",
    "channels": "fa5s.sliders-h",
    "routing": "fa5s.project-diagram",
    "diff": "fa5s.code-branch",
    "import_": "fa5s.file-import",
    "console": "fa5s.network-wired",
}


class MainWindow(QMainWindow):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__()
        self.session = session
        self._recent: list[str] = []
        menus.build_menus(self)
        self._build_body()
        self._build_changes_dock()
        menus.build_accelerators(self)
        window_state.restore(self)
        self._refresh()

    # -- construction ---------------------------------------------------

    def _build_body(self) -> None:
        self.pages: dict[str, QWidget] = {"doctor": DoctorPage()}
        self.pages["doctor"].repaired.connect(self._refresh)
        self.pages["overview"] = OverviewPage()
        self.pages["channels"] = ChannelsPage()
        self.pages["routing"] = RoutingPage()
        self.pages["diff"] = DiffPage()
        self.pages["import_"] = ImportPage()
        self.pages["import_"].open_settings_requested.connect(self.open_settings)
        self.pages["console"] = EmptyState(text("page.console"))
        live_wiring.wire_console(self, self.pages["console"])

        self.stack = QStackedWidget()
        for key in PAGE_ORDER:
            self.stack.addWidget(self.pages[key])

        self.sidebar = QListWidget()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setFont(caption_font())
        for key in PAGE_ORDER:
            label = text(f"page.{key.removesuffix('_')}")
            item = QListWidgetItem(qta.icon(PAGE_ICONS[key]), label.upper())
            self.sidebar.addItem(item)
        self.sidebar.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.sidebar.setCurrentRow(0)

        body = QHBoxLayout()
        body.addWidget(self.sidebar)
        body.addWidget(self.stack, stretch=1)
        central = QWidget()
        central.setLayout(body)
        self.setCentralWidget(central)

        for key in PAGE_ORDER:
            _chain_tab_order(self.pages[key])

    def switch_to(self, key: str) -> None:
        try:
            row = PAGE_ORDER.index(key)
        except ValueError:
            raise KeyError(
                f"unknown page {key!r}; valid keys are {PAGE_ORDER}"
            ) from None
        self.sidebar.setCurrentRow(row)

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

    # -- actions: seams here; bodies live beside their menus -------------

    def open_settings(self) -> None:
        menus.open_settings(self)

    def show_knowledge_dir(self) -> None:
        window_state.show_knowledge_dir(self)

    def open_file(self) -> None:
        menus.open_file(self)

    def save_as(self) -> None:
        menus.save_as(self)

    def undo(self) -> None:
        menus.undo(self)

    def reanalyse(self) -> None:
        menus.reanalyse(self)

    # -- state ----------------------------------------------------------

    def _remember_recent(self, path: str) -> None:
        window_state.remember_recent(self, path)

    def _open_recent(self, path: str) -> None:
        window_state.open_recent(self, path)

    def closeEvent(self, event) -> None:
        window_state.save_on_close(self)
        super().closeEvent(event)

    def _show_finding(self, finding) -> None:
        self.pages["doctor"].show_finding(finding)

    def _refresh(self) -> None:
        loaded = self.session is not None
        self._save_action.setEnabled(loaded)
        self._undo_action.setEnabled(loaded and self.session.dirty)
        self._reanalyse_action.setEnabled(loaded)

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
        self.setWindowTitle(text("window.title").format(
            app=text("app.title"), file=self.session.path.name,
            profile=profile, mark=mark,
        ))
