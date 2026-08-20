"""Tests for wing_parser.net.client, driven only against tests/fake_wing.py
-- no test here touches a real socket to a real console (design doc sec 7).

Timeouts throughout are kept short (well under a second) so a genuinely
silent address costs the suite milliseconds, not seconds: the module's own
defaults (2.0s request timeout, 0.2s idle gap) are sized for a real desk on
a real network, not for a loopback fake that never has anything in flight.
"""

from __future__ import annotations

import pytest

from tests.fake_wing import FakeWing
from wing_parser.net.client import BatchResult, WingClient
from wing_parser.net.codec import encode, leaf_value

_FAST = dict(timeout=0.5, idle_timeout=0.05)


def test_request_against_a_recorded_fixture_returns_the_decoded_value():
    # get/ch/1/fdr in wing_osc_fixtures.json: display "-42.3", native float
    # bit-exact per design doc sec 2.3 / test_net_codec.py.
    with FakeWing() as fake:
        host, port = fake.osc_address
        with WingClient(host, port, **_FAST) as client:
            message = client.request("/ch/1/fdr")

    assert message is not None
    assert message.address == "/ch/1/fdr"
    native, display = leaf_value(message)
    assert display == "-42.3"
    assert native == pytest.approx(-42.316715240478516)


def test_request_to_a_silent_address_returns_none_and_does_not_raise():
    # get/ch/99/fdr is one of the fixture file's three deliberate no-reply
    # cases (design doc sec 7) -- exactly the sec 2.4(b) "missing address"
    # hazard, which must be silent-but-harmless, never an exception.
    with FakeWing() as fake:
        host, port = fake.osc_address
        with WingClient(host, port, **_FAST) as client:
            message = client.request("/ch/99/fdr")

    assert message is None


def test_get_many_resolves_every_address_matching_by_address_not_position():
    # Six real fixture addresses spread across ch/dca/bus, requested as one
    # pipelined batch. get_many() matches replies to requests by OSC address
    # (they can land in any order over UDP -- nothing here sends them one at
    # a time), so this only passes if the implementation actually keys off
    # `message.address` rather than assuming replies come back in send order.
    addresses = [
        "/ch/1/fdr",
        "/ch/1/mute",
        "/ch/1/name",
        "/ch/1/pan",
        "/dca/1/fdr",
        "/bus/1/fdr",
    ]
    with FakeWing() as fake:
        host, port = fake.osc_address
        with WingClient(host, port, **_FAST) as client:
            result = client.get_many(addresses)

    assert isinstance(result, BatchResult)
    assert result.unresolved == ()
    assert set(result.replies) == set(addresses)
    for address in addresses:
        assert result.replies[address].address == address

    fdr_native, fdr_display = leaf_value(result.replies["/ch/1/fdr"])
    assert fdr_display == "-42.3"
    assert fdr_native == pytest.approx(-42.316715240478516)

    mute_native, _ = leaf_value(result.replies["/ch/1/mute"])
    assert mute_native == 1
    assert isinstance(mute_native, int)


def test_get_many_recovers_from_a_silent_address_mid_batch_via_retry():
    # This is the case sec 2.4(b) exists for. fake_wing can't reproduce the
    # actual cascading poison (it answers each datagram independently), but
    # it can reproduce the client-observable symptom -- a batch that comes
    # back short -- which is all get_many() ever has to react to: it must
    # rotate to a fresh socket and resend whatever didn't answer, and the
    # other four addresses must resolve regardless of where the silent one
    # sat in the batch.
    silent_address = "/ch/40/zzz"  # already a registered no-reply fixture
    addresses = ["/ch/1/fdr", "/ch/1/mute", silent_address, "/ch/1/pan", "/dca/1/fdr"]

    with FakeWing() as fake:
        host, port = fake.osc_address
        packets_before = fake.osc_packets_received
        with WingClient(host, port, **_FAST) as client:
            result = client.get_many(addresses, retry_rounds=2)
        packets_after = fake.osc_packets_received

    # 5 requests on the first pass, plus one resend of the lone straggler
    # per retry round -- proof the retry path actually fired, not just that
    # the final answer looks right.
    assert packets_after - packets_before >= len(addresses) + 1

    assert result.unresolved == (silent_address,)
    assert set(result.replies) == set(addresses) - {silent_address}
    for address in result.replies:
        assert result.replies[address].address == address


def test_unresolved_address_is_reported_distinct_from_an_empty_success():
    # design task requirement: "this address does not exist" (unresolved)
    # must never be confused with "it replied with nothing interesting"
    # (present in .replies, just an address-only / empty-args message).
    empty_ok_address = "/probe/empty_ok"
    silent_address = "/probe/never_answers"
    with FakeWing() as fake:
        # A bare address-only reply -- codec.decode()'s older OSC form
        # (S2.1) -- is a real, successful, argument-less answer.
        fake.register(encode(empty_ok_address), encode(empty_ok_address))
        fake.register(encode(silent_address), None)

        host, port = fake.osc_address
        with WingClient(host, port, **_FAST) as client:
            result = client.get_many([empty_ok_address, silent_address], retry_rounds=1)

    assert empty_ok_address in result.replies
    reply = result.replies[empty_ok_address]
    assert reply.typetag == ""
    assert reply.args == ()

    assert silent_address not in result.replies
    assert result.unresolved == (silent_address,)


def test_get_many_with_no_addresses_returns_an_empty_result_without_sending():
    with FakeWing() as fake:
        host, port = fake.osc_address
        packets_before = fake.osc_packets_received
        with WingClient(host, port, **_FAST) as client:
            result = client.get_many([])
        packets_after = fake.osc_packets_received

    assert result == BatchResult(replies={}, unresolved=())
    assert packets_after == packets_before


def test_client_is_reusable_as_a_context_manager_and_closes_its_socket():
    with FakeWing() as fake:
        host, port = fake.osc_address
        with WingClient(host, port, **_FAST) as client:
            assert client.request("/ch/1/fdr") is not None
        # Socket is closed on exit; sending on it now must fail loudly
        # rather than silently doing nothing.
        with pytest.raises(OSError):
            client.request("/ch/1/fdr")
