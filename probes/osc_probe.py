"""Read-only OSC probe for a live Behringer WING.

SAFETY, which is a property of the code rather than a promise:

  `message()` takes an address and nothing else. There is no parameter
  for arguments and no code path that encodes one -- every packet it
  can produce carries the type-tag string "," with an empty type list.
  A console cannot be given a new value without a value being sent, so
  nothing this file can emit is able to change a parameter.

  The residual risk is an address that is itself an action and needs no
  argument -- a snapshot recall, say. That is handled by choosing
  addresses, not by code: probe nouns, never verbs, and start with an
  address that cannot exist at all.

Written with no third-party dependency on purpose. OSC 1.0 framing is
a few lines, and the point of this probe is to find out what the
console actually speaks -- a library would sit between the wire and
the answer.
"""

from __future__ import annotations

import socket
import struct
import sys
import time

CONSOLE = ("192.168.128.28", 2223)
LISTEN_SECONDS = 1.5


def _ostring(text: str) -> bytes:
    """OSC string: NUL-terminated, then padded to a multiple of four."""
    raw = text.encode("utf-8") + b"\0"
    return raw + b"\0" * ((4 - len(raw) % 4) % 4)


def message(address: str) -> bytes:
    """An OSC message with no arguments. There is no other kind here."""
    return _ostring(address) + _ostring(",")


def decode(packet: bytes) -> str:
    """Best-effort OSC decode. Returns a description, never raises."""
    try:
        end = packet.index(b"\0")
        address = packet[:end].decode("utf-8", "replace")
        cursor = end + (4 - end % 4) % 4 or end + 4
        cursor = (end // 4 + 1) * 4
        tags_end = packet.index(b"\0", cursor)
        tags = packet[cursor:tags_end].decode("utf-8", "replace")
        cursor = ((tags_end // 4) + 1) * 4

        values = []
        for tag in tags.lstrip(","):
            if tag == "i":
                values.append(struct.unpack_from(">i", packet, cursor)[0])
                cursor += 4
            elif tag == "f":
                values.append(round(struct.unpack_from(">f", packet, cursor)[0], 4))
                cursor += 4
            elif tag == "s":
                stop = packet.index(b"\0", cursor)
                values.append(packet[cursor:stop].decode("utf-8", "replace"))
                cursor = ((stop // 4) + 1) * 4
            else:
                values.append(f"<unhandled tag {tag!r}>")
                break
        return f"{address}  {tags}  {values}"
    except Exception as exc:                      # noqa: BLE001 - a probe
        return f"<undecodable: {exc}>  {packet[:80]!r}"


def probe(addresses: list[str]) -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 0))
    sock.settimeout(0.2)
    print(f"listening on UDP {sock.getsockname()[1]}, target {CONSOLE[0]}:{CONSOLE[1]}")

    for address in addresses:
        packet = message(address)
        print(f"\n--> {address!r}   ({len(packet)} bytes, no arguments)")
        sock.sendto(packet, CONSOLE)

        deadline = time.time() + LISTEN_SECONDS
        replies = 0
        while time.time() < deadline:
            try:
                data, source = sock.recvfrom(65535)
            except socket.timeout:
                continue
            replies += 1
            print(f"    <-- {len(data):5} bytes from {source[0]}:{source[1]}")
            print(f"        {decode(data)}")
            if replies >= 40:
                print("        (stopping after 40 replies for this address)")
                break
        if replies == 0:
            print("    <-- nothing")
    sock.close()


if __name__ == "__main__":
    probe(sys.argv[1:] or ["/wing_parser_probe_does_not_exist"])
