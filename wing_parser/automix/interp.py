"""Strength interpolation and the one place a Change is built.

Every stage goes through `Ctx.change`, so reading `before`, moving it
`strength` of the way toward the target, clamping to the safety bounds,
rounding to the leaf's resolution and dropping no-ops happen the same
way for every leaf. A missing leaf becomes a Skipped row, never a Change
(the pointer cannot create keys).
"""

from __future__ import annotations

import math
from typing import Any

from wing_parser.automix.bounds import Bounds
from wing_parser.automix.options import Change, Skipped
from wing_parser.edit import pointer

PREFIX = "ae_data."
MISSING = object()
_RANK = {"high": 0, "medium": 1, "low": 2, "eng_default": 3}


def is_number(value: Any) -> bool:
    """A real number: a bool is never one (True would otherwise pass as 1)."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def is_on(value: Any) -> bool:
    """True for a switched-on leaf in either encoding: bool in a file document,
    1 in a console-pulled one (net/export.py leaves are str/int/float, AM-38)."""
    return value is True or (is_number(value) and value == 1)


def weakest(*confidences: str) -> str:
    """The least trustworthy confidence tag among the inputs."""
    known = [c for c in confidences if c in _RANK]
    return max(known, key=_RANK.__getitem__) if known else "eng_default"


def mid(rng) -> float:
    """Midpoint of a [lo, hi] range, or the number itself."""
    return (rng[0] + rng[1]) / 2 if isinstance(rng, (list, tuple)) else float(rng)


def geo_mid(rng) -> float:
    """Geometric centre of a frequency range, or the number itself."""
    return math.sqrt(rng[0] * rng[1]) if isinstance(rng, (list, tuple)) else float(rng)


def lerp(before: float, target: float, strength: float) -> float:
    return before + strength * (target - before)


def geolerp(before: float, target: float, strength: float) -> float:
    if before <= 0 or target <= 0:
        return lerp(before, target, strength)
    return before * (target / before) ** strength


def nearest(values, x: float) -> float:
    """Closest list member; ties go to the lower one."""
    return min(sorted(values), key=lambda v: abs(v - x))


class Ctx:
    def __init__(self, document: dict, strength: float, bounds: Bounds) -> None:
        self.document, self.strength, self.bounds = document, strength, bounds
        self.skipped: list[Skipped] = []

    def read(self, path: str) -> Any:
        try:
            return pointer.read(self.document, PREFIX + path)
        except KeyError:
            return MISSING

    def skip(self, target: str, reason: str) -> None:
        item = Skipped(target, reason)
        if item not in self.skipped:
            self.skipped.append(item)

    def change(self, path: str, target: Any, *, stage: str, who: str, label: str, why: str,
               src: tuple, conf: str, mode: str = "lin", digits: int = 1,
               window: tuple | None = None, lead: bool = False,
               optional: bool = False, strength: float | None = None) -> Change | None:
        """mode: lin (dB, ms, Q), geo (Hz), switch (bool, enum, ratio list)."""
        if self.bounds.forbidden(path):
            raise ValueError(f"automix may not touch {path}")
        before, strength = self.read(path), self.strength if strength is None else strength
        if before is MISSING:
            if not optional:
                self.skip(who, f"leaf {path} is missing from the scene")
            return None
        numeric = isinstance(target, (int, float)) and not isinstance(target, bool) \
            and isinstance(before, (int, float)) and not isinstance(before, bool)
        if not numeric or mode == "switch":
            after = target if strength >= 0.5 else before
        elif mode == "geo":
            after = geolerp(before, target, strength)
        else:
            after = lerp(before, target, strength)
        if numeric:
            after = self.bounds.clamp(path, after, lead=lead)
            if window is not None:
                after = min(max(after, window[0]), window[1])
            after = round(after, digits) if digits else int(round(after))
            if after == round(before, digits):
                return None
        if isinstance(target, bool) and is_number(before):
            after = int(target)  # an int-encoded bool leaf keeps the document's own type (AM-38)
        if after == before:
            return None
        return Change(PREFIX + path, before, after, stage, who, label, why, tuple(src), conf)
