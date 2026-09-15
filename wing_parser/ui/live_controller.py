"""The Console page's brain: plain functions over `net/`, no Qt.

Mirrors `import_controller.py` -- every decision the live page needs is a
plain function, testable headless -- with one addition it does not need:
a seam. `Transport` names the four `net/` entry points the page uses, so
this module is the ONLY place under `wing_parser/ui/` that says `net`,
and a test can drive the whole page against an in-memory desk
(`tests/fake_desk.py`) with no socket anywhere (spec S7.1, S9.1).

That the seam names exactly four *read-only* calls is also how spec S8
makes a write structurally impossible in this wave: `net/write.py` has no
way in, because nothing here reaches for it.

Failures pass through untouched. `query_identity` already raises
`TimeoutError` naming the host and the 2.0 s it waited (`identity.py:83`)
and `IdentityError`, which is a `ValueError` (`identity.py:29`), so the
page shows one error line instead of inventing a second taxonomy -- the
`import_controller.read_with` precedent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from wing_parser.net.client import WingClient
from wing_parser.net.identity import WingIdentity, query_identity
from wing_parser.net.snapshot import SnapshotResult, take_snapshot
from wing_parser.net.watch.list import WatchList, build_watch_list


class EmptyReadError(OSError):
    """A pull that reached the desk's address and read nothing at all.

    Ported from `cli/commands.py:47-62`, where it is a printed line and a
    `None` return. It has to be an *error* rather than an empty result:
    OSC is UDP, so an unreachable host raises nothing -- every leaf just
    times out -- and `take_snapshot` then faithfully returns a valid,
    empty scene. A UI that passed that on would hand the advisory engine
    nothing, which truthfully finds nothing wrong with nothing, and
    Doctor would show "No findings." for a desk it never reached. That is
    exactly what `doctor --live` did before this guard existed.

    An `OSError` because that is the vocabulary every other live-read
    failure already speaks (`commands.py:25-28`), so the page catches it
    without inventing a third branch.

    Both counts, never one: `walk_schema` runs first and the leaf reads
    run after it, so `nodes` can be 0 while every leaf timed out.
    Reporting only nodes would say "0 top-level node(s)" and discard the
    one number that says what actually happened.
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
    """The four net/ entry points the Console page uses, injectable."""

    identity: Callable[[str], WingIdentity]
    walk: Callable[[str], WatchList]
    snapshot: Callable[[str], SnapshotResult]
    client: Callable[[str], WingClient]


REAL = Transport(
    identity=query_identity,
    walk=build_watch_list,
    snapshot=take_snapshot,
    client=WingClient,
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
    read is usable and must never look complete, so the page keeps this as
    a persistent banner; a clean read reports nothing, because a warning
    shown every time teaches the reader to skip it. The node names are
    listed -- they are few and they say *where* the hole is -- and the
    clause is dropped entirely, not rendered empty, when there are none.
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
