"""The sidebar shell routes sessions to every page."""

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def window(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.main_window import MainWindow

    return MainWindow(None)


def test_sidebar_lists_six_pages_in_order(window):
    from wing_parser.ui.main_window import PAGE_ORDER

    assert PAGE_ORDER == ["doctor", "overview", "channels", "routing",
                          "diff", "import_"]


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
