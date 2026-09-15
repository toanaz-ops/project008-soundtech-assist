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

from wing_parser.net.client import BatchResult
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import WingIdentity


class _FakeClient:
    """Stands in for `net.client.WingClient` against one `FakeDesk`."""

    def __init__(self, desk: "FakeDesk") -> None:
        self._desk = desk
        self._round_index = 0

    def get_many(self, addresses: Any, **_kw: Any) -> BatchResult:
        addresses = tuple(addresses)
        self._desk.calls.append(("get_many", len(addresses)))
        round_ = self._next_round()
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

    def _next_round(self) -> dict[str, object]:
        """The round `get_many` consumes this call.

        Empty when no rounds were scripted at all -- every address then
        falls back to `leaves` below, which is what a plain discovery
        walk or snapshot pull scripts. A scripted-but-empty round (`{}`)
        is a round the desk chose to ignore -- it falls back the same
        way, this call just contributed nothing new. Once the list runs
        out its last entry repeats forever, so a caller polling past the
        end of a script sees steady state rather than an IndexError.
        """
        rounds = self._desk.rounds
        if not rounds:
            return {}
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
                 an EMPTY dict is a round the desk ignored, and a list that runs out
                 repeats its last entry forever
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

        Imported here, not at module level, so this file stands alone
        before `live_controller.py` exists -- only a caller that reaches
        for a live transport needs that module at all.
        """
        from wing_parser.ui import live_controller

        return live_controller.Transport(self)

    def client(self, host: str | None = None) -> _FakeClient:
        return _FakeClient(self)
