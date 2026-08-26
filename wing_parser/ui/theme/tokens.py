"""The one colour and measurement table.

Every value here is an int (`0xRRGGBB`), never a `#` string: the
no-hex-literal scan runs with an empty allowlist over the rest of
wing_parser/ui, so even this file cannot cheat -- and a typo'd token
name fails at import time instead of shipping a wrong shade.

The palette is the approved table from spec-ui-mockup.md section 2.
Tokens with no consumer yet (`trace`, `grid`, `peak`, `marker`,
`cooling`, `settled`) stay anyway: the shared table is the point, and
the parity test asserts both apps carry the identical set. `raise_`
carries the trailing underscore because `raise` is a keyword.
"""

from __future__ import annotations

COLOURS: dict[str, int] = {
    "background": 0x0A0B0D,
    "panel": 0x131519,
    "raise_": 0x1B1E24,
    "well": 0x0C0E11,
    "border": 0x2B2F37,
    "shade": 0x060709,
    "text": 0xE8EAED,
    "dim": 0x868D98,
    "faded": 0x5C636E,
    "accent": 0xFF9F1C,
    "warn": 0xFFC24D,
    "ok": 0x6EE7A0,
    "danger": 0xFF5A4E,
    "trace": 0xFFB552,
    "grid": 0x1D2128,
    "peak": 0xDDE6F0,
    "marker": 0xFF9F1C,
    "cooling": 0xC9D1D9,
    "settled": 0x5FC9FF,
}

# The handsfree study's spacing measurements, in px.
METRICS: dict[str, int] = {
    "unit": 4,
    "gap": 8,
    "margin": 12,
    "touch_target": 44,
    "field_height": 26,
    "caption_height": 30,
    "legend_gutter": 74,
    "radius_field": 3,
    "radius_switch": 4,
}

# Type scale, in px font size, and per-face tracking in em/glyph.
# Ordering pinned by the study's test: SWITCH > BRAND > CAPTION >
# COLUMN > HINT, TABLE < BASE.
SWITCH_SIZE = 16.0
BRAND_SIZE = 14.0
CAPTION_SIZE = 11.0
COLUMN_SIZE = 10.5
HINT_SIZE = 10.0
TABLE_SIZE = 12.0
BASE_SIZE = 13.0

TRACK_CAPTION = 0.18
TRACK_COLUMN = 0.12
TRACK_SWITCH = 0.08


def hex_str(name: str) -> str:
    """Format one token as the lowercase `#rrggbb` QSS/QColor wants."""
    return "#%06x" % COLOURS[name]
