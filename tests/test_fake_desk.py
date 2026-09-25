"""Tests for `FakeDesk`, the only "desk" any wave-2 test ever sees.

No socket, no bytes: `_FakeClient.get_many` must hand back a real
`net.client.BatchResult` holding real `net.codec.OscMessage` objects,
built the same way spec S9.1 and the task-1 brief spell out.
"""

from __future__ import annotations

import pytest

from wing_parser.net.client import BatchResult
from wing_parser.net.codec import OscMessage, leaf_value
from wing_parser.net.identity import WingIdentity
from wing_parser.net.snapshot import SnapshotResult
from wing_parser.net.watch.list import WatchList
from tests.fake_desk import FakeDesk


def test_get_many_returns_real_batchresult_objects():
    leaves = {
        "/ch/1/$fdr": OscMessage("/ch/1/$fdr", "sff", ("-6.0", 0.5, -6.0)),
        "/ch/1/name": OscMessage("/ch/1/name", "s", ("KICK",)),
        "/ch/1/col": OscMessage("/ch/1/col", "sfi", ("1", 0.0, 0)),
    }
    desk = FakeDesk(leaves=leaves)

    with desk.client() as client:
        result = client.get_many(
            ["/ch/1/$fdr", "/ch/1/name", "/ch/1/col", "/ch/99/missing"]
        )

    assert isinstance(result, BatchResult)
    assert isinstance(result.replies["/ch/1/$fdr"], OscMessage)
    assert leaf_value(result.replies["/ch/1/$fdr"]) == (-6.0, "-6.0")
    assert leaf_value(result.replies["/ch/1/name"]) == ("KICK", "KICK")
    assert leaf_value(result.replies["/ch/1/col"]) == (1, "1")
    assert result.unresolved == ("/ch/99/missing",)


def test_a_scripted_round_is_consumed_once_per_get_many():
    round_one = {"/ch/1/$fdr": OscMessage("/ch/1/$fdr", "sff", ("-3.0", 0.6, -3.0))}
    round_two = {"/ch/1/$fdr": OscMessage("/ch/1/$fdr", "sff", ("0.0", 0.75, 0.0))}
    # A round that answers some addresses still falls back to `leaves` for
    # the rest -- only a round the desk IGNORED (an empty dict, below)
    # answers nothing at all.
    desk = FakeDesk(
        leaves={"/ch/2/$fdr": OscMessage("/ch/2/$fdr", "sff", ("-9.0", 0.4, -9.0))},
        rounds=[round_one, round_two],
    )
    client = desk.client()

    first = client.get_many(["/ch/1/$fdr", "/ch/2/$fdr"])
    second = client.get_many(["/ch/1/$fdr", "/ch/2/$fdr"])

    assert first.replies["/ch/1/$fdr"] is round_one["/ch/1/$fdr"]
    assert second.replies["/ch/1/$fdr"] is round_two["/ch/1/$fdr"]
    assert first.replies["/ch/2/$fdr"] is desk.leaves["/ch/2/$fdr"]
    assert second.replies["/ch/2/$fdr"] is desk.leaves["/ch/2/$fdr"]


def test_an_empty_scripted_round_answers_nothing():
    # A round the desk IGNORED, per the task-1 brief: no replies at all,
    # every requested address unresolved -- NOT a fallback to `leaves`.
    # The second desk below is the no-rounds case, for contrast: same
    # leaves, same request, an answer.
    leaf = OscMessage("/ch/1/$fdr", "sff", ("-6.0", 0.5, -6.0))
    ignored = FakeDesk(leaves={"/ch/1/$fdr": leaf}, rounds=[{}])
    answering = FakeDesk(leaves={"/ch/1/$fdr": leaf})

    silent = ignored.client().get_many(["/ch/1/$fdr", "/ch/2/$fdr"])
    answered = answering.client().get_many(["/ch/1/$fdr", "/ch/2/$fdr"])

    assert silent.replies == {}
    assert silent.unresolved == ("/ch/1/$fdr", "/ch/2/$fdr")
    assert answered.replies == {"/ch/1/$fdr": leaf}
    assert answered.unresolved == ("/ch/2/$fdr",)


