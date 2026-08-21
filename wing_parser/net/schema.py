"""Breadth-first ``,s ?`` walk of the WING address tree -- shape discovery only.

Design doc S2.3 (the ``,s ?`` reply format), S2.4 (why pipelining schema
queries is safe), S2.5 (0.95s BFS-pipelined vs 55s one request at a time),
S2.10 (the tree is dynamic -- walk fresh every snapshot, never cache).

Transport is ``WingClient``, including its rotate-on-shortfall recovery.
An earlier version of this module ran its own socket loop, on the reasoning
that S2.4 makes a schema reply too small to be the oversized kind that
poisons a source port. Measured against the console, that reasoning was
wrong in effect: the walk stopped resolving at ``/fx/1`` and lost every
reply after it -- 901 of 5330 nodes and 23895 of 25060 leaves, identically
at every timeout from 0.2s to 1.0s and at 2 or 4 retry rounds. Whatever
poisons the port, rotating away from it is the only measured recovery
(S2.4), and WingClient already does that.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from wing_parser.net.client import (
    DEFAULT_BATCH_SIZE,
    DEFAULT_IDLE_TIMEOUT,
    DEFAULT_RETRY_ROUNDS,
    OSC_PORT,
    WingClient,
)
from wing_parser.net.codec import OscMessage
from wing_parser.net.nodetext import NodeTextError, parse_node_text

_SCHEMA_TYPETAG = "s"
_SCHEMA_ARG = "?"
_DUMP_ARG = "*"
_NODE_MARKER = "(node)"
# One line of a ,s ? reply body: leading whitespace, a name with no
# whitespace in it, then whatever is left -- S2.3's own examples are
# "(node)" or a type description like "int [1 .. 18]".
_LINE_RE = re.compile(r"^\s*(\S+)\s+(.*)$")

# S2.2's address map, exactly: the twelve ae_data roots, plus the one
# ce_data root. Root "/" is never queried directly -- its own children
# include several other "$..." names ($stat, $syscfg, $globals, rec) that
# are out of scope anyway, so seeding the known roots is simpler than
# walking "/" and filtering after the fact. $ctl needs this seeding
# regardless: it is the one "$" name in the whole tree that must be
# descended into rather than skipped (S2.2), so it can never be reached by
# the ordinary $-skip rule applied to every other node's children.
AE_ROOTS = ("cfg", "io", "ch", "aux", "bus", "main", "mtx", "dca", "mgrp", "fx", "cards", "play")
CE_ROOT = "$ctl"


@dataclass(frozen=True)
class SchemaResult:
    """A completed (or best-effort) walk.

    `unresolved_nodes` is kept distinct from `leaves` for the same reason
    `client.BatchResult` keeps `unresolved` separate from `replies`: a node
    that never answered must stay visible to the caller, never silently
    indistinguishable from a node that simply has no children.
    """

    leaves: dict[str, str]
    unresolved_nodes: tuple[str, ...]


def walk_schema(
    host: str,
    port: int = OSC_PORT,
    batch_size: int = DEFAULT_BATCH_SIZE,
    retry_rounds: int = DEFAULT_RETRY_ROUNDS,
    idle_timeout: float = DEFAULT_IDLE_TIMEOUT,
    client: WingClient | None = None,
) -> SchemaResult:
    """Discover every leaf address currently on the console, breadth-first.

    Each level of the tree is one pipelined batch (S2.5: fire the whole
    level, then collect) -- never one request per address, which measured
    58x slower for the identical result. Fresh every call: S2.10 shows the
    tree's shape depends on live parameter values (e.g. a dyn model key),
    so a cached inventory would silently miss what a loaded desk exposes.

    `client` lets a caller share one connection across the schema walk and
    the value reads that follow, and lets a test drive the whole walk
    against the loopback fake.
    """
    owned = client is None
    connection = (
        client if client is not None else WingClient(host, port, idle_timeout=idle_timeout)
    )
    try:
        frontier = [f"/{name}" for name in AE_ROOTS] + [f"/{CE_ROOT}"]
        leaves: dict[str, str] = {}
        unresolved: list[str] = []

        while frontier:
            result = connection.get_many(
                frontier,
                batch_size=batch_size,
                retry_rounds=retry_rounds,
                typetag=_SCHEMA_TYPETAG,
                args=(_SCHEMA_ARG,),
            )
            unresolved.extend(result.unresolved)
            frontier = _expand(result.replies, leaves)

        still_missing = _recover_by_dump(connection, unresolved, leaves)
        return SchemaResult(leaves=leaves, unresolved_nodes=tuple(still_missing))
    finally:
        if owned:
            connection.close()


def _expand(replies: dict[str, OscMessage], leaves: dict[str, str]) -> list[str]:
    """Parse one level's replies, filing leaves into `leaves` and
    returning the next level's node addresses to query."""
    next_frontier: list[str] = []
    for address, message in replies.items():
        (text,) = message.args  # a ,s ? reply is always one string blob (S2.3)
        for name, is_node, type_text in _parse_lines(text):
            if name.startswith("$"):
                continue  # S2.2: read-only, absent from .snap
            child_address = f"{address}/{name}"
            if is_node:
                next_frontier.append(child_address)
            else:
                leaves[child_address] = type_text
    return next_frontier


