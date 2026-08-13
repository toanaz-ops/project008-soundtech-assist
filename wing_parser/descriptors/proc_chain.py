"""Decode the encoded processing-chain string, tap point, and source group."""

from __future__ import annotations

from wing_parser.descriptors import registry


def decode(proc: str) -> tuple[str, ...]:
    """Turn 'GEDI' into ('GATE', 'EQ', 'DELAY', 'INSERT').

    Order is significant: it is the order the blocks run in. An
    unrecognised letter becomes UNKNOWN_<letter> rather than being
    silently dropped, so a new firmware block shows up in output.
    """
    doc = registry.load("proc_chain")
    blocks = doc["blocks"]
    prefix = doc["unknown_prefix"]
    return tuple(
        blocks[letter]["id"] if letter in blocks else f"{prefix}{letter}"
        for letter in (proc or "")
    )


def tap_point(ptap: str | int) -> str:
    """Map ch.ptap to a named tap point. The file stores this as a string."""
    doc = registry.load("tap_points")
    entry = doc["points"].get(str(ptap))
    return entry["id"] if entry else doc["unknown"]


def source_group_label(group: str) -> str:
    entry = registry.load("io")["groups"].get(group)
    return entry["label"] if entry else group
