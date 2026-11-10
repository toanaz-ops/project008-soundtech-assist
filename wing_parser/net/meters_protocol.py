"""Pure encode/decode for the WING native-protocol meter channel (ch. 3).

EXPERIMENTAL and UNVERIFIED against a real desk (acceptance: HW-192).
Source: Maillot, "WING Remote Protocols" V3.0.5-1, pp.86-87, 108-111.
No sockets here; see `meters.py` for the reader.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

ESCAPE = 0xDF
TOKEN_PORT, TOKEN_REPORT = 0xD3, 0xD4
TOKEN_COLLECTION_START, TOKEN_COLLECTION_END = 0xDC, 0xDE
FRAME_END = 0xD1  # follows ESCAPE: "df d1"
NO_SIGNAL_RAW = -0x8000

FAMILY_CHANNEL, FAMILY_AUX, FAMILY_BUS, FAMILY_MAIN = 0xA0, 0xA1, 0xA2, 0xA3
FAMILY_MATRIX, FAMILY_DCA, FAMILY_FX = 0xA4, 0xA5, 0xA6

# Channel V1: 8 words per channel (doc Table 5). V2 layout is UNVERIFIED.
CHANNEL_V1 = ("in_l", "in_r", "out_l", "out_r", "gate_key", "gate_gain",
              "dyn_key", "dyn_gain")


def _escape(data: bytes) -> bytes:
    return data.replace(b"\xdf", b"\xdf\xde")


def _frame(body: bytes) -> bytes:
    """Wrap a body in the native-protocol channel 3 frame: df d3 ... df d1."""
    return bytes([ESCAPE, 0xD3]) + body + bytes([ESCAPE, FRAME_END])


def encode_port_request(port: int) -> bytes:
    """Declare the client UDP port: `df d3 d3 <hi lo> df d1`."""
    if not 0 < port < 65536:
        raise ValueError(f"bad UDP port: {port}")
    return _frame(bytes([TOKEN_PORT]) + _escape(struct.pack(">H", port)))


def encode_meter_request(report_id: int,
                         families: list[tuple[int, list[int]]]) -> bytes:
    """Request one collection. Indices are 1-based here, 0-based on the wire."""
    body = bytes([TOKEN_REPORT]) + _escape(struct.pack(">I", report_id))
    body += bytes([TOKEN_COLLECTION_START])
    for family, indices in families:
        body += bytes([family])
        for index in indices:
            if not 1 <= index <= 128:
                raise ValueError(f"meter index out of range: {index}")
            body += bytes([index - 1])
    return _frame(body + bytes([TOKEN_COLLECTION_END]))


def encode_renew(report_id: int) -> bytes:
    """Renew the request (keeps data flowing; desk times out after 5 s)."""
    return _frame(bytes([TOKEN_REPORT]) + _escape(struct.pack(">I", report_id)))


@dataclass(frozen=True)
class MeterFrame:
    report_id: int
    records: list[dict[str, float | None]]  # None = no signal (0x8000)


def decode_meter_packet(data: bytes,
                        layout: tuple[str, ...] = CHANNEL_V1) -> MeterFrame:
    """<report id 4B BE><n x int16 BE>; dB = raw / 256."""
    stride = len(layout)
    if len(data) < 4 or (len(data) - 4) % (2 * stride):
        raise ValueError(f"bad meter packet length: {len(data)}")
    (report_id,) = struct.unpack_from(">I", data)
    count = (len(data) - 4) // 2
    raws = struct.unpack_from(f">{count}h", data, 4)
    values = [None if r == NO_SIGNAL_RAW else r / 256.0 for r in raws]
    records = [dict(zip(layout, values[i:i + stride]))
               for i in range(0, count, stride)]
    return MeterFrame(report_id, records)
