"""`FakeDesk` -- the only "desk" any wave-2 test ever sees. No socket.

`tests/fake_wing.py` stays the loopback fake for `net/`'s own tests,
which need real wire bytes; the controller layer (`live_controller.py`,
task 2+) never touches a socket, so its tests script an in-memory desk
instead. Everything `_FakeClient` hands back is a real
`net.client.BatchResult` holding real `net.codec.OscMessage` objects
built directly, so a test can call `codec.leaf_value` on a reply exactly
as `live_controller` will.
"""

from __future__ import annotations

from typing import Any

from wing_parser.core.loader import RawScene
from wing_parser.core.versions import load_registry, resolve
from wing_parser.net.client import BatchResult
from wing_parser.net.codec import OscMessage, leaf_value
from wing_parser.net.identity import WingIdentity

# `_place` is private, and imported anyway: it is the ae/ce nesting rule
# net S2.2 defines, and a double that re-implemented it could drift from
# the real `take_snapshot` while still passing its own tests.
from wing_parser.net.snapshot import SNAPSHOT_TYPE_ID, SnapshotResult, _place
from wing_parser.net.watch import poller
from wing_parser.net.watch.list import WatchList


class _FakeClient:
    """Stands in for `net.client.WingClient` against one `FakeDesk`."""

    def __init__(self, desk: "FakeDesk") -> None:
        self._desk = desk
        self._round_index = 0

    def get_many(self, addresses: Any, **_kw: Any) -> BatchResult:
        addresses = tuple(addresses)
        self._desk.calls.append(("get_many", len(addresses)))
        round_ = self._next_round()
        if round_ is not None and not round_:
            # A round the desk ignored: it answered nothing, so nothing
            # resolved -- not even an address `leaves` could have served.
            return BatchResult(replies={}, unresolved=addresses)
        round_ = round_ or {}
        replies: dict[str, OscMessage] = {}
        unresolved: list[str] = []
        for address in addresses:
            if address in round_:
                replies[address] = round_[address]
            elif address in self._desk.leaves:
                replies[address] = self._desk.leaves[address]
            else:
                unresolved.append(address)
        return BatchResult(replies=replies, unresolved=tuple(unresolved))

    def request(self, address: str, **_kw: Any) -> OscMessage | None:
        self._desk.calls.append(("request", 1))
        return self._desk.leaves.get(address)

    def close(self) -> None:
        pass

    def __enter__(self) -> "_FakeClient":
        return self

    def __exit__(self, *exc_info: object) -> None:
        self.close()

    def _next_round(self) -> dict[str, object] | None:
        """The round `get_many` consumes this call, or `None` for no script.

        `None` when no rounds were scripted at all -- every address then
        falls back to `leaves`, which is what a plain discovery walk or
        snapshot pull scripts. A scripted-but-empty round (`{}`) is a
        round the desk IGNORED: `get_many` answers nothing and leaves
        every requested address unresolved, with no fallback, which is
        how a test scripts a desk that has gone quiet without raising.
        Once the list runs out its last entry repeats forever, so a
        caller polling past the end of a script sees steady state rather
        than an IndexError.
        """
        rounds = self._desk.rounds
        if not rounds:
            return None
        index = min(self._round_index, len(rounds) - 1)
        self._round_index += 1
        return rounds[index]


class FakeDesk:
    """Everything live_controller can reach, in memory. No socket anywhere.

    identity   : WingIdentity | Exception   -- returned, or raised
    leaves     : dict[str, OscMessage]      -- the console's whole surface
    unresolved : tuple[str, ...]            -- what the walk could not resolve
    strips     : dict[str, int]             -- per-family counts for the WatchList
    rounds     : list[dict[str, object]]    -- scripted samples, consumed one per get_many;
                 an EMPTY dict is a round the desk ignored (nothing answered, every
                 address unresolved, no fallback to `leaves`), and a list that runs
                 out repeats its last entry forever
    calls      : list[tuple[str, int]]      -- ("get_many", len(addresses)), in order
    """

    def __init__(
        self,
        identity: WingIdentity | Exception | None = None,
        leaves: dict[str, OscMessage] | None = None,
        unresolved: tuple[str, ...] = (),
        strips: dict[str, int] | None = None,
        rounds: list[dict[str, object]] | None = None,
    ) -> None:
        self.identity = identity
        self.leaves: dict[str, OscMessage] = dict(leaves) if leaves else {}
        self.unresolved: tuple[str, ...] = tuple(unresolved)
        self.strips: dict[str, int] = dict(strips) if strips else {}
        self.rounds: list[dict[str, object]] = list(rounds) if rounds else []
        self.calls: list[tuple[str, int]] = []

    def transport(self):
        """The `live_controller.Transport` wrapping this desk.

        Imported here, not at module level, so `live_controller` is only
        needed by a caller that actually reaches for a live transport.
        """
        from wing_parser.ui import live_controller

        return live_controller.Transport(
            identity=self._identity,
            walk=self._walk,
            snapshot=self._snapshot,
            client=self.client,
            # The REAL poller, not a double: what a watch test needs
            # faked is the desk, and `poller.watch` reaches it only
            # through `client()` above.
            watch=poller.watch,
        )

    def client(self, host: str | None = None) -> _FakeClient:
        return _FakeClient(self)

    # -- the four transport callables -------------------------------------

    def _identity(self, host: str) -> WingIdentity:
        """`query_identity`: the scripted identity, returned or raised."""
        if isinstance(self.identity, Exception):
            raise self.identity
        return self.identity

    def _walk(self, host: str) -> WatchList:
        """`build_watch_list`, from the desk's own fields.

        Deliberately does not go through `client()`: the real walk reads
        the console's SHAPE, and letting it spend rounds here would put
        entries in `calls` that a watch test then has to skip past.
        """
        return WatchList(
            addresses=tuple(self.leaves),
            unresolved=self.unresolved,
            strips=dict(self.strips),
        )

    def _snapshot(self, host: str) -> SnapshotResult:
        """`take_snapshot`: every leaf read through `client()`, then
        decoded and filed by the real `leaf_value`/`_place`, so a pulled
        `RawScene` is assembled by exactly the rule a real pull uses
        (`snapshot.py:87-113`). Costs one `("get_many", n)` in `calls`."""
        batch = self.client(host).get_many(tuple(self.leaves))
        ae: dict[str, Any] = {}
        ce: dict[str, Any] = {}
        for address, message in batch.replies.items():
            value, _display = leaf_value(message)
            _place(ae, ce, address, value)
        return SnapshotResult(
            raw=RawScene(
                version=resolve(SNAPSHOT_TYPE_ID, load_registry()),
                ae=ae,
                ce=ce,
                meta={},
                path=None,
                source=f"wing://{host}",
            ),
            unresolved_nodes=self.unresolved,
            unresolved_leaves=batch.unresolved,
        )
