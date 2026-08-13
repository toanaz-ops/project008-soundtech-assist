"""Turn raw .snap encodings into ordinary Python values.

Two conversions live here and nowhere else:

  * the -144 sentinel, which the console writes for -inf dB
  * string numeric section keys ("1".."40"), which become ints

Doing this at the data layer means no consumer ever has to remember
that -144 is special.
"""

from __future__ import annotations

from typing import Any

NEG_INF: float = float("-inf")
SENTINEL_MINUS_INF: int = -144


def to_db(value: float | int | None) -> float:
    """Convert a raw level field to dB, mapping the sentinel to -inf."""
    if value is None:
        return NEG_INF
    numeric = float(value)
    if numeric <= SENTINEL_MINUS_INF:
        return NEG_INF
    return numeric


def from_db(value: float) -> float:
    """Inverse of to_db, for writing a level back into .snap form."""
    if value == NEG_INF:
        return float(SENTINEL_MINUS_INF)
    return float(value)


def is_silent(db: float) -> bool:
    return db == NEG_INF


def int_keyed(section: dict[str, Any]) -> dict[int, Any]:
    """Convert a string-keyed section to int keys, ascending."""
    converted: dict[int, Any] = {}
    for key, value in section.items():
        try:
            converted[int(key)] = value
        except (TypeError, ValueError) as exc:
            raise ValueError(f"section has a non-numeric key: {key!r}") from exc
    return dict(sorted(converted.items()))
