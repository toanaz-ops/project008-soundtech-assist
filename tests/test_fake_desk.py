"""Tests for `FakeDesk`, the only "desk" any wave-2 test ever sees.

No socket, no bytes: `_FakeClient.get_many` must hand back a real
`net.client.BatchResult` holding real `net.codec.OscMessage` objects,
built the same way spec S9.1 and the task-1 brief spell out.
"""

from __future__ import annotations

from wing_parser.net.client import BatchResult
from wing_parser.net.codec import OscMessage, leaf_value
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
    desk = FakeDesk(rounds=[round_one, round_two])
    client = desk.client()

    first = client.get_many(["/ch/1/$fdr"])
    second = client.get_many(["/ch/1/$fdr"])

    assert first.replies["/ch/1/$fdr"] is round_one["/ch/1/$fdr"]
    assert second.replies["/ch/1/$fdr"] is round_two["/ch/1/$fdr"]


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
