import pytest

pytest.importorskip("PySide6.QtWidgets")


def test_summary_pairs_land_in_the_table(qt_app, vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.routing_page import RoutingPage
    from wing_parser.ui.session import Session

    page = RoutingPage()
    page.set_session(Session.open(vu_path))
    assert page.summary_model.rowCount() >= 1
    labels = [page.summary_model.item(row, 0).text()
              for row in range(page.summary_model.rowCount())]
    assert "Live channels" in labels


def test_unclassified_list_clears(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from wing_parser.ui.routing_page import RoutingPage

    page = RoutingPage()
    page.set_session(None)
    assert page.unclassified_list.count() == 0
