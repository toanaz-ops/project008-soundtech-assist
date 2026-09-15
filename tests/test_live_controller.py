"""The live controller's transport seam, `connect` and `discover`.

No socket anywhere: every test drives a `FakeDesk` (`tests/fake_desk.py`),
the only desk wave 2 ever sees. Spec S7.1 (the four-callable seam) and
S9.1 (connect: success, `TimeoutError`, malformed identity; discover:
clean, and unresolved-families).
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
from wing_parser.net.snapshot import take_snapshot
from wing_parser.net.watch.list import WatchList, build_watch_list
from wing_parser.ui.live_controller import REAL, Transport, connect, discover

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
