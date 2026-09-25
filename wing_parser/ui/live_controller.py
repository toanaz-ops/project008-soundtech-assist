"""The Console page's brain: plain functions over `net/`, no Qt.

Mirrors `import_controller.py` -- every decision the live page needs is a
plain function, testable headless -- with one addition it does not need:
a seam. `Transport` names the six `net/` entry points the page uses, so
this module is the ONLY place under `wing_parser/ui/` that says `net`,
and a test can drive the whole page against an in-memory desk
(`tests/fake_desk.py`) with no socket anywhere (spec S7.1, S9.1).

That the seam names six *read-only* calls and no others is how spec S8
makes a write impossible in this wave: `net/write.py` has no way in.

Failures pass through untouched: `query_identity`'s `TimeoutError`
naming the host and the 2.0 s it waited (`identity.py:83`), and its
`IdentityError`, a `ValueError` (`identity.py:29`), reach the page as
they are -- the `import_controller.read_with` precedent.

**D-41**: `discover`/`pull` take an optional `cache: SchemaCache`
(`live_schema_cache.py`). Omitted, both walk exactly as before -- the
default is unchanged. Handed one, whichever of the two runs FIRST for a
connection walks once (via the sixth entry, `walk_schema`) and remembers
it; the other reuses it via `net/`'s own `schema=` parameter instead of
paying for a second walk. The cache is the caller's (`ConsolePage`'s) to
clear -- neither function here writes to one it was not explicitly handed.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterator

from wing_parser.net.client import WingClient
from wing_parser.net.identity import WingIdentity, query_identity
from wing_parser.net.schema import SchemaResult, walk_schema
from wing_parser.net.snapshot import SnapshotResult, take_snapshot
from wing_parser.net.watch import poller
from wing_parser.net.watch.events import Change
from wing_parser.net.watch.list import WatchList, build_watch_list
from wing_parser.ui.live_errors import EmptyReadError
from wing_parser.ui.live_schema_cache import SchemaCache
from wing_parser.ui.live_session_build import session_from_snapshot, suggested_name

__all__ = [
    "REAL", "Transport", "EmptyReadError", "SchemaCache",
    "connect", "discover", "pull", "incomplete_report",
    "session_from_snapshot", "suggested_name",
]


@dataclass(frozen=True)
class Transport:
    """The six net/ entry points the Console page uses, injectable.

    `watch` is the poller's loop, read-only like the rest (it only calls
    `get_many` on the client it is handed, `poller.py:36,51`), and named
    here because `GeneratorWorker` (S7.3), which drains it on a thread,
    must not say `net` either.

    `walk_schema` (D-41) is the shape walk `walk`/`snapshot` otherwise run
    internally -- named here so a caller that wants to SHARE one walk
    between them (a `SchemaCache`, see `discover`/`pull`) can trigger it
    explicitly instead of paying for it a second time.
    """

    identity: Callable[[str], WingIdentity]
    walk: Callable[..., WatchList]
    snapshot: Callable[..., SnapshotResult]
    client: Callable[[str], WingClient]
    watch: Callable[..., Iterator[Change]]
    walk_schema: Callable[[str], SchemaResult]


REAL = Transport(
    identity=query_identity,
    walk=build_watch_list,
    snapshot=take_snapshot,
    client=WingClient,
    watch=poller.watch,
    walk_schema=walk_schema,
)


def connect(host: str, transport: Transport = REAL) -> WingIdentity:
    """The `WING?` handshake, and the only call that fails loudly.

    OSC on 2223 is UDP: a GET against an absent address simply goes quiet
    and `WingClient.request` answers `None` rather than raising
    (`client.py:139-141`), so silence there means nothing. This one
    exchange is the page's proof a desk is actually there, which is why
    its `TimeoutError` reaches the operator unchanged rather than being
    softened into an empty result (design D2).
    """
    return transport.identity(host)


def _schema_for(
    host: str, transport: Transport, cache: SchemaCache | None
) -> SchemaResult | None:
    """D-41: `None` when no `cache` is in play -- `discover`/`pull` then
    walk exactly as before, every call. Given one, its remembered schema
    (walking once, via `transport.walk_schema`, the first time either
    caller asks) so the other reuses it instead of paying for a second
    walk."""
    if cache is None:
        return None
    schema = cache.get()
    if schema is None:
        schema = transport.walk_schema(host)
        cache.set(schema)
    return schema


def discover(
    host: str, transport: Transport = REAL, *, cache: SchemaCache | None = None
) -> WatchList:
    """Walk the console and return the watch list exactly as built.

    `build_watch_list` (`watch/list.py:67`) already carries `addresses`,
    the `unresolved` nodes the walk could not reach, and a per-family
    `strips` count -- the whole discovery panel -- so reshaping it here
    could only lose the unresolved half, which `WatchList` keeps as a
    field rather than an omission precisely so a node that never answered
    stays visible to its caller (`watch/list.py:39-48`).

    `schema` is passed on only when `cache` actually produced one: a
    `transport.walk` a test swapped in (a plain `def _walk(host)`, no
    `schema` keyword) must keep working exactly as before `cache` existed.
    """
    schema = _schema_for(host, transport, cache)
    return transport.walk(host, schema=schema) if schema is not None else transport.walk(host)


def pull(
    host: str, transport: Transport = REAL, *, cache: SchemaCache | None = None
) -> SnapshotResult:
    """Read the whole console, refusing a read that reached nothing.

    Whatever the snapshot raises -- `OSError`, `ValueError` -- reaches the
    caller untouched, as everywhere else here. The one thing this adds is
    the failure that raises nothing at all: see `EmptyReadError`.
    """
    schema = _schema_for(host, transport, cache)
    result = (transport.snapshot(host, schema=schema) if schema is not None
              else transport.snapshot(host))
    if not result.raw.ae and not result.raw.ce:
        raise EmptyReadError(
            host, len(result.unresolved_nodes), len(result.unresolved_leaves)
        )
    return result


def incomplete_report(result: SnapshotResult) -> str | None:
    """How much of a partial read did not answer, or `None` if all of it did.

    The other half of `_load`'s pair (`cli/commands.py:64-78`). A partial
    read is usable and must never look complete, so this is a persistent
    banner; a clean read reports nothing, because a warning shown every
    time teaches the reader to skip it. The node names are listed -- few,
    and they say *where* -- and that clause is dropped when there are none.
    """
    if not result.unresolved_nodes and not result.unresolved_leaves:
        return None
    named = (
        f"; nodes: {', '.join(result.unresolved_nodes)}"
        if result.unresolved_nodes
        else ""
    )
    return (
        f"incomplete read: {len(result.unresolved_nodes)} node(s) and "
        f"{len(result.unresolved_leaves)} leaf/leaves did not answer{named}"
    )


# `suggested_name`/`session_from_snapshot` live in `live_session_build.py`
# now (D-41, headroom) and are re-exported above.
