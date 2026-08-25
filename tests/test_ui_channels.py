import pytest

pytest.importorskip("PySide6.QtWidgets")


def test_selecting_a_row_fills_the_detail_pane(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.channels_page import ChannelsPage
    from wing_parser.ui.session import Session

    page = ChannelsPage()
    page.set_session(Session.open(vu_path))
    page.table.selectRow(0)
    number = page.rows[0].number
    assert f"{number}" in page.detail_title.text()


def test_empty_until_a_session_arrives(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.channels_page import ChannelsPage

    page = ChannelsPage()
    page.set_session(None)
    assert page.table.model().rowCount() == 0
    assert page.detail_title.text() == ""
