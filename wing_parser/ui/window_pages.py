"""Building the window's pages and sidebar (split out of `main_window.py`).

Wave 5 added an eighth page to a shell that was at 198 of its 200 lines, so
the construction half moved here by responsibility: `MainWindow` keeps
behaviour (switching, the dock, refresh); this module knows which pages
exist, what they are called and how the Console page is wired to the window.
`main_window` re-exports `PAGE_ORDER` and `PAGE_ICONS` -- the tests import
them from there.
"""

from __future__ import annotations

import qtawesome as qta
from PySide6.QtWidgets import QListWidget, QListWidgetItem, QStackedWidget, QWidget

from wing_parser.ui import live_wiring, state_store
from wing_parser.ui.channels_page import ChannelsPage
from wing_parser.ui.console_page import ConsolePage
from wing_parser.ui.diff_page import DiffPage
from wing_parser.ui.doctor_page import DoctorPage
from wing_parser.ui.import_page import ImportPage
from wing_parser.ui.log_page import LogPage
from wing_parser.ui.overview_page import OverviewPage
from wing_parser.ui.routing_page import RoutingPage
from wing_parser.ui.texts import text
from wing_parser.ui.theme.widgets import caption_font

PAGE_ORDER = list(state_store.PAGE_KEYS)

PAGE_ICONS = {
    "doctor": "fa5s.stethoscope",
    "overview": "fa5s.chart-bar",
    "channels": "fa5s.sliders-h",
    "routing": "fa5s.project-diagram",
    "diff": "fa5s.code-branch",
    "import_": "fa5s.file-import",
    "console": "fa5s.network-wired",
    "log": "fa5s.clipboard-list",
}


def build_pages(window) -> dict[str, QWidget]:
    """Every page, wired to the window where it needs to be."""
    pages: dict[str, QWidget] = {"doctor": DoctorPage()}
    pages["doctor"].repaired.connect(window._refresh)
    pages["overview"] = OverviewPage()
    pages["channels"] = ChannelsPage()
    pages["routing"] = RoutingPage()
    pages["diff"] = DiffPage()
    pages["import_"] = ImportPage()
    pages["import_"].open_settings_requested.connect(window.open_settings)
    pages["console"] = ConsolePage()
    live_wiring.wire_console(window, pages["console"])
    pages["console"].session_pulled.connect(
        pages["import_"].scene_step.set_pulled_session)
    pages["log"] = LogPage()
    return pages


def build_stack(pages: dict[str, QWidget]) -> QStackedWidget:
    stack = QStackedWidget()
    for key in PAGE_ORDER:
        stack.addWidget(pages[key])
    return stack


def build_sidebar(stack: QStackedWidget) -> QListWidget:
    sidebar = QListWidget()
    sidebar.setObjectName("sidebar")
    sidebar.setFont(caption_font())
    for key in PAGE_ORDER:
        label = text(f"page.{key.removesuffix('_')}")
        sidebar.addItem(QListWidgetItem(qta.icon(PAGE_ICONS[key]), label.upper()))
    sidebar.currentRowChanged.connect(stack.setCurrentIndex)
    sidebar.setCurrentRow(0)
    return sidebar
