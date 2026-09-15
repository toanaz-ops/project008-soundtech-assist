"""The live controller: the transport seam, `connect`, `discover`, `pull`.

No socket anywhere: every test drives a `FakeDesk` (`tests/fake_desk.py`),
the only desk wave 2 ever sees. Spec S7.1 (the four-callable seam, and
both guards ported from `cli/commands.py:_load`) and S9.1 (connect:
success, `TimeoutError`, malformed identity; discover: clean, and
unresolved-families; pull against a desk that answers nothing; pull
partial).
"""

from __future__ import annotations

import dataclasses

import pytest

from tests.fake_desk import FakeDesk
from wing_parser.net.client import WingClient
from wing_parser.net.codec import OscMessage
from wing_parser.net.identity import (
    IdentityError,
    WingIdentity,
    parse_identity,
    query_identity,
)
from wing_parser.net.snapshot import SnapshotResult, take_snapshot
from wing_parser.net.watch.list import WatchList, build_watch_list
from wing_parser.ui.live_controller import (
    REAL,
    EmptyReadError,
    Transport,
    connect,
    discover,
    incomplete_report,
    pull,
)

HOST = "192.168.128.28"

GIAQUY = WingIdentity(
    ip=HOST,
    name="WING-GIAQUY",
    model="wing-rack",
    serial="01009Y90604AAE",
    firmware="3.1-0-g9f314617:release",
)


def _fader(address: str) -> OscMessage:
    return OscMessage(address, "sff", ("-6.0", 0.5, -6.0))


def _loaded_desk() -> FakeDesk:
    """A desk with one ae leaf and one ce leaf -- enough to be non-empty."""
    return FakeDesk(
        leaves={
            "/ch/1/name": OscMessage("/ch/1/name", "s", ("KICK",)),
            "/$ctl/cfg/dark": OscMessage("/$ctl/cfg/dark", "sfi", ("1", 0.0, 0)),
        }
    )


def _real_snapshot() -> SnapshotResult:
    """One `SnapshotResult` assembled by FakeDesk's real pull path.

    Tests that need a *pathological* read `dataclasses.replace` fields on
    this rather than hand-building a `RawScene`, so the version, meta and
    source of every fixture below are the ones a real pull produces.
    """
    return _loaded_desk().transport().snapshot(HOST)


def _transport_snapshotting(snapshot) -> Transport:
    """A `Transport` whose `snapshot` is `snapshot` and nothing else changed.

    Injecting the seam's own field is what `Transport` exists for (S7.1,
    "injectable"): `FakeDesk` models a desk that answers, and a desk that
    answers *nothing while raising nothing* -- the UDP case the guard was
    written for -- is exactly what it cannot model.
    """
    return dataclasses.replace(FakeDesk().transport(), snapshot=snapshot)


def test_connect_returns_the_desks_identity():
    desk = FakeDesk(identity=GIAQUY)

    assert connect(HOST, desk.transport()) is GIAQUY


def test_connect_lets_a_timeout_through_untranslated():
    # The exact object `query_identity` raises (identity.py:83-85), not a
    # look-alike: connect must not wrap, rename or re-raise it.
    stall = TimeoutError("no WING? reply from 10.0.0.9:2222 within 2.0s")
    desk = FakeDesk(identity=stall)

    with pytest.raises(TimeoutError) as caught:
        connect("10.0.0.9", desk.transport())

    assert caught.value is stall


def test_connect_lets_a_malformed_reply_raise_identityerror():
    # Built by the real parser rather than by hand, so the error this test
    # asserts on is the one a short WING? reply genuinely produces.
    with pytest.raises(IdentityError) as refused:
        parse_identity(b"WING,192.168.128.28,WING-GIAQUY")
    desk = FakeDesk(identity=refused.value)

    with pytest.raises(IdentityError) as caught:
        connect(HOST, desk.transport())

    assert caught.value is refused.value
    # `IdentityError` is already a `ValueError` (identity.py:29), so the
    # page's one error line needs no second taxonomy to catch it.
    assert isinstance(caught.value, ValueError)


def test_discover_returns_the_watchlist_untouched():
    leaves = {
        "/ch/1/$fdr": _fader("/ch/1/$fdr"),
        "/ch/2/$fdr": _fader("/ch/2/$fdr"),
        "/bus/1/$fdr": _fader("/bus/1/$fdr"),
    }
    desk = FakeDesk(leaves=leaves, strips={"ch": 2, "bus": 1})

    found = discover(HOST, desk.transport())

    # `type(...) is` and not `isinstance`: a reshaped or wrapped result
    # would still pass an isinstance check against a subclass.
    assert type(found) is WatchList
    assert found.addresses == tuple(leaves)
    assert found.strips == {"ch": 2, "bus": 1}
    assert found.unresolved == ()


