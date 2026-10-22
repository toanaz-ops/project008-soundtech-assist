"""One bad datagram must not abort a whole pull / discover / watch
(audit 2026-10-21, finding 3). FakeWing and stub sockets only."""

from __future__ import annotations

import struct

import pytest

from tests.fake_wing import FakeWing
from wing_parser.net import schema
from wing_parser.net.client import WingClient
from wing_parser.net.codec import OscMessage, decode, encode, leaf_value

_FAST = dict(timeout=0.5, idle_timeout=0.05)


def _padded(raw: bytes) -> bytes:
    return raw + b"\x00" * (4 - len(raw) % 4)


def _name_reply(address: str, name: str) -> bytes:
    """A ,s reply whose payload is UTF-8 -- `encode` is ASCII-only, so build it by hand."""
    return _padded(address.encode("ascii")) + _padded(b",s") + _padded(name.encode("utf-8"))


# -- codec ---------------------------------------------------------------


def test_a_non_ascii_name_decodes_instead_of_raising():
    message = decode(_name_reply("/ch/1/name", "Đàn bầu"))

    assert message.address == "/ch/1/name"
    value, _display = leaf_value(message)
    assert value == "Đàn bầu"


def test_undecodable_bytes_become_replacement_characters_not_an_exception():
    raw = _padded(b"/ch/1/name") + _padded(b",s") + _padded(b"Vo\xff\xfeng")

    value, _display = leaf_value(decode(raw))

    assert value.startswith("Vo") and value.endswith("ng") and "\ufffd" in value


def test_a_truncated_sff_raises_a_catchable_error_not_garbage():
    whole = encode("/ch/1/fdr", "sff", ("-6.0", 0.0, -6.0))

    with pytest.raises((ValueError, struct.error)):
        decode(whole[:-2])


# -- client --------------------------------------------------------------


def test_one_truncated_datagram_does_not_abort_get_many():
    bad, good = "/ch/1/fdr", "/ch/2/fdr"
    with FakeWing() as fake:
        fake.register(encode(bad), encode(bad, "sff", ("-6.0", 0.0, -6.0))[:-2])
        fake.register(encode(good), encode(good, "sff", ("-3.0", 0.0, -3.0)))
        host, port = fake.osc_address
        with WingClient(host, port, **_FAST) as client:
            result = client.get_many([bad, good], retry_rounds=1)

    assert set(result.replies) == {good}
    assert result.unresolved == (bad,)


def test_a_stray_non_ascii_datagram_is_kept_not_fatal():
    address = "/ch/1/name"
    with FakeWing() as fake:
        fake.register(encode(address), _name_reply(address, "Đài"))
        host, port = fake.osc_address
        with WingClient(host, port, **_FAST) as client:
            result = client.get_many([address], retry_rounds=0)

    assert leaf_value(result.replies[address])[0] == "Đài"


class _ResettingSocket:
    """recvfrom raises what Windows raises after an ICMP port-unreachable."""

    def settimeout(self, _value):
        pass

    def sendto(self, _data, _addr):
        return 0

    def recvfrom(self, _size):
        raise ConnectionResetError(10054, "forcibly closed by the remote host")

    def close(self):
        pass


def test_a_connection_reset_is_a_miss_in_get_many_and_request(monkeypatch):
    monkeypatch.setattr(WingClient, "_new_socket", lambda self: _ResettingSocket())
    with WingClient("127.0.0.1", 9, **_FAST) as client:
        assert client.request("/ch/1/fdr") is None
        result = client.get_many(["/ch/1/fdr", "/ch/2/fdr"], retry_rounds=1)

    assert result.replies == {}
    assert set(result.unresolved) == {"/ch/1/fdr", "/ch/2/fdr"}


def test_a_malformed_reply_to_request_is_none_not_a_raise():
    address = "/ch/1/fdr"
    with FakeWing() as fake:
        fake.register(encode(address), encode(address, "sff", ("-6.0", 0.0, -6.0))[:-2])
        host, port = fake.osc_address
        with WingClient(host, port, **_FAST) as client:
            assert client.request(address) is None


# -- schema --------------------------------------------------------------


def test_an_address_only_schema_reply_names_no_children_instead_of_raising():
    leaves: dict[str, str] = {}
    replies = {
        "/ch": OscMessage(address="/ch", typetag="", args=()),
        "/bus": OscMessage(address="/bus", typetag="s",
                           args=("  fdr            fader [-oo .. 10.0 dB], 1024 steps\n",)),
    }

    frontier = schema._expand(replies, leaves)

    assert frontier == []
    assert leaves == {"/bus/fdr": "fader [-oo .. 10.0 dB], 1024 steps"}
