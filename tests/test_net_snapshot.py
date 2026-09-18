"""Tests for wing_parser.net.snapshot, driven only against tests/fake_wing.py
-- no test here touches a real socket to a real console (design doc S7).

`get/ch/1/in/conn/in` in wing_osc_fixtures.json is the recorded instance of
the S2.3 ,sfi disagreement (display '1', native 0) and is loaded
automatically by FakeWing(); every test below relies on it rather than
inventing its own disagreeing leaf, so the fixture and the design doc's
own citation of it stay the single source of truth.
"""

from __future__ import annotations

import pytest

import wing_parser.net.snapshot as snapshot_module
from tests.fake_wing import FakeWing
from wing_parser.net.codec import encode
from wing_parser.net.schema import AE_ROOTS, SchemaResult
from wing_parser.net.snapshot import SnapshotResult, take_snapshot
from wing_parser.query.scene import WingScene

FAST = dict(batch_size=200, retry_rounds=1, idle_timeout=0.03)


def _schema_tx(address: str) -> bytes:
    return encode(address, "s", ("?",))


def _schema_rx(address: str, body: str) -> bytes:
    return encode(address, "s", (body,))


def _value_rx(address: str, typetag: str, args: tuple) -> bytes:
    return encode(address, typetag, args)


def _register_empty_roots(fake: FakeWing, skip: set[str]) -> None:
    """Answer every S2.2 ae-data root this module always seeds, except the
    ones a test overrides itself, with "no children" -- so a test can
    assert a clean `unresolved_nodes` instead of the eleven-odd stock
    roots it never cared about drowning out the one address it does."""
    for name in AE_ROOTS:
        if name not in skip:
            fake.register(_schema_tx(f"/{name}"), _schema_rx(f"/{name}", ""))


def _register_minimal_tree(fake: FakeWing) -> None:
    """/ch/1/fdr (,sff), /ch/1/in/conn/in (,sfi, real disagreement
    fixture), and /$ctl/cfg/on (,sfi) -- small enough to assert an exact
    ae/ce dict against, but touching every tag S2.3's rule distinguishes."""
    _register_empty_roots(fake, skip={"ch"})
    fake.register(_schema_tx("/ch"), _schema_rx("/ch", "  1              (node)\n"))
    fake.register(
        _schema_tx("/ch/1"),
        _schema_rx(
            "/ch/1",
            "  fdr            fader [-oo .. 10.0 dB], 1024 steps\n  in             (node)\n",
        ),
    )
    fake.register(_schema_tx("/ch/1/in"), _schema_rx("/ch/1/in", "  conn           (node)\n"))
    fake.register(
        _schema_tx("/ch/1/in/conn"), _schema_rx("/ch/1/in/conn", "  in             int [1 .. 64]\n")
    )
    fake.register(_schema_tx("/$ctl"), _schema_rx("/$ctl", "  cfg            (node)\n"))
    fake.register(_schema_tx("/$ctl/cfg"), _schema_rx("/$ctl/cfg", "  on             int [0 .. 1]\n"))

    fake.register(
        encode("/ch/1/fdr"), _value_rx("/ch/1/fdr", "sff", ("-6.0", 0.5, -6.0))
    )
    # get/ch/1/in/conn/in is already loaded by FakeWing() -- the real
    # recorded ,sfi disagreement (display '1', native 0).
    fake.register(encode("/$ctl/cfg/on"), _value_rx("/$ctl/cfg/on", "sfi", ("1", 1.0, 1)))


def test_snapshot_converts_values_by_the_s2_3_rule_and_routes_ae_ce():
    with FakeWing() as fake:
        _register_minimal_tree(fake)
        host, port = fake.osc_address
        result = take_snapshot(host, port, **FAST)

    assert isinstance(result, SnapshotResult)
    assert result.unresolved_nodes == ()
    assert result.unresolved_leaves == ()

    # ,sff: native float, not the rounded display (S2.3).
    assert result.raw.ae["ch"]["1"]["fdr"] == pytest.approx(-6.0)
    # ,sfi: the DISPLAY int (1), never the 0-based native (0) -- this is
    # the exact leaf design doc S2.3 cites as the recorded disagreement.
    assert result.raw.ae["ch"]["1"]["in"]["conn"]["in"] == 1
    assert isinstance(result.raw.ae["ch"]["1"]["in"]["conn"]["in"], int)
    # /$ctl/... is keyed from *below* $ctl into ce, not ae, and not under
    # a literal "$ctl" key either (S2.2).
    assert result.raw.ce["cfg"]["on"] == 1
    assert "$ctl" not in result.raw.ce
    assert "ctl" not in result.raw.ae
    assert "$ctl" not in result.raw.ae


