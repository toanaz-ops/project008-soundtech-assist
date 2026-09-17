"""The sidebar shell routes sessions to every page."""

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def window(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.main_window import MainWindow

    return MainWindow(None)


def test_sidebar_lists_seven_pages_in_order(window):
    from wing_parser.ui.main_window import PAGE_ORDER

    assert PAGE_ORDER == ["doctor", "overview", "channels", "routing",
                          "diff", "import_", "console"]


def test_ctrl_7_switches_to_the_console_page(window):
    from PySide6.QtGui import QShortcut

    shortcut = next(
        s for s in window.findChildren(QShortcut)
        if s.key().toString() == "Ctrl+7"
    )
    shortcut.activated.emit()
    assert window.stack.currentWidget() is window.pages["console"]


def test_switching_changes_the_visible_page(window):
    window.switch_to("overview")
    assert window.stack.currentWidget() is window.pages["overview"]


def test_switching_to_an_unknown_key_raises_keyerror_naming_the_valid_ones(
        window):
    from wing_parser.ui.main_window import PAGE_ORDER

    with pytest.raises(KeyError) as excinfo:
        window.switch_to("no-such-page")
    for key in PAGE_ORDER:
        assert key in str(excinfo.value)


def test_open_session_fans_out_to_every_page(window, vu_path, monkeypatch):
    from wing_parser.ui.doctor_page import DoctorPage
    from wing_parser.ui.session import Session

    received = []
    monkeypatch.setattr(
        DoctorPage, "set_session", lambda self, session: received.append(session)
    )
    session = Session.open(vu_path)
    window.session = session
    window._refresh()
    assert received == [session]


def test_doctor_widgets_still_reachable(window):
    assert window.findings_view is window.pages["doctor"].findings_view


def test_the_apply_delay_survives_closing_the_window(qt_app, tmp_path, monkeypatch):
    from wing_parser import config
    from wing_parser.ui import state_store
    from wing_parser.ui.main_window import MainWindow

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.setenv("WING_DISABLE_LLM", "1")

    window = MainWindow(None)
    window._apply_delay = 17
    window.close()

    assert state_store.load(tmp_path)["apply_delay"] == 17, (
        "save_on_close rebuilds the saved dict from an explicit literal -- "
        "a key missing there is erased on every quit"
    )
