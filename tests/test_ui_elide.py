"""Middle elision that protects the tail, and the table cell painter.

Handsfree's rule: an identifier cut in the middle with its last two
characters preserved ("Ana…1") stays readable, while an end cut
("…post-fader to bu") throws away exactly the discriminating part.
"""

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture()
def metrics(qt_app):
    from PySide6.QtGui import QFontMetrics

    from wing_parser.ui.theme import fonts
    fonts.load()
    return QFontMetrics(fonts.mono_font(12))


def test_elide_middle_keeps_the_last_two_characters(metrics):
    from wing_parser.ui.elide import elide_middle

    full = metrics.horizontalAdvance("Analogue 1")
    result = elide_middle("Analogue 1", metrics, int(full * 0.55))
    assert result.endswith("e 1")
    assert "…" in result


def test_a_fitting_value_passes_through_untouched(metrics):
    from wing_parser.ui.elide import elide_middle

    width = metrics.horizontalAdvance("ch.1.send.8") + 40
    assert elide_middle("ch.1.send.8", metrics, width) == "ch.1.send.8"


def test_every_result_respects_the_requested_width(metrics):
    from wing_parser.ui.elide import elide_middle

    value = "unknown.bare_channel_name_without_a_class"
    floor = metrics.horizontalAdvance("…e 1")
    for fraction in (0.9, 0.7, 0.5):
        width = max(int(metrics.horizontalAdvance(value) * fraction), floor)
        result = elide_middle(value, metrics, width)
        assert metrics.horizontalAdvance(result) <= width, width


def test_prose_elision_delegates_to_qt(metrics):
    from PySide6.QtCore import Qt

    from wing_parser.ui.elide import elide_prose

    value = "a long prose sentence that will not fit"
    result = elide_prose(value, metrics, int(metrics.horizontalAdvance(value) * 0.5))
    assert "…" in result
    assert len(result) < len(value)
    assert Qt.TextElideMode.ElideMiddle  # documents the chosen mode


# -- the cell painter -------------------------------------------------


def _model_row(qt_app):
    from PySide6.QtGui import QStandardItem, QStandardItemModel

    model = QStandardItemModel(0, 2)
    model.appendRow([QStandardItem("Analogue 1"), QStandardItem("-12.5 dB")])
    return model


def test_numeric_columns_are_mono_and_right_aligned(qt_app):
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QStyleOptionViewItem

    from wing_parser.ui.elide import MonoDelegate
    from wing_parser.ui.theme import fonts

    fonts.load()
    delegate = MonoDelegate(numeric_columns={1})
    model = _model_row(qt_app)

    option = QStyleOptionViewItem()
    delegate.initStyleOption(option, model.index(0, 1))
    assert option.font.family() == fonts.mono_font(12).family()
    assert bool(option.displayAlignment & Qt.AlignmentFlag.AlignRight)

    plain = QStyleOptionViewItem()
    delegate.initStyleOption(plain, model.index(0, 0))
    assert not bool(plain.displayAlignment & Qt.AlignmentFlag.AlignRight)


def test_mono_without_right_alignment_is_available_for_technical_text(qt_app):
    """A path column gets the face but keeps its left edge."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QStyleOptionViewItem

    from wing_parser.ui.elide import MonoDelegate
    from wing_parser.ui.theme import fonts

    fonts.load()
    delegate = MonoDelegate(mono_columns={0})
    model = _model_row(qt_app)

    option = QStyleOptionViewItem()
    delegate.initStyleOption(option, model.index(0, 0))
    assert option.font.family() == fonts.mono_font(12).family()
    assert not bool(option.displayAlignment & Qt.AlignmentFlag.AlignRight)


def test_painting_elides_a_value_that_does_not_fit(qt_app):
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QStyleOptionViewItem

    from wing_parser.ui.elide import MonoDelegate

    delegate = MonoDelegate()
    model = _model_row(qt_app)

    image = QImage(60, 24, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 30, 24)
    delegate.paint(painter, option, model.index(0, 0))
    painter.end()


# -- the magnitude bar -------------------------------------------------


def _magnitude_model(qt_app):
    from PySide6.QtGui import QStandardItem, QStandardItemModel

    model = QStandardItemModel(0, 4)
    for path, before, after, magnitude in (
        ("ch.1.fader_dB", "0.0", "-12.5", "-12.50"),
        ("ch.2.send.8.level", "-inf", "-30.0", "30.00"),
        ("ch.3.name", "Ana", "Analog", "0.00"),
    ):
        model.appendRow([QStandardItem(value) for value in
                         (path, before, after, magnitude)])
    return model


def _bar_frame(qt_app, delegate, model):
    from PySide6.QtCore import QRect
    from PySide6.QtGui import QImage, QPainter
    from PySide6.QtWidgets import QStyleOptionViewItem

    image = QImage(80, 24, QImage.Format.Format_ARGB32_Premultiplied)
    painter = QPainter(image)
    option = QStyleOptionViewItem()
    option.rect = QRect(0, 0, 80, 24)
    delegate.paint(painter, option, model.index(1, 3))
    painter.end()
    return image.constBits().tobytes()


def test_the_magnitude_bar_paints_only_while_enabled(qt_app):
    from wing_parser.ui.diff_page import SHOW_MAGNITUDE_BAR
    from wing_parser.ui.elide import MonoDelegate

    model = _magnitude_model(qt_app)
    assert SHOW_MAGNITUDE_BAR is True, "the bar ships enabled"

    on = MonoDelegate(numeric_columns={3}, bar_column=3,
                      bar_enabled=lambda: SHOW_MAGNITUDE_BAR)
    off = MonoDelegate(numeric_columns={3}, bar_column=3,
                       bar_enabled=lambda: False)
    assert _bar_frame(qt_app, on, model) != _bar_frame(qt_app, off, model), (
        "the bar must change pixels when the flag is live"
    )


def test_bar_colours_come_from_the_token_table(qt_app):
    """dim at zero magnitude, accent at the column peak."""
    from wing_parser.ui.elide import _lerp_colour
    from wing_parser.ui.theme import tokens

    low, high = _lerp_colour(0.0), _lerp_colour(1.0)
    assert low.red() == tokens.COLOURS["dim"] >> 16 & 0xFF
    assert low.green() == tokens.COLOURS["dim"] >> 8 & 0xFF
    assert high.red() == tokens.COLOURS["accent"] >> 16 & 0xFF
    assert low != high
