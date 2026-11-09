"""EXPERIMENTAL WING native-protocol meter reader (not OSC: OSC has no meters).

Status: UNVERIFIED on a real desk; OFF by default; acceptance pending (HW-192).
UNVERIFIED points:
  * request transport (TCP native channel vs UDP 2222) -- caller injects it;
  * V2 channel layout (stride 11) -- only V1 (stride 8) is implemented;
  * pre/post-fader tap, mixed-family layout, multiple collections;
  * safe write rate (none documented; this reader only sends renews).
Meter data flows to our UDP port for 5 s per request; renew every 3 s.
Sockets are injected so tests never open one.
"""

from __future__ import annotations

import socket
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from wing_parser.net.meters_protocol import (
    CHANNEL_V1, FAMILY_CHANNEL, decode_meter_packet, encode_meter_request,
    encode_port_request, encode_renew)

RENEW_INTERVAL_S = 3.0
DEFAULT_REPORT_ID = 1


class _UdpLike(Protocol):
    def recvfrom(self, bufsize: int) -> tuple[bytes, object]: ...


@dataclass(frozen=True)
class ChannelMeters:
    in_l: float | None
    in_r: float | None
    out_l: float | None
    out_r: float | None
    gate_key: float | None
    gate_gain: float | None
    dyn_key: float | None
    dyn_gain: float | None


class MeterReader:
    def __init__(self, control_send: Callable[[bytes], None], udp_socket: _UdpLike,
                 udp_port: int, clock: Callable[[], float] = time.monotonic,
                 report_id: int = DEFAULT_REPORT_ID) -> None:
        self._send, self._sock, self._port = control_send, udp_socket, udp_port
        self._clock, self._report_id = clock, report_id
        self._channels: list[int] = []
        self._last_renew: float | None = None
        self._last_rx: float | None = None
        self._latest: dict[int, ChannelMeters] = {}

    def subscribe(self, channels: list[int]) -> None:
        self._channels = list(channels)
        self._latest = {}
        self._send(encode_port_request(self._port))
        self._send(encode_meter_request(
            self._report_id, [(FAMILY_CHANNEL, self._channels)]))
        self._last_renew = self._clock()

    def renew_if_due(self) -> bool:
        now = self._clock()
        if self._last_renew is None or now - self._last_renew < RENEW_INTERVAL_S:
            return False
        self._send(encode_renew(self._report_id))
        self._last_renew = now
        return True

    def poll(self) -> dict[int, ChannelMeters]:
        while True:
            try:
                data, _ = self._sock.recvfrom(4096)
            except (BlockingIOError, TimeoutError):
                break
            try:
                frame = decode_meter_packet(data, CHANNEL_V1)
            except ValueError:
                continue
            if (frame.report_id != self._report_id
                    or len(frame.records) != len(self._channels)):
                continue
            self._latest = {ch: ChannelMeters(**rec)
                            for ch, rec in zip(self._channels, frame.records)}
            self._last_rx = self._clock()
        return dict(self._latest)

    def is_stale(self, max_age: float = 1.0) -> bool:
        return self._last_rx is None or self._clock() - self._last_rx > max_age


def open_udp_socket(port: int) -> socket.socket:  # never called by tests
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", port))
    sock.setblocking(False)
    return sock
