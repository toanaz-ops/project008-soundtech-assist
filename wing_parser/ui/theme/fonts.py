"""Register the vendored house faces with Qt.

Two measured traps shape this module:

- Both Saira weights live under ONE family ("Saira Condensed"), same
  for IBM Plex Mono. Weight cannot be chosen by family name -- load
  every file, read each family back from applicationFontFamilies(), and
  request Bold/DemiBold on that family. Asking for Bold on a family
  that lacks the face makes Qt synthesise a fake bold, silently.
- Letter spacing must be AbsoluteSpacing, sized in em of the requested
  pixel size (`tracking * size`). PercentageSpacing scales each glyph's
  own advance, which on a condensed face moves the figure with the font.

A missing file does NOT raise: addApplicationFont() simply fails, so
every miss is recorded in failed() and surfaced by test.
"""

from __future__ import annotations

from PySide6.QtGui import QFont, QFontDatabase

from wing_parser.ui.theme.paths import resource_path

_FACES = (
    "SairaCondensed-SemiBold.ttf",
    "SairaCondensed-Bold.ttf",
    "IBMPlexSans-Regular.ttf",
    "IBMPlexMono-Regular.ttf",
    "IBMPlexMono-Medium.ttf",
)

_families: dict[str, str] = {}
_missed: list[str] = []


def load() -> None:
    """Idempotent: register all five files; record which fell back."""
    if _families or _missed:
        return
    for name in _FACES:
        font_id = QFontDatabase.addApplicationFont(str(resource_path("fonts") / name))
        if font_id < 0:
            _missed.append(name)
            continue
        for family in QFontDatabase.applicationFontFamilies(font_id):
            _families.setdefault(family, name)


def failed() -> tuple[str, ...]:
    return tuple(_missed)


def _family_for(face: str) -> str:
    """Never hardcode a family string; read it back from what loaded."""
    for family, name in _families.items():
        if name == face:
            return family
    return QFont().family()


def legend_font(size: float, bold: bool = True,
                tracking: float = 0.0) -> QFont:
    """Saira Condensed, SemiBold or Bold, tracked in em per glyph."""
    font = QFont(_family_for(
        "SairaCondensed-Bold.ttf" if bold else "SairaCondensed-SemiBold.ttf"))
    weight = QFont.Weight.Bold if bold else QFont.Weight.DemiBold
    return _sized(font, weight, size, tracking)


def mono_font(size: float, medium: bool = False) -> QFont:
    """IBM Plex Mono, Regular or Medium."""
    font = QFont(_family_for(
        "IBMPlexMono-Medium.ttf" if medium else "IBMPlexMono-Regular.ttf"))
    weight = QFont.Weight.Medium if medium else QFont.Weight.Normal
    return _sized(font, weight, size)


def base_font(size: float) -> QFont:
    """IBM Plex Sans Regular -- the body face."""
    return _sized(QFont(_family_for("IBMPlexSans-Regular.ttf")),
                  QFont.Weight.Normal, size)


def _sized(font: QFont, weight: QFont.Weight, size: float,
           tracking: float = 0.0) -> QFont:
    font.setWeight(weight)
    pixels = int(size + 0.5)
    font.setPixelSize(pixels)
    # AbsoluteSpacing, not Percentage: `tracking * size` is exactly one
    # em per glyph, what JUCE's withExtraKerningFactor and CSS em mean.
    font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, tracking * size)
    return font
