"""Regression pins for the theme/elide debt closed on fix/ui-theme-debt
(D-32, D-33, D-34, D-35)."""

from __future__ import annotations

import logging
import sys


def test_a_missing_face_never_resolves_to_the_system_family(qt_app):
    """D-32: a face that did not load must not masquerade as a house font."""
    from PySide6.QtGui import QFont

    from wing_parser.ui.theme import fonts

    fonts.load()
    missing = fonts._family_for("NoSuchFace-Regular.ttf")
    assert missing == fonts.MISSING_FAMILY
    assert missing != QFont().family()
    assert fonts.failed() == ()


def test_apply_uses_the_cached_stylesheet(qt_app, monkeypatch):
    """D-33: the applied sheet and the cached copy share one path."""
    from wing_parser.ui import theme
    from wing_parser.ui.theme import install

    calls = []
    monkeypatch.setattr(theme, "load_stylesheet",
                        lambda: calls.append(1) or "")
    monkeypatch.setattr(qt_app, "_wing_theme_applied", False, raising=False)
    install.apply(qt_app)
    assert calls == [1]


def test_missing_qtawesome_is_logged_once(qt_app, monkeypatch, caplog):
    """D-33: a missing icon dependency leaves a trace, exactly one."""
    from wing_parser.ui.theme import install

    monkeypatch.setitem(sys.modules, "qtawesome", None)
    monkeypatch.setattr(install, "_icons_warned", False)
    with caplog.at_level(logging.WARNING, logger=install.__name__):
        for _ in range(2):
            monkeypatch.setattr(qt_app, "_wing_theme_applied", False,
                                raising=False)
            install.apply(qt_app)
    records = [r for r in caplog.records if "qtawesome" in r.getMessage()]
    assert len(records) == 1


def _two_row_model(first, second):
    from PySide6.QtGui import QStandardItem, QStandardItemModel

    model = QStandardItemModel(0, 1)
    for value in (first, second):
        model.appendRow([QStandardItem(value)])
    return model


def test_bar_peak_follows_data_changes_at_the_same_row_count(qt_app):
    """D-34: same rows, new values -> the bar scales against the new peak."""
    from wing_parser.ui.elide import MonoDelegate

    model = _two_row_model("10", "5")
    delegate = MonoDelegate(bar_column=0)
    assert delegate._bar_fraction(model.index(1, 0)) == 0.5
    model.item(0, 0).setText("100")
    assert delegate._bar_fraction(model.index(1, 0)) == 0.05


def test_bar_peak_follows_a_model_reset(qt_app):
    """D-34: clear + refill to the same row count rescales."""
    from wing_parser.ui.elide import MonoDelegate

    model = _two_row_model("10", "5")
    delegate = MonoDelegate(bar_column=0)
    delegate._bar_fraction(model.index(1, 0))
    model.clear()
    for value in ("40", "20"):
        from PySide6.QtGui import QStandardItem

        model.appendRow([QStandardItem(value)])
    assert delegate._bar_fraction(model.index(1, 0)) == 0.5


def test_screenshot_restores_the_bar_flag_after_a_failure(qt_app, monkeypatch,
                                                          tmp_path):
    """D-35: a raise while the flag is off must not leave it off."""
    import pytest

    from wing_parser.ui import __main__ as entry, diff_page
    from wing_parser.ui.main_window import MainWindow

    real_render = MainWindow.render

    def render(self, target, *args, **kwargs):
        if diff_page.SHOW_MAGNITUDE_BAR is False:
            raise RuntimeError("boom")
        return real_render(self, target, *args, **kwargs)

    monkeypatch.setattr(MainWindow, "render", render)
    monkeypatch.setattr(diff_page, "SHOW_MAGNITUDE_BAR", True)
    with pytest.raises(RuntimeError, match="boom"):
        entry.main(["--screenshot", str(tmp_path)])
    assert diff_page.SHOW_MAGNITUDE_BAR is True