def _parse_lines(text: str) -> list[tuple[str, bool, str]]:
    result: list[tuple[str, bool, str]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        match = _LINE_RE.match(line)
        if not match:  # no recorded reply has ever failed this; defensive only
            continue
        name, rest = match.group(1), match.group(2).strip()
        result.append((name, rest == _NODE_MARKER, rest))
    return result


def _recover_by_dump(
    connection: WingClient, nodes: list[str], leaves: dict[str, str]
) -> list[str]:
    """Last resort for a node whose ``,s ?`` reply overflows the console's
    ~2 kB ceiling: read its ``,s *`` dump instead and take the key names.

    A dump is far shorter than a schema for the same node because it
    carries values rather than value ranges -- measured on a loaded VSS3
    reverb, ``/fx/1``: schema oversized and unanswerable, dump 338
    characters listing all 34 parameters. Effect slots are where this
    bites, since S2.10's dynamic tree gives a loaded effect a much larger
    parameter list than the empty slot the console ships with.

    Only the key NAMES are taken. The values in a dump are lossy display
    text (S2.3) and are never used -- every value still comes from a
    per-leaf read. The declared type is recorded empty because a dump does
    not carry one; nothing needs it, as `codec.leaf_value` keys off the
    reply's own tag rather than the schema.

    Each node is asked for on its own, one request per batch, because an
    oversized reply poisons the source port and these are exactly the
    nodes already suspected of being oversized.
    """
    unrecovered: list[str] = []
    for address in nodes:
        result = connection.get_many(
            [address], batch_size=1, typetag=_SCHEMA_TYPETAG, args=(_DUMP_ARG,)
        )
        message = result.replies.get(address)
        if message is None or not message.args:
            unrecovered.append(address)
            continue
        try:
            tree = parse_node_text(message.args[0])
        except NodeTextError:
            unrecovered.append(address)
            continue
        _file_dump_keys(address, tree, leaves)
    return unrecovered


def _file_dump_keys(prefix: str, tree: dict, leaves: dict[str, str]) -> None:
    """A nested dict in a parsed dump is a child node; anything else is a
    leaf. Recursing here rather than re-querying keeps the whole recovery
    to one request per unresolved node."""
    for name, value in tree.items():
        if name.startswith("$"):
            continue  # S2.2: read-only, absent from .snap
        child = f"{prefix}/{name}"
        if isinstance(value, dict):
            _file_dump_keys(child, value, leaves)
        else:
            leaves.setdefault(child, "")
