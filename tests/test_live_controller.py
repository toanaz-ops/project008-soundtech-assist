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
import json
import re
from pathlib import Path

import pytest

from tests.fake_desk import FakeDesk
from wing_parser.edit import pointer
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
    session_from_snapshot,
    suggested_name,
)
from wing_parser.ui.session import Session

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


def _desk_holding(snap_path: Path) -> FakeDesk:
    """A `FakeDesk` whose surface is a real `.snap` file, leaf by leaf.

    The point of the parity tests is that a pulled scene is not a
    near-miss of a file-loaded one, so the desk has to answer with the
    real file's 28 559 leaves rather than a hand-picked handful. Each JSON
    leaf becomes the OSC reply a console would send for it, following
    `codec.leaf_value`'s per-tag rule (`codec.py:107-135`): `,s` for a
    string, `,sfi` for an int or a bool -- WING's wire never distinguishes
    the two (`net/export.py:3-9`), which is exactly why `to_snap_json` has
    a boolean oracle to put the `bool`s back -- and `,sff` for a float,
    whose native value is the last argument.
    """
    document = json.loads(snap_path.read_text(encoding="utf-8"))
    leaves: dict[str, OscMessage] = {}

    def collect(node, parts: list[str]) -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                collect(value, parts + [key])
            return
        address = "/" + "/".join(parts)
        if isinstance(node, bool):
            leaves[address] = OscMessage(address, "sfi", (str(int(node)), 0.0, int(node)))
        elif isinstance(node, int):
            leaves[address] = OscMessage(address, "sfi", (str(node), 0.0, node))
        elif isinstance(node, float):
            leaves[address] = OscMessage(address, "sff", (str(node), 0.0, node))
        else:
            leaves[address] = OscMessage(address, "s", (node,))

    collect(document.get("ae_data") or {}, [])
    # ce_data's top-level keys are $ctl's children, not $ctl itself, so the
    # segment has to go back on to make an address (net S2.2, the rule
    # `snapshot._place` strips on the way in).
    collect(document.get("ce_data") or {}, ["$ctl"])
    return FakeDesk(leaves=leaves)


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


@pytest.fixture
def vu_desk(vu_path, monkeypatch) -> FakeDesk:
    """A desk answering exactly what `user-files/example-Vu.snap` holds."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return _desk_holding(vu_path)


def test_a_pulled_session_carries_findings_and_channels_like_an_opened_file(
    vu_desk, vu_path
):
    pulled, _original = session_from_snapshot(pull(HOST, vu_desk.transport()), GIAQUY)
    opened = Session.open(vu_path)

    # Non-empty first, so neither half can agree with the other by both
    # being empty -- the way a parity test passes vacuously.
    assert pulled.findings()
    assert pulled.scene.channels()
    # Then identical: same findings, same channels, as the wave claims.
    assert sorted((f.rule_id, f.target) for f in pulled.findings()) == sorted(
        (f.rule_id, f.target) for f in opened.findings()
    )
    assert [c.name for c in pulled.scene.channels()] == [
        c.name for c in opened.scene.channels()
    ]


def test_export_writes_the_repaired_document_not_the_pull_time_bytes(
    vu_desk, tmp_path
):
    session, original = session_from_snapshot(pull(HOST, vu_desk.transport()), GIAQUY)
    target = next(f for f in session.findings() if f.rule_id == "G8")

    assert session.repair(target) is True
    patch = session.changes()[0]
    out = tmp_path / "out.snap"
    session.save_as(out)

    # The repair is in the exported file, and the finding it cleared is
    # gone when that file is reopened as an ordinary scene.
    written = json.loads(out.read_text(encoding="utf-8"))
    assert pointer.read(written, patch.path) == patch.after
    assert not [
        finding
        for finding in Session.open(out).findings()
        if (finding.rule_id, finding.target) == (target.rule_id, target.target)
    ]
    # And still absent from the pull-time original (D3): exporting those
    # bytes instead of `save_as` would have silently dropped the repair.
    assert pointer.read(json.loads(original), patch.path) == patch.before
    assert patch.before != patch.after


def test_suggested_name_uses_the_desk_name_when_identity_is_known():
    assert re.fullmatch(r"WING-GIAQUY-\d{8}-\d{4}\.snap", suggested_name(GIAQUY, HOST))


def test_suggested_name_falls_back_to_the_host_without_identity():
    assert re.fullmatch(
        r"wing-192\.168\.128\.28-\d{8}-\d{4}\.snap", suggested_name(None, HOST)
    )


def test_the_suggested_name_is_a_bare_filename_with_no_directory():
    # D4: it names nothing on disk. Both forms, because the fallback
    # interpolates a host the operator typed.
    for name in (suggested_name(GIAQUY, HOST), suggested_name(None, HOST)):
        assert Path(name).name == name
        assert Path(name).parent == Path(".")
        assert not Path(name).is_absolute()
