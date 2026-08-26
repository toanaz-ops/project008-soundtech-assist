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
        m[f"METRICS_{key}"] = str(value)
    return m


def build() -> str:
    # Two templates, concatenated before substitution: one file per
    # concern, both under the house line budget. `substitute` (not
    # `safe_substitute`) still guards every placeholder across both.
    template = "\n".join(
        resource_path(name).read_text(encoding="utf-8")
        for name in ("theme.qss", "chrome.qss")
    )
    return string.Template(template).substitute(mapping())
