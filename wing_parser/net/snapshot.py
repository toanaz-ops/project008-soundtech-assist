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

# A console never authors a .snap at all -- WING-Edit does, and the `type`
# id tracks WING-Edit's own version, not the desk's firmware. Measured
# across seven files: WING Edit 3.0 writes snapshot.9, 3.2.1 writes
# snapshot.10, 3.3.3 writes snapshot.11, and the three envelopes genuinely
# differ (3.0 keeps WING-Edit's layer layout beside ae_data as
# `wedit_layer`; 3.2 adds ae_globals/ce_globals and renames every creator
# field).
#
# So the question is not "what would the rack write" but "which schema does
# THIS exporter emit", and that has a checked answer: net/export.py writes
# creator/creator_vers/creator_model/creator_name with no globals, and the
# scene carries the wlive+wmadi cards -- which is snapshot.11 exactly, as
# `tests/test_net_export.py` pins.
SNAPSHOT_TYPE_ID = "snapshot.11"

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
        version=resolve(SNAPSHOT_TYPE_ID, load_registry()),
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
