"""The Console page's brain: plain functions over `net/`, no Qt.

Mirrors `import_controller.py` -- every decision the live page needs is a
plain function, testable headless -- with one addition it does not need:
a seam. `Transport` names the five `net/` entry points the page uses, so
this module is the ONLY place under `wing_parser/ui/` that says `net`,
and a test can drive the whole page against an in-memory desk
(`tests/fake_desk.py`) with no socket anywhere (spec S7.1, S9.1).

That the seam names five *read-only* calls and no others is how spec S8
makes a write impossible in this wave: `net/write.py` has no way in.

Failures pass through untouched: `query_identity`'s `TimeoutError`
naming the host and the 2.0 s it waited (`identity.py:83`), and its
`IdentityError`, a `ValueError` (`identity.py:29`), reach the page as
they are -- the `import_controller.read_with` precedent.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Callable, Iterator

from wing_parser.net.client import WingClient
from wing_parser.net.export import to_snap_json
from wing_parser.net.identity import WingIdentity, query_identity
from wing_parser.net.snapshot import SnapshotResult, take_snapshot
from wing_parser.net.watch import poller
from wing_parser.net.watch.events import Change
from wing_parser.net.watch.list import WatchList, build_watch_list
from wing_parser.ui.session import Session

# `wing://<host>` is the prefix `net/snapshot.py:106` stamps onto every
# scene read off a console, and `RawScene.source` is the only record a
# `SnapshotResult` keeps of which desk it came from -- so it is the one
# place `session_from_snapshot` can recover the host its filename needs.
_LIVE_SOURCE = "wing://"


class EmptyReadError(OSError):
    """A pull that reached the desk's address and read nothing at all.

    Ported from `cli/commands.py:47-62`, where it is a printed line and a
    `None` return. It has to be an *error* rather than an empty result:
    OSC is UDP, so an unreachable host raises nothing -- every leaf times
    out, `take_snapshot` faithfully returns a valid empty scene, and the
    advisory engine truthfully finds nothing wrong with it. `doctor
    --live` showed "No findings." for a desk it had never reached, until
    this guard existed. An `OSError` because that is the vocabulary every
    other live-read failure already speaks (`commands.py:25-28`). Both
    counts, never one: `walk_schema` runs first and the leaf reads run
    after it, so `nodes` can be 0 while every leaf timed out.
    """

    def __init__(self, host: str, nodes: int, leaves: int) -> None:
        super().__init__(
            f"no console answered at {host}: read nothing at all "
            f"({nodes} top-level node(s) and {leaves} leaf/leaves did not "
            f"answer). Check the address and that the desk is on the network."
        )
        self.host = host
        self.nodes = nodes
        self.leaves = leaves


@dataclass(frozen=True)
class Transport:
    """The five net/ entry points the Console page uses, injectable.

    `watch` is the poller's loop, read-only like the rest (it only calls
    `get_many` on the client it is handed, `poller.py:36,51`), and named
    here because `GeneratorWorker` (S7.3), which drains it on a thread,
    must not say `net` either.
    """

    identity: Callable[[str], WingIdentity]
    walk: Callable[[str], WatchList]
    snapshot: Callable[[str], SnapshotResult]
    client: Callable[[str], WingClient]
    watch: Callable[..., Iterator[Change]]


REAL = Transport(
    identity=query_identity,
    walk=build_watch_list,
    snapshot=take_snapshot,
    client=WingClient,
    watch=poller.watch,
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


def discover(host: str, transport: Transport = REAL) -> WatchList:
    """Walk the console and return the watch list exactly as built.

    `build_watch_list` (`watch/list.py:67`) already carries `addresses`,
    the `unresolved` nodes the walk could not reach, and a per-family
    `strips` count -- the whole discovery panel -- so reshaping it here
    could only lose the unresolved half, which `WatchList` keeps as a
    field rather than an omission precisely so a node that never answered
    stays visible to its caller (`watch/list.py:39-48`).
    """
    return transport.walk(host)


def pull(host: str, transport: Transport = REAL) -> SnapshotResult:
    """Read the whole console, refusing a read that reached nothing.

    Whatever the snapshot raises -- `OSError`, `ValueError` -- reaches the
    caller untouched, as everywhere else here. The one thing this adds is
    the failure that raises nothing at all: see `EmptyReadError`.
    """
    result = transport.snapshot(host)
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


def suggested_name(identity: WingIdentity | None, host: str) -> str:
    """What to call a pulled scene: `WING-GIAQUY-20260915-1432.snap`.

    A **bare filename, no directory** (D4): a `path` naming a real file
    would let a plain Save overwrite something nobody chose. Sanitised
    at the source (D-43) because `menus.save_as` proposes from this same
    path (`menus.py:87-89`) and `WingIdentity.name` is whatever somebody
    typed into the desk -- "FOH/Monitors" would otherwise arrive as a
    directory. Dot and dash survive: the fallback stays an address.
    """
    stamp = datetime.now().strftime("%Y%m%d-%H%M")
    stem = identity.name if identity is not None else f"wing-{host}"
    who = re.sub(r"[^\w.\-]", "_", stem)
    return f"{who}-{stamp}.snap"


def session_from_snapshot(
    result: SnapshotResult,
    identity: WingIdentity | None,
    profile: str | None = None,
) -> tuple[Session, str]:
    """A pulled scene as an ordinary `Session`, plus the pull-time text.

    The scene goes through `net/export.py`'s serialiser and straight back
    through `json.loads`, so what the `Session` holds is the same
    document an opened `.snap` would give it -- which is why Doctor,
    Overview, Channels, Routing and Diff need to know nothing about
    consoles.

    The text is returned as well, and it is the *pull-time original*
    (D3): export must go through `Session.save_as`, which writes the
    patched document (`session.py:92-96` -> `_document()` at `:43-44`),
    so writing this string instead would silently drop every repair made
    after the pull. Only the tests keep it, to prove that difference.
    """
    text = to_snap_json(result.raw, identity)
    host = result.raw.source.removeprefix(_LIVE_SOURCE)
    session = Session(
        json.loads(text), Path(suggested_name(identity, host)), profile
    )
    return session, text
