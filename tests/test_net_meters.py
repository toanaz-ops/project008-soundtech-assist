"""Meter reader tests -- fake sockets only, no real network."""

import pytest

from wing_parser.net.meters import MeterReader
from wing_parser.net.meters_protocol import (
    FAMILY_CHANNEL, FAMILY_FX, decode_meter_packet, encode_meter_request,
    encode_port_request, encode_renew)

DOC_PACKET = bytes.fromhex("00000002" "9bb2" "9bb2" "8000" "8000"
                           "9b7c" "0000" "8000" "0000")


class FakeUdp:
    def __init__(self):
        self.queue = []

    def recvfrom(self, size):
        if not self.queue:
            raise BlockingIOError
        return self.queue.pop(0), ("1.2.3.4", 2222)


class Clock:
    def __init__(self):
        self.t = 100.0

    def __call__(self):
        return self.t


def test_port_request_doc_example():
    assert encode_port_request(14135) == bytes.fromhex("dfd3d33737dfd1")


def test_port_request_escapes_df_byte():
    assert encode_port_request(0xDF01)[3:6] == bytes.fromhex("dfde01")


def test_meter_request_doc_example():
    out = encode_meter_request(2, [(FAMILY_CHANNEL, [1, 2, 9]), (FAMILY_FX, [5])])
    assert out == bytes.fromhex("dfd3d400000002dca0000108a604dedfd1")


def test_single_channel_request_matches_doc_sequence():
    assert encode_meter_request(2, [(FAMILY_CHANNEL, [2])]) == bytes.fromhex(
        "dfd3d400000002dca001dedfd1")


def test_renew_doc_example_and_id_escape():
    assert encode_renew(2) == bytes.fromhex("dfd3d400000002dfd1")
    assert b"\xdf\xde" in encode_renew(0xDF)


def test_index_out_of_range_rejected():
    with pytest.raises(ValueError):
        encode_meter_request(1, [(FAMILY_CHANNEL, [0])])


def test_decode_doc_buffer():
    frame = decode_meter_packet(DOC_PACKET)
    assert frame.report_id == 2
    rec = frame.records[0]
    assert rec["in_l"] == -100.3046875 and rec["in_r"] == -100.3046875
    assert rec["out_l"] is None and rec["out_r"] is None
    assert rec["gate_key"] == (0x9B7C - 0x10000) / 256
    assert rec["gate_gain"] == 0.0 and rec["dyn_key"] is None


def test_decode_rejects_bad_length():
    with pytest.raises(ValueError):
        decode_meter_packet(DOC_PACKET[:-2])


def test_subscribe_poll_and_staleness():
    sent, udp, clock = [], FakeUdp(), Clock()
    reader = MeterReader(sent.append, udp, 14135, clock, report_id=2)
    assert reader.is_stale()
    reader.subscribe([5])
    assert sent[0] == encode_port_request(14135)
    assert sent[1] == encode_meter_request(2, [(FAMILY_CHANNEL, [5])])
    udp.queue += [b"junk", DOC_PACKET]
    meters = reader.poll()
    assert meters[5].in_l == -100.3046875 and meters[5].out_l is None
    clock.t += 0.9
    assert not reader.is_stale()
    clock.t += 0.2
    assert reader.is_stale()


def test_renew_timing_and_foreign_report_ignored():
    sent, udp, clock = [], FakeUdp(), Clock()
    reader = MeterReader(sent.append, udp, 14135, clock, report_id=2)
    reader.subscribe([1])
    clock.t += 2.9
    assert not reader.renew_if_due()
    clock.t += 0.2
    assert reader.renew_if_due() and sent[-1] == encode_renew(2)
    assert not reader.renew_if_due()
    udp.queue.append(b"\x00\x00\x00\x09" + DOC_PACKET[4:])
    assert reader.poll() == {}
