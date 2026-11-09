"""D-52 #3: `live_write._read`, the REAL transport's one-leaf read.

No socket: `WingClient` is replaced by a stub that records what it was
asked and answers with a canned `OscMessage` (or silence). The tests pin the
existing behaviour -- the real desk is still on the section 9.3 acceptance
list.
"""
from __future__ import annotations

import pytest

from wing_parser.net.codec import OscMessage
from wing_parser.ui import live_write

HOST = "192.168.128.28"
BOOL_PATH = "ae_data.ch.1.in.set.inv"      # boolean shape in wing_jsontypes.yaml
BOOL_OSC = "/ch/1/in/set/inv"
FLOAT_PATH = "ae_data.ch.1.fdr"
FLOAT_OSC = "/ch/1/fdr"


class _StubClient:
    reply: OscMessage | None = None
    calls: list = []
    closed = 0

    def __init__(self, host):
        type(self).calls.append(("host", host))

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        type(self).closed += 1

    def request(self, address, *args, **kwargs):
        type(self).calls.append(("request", address))
        return type(self).reply


@pytest.fixture
def stub(monkeypatch):
    _StubClient.reply = None
    _StubClient.calls = []
    _StubClient.closed = 0
    monkeypatch.setattr(live_write, "WingClient", _StubClient)
    return _StubClient


def test_read_normalises_a_bool_leaf_like_the_write_path(stub):
    # ,sfi leaf: display string "1" parses to int 1; the scene holds a bool.
    stub.reply = OscMessage(BOOL_OSC, "sfi", ("1", 0.0, 1))
    value = live_write._read(HOST, BOOL_PATH)
    assert value is True
    assert stub.calls == [("host", HOST), ("request", BOOL_OSC)]
    assert stub.closed == 1


def test_read_returns_a_non_bool_leaf_unchanged(stub):
    stub.reply = OscMessage(FLOAT_OSC, "sff", ("-6.0", 0.0, -6.0))
    assert live_write._read(HOST, FLOAT_PATH) == pytest.approx(-6.0)


def test_read_returns_none_when_the_desk_does_not_answer(stub):
    stub.reply = None
    assert live_write._read(HOST, BOOL_PATH) is None
    assert stub.closed == 1   # the client is released on silence too


def test_real_transport_wires_read_to_this_function():
    assert live_write.REAL.read is live_write._read
