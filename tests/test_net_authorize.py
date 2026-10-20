"""`write._authorize` asks the desk for its identity only when a serial pin is
set (audit 2026-10-21, finding 4). FakeWing only; nothing leaves loopback."""

from __future__ import annotations

import pytest

from tests.fake_wing import FakeWing
from wing_parser.net import write
from wing_parser.net.codec import encode

_FAST = dict(timeout=0.5)
_ADDRESS = "/ch/40/fdr"


def _run(fake, **kwargs):
    host, osc_port = fake.osc_address
    _, identity_port = fake.identity_address
    return write.set(host, _ADDRESS, -6.0, osc_port=osc_port,
                     identity_port=identity_port, confirm=True, **_FAST, **kwargs)


def _register(fake):
    fake.register(encode(_ADDRESS, "s", ("-6.0",)), None)
    fake.register(encode(_ADDRESS), encode(_ADDRESS, "sff", ("-6.0", 0.0, -6.0)))


def test_a_confirmed_set_sends_zero_identity_packets_without_a_serial_pin(monkeypatch):
    monkeypatch.delenv("WING_WRITE_ALLOW_SERIAL", raising=False)
    with FakeWing() as fake:
        _register(fake)

        result = _run(fake)

        assert fake.identity_packets_received == 0
        assert fake.osc_packets_received == 2     # the SET and its read-back GET
    assert result.matched is True


def test_an_empty_serial_pin_counts_as_unset(monkeypatch):
    monkeypatch.setenv("WING_WRITE_ALLOW_SERIAL", "")
    with FakeWing() as fake:
        _register(fake)

        _run(fake)

        assert fake.identity_packets_received == 0


def test_a_serial_pin_still_queries_identity_exactly_once_and_refuses_a_mismatch(monkeypatch):
    monkeypatch.setenv("WING_WRITE_ALLOW_SERIAL", "SOME-OTHER-SERIAL")
    with FakeWing() as fake:
        _register(fake)

        with pytest.raises(write.SerialMismatchError):
            _run(fake)

        assert fake.identity_packets_received == 1
        assert fake.osc_packets_received == 0     # refused before the SET


def test_node_write_and_push_also_skip_the_identity_query_without_a_pin(monkeypatch):
    monkeypatch.delenv("WING_WRITE_ALLOW_SERIAL", raising=False)
    with FakeWing() as fake:
        host, osc_port = fake.osc_address
        _, identity_port = fake.identity_address

        write.push(host, {_ADDRESS: -6.0}, osc_port=osc_port,
                   identity_port=identity_port, confirm=True, **_FAST)
        write.node_write(host, "/ch/40", {"fdr": -6.0}, osc_port=osc_port,
                         identity_port=identity_port, confirm=True, **_FAST)

        assert fake.identity_packets_received == 0
