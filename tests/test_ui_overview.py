import pytest

pytest.importorskip("PySide6.QtWidgets")


def test_overview_shows_counts_after_open(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser import WingScene
    from wing_parser.ui.overview_page import OverviewPage
    from wing_parser.ui.session import Session

    page = OverviewPage()
    page.set_session(Session.open(vu_path))
    assert page.count_labels["channels"].text().isdigit()
    assert page.channels_model.rowCount() > 0


def test_overview_clears_without_a_session(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.overview_page import OverviewPage

    page = OverviewPage()
    page.set_session(None)
    assert page.channels_model.rowCount() == 0
