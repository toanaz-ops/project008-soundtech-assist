"""Pure OSC encode/decode for WING's protocol dialect.

No sockets, no I/O here -- `net/client.py` owns the wire, this module owns
the bytes. Behaviour is pinned to what was measured against the lab console
(docs/superpowers/specs/2026-08-21-wing-net-design.md S2.1/2.3/2.6/2.7):
4-byte NUL padding of every string/blob field, the four type tags WING
actually sends (`s`, `f`, `i`, `b`), a bare address-only request form the
console accepts for GET, and the "sff/sfi/s" triplet every per-leaf read
reply comes back as.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from typing import Any, Sequence

_LEAF_TRIPLET_TAGS = ("sff", "sfi", "s")


@dataclass(frozen=True)
class OscMessage:
    address: str
    typetag: str
    args: tuple


def _pad(data: bytes) -> bytes:
    """OSC rounds every string/blob field up to a 4-byte boundary."""
    remainder = len(data) % 4
    if remainder == 0:
        return data
    return data + b"\x00" * (4 - remainder)


def _encode_string(text: str) -> bytes:
    return _pad(text.encode("ascii") + b"\x00")


def _read_string(data: bytes, offset: int) -> tuple[str, int]:
    """Read one NUL-terminated, 4-byte-padded string starting at offset."""
    end = data.index(b"\x00", offset)
    text = data[offset:end].decode("ascii")
    raw_len = end - offset
    padded_len = (raw_len // 4 + 1) * 4  # +1 for the mandatory terminator
    return text, offset + padded_len


def encode(address: str, typetag: str | None = None, args: Sequence[Any] = ()) -> bytes:
    """Build one OSC message.

    `typetag=None` emits the address alone, padded -- the console accepts
    that bare form and it is what a plain GET uses (design doc S2.1).
    """
    message = _encode_string(address)
    if typetag is None:
        return message
    message += _encode_string("," + typetag)
    for tag, arg in zip(typetag, args):
        if tag == "s":
            message += _encode_string(str(arg))
        elif tag == "f":
            message += struct.pack(">f", float(arg))
        elif tag == "i":
            message += struct.pack(">i", int(arg))
        elif tag == "b":
            blob = bytes(arg)
            message += struct.pack(">i", len(blob)) + _pad(blob)
        else:
            raise ValueError(f"unsupported OSC type tag {tag!r} for {address!r}")
    return message


def decode(data: bytes) -> OscMessage:
    """Parse one OSC message, as received from the console.

    Tolerates a reply that is the address alone with nothing after it --
    the older OSC form WING still uses for some replies (design doc S2.1).
    """
    address, offset = _read_string(data, 0)
    if offset >= len(data):
        return OscMessage(address=address, typetag="", args=())
    if data[offset : offset + 1] != b",":
        raise ValueError(f"{address!r}: expected a type tag string at offset {offset}")

    typetag_field, offset = _read_string(data, offset)
    typetag = typetag_field[1:]  # drop the leading comma
    args: list[Any] = []
    for tag in typetag:
        if tag == "s":
            value, offset = _read_string(data, offset)
            args.append(value)
        elif tag == "f":
            args.append(struct.unpack(">f", data[offset : offset + 4])[0])
            offset += 4
        elif tag == "i":
            args.append(struct.unpack(">i", data[offset : offset + 4])[0])
            offset += 4
        elif tag == "b":
            (blob_len,) = struct.unpack(">i", data[offset : offset + 4])
            offset += 4
            args.append(data[offset : offset + blob_len])
            offset += (blob_len + 3) // 4 * 4  # blob padding has no NUL terminator
        else:
            raise ValueError(f"unsupported OSC type tag {tag!r} in {address!r}")
    return OscMessage(address=address, typetag=typetag, args=tuple(args))


def leaf_value(message: OscMessage) -> tuple[Any, str]:
    """Interpret a per-leaf GET reply's ,sff / ,sfi / ,s triplet.

    Every form the console sends carries the NATIVE value as the LAST
    argument, and a display string as the first -- for `,s` those are the
    same string (design doc S2.3). The normalised 0..1 float that ,sff and
    ,sfi carry in the middle has no known consumer and nothing to verify it
    against, so it is left out rather than added on spec.
    """
    if message.typetag not in _LEAF_TRIPLET_TAGS:
        raise ValueError(
            f"{message.address!r}: not a per-leaf reply triplet (typetag {message.typetag!r})"
        )
    display = message.args[0]
    native = message.args[-1]
    return native, display