def test_an_exhausted_round_list_repeats_its_last_entry():
    only_round = {"/ch/1/$fdr": OscMessage("/ch/1/$fdr", "sff", ("-6.0", 0.5, -6.0))}
    desk = FakeDesk(rounds=[only_round])
    client = desk.client()

    results = [client.get_many(["/ch/1/$fdr"]) for _ in range(3)]

    assert all(
        result.replies["/ch/1/$fdr"] is only_round["/ch/1/$fdr"] for result in results
    )


def test_calls_records_the_address_count_of_every_round():
    desk = FakeDesk()
    client = desk.client()

    client.get_many(["/a", "/b", "/c"])
    client.get_many(["/x"])

    assert desk.calls == [("get_many", 3), ("get_many", 1)]


def test_transport_builds_the_four_callables_from_the_desks_own_fields():
    identity = WingIdentity(
        ip="192.168.128.28",
        name="WING-GIAQUY",
        model="wing-rack",
        serial="01009Y90604AAE",
        firmware="3.1-0-g9f314617:release",
    )
    desk = FakeDesk(
        identity=identity,
        leaves={
            "/ch/1/name": OscMessage("/ch/1/name", "s", ("KICK",)),
            "/$ctl/cfg/dark": OscMessage("/$ctl/cfg/dark", "sfi", ("1", 0.0, 0)),
        },
        unresolved=("/mtx",),
        strips={"ch": 1},
    )
    transport = desk.transport()

    assert transport.identity("192.168.128.28") is identity

    walked = transport.walk("192.168.128.28")
    assert type(walked) is WatchList
    assert walked.addresses == ("/ch/1/name", "/$ctl/cfg/dark")
    assert walked.unresolved == ("/mtx",)
    assert walked.strips == {"ch": 1}

    pulled = transport.snapshot("192.168.128.28")
    assert type(pulled) is SnapshotResult
    # Decoded by the real `leaf_value` and filed by the real `_place`, so
    # `/$ctl/...` lands in ce_data keyed from below $ctl, per net S2.2.
    assert pulled.raw.ae == {"ch": {"1": {"name": "KICK"}}}
    assert pulled.raw.ce == {"cfg": {"dark": 1}}
    assert pulled.raw.source == "wing://192.168.128.28"
    assert pulled.unresolved_nodes == ("/mtx",)
    assert pulled.unresolved_leaves == ()

    with transport.client("192.168.128.28") as client:
        assert client.get_many(["/ch/1/name"]).replies["/ch/1/name"] is (
            desk.leaves["/ch/1/name"]
        )


def test_walk_and_snapshot_derive_from_a_supplied_schema_not_live_leaves():
    """I2 (D-41 fix round): a schema someone hands in (a `SchemaCache`
    round trip) must determine what `_walk`/`_snapshot` see -- mirroring
    `build_watch_list`/`take_snapshot`, which read `schema.leaves` rather
    than re-deriving from the desk. Without this, a stale or cross-desk
    schema can never actually show up against this double, and the C1/I1
    regression tests would not be real."""
    from wing_parser.net.schema import SchemaResult

    desk = FakeDesk(
        leaves={
            "/ch/1/name": OscMessage("/ch/1/name", "s", ("KICK",)),
            "/ch/2/name": OscMessage("/ch/2/name", "s", ("SNARE",)),
        },
    )
    # A schema from an earlier, smaller/incomplete walk -- as if it were
    # reused here instead of a fresh one.
    stale = SchemaResult(leaves={"/ch/1/name": "s"}, unresolved_nodes=("/mtx",))

    walked = desk.transport().walk("HOST", schema=stale)
    assert walked.addresses == ("/ch/1/name",), "must come from schema, not desk.leaves"
    assert walked.unresolved == ("/mtx",)

    pulled = desk.transport().snapshot("HOST", schema=stale)
    assert pulled.raw.ae == {"ch": {"1": {"name": "KICK"}}}, "only the schema's leaf was read"
    assert pulled.unresolved_nodes == ("/mtx",)
    # No new walk counted -- a schema was already supplied both times.
    assert desk.walks == []


def test_transport_identity_raises_the_exception_the_desk_was_given():
    refused = TimeoutError("no WING? reply from 10.0.0.9:2222 within 2.0s")
    desk = FakeDesk(identity=refused)

    with pytest.raises(TimeoutError) as caught:
        desk.transport().identity("10.0.0.9")

    assert caught.value is refused
