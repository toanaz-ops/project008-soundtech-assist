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
