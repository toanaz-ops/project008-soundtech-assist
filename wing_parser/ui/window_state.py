"""Persistence wiring for the window shell: geometry, page, recents.

Task-C split: thin functions over `state_store` + MainWindow. The
window keeps delegating methods as the seams (`_remember_recent`,
`_open_recent`, `closeEvent`); behaviour is byte-preserved.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QByteArray
from PySide6.QtWidgets import QMessageBox

from wing_parser import config
from wing_parser.ui import state_store
from wing_parser.ui.session import Session
from wing_parser.ui.texts import text


def restore(window) -> None:
    """Geometry, last page and recents, read before first paint."""
    state = state_store.load(config.knowledge_dir())
    window._recent = state["recent"]
    rebuild_recent_menu(window)
    restore_consoles(window, state["consoles"])
    window._apply_delay = state["apply_delay"]
    if state["geometry"]:
        window.restoreGeometry(
            QByteArray.fromHex(state["geometry"].encode("ascii"))
        )
    else:
        window.resize(1280, 760)
    if state["page"]:
        window.switch_to(state["page"])


def restore_consoles(window, consoles) -> None:
    """Offer the remembered console addresses, before first paint.

    Read and written beside `recent` because it is the same kind of
    fact -- where he was last working -- and kept out of the Console
    page itself because a widget that reads the state file is a widget
    that cannot be built in a test without one. The `hasattr` mirrors
    `live_wiring.wire_console`: until a page offers the seam, this is a
    no-op rather than a crash.
    """
    window._consoles = list(consoles)
    page = window.pages["console"]
    if hasattr(page, "set_consoles"):
        page.set_consoles(window._consoles)


def remember_console(window, host: str) -> None:
    """Move `host` to the top; `save_on_close` is what writes it down.

    `state_store.remember_console` compares plain strings rather than
    paths (`state_store.py:76-83`): an address is not a filename.
    """
    window._consoles = state_store.remember_console(window._consoles, host)


def remember_recent(window, path: str) -> None:
    window._recent = state_store.remember_recent(window._recent, path)
    rebuild_recent_menu(window)


def rebuild_recent_menu(window) -> None:
    window._recent_menu.clear()
    for entry in window._recent:
        window._recent_menu.addAction(
            Path(entry).name,
            lambda checked=False, path=entry: window._open_recent(path),
        )


def open_recent(window, path: str) -> None:
    try:
        window.session = Session.open(path)
    except (ValueError, OSError):
        # Chosen degradation (ruled task 1b-21): tell the operator,
        # then drop the dead entry so the menu self-heals.
        QMessageBox.information(
            window,
            text("recent.missing.title"),
            text("recent.missing.body").format(file=path),
        )
        window._recent = state_store.forget_recent(window._recent, path)
        rebuild_recent_menu(window)
        return
    remember_recent(window, str(window.session.path))
    adopt_session(window)


def adopt_session(window) -> None:
    """Everything a freshly opened scene needs, wherever it came from."""
    window.switch_to("doctor")
    window._show_finding(None)
    window._refresh()


def show_knowledge_dir(window) -> None:
    """Name the directory holding the verdict log and the principles.

    Worth a menu item because in a packaged build it is not where
    anyone would guess: the app runs from one place and keeps his
    work in another, since a frozen bundle is deleted on exit.
    """
    directory = config.knowledge_dir()
    QMessageBox.information(
        window,
        text("knowledge.title"),
        text("knowledge.body").format(directory=directory),
    )


def save_on_close(window) -> None:
    row = window.sidebar.currentRow()
    state_store.save(
        config.knowledge_dir(),
        {
            "geometry": bytes(window.saveGeometry().toHex()).decode("ascii"),
            "page": state_store.PAGE_KEYS[row]
            if 0 <= row < len(state_store.PAGE_KEYS)
            else None,
            "recent": window._recent,
            "consoles": window._consoles,
            "apply_delay": getattr(window, "_apply_delay",
                                   state_store.DEFAULTS["apply_delay"]),
        },
    )
