"""The menu bar, the ruled accelerators, and the actions they fire.

Task-C split: everything that exists to serve a menu lives beside the
menus -- construction, the shortcut map, and the File/Edit/Tools slots.
MainWindow keeps thin delegating methods as the public seams; behaviour
is byte-preserved. `adopt_session` lives in window_state because both
open paths (menu and recent list) share it.
"""

from __future__ import annotations

from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import QFileDialog, QMessageBox

from wing_parser.ui.session import Session
from wing_parser.ui.settings_dialog import SettingsDialog
from wing_parser.ui.state_store import PAGE_KEYS
from wing_parser.ui.texts import text
from wing_parser.ui.window_state import adopt_session

FILTER = "WING scene (*.snap);;All files (*)"


def build_menus(window) -> None:
    file_menu = window.menuBar().addMenu(text("menu.file"))
    window._open_action = file_menu.addAction("&Open...", window.open_file)
    window._save_action = file_menu.addAction("Save &As...", window.save_as)
    window._recent_menu = file_menu.addMenu(text("menu.recent"))
    edit_menu = window.menuBar().addMenu(text("menu.edit"))
    window._undo_action = edit_menu.addAction("&Undo", window.undo)
    tools_menu = window.menuBar().addMenu(text("menu.tools"))
    tools_menu.addAction(text("menu.settings"), window.open_settings)
    window._reanalyse_action = tools_menu.addAction(
        text("menu.reanalyse"), window.reanalyse
    )
    help_menu = window.menuBar().addMenu(text("menu.help"))
    help_menu.addAction(
        "Where my judgements are stored...", window.show_knowledge_dir
    )


def build_accelerators(window) -> None:
    """The ruled map: Ctrl+O / Ctrl+Shift+S / Ctrl+Z / Ctrl+1..6 / F5.

    Menu labels stay clean — the shortcut is bound with setShortcut,
    never appended to the text. Page keys are QShortcuts so they do
    not become menu rows; emitting their activated signal is how the
    tests prove each one lands on its page.
    """
    window._open_action.setShortcut(QKeySequence("Ctrl+O"))
    # Save As semantics per the 2026-08-26 ruling: plain Ctrl+S stays free.
    window._save_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
    window._undo_action.setShortcut(QKeySequence("Ctrl+Z"))
    window._reanalyse_action.setShortcut(QKeySequence("F5"))
    for index, key in enumerate(PAGE_KEYS, start=1):
        shortcut = QShortcut(QKeySequence(f"Ctrl+{index}"), window)
        shortcut.activated.connect(
            lambda checked=False, page=key: window.switch_to(page)
        )


def open_settings(window) -> None:
    """Modal: the operator finishes or cancels the key edit in one go."""
    SettingsDialog(window).exec()


def open_file(window) -> None:
    name, _ = QFileDialog.getOpenFileName(
        window, "Open a WING scene", "", FILTER
    )
    if not name:
        return
    try:
        window.session = Session.open(name)
    except (ValueError, OSError) as exc:
        # Stay on the scene already loaded. A failed Open must never
        # leave the operator with an empty window and a lost session.
        QMessageBox.critical(window, text("error.open"), str(exc))
        return
    window._remember_recent(str(window.session.path))
    adopt_session(window)


def save_as(window) -> None:
    if window.session is None:
        return
    suggested = str(
        window.session.path.with_name(window.session.path.stem + "-edited.snap")
    )
    name, _ = QFileDialog.getSaveFileName(
        window, "Save the edited scene", suggested, FILTER
    )
    if not name:
        return
    try:
        window.session.save_as(name)
    except OSError as exc:
        # The journal is untouched and the window stays dirty.
        QMessageBox.critical(window, text("error.save"), str(exc))
        return
    QMessageBox.information(window, text("save.done"), f"Wrote {name}")


def undo(window) -> None:
    if window.session is not None and window.session.undo():
        window._refresh()


def reanalyse(window) -> None:
    """F5: re-run the whole derive pipeline on the current session.

    The findings list is always re-computed truth (see session.py),
    so a fresh derivation is all "re-analyse" has to mean.
    """
    if window.session is not None:
        window.session.reanalyse()
        window._refresh()
