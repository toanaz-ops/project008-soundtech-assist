"""The window shell: menus, file dialogs, the sidebar and the title.

Behaviour lives in Session. This file turns clicks into Session calls
and Session state into widgets, and holds no rule knowledge of its own.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QComboBox,
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QScrollArea,
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
from wing_parser.ui.theme.widgets import caption_font
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


def _tab_stops(parent: QWidget) -> list[QWidget]:
    """The widgets of one page a Tab press can actually land on.

    Scroll-area internals (viewport, bars) and combo-popup machinery
    take focus but only ever forward it, so they are not stops; the
    scroll *container* itself is skipped the same way. QTableView stays:
    it is a real stop that merely happens to own scrollbars.
    """
    stops: list[QWidget] = []
    for child in parent.findChildren(QWidget):
        policy = child.focusPolicy()
        if not policy & Qt.FocusPolicy.TabFocus and not policy & Qt.FocusPolicy.StrongFocus:
            continue
        ancestor = child.parentWidget()
        while ancestor is not None and ancestor is not parent:
            if isinstance(ancestor, QComboBox):
                break  # popup list of a combo: focus lands via the combo
            ancestor = ancestor.parentWidget()
        else:
            name = child.objectName()
            forwards = name.startswith("qt_scrollarea") or isinstance(child, QScrollArea)
            if not forwards:
                # Views route focus through their viewport (focusProxy),
                # so the chain speaks in proxies — normalise to it.
                effective = child.focusProxy() or child
                if effective not in stops:
                    stops.append(effective)
    return stops


def _chain_tab_order(parent: QWidget) -> None:
    """Link the page's own focus stops into one explicit Tab chain.

    Without this Qt invents a chain across the whole window in creation
    order, and Tab wanders out of the visible page. The Task 18 focus
    ring makes the resulting order visible.
    """
    for current, following in zip(_tab_stops(parent), _tab_stops(parent)[1:]):
        QWidget.setTabOrder(current, following)


class MainWindow(QMainWindow):
    def __init__(self, session: Session | None = None) -> None:
        super().__init__()
        self.session = session
        self._build_menus()
        self._build_body()
        self._build_changes_dock()
        self._build_accelerators()
        self.resize(1280, 760)
        self._refresh()

    # -- construction ---------------------------------------------------

    def _build_menus(self) -> None:
        file_menu = self.menuBar().addMenu(text("menu.file"))
        self._open_action = file_menu.addAction("&Open...", self.open_file)
        self._save_action = file_menu.addAction("Save &As...", self.save_as)
        edit_menu = self.menuBar().addMenu(text("menu.edit"))
        self._undo_action = edit_menu.addAction("&Undo", self.undo)
        tools_menu = self.menuBar().addMenu(text("menu.tools"))
        tools_menu.addAction(text("menu.settings"), self.open_settings)
        self._reanalyse_action = tools_menu.addAction(
            text("menu.reanalyse"), self.reanalyse
        )
        help_menu = self.menuBar().addMenu(text("menu.help"))
        help_menu.addAction("Where my judgements are stored...", self.show_knowledge_dir)

    def _build_accelerators(self) -> None:
        """The ruled map: Ctrl+O / Ctrl+Shift+S / Ctrl+Z / Ctrl+1..6 / F5.

        Menu labels stay clean — the shortcut is bound with setShortcut,
        never appended to the text. Page keys are QShortcuts so they do
        not become menu rows; emitting their activated signal is how the
        tests prove each one lands on its page.
        """
        self._open_action.setShortcut(QKeySequence("Ctrl+O"))
        # Save As semantics per the 2026-08-26 ruling: plain Ctrl+S stays free.
        self._save_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        self._undo_action.setShortcut(QKeySequence("Ctrl+Z"))
        self._reanalyse_action.setShortcut(QKeySequence("F5"))
        for index, key in enumerate(PAGE_ORDER, start=1):
            shortcut = QShortcut(QKeySequence(f"Ctrl+{index}"), self)
            shortcut.activated.connect(
                lambda checked=False, page=key: self.switch_to(page)
            )

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
            text("knowledge.title"),
            text("knowledge.body").format(directory=directory),
        )

    def _build_body(self) -> None:
        self.pages: dict[str, QWidget] = {"doctor": DoctorPage()}
        self.pages["doctor"].repaired.connect(self._refresh)
        self.pages["overview"] = OverviewPage()
        self.pages["channels"] = ChannelsPage()
        self.pages["routing"] = RoutingPage()
        self.pages["diff"] = DiffPage()
        self.pages["import_"] = ImportPage()
        self.pages["import_"].open_settings_requested.connect(self.open_settings)

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
            QMessageBox.critical(self, text("error.open"), str(exc))
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
            QMessageBox.critical(self, text("error.save"), str(exc))
            return
        QMessageBox.information(self, text("save.done"), f"Wrote {name}")

    def undo(self) -> None:
        if self.session is not None and self.session.undo():
            self._refresh()

    def reanalyse(self) -> None:
        """F5: re-run the whole derive pipeline on the current session.

        The findings list is always re-computed truth (see session.py),
        so a fresh derivation is all "re-analyse" has to mean.
        """
        if self.session is not None:
            self.session.reanalyse()
            self._refresh()

    # -- state ----------------------------------------------------------

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
        self.setWindowTitle(f"wing — {self.session.path.name}{profile}{mark}")
