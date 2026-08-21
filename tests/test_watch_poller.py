"""Tests for the polling loop. No socket: a stub client returns scripted
rounds, so the loop's behaviour is examined without timing flakiness."""

from __future__ import annotations

from wing_parser.net.client import BatchResult
from wing_parser.net.codec import OscMessage
from wing_parser.net.watch.list import WatchList
from wing_parser.net.watch.poller import sample, watch


def _fdr(value: float) -> OscMessage:
    display = "-oo" if value == -144.0 else f"{value}"
    return OscMessage(address="", typetag="sff", args=(display, 0.0, value))


def _name(text: str) -> OscMessage:
    return OscMessage(address="", typetag="s", args=(text,))


class StubClient:
    """Replays a scripted list of {address: OscMessage} rounds."""

    def __init__(self, rounds, labels=None):
        self._rounds = list(rounds)
        self._labels = labels or {}
        self.calls = 0

    def get_many(self, addresses, **kwargs):
        addresses = list(addresses)
        if addresses and addresses[0].endswith("/name"):
            replies = {a: _name(self._labels.get(a, "")) for a in addresses}
            return BatchResult(replies=replies, unresolved=())
        index = min(self.calls, len(self._rounds) - 1)
        self.calls += 1
        replies = dict(self._rounds[index])
        missing = tuple(a for a in addresses if a not in replies)
        return BatchResult(replies=replies, unresolved=missing)


def _list(*addresses) -> WatchList:
    return WatchList(addresses=tuple(addresses), unresolved=(), strips={"ch": 1})


def _run(client, watch_list, rounds):
    """Drive the loop for an exact number of rounds, with a clock that
    advances on every call and never runs dry, and a sleep that does not.

    Bounded by max_rounds rather than duration: the loop calls clock()
    twice per round plus once per change, so a scripted tick list would
    run out at a data-dependent point.
    """
    state = {"now": 0.0}

    def clock() -> float:
        state["now"] += 0.01
        return state["now"]

    return list(
        watch(
            client,
            watch_list,
            interval=0.0,
            max_rounds=rounds,
            clock=clock,
            sleep=lambda _seconds: None,
        )
    )


def test_sample_reads_the_native_float_for_an_sff_leaf():
    client = StubClient([{"/ch/1/$fdr": _fdr(-7.9)}])
    assert sample(client, ["/ch/1/$fdr"]) == {"/ch/1/$fdr": -7.9}


def test_a_changed_value_produces_one_change_naming_before_and_after():
    client = StubClient(
        [
            {"/ch/1/$fdr": _fdr(-144.0)},
            {"/ch/1/$fdr": _fdr(-7.9)},
            {"/ch/1/$fdr": _fdr(-7.9)},
        ]
    )
    changes = _run(client, _list("/ch/1/$fdr"), 3)
    assert len(changes) == 1
    assert changes[0].before == -144.0
    assert changes[0].after == -7.9
    assert changes[0].address == "/ch/1/$fdr"


def test_a_steady_value_produces_nothing():
    client = StubClient([{"/ch/1/$fdr": _fdr(-7.9)}])
    assert _run(client, _list("/ch/1/$fdr"), 4) == []


def test_a_leaf_that_stops_answering_is_not_reported_as_a_change():
    """It failed to answer; it did not move. Reporting -7.9 -> None would
    invent a value the console never stated."""
    client = StubClient(
        [
            {"/ch/1/$fdr": _fdr(-7.9)},
            {},                      # silent round
            {"/ch/1/$fdr": _fdr(-7.9)},
        ]
    )
    assert _run(client, _list("/ch/1/$fdr"), 3) == []


def test_a_value_that_moves_while_a_leaf_is_silent_is_still_caught_afterwards():
    client = StubClient(
        [
            {"/ch/1/$fdr": _fdr(-144.0)},
            {},
            {"/ch/1/$fdr": _fdr(0.0)},
            {"/ch/1/$fdr": _fdr(0.0)},
        ]
    )
    changes = _run(client, _list("/ch/1/$fdr"), 4)
    assert len(changes) == 1
    assert changes[0].before == -144.0
    assert changes[0].after == 0.0


def test_the_change_carries_the_strips_name():
    client = StubClient(
        [
            {"/ch/1/$fdr": _fdr(-144.0)},
            {"/ch/1/$fdr": _fdr(-7.9)},
        ],
        labels={"/ch/1/name": "Kick In"},
    )
    changes = _run(client, _list("/ch/1/$fdr"), 2)
    assert changes[0].label == "Kick In"
