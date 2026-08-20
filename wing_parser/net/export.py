"""Serialise a `RawScene` to `.snap` file text, with WING's own JSON types.

Design doc S5. A `RawScene` built from `net/snapshot.py` (a live console)
holds every leaf as `str`, `int` or `float` -- never `bool` -- because
`codec.leaf_value` never produces one (S2.3: the OSC wire never
distinguishes "the true/false WING wants here" from "a plain integer
WING wants here"; both are the same `,sfi` int). A `RawScene` built from
`core/loader.load_raw` (an existing `.snap` file) already carries the
file's own JSON types, `bool` included, straight out of `json.loads`.
This module has to be correct for both origins, so it applies the same
two rules uniformly rather than special-casing "did this come off the
wire":

1. Any leaf whose shape path is in the boolean oracle
   (`net/jsontypes.py`) is written as `true`/`false`. Applying this to a
   leaf that is already a Python `bool` is a no-op (`bool(True) is
   True`); applying it to the `int` a live snapshot produced is what
   makes console-sourced exports look like WING's own files.
2. Any `float` that is integral is written as a bare int, never with a
   trailing `.0` -- WING's own convention (S5: neither reference file
   contains a single `":N.0"`).

**Known, accepted infidelity:** 18 of the 342 boolean shapes -- the send
`plink` family -- are `int` in `example-Vu.snap` and `bool` in
`factory-scene.snap`; WING itself is not consistent about them (S5). Rule
1 above always resolves them to `bool`, so re-exporting `example-Vu.snap`
changes those 18 shapes' JSON type from `int` to `bool`. This is not a
bug in this module -- there is no rule that could reproduce both
reference files' choice at once -- and `tests/test_net_export.py`
documents it as a named, expected exception rather than a passing
coincidence.
"""

from __future__ import annotations

import json
from typing import Any

from wing_parser.core.loader import RawScene
from wing_parser.net.identity import WingIdentity
from wing_parser.net.jsontypes import is_boolean_shape

# ce_data's own top-level keys are $ctl's children, not $ctl itself
# (net/snapshot.py strips this same segment on the way in -- S2.2), so
# shape lookups for the ce tree must add it back to match the oracle,
# which was generated with ce_data rooted at $ctl (generate_jsontypes.py).
_CE_ROOT = "$ctl"

# S5/S7: no console-authored .snap has ever been observed, so nothing has
# measured what a live rack would write into these fields if it saved a
# file itself. Inventing a plausible-looking value (a fake app name, a
# fake version) would fail the project's own "never fabricate" rule the
# moment someone diffed it against a real WING-Edit export. This literal
# string says exactly that, in the file itself, rather than silently
# looking like real provenance.
_NO_IDENTITY = "<unknown: no WingIdentity supplied>"

# The one piece of "who produced this file" this process can state
# honestly without a console: its own package version. Not a stand-in for
# WING-Edit's creator/creator_vers -- this tool is not WING-Edit, and
# saying so is more honest than borrowing WING-Edit's field values for a
# file WING-Edit did not create.
_CREATOR = "wing-parser"


def to_snap_json(raw: RawScene, identity: WingIdentity | None = None) -> str:
    """Render `raw` as the text of a `.snap` file.

    `type` comes from `raw.version.type_id` -- the schema id the scene
    was already resolved against, either read verbatim from a file
    (`core/loader.load_raw`) or, for a console-sourced scene, the
    unmeasured assumption `net/snapshot.py` documents and carries here
    unchanged (S2.3/S7: no console-authored `.snap` exists to check which
    `type` id a live rack would actually write).

    `identity`, when given, supplies the console's own model and name for
    `creator_model`/`creator_name`; `creator`/`creator_vers` name this
    tool itself, because a `WingIdentity` (S2.1's `WING?` handshake) has
    no field for the *editing software*'s name or version, and guessing
    one would be exactly the fabrication the project forbids. When
    `identity` is None, every creator_* field is the same honest
    placeholder rather than a fabricated console identity.
    """
    envelope: dict[str, Any] = {
        "type": raw.version.type_id,
        "creator": _CREATOR,
        "creator_vers": _package_version(),
        "creator_model": identity.model if identity is not None else _NO_IDENTITY,
        "creator_name": identity.name if identity is not None else _NO_IDENTITY,
    }
    envelope["ae_data"] = _convert(raw.ae, [])
    envelope["ce_data"] = _convert(raw.ce, [_CE_ROOT])
    return json.dumps(envelope, indent=2, ensure_ascii=False)


def _package_version() -> str:
    # Imported lazily so a circular import can never appear just because
    # export.py is imported early in some other module's chain.
    from wing_parser import __version__

    return __version__


def _convert(node: Any, parts: list[str]) -> Any:
    """Recreate `node`'s leaves with WING's own JSON types (module docstring).

    `parts` grows with every dict level so a leaf's shape path -- what
    `is_boolean_shape` actually looks up -- reflects its full position in
    the tree, not just its own key.
    """
    if isinstance(node, dict):
        return {key: _convert(value, parts + [key]) for key, value in node.items()}
    if isinstance(node, bool):
        return node
    if isinstance(node, int):
        return bool(node) if is_boolean_shape(parts) else node
    if isinstance(node, float) and node.is_integer():
        return int(node)
    return node
