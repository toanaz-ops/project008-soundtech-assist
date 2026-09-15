"""`RoundGuard` and `watch_rate`: the non-Qt heart of cancel and desk-lost.

Driven by the **real** `wing_parser.net.watch.poller.watch` over a
`FakeDesk`, because the behaviour under test is entirely about *where in
the poller's own call sequence* the guard gets to look. A hand-rolled
loop standing in for the poller would be a loop written to agree with the
guard, and would not have caught the correction below.

This is the one file in wave 2's test suite that names `net` alongside
`ui`: `live_guard.py` itself imports nothing from `net` at all -- it
wraps whatever object has `.get_many(addresses, **kw)` -- and this file
supplies the real poller as that object's caller. Spec S7.1, D6.
"""

from __future__ import annotations

import threading

import pytest

from tests.fake_desk import FakeDesk
from wing_parser.net.codec import OscMessage
from wing_parser.net.watch import poller
from wing_parser.net.watch.events import split_address
from wing_parser.net.watch.list import FAMILIES, WatchList, load_watch_keys
from wing_parser.ui.live_guard import Cancelled, DeskLost, RoundGuard, watch_rate

HOST = "192.168.128.28"

# A WING rack's shipped strip counts. 40+16+4+8+16 = 84 strips, and with
# watchlist.yaml's three keys for ch/bus/main/mtx and one for dca,
# 40*3 + 16*3 + 4*3 + 8*3 + 16*1 = 220 addresses. Both numbers are
# asserted in `test_the_watch_list_fixture_is_the_shipped_84_strips_and_220_addresses`
# rather than trusted, because every on_round assertion below depends on
# them.
_STRIP_COUNTS = {"ch": 40, "bus": 16, "main": 4, "mtx": 8, "dca": 16}


def _never(_seconds: float) -> None:
    raise AssertionError("poller.watch slept; interval=0 should never reach sleep")


def _watch_list() -> WatchList:
    """The shipped watch list, built without walking a console.

    Same keys (`load_watch_keys`) and same family order (`FAMILIES`) as
    `build_watch_list` (`watch/list.py:99-105`), so the address list the
    poller sees here is shaped exactly like a real walk's.
    """
    keys = load_watch_keys()
    addresses: list[str] = []
    for family in FAMILIES:
        for number in range(1, _STRIP_COUNTS[family] + 1):
            addresses.extend(f"/{family}/{number}/{key}" for key in keys[family])
    return WatchList(
        addresses=tuple(addresses), unresolved=(), strips=dict(_STRIP_COUNTS)
    )


def _reply(address: str) -> OscMessage:
    """One leaf reply, tagged the way its key really is on the wire."""
    if address.endswith("$fdr"):
        return OscMessage(address, "sff", ("-6.0", 0.5, -6.0))
    if address.endswith("/name"):
        return OscMessage(address, "s", ("KICK",))
    return OscMessage(address, "sfi", ("0", 0.0, 0))


def _fader(address: str, db: float) -> OscMessage:
    return OscMessage(address, "sff", (str(db), 0.5, db))


def _answering_leaves(watch_list: WatchList) -> dict[str, OscMessage]:
    """Every address the poller asks for: the 220 watched leaves, and the
    84 `/<strip>/name` labels `read_labels` reads first (`poller.py:84`)."""
    leaves = {address: _reply(address) for address in watch_list.addresses}
    for strip in {split_address(a)[0] for a in watch_list.addresses}:
        leaves[f"{strip}/name"] = _reply(f"{strip}/name")
    return leaves


class _RecordingClient:
    """A client that is not a `WingClient` and not a `FakeDesk` either.

    `RoundGuard` must work over anything with the right methods -- that
    is what keeps `live_guard.py` free of any `net` import -- so the
    delegation test drives it with an object `net/` has never heard of.
    """

    def __init__(self) -> None:
        self.calls: list[str] = []
        self.reply = OscMessage("/ch/1/name", "s", ("KICK",))

    def get_many(self, addresses, **_kw):
        raise AssertionError("the delegation test never runs a round")

    def request(self, address, **_kw):
        self.calls.append(f"request {address}")
        return self.reply

    def close(self):
        self.calls.append("close")

    def __enter__(self):
        self.calls.append("enter")
        return self

    def __exit__(self, *exc_info):
        self.calls.append("exit")
        return False


def test_the_watch_list_fixture_is_the_shipped_84_strips_and_220_addresses():
    watch_list = _watch_list()

    assert len(watch_list.addresses) == 220
    assert len({split_address(a)[0] for a in watch_list.addresses}) == 84


