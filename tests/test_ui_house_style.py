import pytest

pytest.importorskip("PySide6.QtWidgets")

# The token module lands in the NEXT task; until it does these are the
# measured literals this task asserts against. Task 17 swaps them for
# tokens.CAPTION_SIZE / tokens.TRACK_CAPTION.
CAPTION_SIZE = 11.0
TRACK_CAPTION = 0.20


def test_every_face_is_vendored_rather_than_resolved_from_the_machine(qt_app):
    """A missing font does not fail at runtime -- it silently falls back.
    This is the only way to tell a vendored face from a substitution."""
    from wing_parser.ui.theme import fonts
    fonts.load()
    assert fonts.failed() == (), f"fell back to system faces: {fonts.failed()}"


def test_the_licences_ship_beside_the_faces():
    from wing_parser.ui.theme.paths import resource_path
    folder = resource_path("fonts")
    assert {p.name for p in folder.glob("*.ttf")} == {
        "SairaCondensed-SemiBold.ttf", "SairaCondensed-Bold.ttf",
        "IBMPlexSans-Regular.ttf",
        "IBMPlexMono-Regular.ttf", "IBMPlexMono-Medium.ttf",
    }
    assert len(list(folder.glob("OFL-*.txt"))) == 3


def test_bold_is_a_real_face_not_a_synthesised_one(qt_app):
    from PySide6.QtGui import QFontInfo
    from wing_parser.ui.theme import fonts
    bold = fonts.legend_font(14.0, bold=True)
    assert QFontInfo(bold).weight() == bold.weight()


def test_tracking_adds_the_studys_em_per_glyph(qt_app):
    from PySide6.QtGui import QFontMetricsF
    from wing_parser.ui.theme import fonts
    sample = "ACTIVE NOTCHES"
    plain = fonts.legend_font(CAPTION_SIZE, tracking=0.0)
    tracked = fonts.legend_font(CAPTION_SIZE, tracking=TRACK_CAPTION)
    delta = (QFontMetricsF(tracked).horizontalAdvance(sample)
             - QFontMetricsF(plain).horizontalAdvance(sample))
    expected = TRACK_CAPTION * int(CAPTION_SIZE + 0.5) * len(sample)
    assert abs(delta - expected) < 0.6
