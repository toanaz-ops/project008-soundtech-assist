"""Substitute the token table into the QSS template.

`string.Template.substitute`, never `safe_substitute`: a `$typo` must
raise at startup rather than ship a literal `$typo` into a rule Qt
then discards with no diagnostic.
"""

from __future__ import annotations

import string

from wing_parser.ui.theme import tokens
from wing_parser.ui.theme.paths import resource_path


def mapping() -> dict[str, str]:
    m = {name: tokens.hex_str(name) for name in tokens.COLOURS}
    for key, value in tokens.METRICS.items():
        if key.endswith(("_field", "_switch")) and key.startswith("radius"):
            m[f"METRICS_{key}"] = str(value)
    return m


def build() -> str:
    template = resource_path("theme.qss").read_text(encoding="utf-8")
    return string.Template(template).substitute(mapping())
