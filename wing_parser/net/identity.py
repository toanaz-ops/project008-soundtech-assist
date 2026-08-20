"""The `WING?` handshake on UDP 2222 -- plain text, not OSC.

Sub-project C+D talks to the console over OSC on 2223 (see
`net/codec.py`), but the very first exchange with any console happens
on a *different* port with a *different* wire format entirely: five
raw ASCII bytes out, one comma-separated line back (design doc
sec 2.1). Keeping that one exchange in its own module means nothing
here needs to know OSC exists.

This handshake is also the write-safety identity echo required by
sec 6.2 -- a caller is about to trust "this is the console I meant to
write to" on the strength of this parse, so parsing here is
deliberately strict: a short or mistagged reply raises rather than
handing back a partially-filled record that *looks* trustworthy.
"""

from __future__ import annotations

import socket
from dataclasses import dataclass

IDENTITY_PORT = 2222

_QUERY = b"WING?"
_PREFIX = "WING,"
_FIELD_NAMES = ("ip", "name", "model", "serial", "firmware")


class IdentityError(ValueError):
    """A WING? reply did not carry a complete, well-formed record."""


@dataclass(frozen=True)
class WingIdentity:
    ip: str
    name: str
    model: str
    serial: str
    firmware: str


def parse_identity(raw: bytes) -> WingIdentity:
    """Parse a raw WING? reply, e.g.

    ``WING,192.168.128.28,WING-GIAQUY,wing-rack,01009Y90604AAE,3.1-0-g9f314617:release``

    Strict on purpose: a reply missing the leading tag or missing any
    of the five fields is an error, never a partial `WingIdentity`.
    """
    try:
        text = raw.decode("ascii")
    except UnicodeDecodeError as exc:
        raise IdentityError(f"WING? reply is not ASCII: {raw!r}") from exc

    if not text.startswith(_PREFIX):
        raise IdentityError(f"WING? reply does not start with {_PREFIX!r}: {text!r}")

    fields = text[len(_PREFIX):].split(",")
    if len(fields) != len(_FIELD_NAMES):
        raise IdentityError(
            f"WING? reply has {len(fields)} field(s), expected "
            f"{len(_FIELD_NAMES)} ({', '.join(_FIELD_NAMES)}): {text!r}"
        )

    return WingIdentity(**dict(zip(_FIELD_NAMES, fields)))


def query_identity(
    host: str, port: int = IDENTITY_PORT, timeout: float = 2.0
) -> WingIdentity:
    """Send `WING?` to `host:port` and return the parsed identity.

    A bare `socket.timeout` names neither the host nor the protocol
    that stalled; wrap it so a `wing net` command can surface "no
    console at that address" instead of an opaque traceback.
    """
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.settimeout(timeout)
        sock.sendto(_QUERY, (host, port))
        try:
            raw, _ = sock.recvfrom(4096)
        except socket.timeout as exc:
            raise TimeoutError(
                f"no WING? reply from {host}:{port} within {timeout}s"
            ) from exc

    return parse_identity(raw)