def test_discover_reports_the_families_the_walk_could_not_resolve():
    desk = FakeDesk(
        leaves={"/ch/1/$fdr": _fader("/ch/1/$fdr")},
        unresolved=("/mtx", "/dca"),
        strips={"ch": 1},
    )

    found = discover(HOST, desk.transport())

    assert found.unresolved == ("/mtx", "/dca")
    assert found.strips == {"ch": 1}


def test_real_transport_names_only_read_only_entry_points():
    assert tuple(field.name for field in dataclasses.fields(Transport)) == (
        "identity",
        "walk",
        "snapshot",
        "client",
    )
    assert REAL.identity is query_identity
    assert REAL.walk is build_watch_list
    assert REAL.snapshot is take_snapshot
    assert REAL.client is WingClient
    # Frozen: `REAL` is one module-level object every page shares, so a
    # write path must not be assignable onto it after import.
    with pytest.raises(dataclasses.FrozenInstanceError):
        REAL.identity = query_identity


def test_pull_against_a_silent_desk_raises_naming_host_and_both_counts():
    # The shape the guard exists for (commands.py:39-62): OSC is UDP, so
    # an unreachable host raises nothing at all -- the walk reported three
    # nodes it could not reach, every one of the 220 leaf reads then timed
    # out, and `take_snapshot` returned a perfectly valid empty scene.
    clean = _real_snapshot()
    silent = dataclasses.replace(
        clean,
        raw=dataclasses.replace(clean.raw, ae={}, ce={}),
        unresolved_nodes=("/ch", "/bus", "/main"),
        unresolved_leaves=tuple(f"/ch/{n}/$fdr" for n in range(1, 221)),
    )
    reads: list[str] = []

    def _snapshot(host: str) -> SnapshotResult:
        reads.append(host)
        return silent

    with pytest.raises(EmptyReadError) as caught:
        pull("10.0.0.9", _transport_snapshotting(_snapshot))

    assert str(caught.value) == (
        "no console answered at 10.0.0.9: read nothing at all "
        "(3 top-level node(s) and 220 leaf/leaves did not answer). "
        "Check the address and that the desk is on the network."
    )
    assert (caught.value.host, caught.value.nodes, caught.value.leaves) == (
        "10.0.0.9",
        3,
        220,
    )
    # No `Session` is built: the desk was read exactly once and `pull`
    # raised instead of returning, so nothing downstream ever ran.
    assert reads == ["10.0.0.9"]
    # An `OSError`, like every other live-read failure, so the page needs
    # no third branch to show it as one error line.
    assert isinstance(caught.value, OSError)


def test_pull_returns_the_snapshot_result_on_a_clean_read():
    desk = _loaded_desk()

    result = pull(HOST, desk.transport())

    assert type(result) is SnapshotResult
    assert result.raw.ae == {"ch": {"1": {"name": "KICK"}}}
    assert result.raw.ce == {"cfg": {"dark": 1}}
    assert result.unresolved_nodes == ()
    assert result.unresolved_leaves == ()


def test_incomplete_report_is_none_on_a_clean_read():
    # Silence on a clean read is deliberate (commands.py:65-67): a warning
    # printed every time teaches the reader to skip it.
    assert incomplete_report(pull(HOST, _loaded_desk().transport())) is None


def test_incomplete_report_names_the_counts_and_the_node_names():
    clean = _real_snapshot()

    both = dataclasses.replace(
        clean,
        unresolved_nodes=("/mtx", "/dca"),
        unresolved_leaves=("/ch/7/$fdr", "/ch/8/$fdr", "/ch/9/$fdr"),
    )
    assert incomplete_report(both) == (
        "incomplete read: 2 node(s) and 3 leaf/leaves did not answer; "
        "nodes: /mtx, /dca"
    )

    # Leaves only: the node names clause is dropped entirely rather than
    # rendered empty (the `if snapshot.unresolved_nodes else ""` at
    # commands.py:72-76).
    leaves_only = dataclasses.replace(
        clean, unresolved_leaves=("/ch/7/$fdr", "/ch/8/$fdr", "/ch/9/$fdr")
    )
    assert incomplete_report(leaves_only) == (
        "incomplete read: 0 node(s) and 3 leaf/leaves did not answer"
    )


def test_pull_lets_an_oserror_from_the_transport_through():
    refused = OSError("[Errno 10051] a socket operation was attempted to an "
                      "unreachable network")

    def _snapshot(host: str) -> SnapshotResult:
        raise refused

    with pytest.raises(OSError) as caught:
        pull("10.0.0.9", _transport_snapshotting(_snapshot))

    assert caught.value is refused
    # Untranslated means untranslated: not re-raised as the guard's own
    # error, which would tell the operator the desk answered nothing when
    # in fact the send itself never left the machine.
    assert not isinstance(caught.value, EmptyReadError)
