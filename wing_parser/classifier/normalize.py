"""Normalize a channel or bus name before matching.

Real scene files carry trailing spaces ("Kick In "), inconsistent case,
and tabs. Matching against the raw string would miss all of them.
"""

from __future__ import annotations

import re

_WHITESPACE = re.compile(r"\s+")


def clean(name: str) -> str:
    return _WHITESPACE.sub(" ", (name or "").strip()).casefold()
