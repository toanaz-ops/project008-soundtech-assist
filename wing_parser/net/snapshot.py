"""Read every leaf the current schema exposes and assemble a RawScene.

Design doc S2.2 (address space maps 1-to-1 onto .snap), S2.3 (the leaf
triplet -> value rule, already implemented by `codec.leaf_value`), S2.5
(the whole-console read budget), S4 (phase 2: VALUES, on top of phase 1's
`net/schema.py` SHAPE).

**Every value here comes from a per-leaf GET**, exactly the request
`net/client.py` exists to pipeline. That is the part that matters: a
node dump's values are lossy display text (S2.3), so none may ever reach
a scene.

`net/schema.py` does fall back to a `,s *` dump for a node whose `,s ?`
reply overflows -- a loaded effect slot, in practice -- but it takes only
the key NAMES from it. Those names then come back here and are read
individually like every other leaf, so the lossy values are never used.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from wing_parser.core.loader import RawScene
from wing_parser.core.versions import load_registry, resolve
from wing_parser.net.client import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_IDLE_TIMEOUT,
    DEFAULT_RETRY_ROUNDS,
    OSC_PORT,
    WingClient,
)
from wing_parser.net.codec import leaf_value
from wing_parser.net.schema import walk_schema

# S2.11/S4: no console-authored .snap exists to confirm which `type` id a
# live rack would write -- that field is stamped by WING-Edit when IT
# saves a file, and this subsystem has never observed a save that
# originated from the console itself. example-Vu.snap is the file that
# was actually pushed to and read back from the lab console throughout
# this design's own measurements (S2.3, S2.6, S7's round-trip plan), and
# it carries "snapshot.11" -- the registry's newest known schema.
# factory-scene.snap, the other reference file, carries "snapshot.10"
# instead, so the two references do not even agree with each other; there
# is genuinely no measured answer here.
#
# ASSUMPTION, not a measurement: use "snapshot.11". To settle it for real,
# save a scene from WING-Edit while it is connected to this exact console
# and firmware, then read the `type` field WING-Edit itself writes.
ASSUMED_TYPE_ID = "snapshot.11"

_CE_ROOT_SEGMENT = "$ctl"


@dataclass(frozen=True)
class SnapshotResult:
    """A snapshot attempt and everything that did not make it in.

    Kept alongside `RawScene` rather than folded into it, because
    `RawScene` (shared with the file-loading path) has no field for "this
    much of the console didn't answer", and inventing one there would
    ripple a live-only concern into `core/loader.load_raw` too.
    """

    raw: RawScene
    unresolved_nodes: tuple[str, ...]
    unresolved_leaves: tuple[str, ...]


def take_snapshot(
    host: str,
    port: int = OSC_PORT,
    batch_size: int = DEFAULT_BATCH_SIZE,
    retry_rounds: int = DEFAULT_RETRY_ROUNDS,
    idle_timeout: float = DEFAULT_IDLE_TIMEOUT,
) -> SnapshotResult:
    """Walk the current shape, read every leaf, and assemble a RawScene.

    Fresh shape every call (S2.10): a cached inventory would silently miss
    whatever parameters the loaded desk currently exposes. Unresolved
    nodes and leaves are reported, never dropped -- a caller that wants a
    complete scene must be able to tell "empty" apart from "incomplete".
    """
    schema = walk_schema(
        host, port, batch_size=batch_size, retry_rounds=retry_rounds, idle_timeout=idle_timeout
    )

    with WingClient(host, port, idle_timeout=idle_timeout) as client:
        batch = client.get_many(list(schema.leaves), batch_size=batch_size, retry_rounds=retry_rounds)

    ae: dict[str, Any] = {}
    ce: dict[str, Any] = {}
    for address, message in batch.replies.items():
        value, _display = leaf_value(message)
        _place(ae, ce, address, value)

    raw = RawScene(
        version=resolve(ASSUMED_TYPE_ID, load_registry()),
        ae=ae,
        ce=ce,
        # Nothing downstream reads RawScene.meta -- WingScene.__init__
        # never touches it (design doc S4) -- so there is nothing to gain
        # and only fabrication to risk by inventing creator_* fields the
        # console never actually stated (the same lesson S2.3 draws about
        # leaf values applies here too).
        meta={},
        path=None,
        source=f"wing://{host}",
    )
    return SnapshotResult(
        raw=raw,
        unresolved_nodes=schema.unresolved_nodes,
        unresolved_leaves=batch.unresolved,
    )


def _place(ae: dict[str, Any], ce: dict[str, Any], address: str, value: Any) -> None:
    """File one leaf's value into the ae/ce nesting S2.2 defines.

    `/$ctl/...` is ce_data, keyed from *below* $ctl -- S2.2: ce_data's own
    top-level keys are $ctl's children (cfg, layer, user, ...), not $ctl
    itself. Everything else is ae_data, keyed exactly as the OSC address
    reads, which is already the .snap layout (S2.2's whole point).
    """
    segments = address.lstrip("/").split("/")
    if segments[0] == _CE_ROOT_SEGMENT:
        tree, segments = ce, segments[1:]
    else:
        tree = ae

    for segment in segments[:-1]:
        tree = tree.setdefault(segment, {})
    tree[segments[-1]] = value
