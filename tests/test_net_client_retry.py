"""The retry ladder has to serve two opposite cases without a flag.

A *poisoned* batch is one bad request taking its innocent neighbours down
with it: halving the chunk size and rotating the port isolates the culprit
and recovers the rest. An *absent* set is thousands of addresses that will
never answer because the console does not have them -- a rack with no
StageConnect device, or a WEDIT layer WING-Edit never created here.

Bisecting an absent set is pure cost. Measured before the no-progress
guard existed: pushing a scene authored elsewhere drove the ladder to
chunk size 1 and paid an idle timeout per address, running past two
minutes where the writes themselves take 1.1 seconds.
"""

from __future__ import annotations

import time

import pytest

from tests.fake_wing import FakeWing
from wing_parser.net.client import WingClient
from wing_parser.net.codec import encode

FAST = dict(timeout=0.5, idle_timeout=0.02)


def _silent(fake, addresses):
    for address in addresses:
        fake.register(encode(address), None)


def test_a_large_absent_set_stops_instead_of_bisecting_to_one():
    """The guard is a time bound, so assert on time -- but generously, so
    the test pins the behaviour rather than the machine's speed. With the
    ladder running to chunk size 1 this takes idle_timeout per address."""
    addresses = [f"/nosuch/{n}/fdr" for n in range(400)]
    with FakeWing() as fake:
        _silent(fake, addresses)
        host, port = fake.osc_address
        with WingClient(host, port, **FAST) as client:
            started = time.monotonic()
            result = client.get_many(addresses, batch_size=200, retry_rounds=8)
            elapsed = time.monotonic() - started

    assert set(result.unresolved) == set(addresses)
    assert not result.replies
    # 400 addresses at chunk size 1 would be 400 idle waits. Two rounds'
    # worth of chunked waits is the intended cost.
    assert elapsed < 2.0, f"retry ladder did not stop early: {elapsed:.2f}s"


def test_a_round_that_recovers_something_keeps_going():
    """The guard must not fire while progress is still being made, or a
    genuinely poisoned batch would never be isolated."""
    good = [f"/ch/{n}/fdr" for n in range(1, 9)]
    with FakeWing() as fake:
        for address in good:
            fake.register(encode(address), encode(address, "sff", ("0.0", 0.75, 0.0)))
        _silent(fake, ["/ch/99/fdr"])
        host, port = fake.osc_address
        with WingClient(host, port, **FAST) as client:
            result = client.get_many(good + ["/ch/99/fdr"], batch_size=200, retry_rounds=8)

    assert set(result.replies) == set(good)
    assert result.unresolved == ("/ch/99/fdr",)


def test_everything_answering_costs_no_retry_at_all():
    good = [f"/ch/{n}/fdr" for n in range(1, 5)]
    with FakeWing() as fake:
        for address in good:
            fake.register(encode(address), encode(address, "sff", ("0.0", 0.75, 0.0)))
        host, port = fake.osc_address
        before = fake.osc_packets_received
        with WingClient(host, port, **FAST) as client:
            result = client.get_many(good, batch_size=200, retry_rounds=8)
        sent = fake.osc_packets_received - before

    assert set(result.replies) == set(good)
    assert result.unresolved == ()
    assert sent == len(good), "a fully answered batch must not be retried"