def test_the_guard_raises_desklost_on_the_third_consecutive_empty_round():
    watch_list = _watch_list()
    # One scripted-but-empty round, which repeats forever: a desk that
    # answers nothing while raising nothing -- OSC is UDP.
    desk = FakeDesk(rounds=[{}])
    seen: list[tuple[int, int]] = []
    guard = RoundGuard(
        desk.client(HOST), HOST, threading.Event(), on_round=lambda a, t: seen.append((a, t))
    )
    produced = []

    with pytest.raises(DeskLost) as caught:
        # `max_rounds` is a backstop, not the mechanism: the guard raises
        # on the loop's FIRST round. Without it a regression that never
        # raises would hang this test instead of failing it.
        for change in poller.watch(
            guard, watch_list, interval=0, sleep=_never, max_rounds=10
        ):
            produced.append(change)

    # D6: the poller yields only on a Change (`poller.py:101-114`) and
    # carries a silent address's previous value forward on purpose
    # (`:116-119`), so a dead desk produces NOTHING to inspect. Judging
    # it from the output was never possible; the guard has to raise.
    assert produced == []
    # read_labels goes first over one address per strip (`poller.py:84`),
    # then the priming sample, then the loop's first round -- so the
    # counts are 84, 220, 220, not 220 three times.
    assert seen == [(0, 84), (0, 220), (0, 220)]
    assert caught.value.host == HOST
    assert caught.value.rounds == 3
    assert HOST in str(caught.value)
    assert isinstance(caught.value, OSError)


def test_one_answering_round_resets_the_lost_counter():
    watch_list = _watch_list()
    desk = FakeDesk(
        rounds=[
            {},                                            # read_labels: silent
            {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},     # priming: one answer
            {},                                            # loop 1: silent
            {},                                            # loop 2: silent, then repeats
        ]
    )
    seen: list[tuple[int, int]] = []
    guard = RoundGuard(
        desk.client(HOST), HOST, threading.Event(), on_round=lambda a, t: seen.append((a, t))
    )

    with pytest.raises(DeskLost) as caught:
        list(
            poller.watch(
                guard, watch_list, interval=0, sleep=_never, max_rounds=10
            )
        )

    # The single answering round clears the run, so the desk is not
    # declared lost until three MORE empty ones -- five rounds, not three.
    assert seen == [(0, 84), (1, 220), (0, 220), (0, 220), (0, 220)]
    assert caught.value.rounds == 3


def test_the_guard_raises_cancelled_before_the_next_round():
    watch_list = _watch_list()
    leaves = _answering_leaves(watch_list)
    desk = FakeDesk(
        leaves=leaves,
        rounds=[
            {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},   # read_labels
            {"/ch/1/$fdr": _fader("/ch/1/$fdr", -6.0)},   # priming
            {"/ch/1/$fdr": _fader("/ch/1/$fdr", -3.0)},   # loop 1: a change
        ],
    )
    cancel = threading.Event()
    guard = RoundGuard(desk.client(HOST), HOST, cancel)
    # interval=0 means `remaining` is never positive, so `poller.py:121-123`
    # never reaches `sleep` -- and `_never` would fail the test if it did.
    # A cancel check living in the injected sleep would therefore be
    # unreachable here, which is the whole reason it lives in get_many.
    events = poller.watch(guard, watch_list, interval=0, sleep=_never)

    change = next(events)
    assert (change.address, change.after) == ("/ch/1/$fdr", -3.0)

    cancel.set()
    sent_before_stop = list(desk.calls)
    with pytest.raises(Cancelled):
        next(events)

    # BEFORE the round, not after it: the cancelled round never reached
    # the desk at all. Checking afterwards would also raise `Cancelled`
    # here, but only once one more batch of 220 reads had gone out to a
    # console the operator has just asked to be left alone.
    assert desk.calls == sent_before_stop


def test_the_guard_delegates_request_close_and_the_context_manager_pair():
    client = _RecordingClient()
    guard = RoundGuard(client, HOST, threading.Event())

    with guard as entered:
        # The guard itself, never the bare client: a caller that got the
        # client back would make its rounds unguarded.
        assert entered is guard
        assert guard.request("/ch/1/name") is client.reply
    guard.close()

    assert client.calls == ["enter", "request /ch/1/name", "exit", "close"]


def test_watch_rate_returns_events_per_second_and_elapsed():
    assert watch_rate(120, 30.0) == (4.0, 30.0)


def test_watch_rate_is_zero_rather_than_a_zero_division_at_time_zero():
    assert watch_rate(7, 0.0) == (0.0, 0.0)
    assert watch_rate(0, 0.0) == (0.0, 0.0)
