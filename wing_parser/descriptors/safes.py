"""Decode the ce_data.safes positional bitmap.

Scene Safe turns out to live inside the file, not only in console state,
which is why scene-safe rules are reachable in Phase 1.
"""

from __future__ import annotations

from typing import Any

from wing_parser.descriptors import registry


def decode(bitmap: str, expected: int | None = None) -> tuple[bool, ...]:
    """One bool per position. Index 0 is position 1."""
    doc = registry.load("safes")
    blank = doc["not_safe_char"]
    text = bitmap or ""
    if expected is not None and len(text) < expected:
        text = text.ljust(expected, blank)
    return tuple(char != blank for char in text)


def decode_scene(ce_safes: dict[str, Any]) -> dict[str, tuple[bool, ...]]:
    """Decode every flat section of ce_data.safes.

    Nested sections (source.A, source.LCL, ...) are skipped; nothing in
    Phase 1 needs per-source safe flags.
    """
    doc = registry.load("safes")
    lengths = doc["expected_lengths"]
    decoded: dict[str, tuple[bool, ...]] = {}
    for section in doc["flat_sections"]:
        value = ce_safes.get(section)
        if isinstance(value, str):
            decoded[section] = decode(value, expected=lengths.get(section))
    return decoded


def is_safe(flags: tuple[bool, ...], number: int) -> bool:
    """1-based lookup. Out of range is False, not an error."""
    if number < 1 or number > len(flags):
        return False
    return flags[number - 1]
