"""The ruled keyboard map: every accelerator resolves to its action.

ToanAZ ruled on 2026-08-26: Ctrl+O opens, Ctrl+Shift+S is Save As
(never plain Ctrl+S), Ctrl+Z undoes, Ctrl+1..Ctrl+6 switch the six
pages in PAGE_ORDER order, Esc closes a dialog and F5 re-analyses.
GUI wave 2 (2026-09-16) added a seventh page, Console, reachable the
same way as Ctrl+7 -- `menus.build_accelerators` binds Ctrl+{index}
over the whole of PAGE_ORDER, so the rule needed no new code; this
module keeps its own six-page PAGE_KEYS below and does not re-test
the seventh -- see tests/test_ui_shell.py for Ctrl+7.
"""

import pytest

pytest.importorskip("PySide6.QtWidgets")

PAGE_KEYS = ["doctor", "overview", "channels", "routing", "diff", "import_"]


@pytest.fixture
def window(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.main_window import MainWindow

    return MainWindow(None)


def _bound_actions(window):
    """Map every keyboard sequence this window binds to its action."""
    from PySide6.QtGui import QAction

    return {
        action.shortcut().toString(): action
        for action in window.findChildren(QAction)
        if not action.shortcut().isEmpty()
    }


def _bound_shortcuts(window):
    from PySide6.QtGui import QShortcut

    return {
        shortcut.key().toString(): shortcut
        for shortcut in window.findChildren(QShortcut)
    }


def _load_session(window, vu_path, monkeypatch):
    from wing_parser.ui.doctor_page import DoctorPage
    from wing_parser.ui.session import Session

    monkeypatch.setattr(
        DoctorPage, "set_session", lambda self, session: None
    )
    window.session = Session.open(vu_path)
    window._refresh()


def test_open_save_as_and_undo_carry_the_ruled_shortcuts(window):
    bound = _bound_actions(window)
    assert "Ctrl+O" in bound
    assert "Ctrl+Shift+S" in bound
    assert "Ctrl+Z" in bound


def test_plain_ctrl_s_is_not_bound_to_anything(window):
    """Save As semantics were ruled explicitly: Ctrl+S must stay free."""
    bound = _bound_actions(window)
    assert "" not in bound
    assert "Ctrl+S" not in bound


def test_ctrl_o_runs_open_file(window, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    calls = []
    monkeypatch.setattr(
        QFileDialog, "getOpenFileName",
        staticmethod(lambda *a, **k: calls.append(a) or ("", "")),
    )
    _bound_actions(window)["Ctrl+O"].trigger()
    assert len(calls) == 1


def test_ctrl_shift_s_runs_save_as(window, vu_path, monkeypatch):
    from PySide6.QtWidgets import QFileDialog

    _load_session(window, vu_path, monkeypatch)
    calls = []
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName",
        staticmethod(lambda *a, **k: calls.append(a) or ("", "")),
    )
    _bound_actions(window)["Ctrl+Shift+S"].trigger()
    assert len(calls) == 1


@pytest.mark.parametrize(
    "index,key", [(1, "doctor"), (2, "overview"), (3, "channels"),
                  (4, "routing"), (5, "diff"), (6, "import_")]
)
def test_ctrl_number_switches_pages_in_page_order(window, index, key):
    shortcut = _bound_shortcuts(window)[f"Ctrl+{index}"]
    shortcut.activated.emit()
    assert window.stack.currentWidget() is window.pages[key]


def test_f5_rederives_the_current_session(window, vu_path, monkeypatch):
    _load_session(window, vu_path, monkeypatch)
    from wing_parser.ui.session import Session

    calls = []
    monkeypatch.setattr(Session, "reanalyse", lambda self: calls.append(self))
    _bound_actions(window)["F5"].trigger()
    assert calls == [window.session]


def test_f5_without_a_session_does_nothing_and_sits_disabled(window):
    action = _bound_actions(window)["F5"]
    assert not action.isEnabled()
    action.trigger()
    assert window.session is None


def test_escape_closes_the_settings_dialog(qt_app):
    """Characterisation: QDialog's built-in Escape handling is the
    documented Esc-closes-a-dialog behaviour the ruling asked for."""
    from PySide6.QtCore import Qt
    from PySide6.QtTest import QTest

    from wing_parser.ui.settings_dialog import SettingsDialog

    dialog = SettingsDialog(probe=lambda cfg: (True, "ok"))
    dialog.show()
    QTest.keyClick(dialog, Qt.Key_Escape)
    assert not dialog.isVisible()


@pytest.mark.parametrize("key", PAGE_KEYS)
def test_tab_order_stays_inside_each_page(window, key):
    """Tab meets the stops in _tab_stops order, and between the first
    and last of them it never wanders out of the visible page."""
    from wing_parser.ui.main_window import _tab_stops

    page = window.pages[key]
    stops = _tab_stops(page)
    if len(stops) < 2:
        pytest.skip(f"{key} exposes fewer than two focus stops")
    walk = []
    current = stops[0]
    for _ in range(500):
        walk.append(current)
        current = current.nextInFocusChain()
        if current is None:
            break
    position = {id(node): index for index, node in enumerate(walk)}
    missing = [s for s in stops if id(s) not in position]
    assert not missing, f"{key}: {len(missing)} stops unreachable by Tab"
    order = [position[id(s)] for s in stops]
    assert order == sorted(order), f"{key}: Tab visits stops out of order"
    segment = walk[order[0]:order[-1] + 1]
    strays = [n for n in segment if n is not page and not page.isAncestorOf(n)]
    assert not strays, (
        f"{key}: Tab leaves the page mid-sequence "
        f"({strays[0].metaObject().className()} intrudes)"
    )
