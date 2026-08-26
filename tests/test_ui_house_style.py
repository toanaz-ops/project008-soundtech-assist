import re
from pathlib import Path

import pytest

import wing_parser.ui as ui_package
from wing_parser.ui.theme.tokens import CAPTION_SIZE, TRACK_CAPTION

pytest.importorskip("PySide6.QtWidgets")

UI_ROOT = Path(ui_package.__file__).resolve().parent
THEME_DIR = UI_ROOT / "theme"

# EMPTY BY DESIGN. tokens.py holds ints and theme.qss holds $placeholders,
# so even the theme package would pass this scan. If this ever needs an
# entry, the port has gone wrong -- fix the source, do not widen the rule.
ALLOWED: set[Path] = set()

LITERALS = (
    re.compile(r"#[0-9A-Fa-f]{3}\b|#[0-9A-Fa-f]{6}\b"),
    re.compile(r"\brgba?\s*\(\s*\d"),
    re.compile(r"\bQColor\s*\(\s*[\d\"']"),      # QColor(255,159,28) has no '#'
    re.compile(r"\bQt\.GlobalColor\."),
)


def _sources():
    for path in sorted(UI_ROOT.rglob("*")):
        if not path.is_file() or path.suffix not in (".py", ".qss"):
            continue
        if "__pycache__" in path.parts:
            continue
        if THEME_DIR in path.parents or path in ALLOWED:
            continue
        yield path


def test_no_colour_literals_outside_the_theme_package():
    offenders = []
    for path in _sources():
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            for pattern in LITERALS:
                hit = pattern.search(line)
                if hit:
                    offenders.append(f"{path.relative_to(UI_ROOT)}:{number}: {hit.group(0)}")
    assert offenders == [], "colour literals outside theme/:\n  " + "\n  ".join(offenders)


def test_the_scan_actually_reaches_the_pages():
    """A scan that walks nothing passes forever."""
    names = {p.name for p in _sources()}
    assert {"main_window.py", "overview_page.py", "settings_dialog.py"} <= names
    assert len(names) >= 20


EXPECTED = {
    "background": 0x0A0B0D, "panel": 0x131519, "raise_": 0x1B1E24,
    "well": 0x0C0E11, "border": 0x2B2F37, "shade": 0x060709,
    "text": 0xE8EAED, "dim": 0x868D98, "faded": 0x5C636E,
    "accent": 0xFF9F1C, "warn": 0xFFC24D, "ok": 0x6EE7A0,
    "danger": 0xFF5A4E, "trace": 0xFFB552, "grid": 0x1D2128,
    "peak": 0xDDE6F0, "marker": 0xFF9F1C, "cooling": 0xC9D1D9,
    "settled": 0x5FC9FF,
}


def test_palette_matches_the_approved_table():
    """A change here means ToanAZ re-approved the palette. Not a broken test."""
    from wing_parser.ui.theme import tokens
    assert tokens.COLOURS == EXPECTED


def test_the_stylesheet_is_fully_substituted_and_declares_no_type():
    from wing_parser.ui.theme import load_stylesheet
    qss = load_stylesheet()
    assert "$" not in qss, "an unsubstituted $token reached the stylesheet"
    assert "var(--" not in qss, "Qt QSS has no CSS custom properties -- tech-debt D-20"
    assert "#0a0b0d" in qss
    for banned in ("font-family", "font-size", "font-weight", "font:"):
        assert banned not in qss, (
            f"{banned} in theme.qss: a QSS font rule can override the QFont that "
            "carries the tracking, and Qt QSS has no letter-spacing to replace it."
        )


def test_the_type_scale_keeps_the_studys_ordering():
    """Pin the ratios, not the pixels -- a size tweak stays a tweak."""
    from wing_parser.ui.theme import tokens as t
    assert t.SWITCH_SIZE > t.BRAND_SIZE > t.CAPTION_SIZE > t.COLUMN_SIZE > t.HINT_SIZE
    assert t.TABLE_SIZE < t.BASE_SIZE
    assert t.TRACK_CAPTION > t.TRACK_COLUMN > t.TRACK_SWITCH


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
