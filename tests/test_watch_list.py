"""Tests for wing_parser.net.watch.list, driven against tests/fake_wing.py.

No test here touches a real console.
"""

from __future__ import annotations

import pytest

from tests.fake_wing import FakeWing
from wing_parser.net.codec import encode
from wing_parser.net.watch.list import build_watch_list, load_watch_keys

FAST = dict(batch_size=200, retry_rounds=1, idle_timeout=0.03)


def _schema_tx(address: str) -> bytes:
    return encode(address, "s", ("?",))


def _schema_rx(address: str, body: str) -> bytes:
    return encode(address, "s", (body,))


def _tiny_desk(fake: FakeWing) -> None:
    """Two channels and one bus, each owning one ordinary leaf and one
    $ leaf. The $ leaf is present in the reply on purpose: the walk must
    skip it, and the builder must add it back from config."""
    fake.register(_schema_tx("/ch"), _schema_rx("/ch", "  1  (node)\n  2  (node)\n"))
    for number in (1, 2):
        fake.register(
            _schema_tx(f"/ch/{number}"),
            _schema_rx(f"/ch/{number}", "  fdr  fader [-oo .. 10.0 dB]\n  $fdr  fader\n"),
        )
    fake.register(_schema_tx("/bus"), _schema_rx("/bus", "  1  (node)\n"))
    fake.register(
        _schema_tx("/bus/1"),
        _schema_rx("/bus/1", "  fdr  fader [-oo .. 10.0 dB]\n"),
    )


def test_addresses_are_the_dollar_keys_of_every_strip_the_walk_found():
    with FakeWing() as fake:
        _tiny_desk(fake)
        host, port = fake.osc_address
        result = build_watch_list(
            host,
            port=port,
            keys={"ch": ("$fdr", "$mute"), "bus": ("$fdr",)},
            **FAST,
        )

    assert result.addresses == (
        "/ch/1/$fdr",
        "/ch/1/$mute",
        "/ch/2/$fdr",
        "/ch/2/$mute",
        "/bus/1/$fdr",
    )
    assert result.strips == {"ch": 2, "bus": 1}


def test_a_family_the_console_does_not_have_contributes_nothing():
    """The 20x cost of an absent address (design doc S2.5) is avoided by
    never emitting one, not by tolerating it."""
    with FakeWing() as fake:
        _tiny_desk(fake)
        host, port = fake.osc_address
        result = build_watch_list(
            host, port=port, keys={"ch": ("$fdr",), "mtx": ("$fdr",)}, **FAST
        )

    assert result.addresses == ("/ch/1/$fdr", "/ch/2/$fdr")
    assert "mtx" not in result.strips
    assert not any("/mtx/" in address for address in result.addresses)


def test_an_unresolved_node_is_reported_and_never_folded_into_absent():
    """Design doc S2.7/S3.2: a builder that cannot say what it failed to
    resolve fails silently, and a watch-list quietly missing four mains
    never reports a main fader move while looking fine doing it."""
    with FakeWing() as fake:
        _tiny_desk(fake)
        # /main answers with a child that then never answers at all.
        fake.register(_schema_tx("/main"), _schema_rx("/main", "  1  (node)\n"))
        fake.register(_schema_tx("/main/1"), None)
        # walk_schema falls back to a ,s * dump for any node its ,s ? query
        # could not resolve, and wing_osc_fixtures.json carries a real recorded
        # dump for /main/1 -- which would answer, recover the node, and keep it
        # out of `unresolved`. Silencing only the schema query makes this test
        # assert nothing.
        fake.register(encode("/main/1", "s", ("*",)), None)
        host, port = fake.osc_address
        result = build_watch_list(
            host, port=port, keys={"ch": ("$fdr",), "main": ("$fdr",)}, **FAST
        )

    assert "/main/1" in result.unresolved


def test_the_shipped_yaml_loads_and_names_the_measured_families():
    keys = load_watch_keys()
    assert set(keys) == {"ch", "bus", "main", "mtx", "dca"}
    # S2.1 measured that /dca exposes only $solo and $sololed -- it has no
    # $fdr, so asking for one would emit an address that cannot answer.
    assert keys["dca"] == ("$solo",)
    assert keys["ch"] == ("$fdr", "$mute", "$solo")


def test_a_family_named_in_config_but_absent_from_the_address_map_is_refused():
    """A typo in watchlist.yaml must fail loudly at build time, not
    produce a watch-list that silently omits what the engineer asked for."""
    with FakeWing() as fake:
        _tiny_desk(fake)
        host, port = fake.osc_address
        with pytest.raises(ValueError, match="chn"):
            build_watch_list(host, port=port, keys={"chn": ("$fdr",)}, **FAST)