def test_snapshot_raw_scene_has_no_path_and_a_host_naming_source():
    with FakeWing() as fake:
        _register_minimal_tree(fake)
        host, port = fake.osc_address
        result = take_snapshot(host, port, **FAST)

    assert result.raw.path is None
    assert result.raw.source == f"wing://{host}"


def test_wing_scene_constructs_from_a_snapshot_raw_scene():
    # The round trip is the whole point of this module (design doc S4):
    # a RawScene read live must be exactly as usable as one read from a
    # file, with no special-casing anywhere in query/.
    with FakeWing() as fake:
        _register_minimal_tree(fake)
        host, port = fake.osc_address
        result = take_snapshot(host, port, **FAST)

    scene = WingScene(result.raw)
    assert isinstance(scene, WingScene)
    assert scene.path is None
    assert scene.source == f"wing://{host}"
    assert scene.channel(1).data.fader_dB == pytest.approx(-6.0)


def test_unresolved_nodes_and_leaves_are_reported_not_silently_dropped():
    with FakeWing() as fake:
        _register_empty_roots(fake, skip={"ch"})
        fake.register(
            _schema_tx("/ch"),
            _schema_rx("/ch", "  1              (node)\n  2              (node)\n"),
        )
        fake.register(
            _schema_tx("/ch/1"),
            _schema_rx(
                "/ch/1",
                "  fdr            fader [-oo .. 10.0 dB], 1024 steps\n"
                # "probeleaf" is not one of the 74 recorded fixtures --
                # picked deliberately so FakeWing's stock table can't
                # accidentally answer it and mask the unresolved case.
                "  probeleaf      int [0 .. 1]\n",
            ),
        )
        # /ch/2's shape is never registered -- a whole subtree that never answers.
        # /ch/1/probeleaf's shape resolves but its value never does.
        fake.register(encode("/ch/1/fdr"), _value_rx("/ch/1/fdr", "sff", ("-6.0", 0.5, -6.0)))

        host, port = fake.osc_address
        result = take_snapshot(host, port, **FAST)

    assert "/ch/2" in result.unresolved_nodes
    assert "/ch/1/probeleaf" in result.unresolved_leaves
    # A leaf that never resolved must never appear with a fabricated value.
    assert "probeleaf" not in result.raw.ae["ch"]["1"]
    assert result.raw.ae["ch"]["1"]["fdr"] == pytest.approx(-6.0)


def test_take_snapshot_with_a_supplied_schema_does_not_walk_again(monkeypatch):
    """D-41: a caller that already walked (Console page's Discover) hands
    that SchemaResult in rather than paying for a second walk."""

    def _must_not_walk(*args, **kwargs):
        raise AssertionError("walk_schema must not be called when schema is supplied")

    monkeypatch.setattr(snapshot_module, "walk_schema", _must_not_walk)

    supplied = SchemaResult(
        leaves={"/ch/1/fdr": "fader", "/$ctl/cfg/on": "int"},
        unresolved_nodes=("/ch/2",),
    )

    with FakeWing() as fake:
        # Only the leaf-value endpoints are registered -- no schema query
        # pair at all -- so a code path that still called walk_schema
        # would get no reply and time out rather than silently pass.
        fake.register(encode("/ch/1/fdr"), _value_rx("/ch/1/fdr", "sff", ("-6.0", 0.5, -6.0)))
        fake.register(encode("/$ctl/cfg/on"), _value_rx("/$ctl/cfg/on", "sfi", ("1", 1.0, 1)))
        host, port = fake.osc_address
        result = take_snapshot(host, port, schema=supplied, **FAST)

    assert isinstance(result, SnapshotResult)
    # The supplied schema's own unresolved_nodes reach the result untouched.
    assert result.unresolved_nodes == ("/ch/2",)
    assert result.raw.ae["ch"]["1"]["fdr"] == pytest.approx(-6.0)
    assert result.raw.ce["cfg"]["on"] == 1


def test_take_snapshot_without_a_schema_still_walks_exactly_once(monkeypatch):
    real_walk_schema = snapshot_module.walk_schema
    calls = []

    def _counting_walk_schema(*args, **kwargs):
        calls.append((args, kwargs))
        return real_walk_schema(*args, **kwargs)

    monkeypatch.setattr(snapshot_module, "walk_schema", _counting_walk_schema)

    with FakeWing() as fake:
        _register_minimal_tree(fake)
        host, port = fake.osc_address
        result = take_snapshot(host, port, **FAST)

    assert len(calls) == 1
    assert result.raw.ae["ch"]["1"]["fdr"] == pytest.approx(-6.0)
