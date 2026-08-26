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


def test_count_values_are_labels_with_a_legend_not_inputs(qt_app, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    from PySide6.QtWidgets import QLabel

    from wing_parser.ui.overview_page import COUNT_KEYS, OverviewPage
    from wing_parser.ui.theme import fonts
    from wing_parser.ui.theme.widgets import Caption

    page = OverviewPage()
    mono_family = fonts.mono_font(12, medium=True).family()
    for key in COUNT_KEYS:
        value = page.count_labels[key]
        assert type(value) is QLabel
        assert value.font().family() == mono_family, key
        legend = page.count_legends[key]
        assert isinstance(legend, Caption), key
        assert legend.text()
