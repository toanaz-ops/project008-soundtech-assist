"""Field-by-field comparison of two scenes.

Walks the frozen records recursively rather than the raw JSON, so paths
read in decoded terms ("ch.8.fader_dB", "ch.8.eq.bands.2.gain") and
levels compare as dB with the sentinel already resolved.

One documented limitation. A record present in one scene and absent from
the other is reported as a single change whose `before` or `after` is the
whole record object, not as per-field changes. Adding or removing a
channel is one logical edit, and both consoles this parser targets carry
a fixed 40, so the case does not arise in practice — but a caller that
assumes every `Change` holds primitive leaves must handle it.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, fields, is_dataclass
from typing import TYPE_CHECKING, Any

from wing_parser.core.normalizer import SENTINEL_MINUS_INF
from wing_parser.query.build_blocks import MATRIX_PREFIX

if TYPE_CHECKING:
    from wing_parser.query.scene import WingScene

# Raw payloads are excluded: eq.raw duplicates the decoded bands, so
# including it would report every EQ change twice.
SKIP_FIELDS = {"raw"}


@dataclass(frozen=True)
class Change:
    path: str
    before: Any
    after: Any
    magnitude: float | None


def _magnitude(before: Any, after: Any) -> float | None:
    """How far a numeric field moved.

    A level at -inf is a fader on its bottom stop, which the console
    writes as -144. Measuring the travel from there gives a real number
    for the largest change a mix can have — silent to audible — instead
    of dropping it to None and ranking it below a 1 dB trim.
    """
    if isinstance(before, bool) or isinstance(after, bool):
        return None
    if not isinstance(before, (int, float)) or not isinstance(after, (int, float)):
        return None

    left, right = float(before), float(after)
    if math.isinf(left) and math.isinf(right):
        return None                       # both silent: no travel
    left = float(SENTINEL_MINUS_INF) if math.isinf(left) else left
    right = float(SENTINEL_MINUS_INF) if math.isinf(right) else right
    return abs(right - left)


def _walk(path: str, before: Any, after: Any, out: list[Change]) -> None:
    if is_dataclass(before) and is_dataclass(after):
        for spec in fields(before):
            if spec.name in SKIP_FIELDS:
                continue
            _walk(
                f"{path}.{spec.name}",
                getattr(before, spec.name),
                getattr(after, spec.name),
                out,
            )
        return

    if isinstance(before, tuple) and isinstance(after, tuple):
        keyed_before = {_key(item, i): item for i, item in enumerate(before)}
        keyed_after = {_key(item, i): item for i, item in enumerate(after)}
        for key in sorted(set(keyed_before) | set(keyed_after), key=str):
            _walk(f"{path}.{key}", keyed_before.get(key), keyed_after.get(key), out)
        return

    if before != after:
        out.append(Change(path, before, after, _magnitude(before, after)))


def _key(item: Any, index: int) -> Any:
    """Match tuple entries by identity where they have one.

    A send's number is not unique on its own — bus 3 and MX3 both report
    dest 3 — so a send keys on the destination as the file itself spells
    it: "3" for bus 3, "MX3" for matrix 3. Those two forms cannot collide
    (buses are 1-16, matrices MX1-MX8), the key doubles as the path
    fragment, and a reader sees the same token the console wrote.
    """
    dest = getattr(item, "dest", None)
    if dest is not None:
        kind = getattr(item, "dest_kind", None)
        return f"{MATRIX_PREFIX}{dest}" if kind == "matrix" else str(dest)
    for attribute in ("name", "number"):
        value = getattr(item, attribute, None)
        if value is not None:
            return value
    return index


def compare(a: "WingScene", b: "WingScene") -> tuple[Change, ...]:
    changes: list[Change] = []

    left_channels, right_channels = a.channel_map(), b.channel_map()
    for number in sorted(set(left_channels) | set(right_channels)):
        left = left_channels.get(number)
        right = right_channels.get(number)
        _walk(
            f"ch.{number}",
            left.data if left else None,
            right.data if right else None,
            changes,
        )

    for kind in ("bus", "aux", "main", "matrix"):
        left_section = {v.number: v.data for v in a.family(kind).values()}
        right_section = {v.number: v.data for v in b.family(kind).values()}
        for number in sorted(set(left_section) | set(right_section)):
            _walk(
                f"{kind}.{number}",
                left_section.get(number),
                right_section.get(number),
                changes,
            )

    return tuple(changes)
