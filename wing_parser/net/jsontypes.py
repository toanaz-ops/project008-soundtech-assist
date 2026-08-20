"""Answer one question: is a leaf's `.snap` representation a JSON boolean?

Design doc S5 explains why the oracle this module reads is only one
question wide: the OSC reply tag already settles everything else --
`,s` is always a string, `,sff` is always a number (see the bare-int
rule in `net/export.py`), and only `,sfi` is ambiguous, because it
covers both plain integers and WING's own booleans. `,sfi`'s *value*
never carries that distinction (both read back as a Python `int`, see
`net/codec.py:leaf_value`), so the only way to tell them apart is to
have already seen which *shape paths* the two reference `.snap` files
wrote as `true`/`false`. That lookup table is
`examples/generate_jsontypes.py`'s output, `net/data/wing_jsontypes.yaml`
-- generated once, offline, never recomputed here.

A "shape path" collapses numeric path segments to `*`, because the
oracle is keyed by node kind, not by channel number: `ch/7/eq/on` and
`ch/31/eq/on` are the same shape, `ch/*/eq/on`, and share one entry.
"""

from __future__ import annotations

from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path

import yaml

_DATA_PATH = Path(__file__).resolve().parent / "data" / "wing_jsontypes.yaml"


def _shape_path(parts: Sequence[str]) -> str:
    return "/".join("*" if p.isdigit() else p for p in parts)


@lru_cache(maxsize=1)
def _boolean_shapes() -> frozenset[str]:
    """Load the oracle once and cache it for the process lifetime.

    `export.py` calls `is_boolean_shape` once per leaf, and a scene has
    tens of thousands of them -- re-reading and re-parsing the YAML file
    on every call would turn a cheap lookup into the dominant cost of a
    snapshot export.
    """
    doc = yaml.safe_load(_DATA_PATH.read_text(encoding="utf-8")) or {}
    return frozenset(doc.get("booleans") or ())


def is_boolean_shape(parts: Sequence[str]) -> bool:
    """True if the leaf at `parts` (e.g. `["ch", "7", "eq", "on"]`) should
    be written to `.snap` as a JSON boolean rather than a JSON int.

    `parts` is the leaf's path as tree keys, ae- or ce-rooted exactly as
    `RawScene.ae`/`RawScene.ce` nest it (so a ce leaf's caller must
    prepend the `$ctl` segment `net/snapshot.py` strips on the way in --
    see `export.py`, which does this once for the whole ce tree). Numeric
    segments are collapsed to `*` before the lookup, so the same shape
    answers for every channel/bus/aux instance.
    """
    return _shape_path(parts) in _boolean_shapes()
