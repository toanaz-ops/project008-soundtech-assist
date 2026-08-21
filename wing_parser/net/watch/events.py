"""One change, and how it reads.

Kept apart from the poller so the loop owns timing and the record owns
presentation, and so a change can be constructed in a test without a
socket anywhere near it.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Change:
    address: str
    strip: str
    key: str
    label: str
    before: object
    after: object
    elapsed: float


def split_address(address: str) -> tuple[str, str]:
    """"/ch/8/$fdr" -> ("/ch/8", "$fdr")."""
    strip, _, key = address.rpartition("/")
    return strip, key


def _shown(change: Change) -> str:
    """A blank name is ordinary -- factory-scene.snap names no channel at
    all -- so fall back to the address rather than leaving a gap."""
    return change.label if change.label else change.strip


def format_change(change: Change) -> str:
    return (
        f"[{change.elapsed:7.2f}s] {_shown(change):<20s} "
        f"{change.key:<8s} {change.before!r} -> {change.after!r}"
    )


def change_as_dict(change: Change) -> dict:
    return {
        "elapsed": round(change.elapsed, 3),
        "address": change.address,
        "strip": change.strip,
        "key": change.key,
        "label": change.label,
        "before": change.before,
        "after": change.after,
    }
