"""Probe 2: find the subscribe verb firmware 3.1 actually accepts.

Probe 1 tried three bare forms and got silence. Silence proves nothing until
the harness is shown to work, so this run opens with a CONTROL: a plain leaf
GET that is already known to reply. If the control is silent the harness is at
fault, not the console, and no other line in the output means anything.

Read-only throughout: every message here either reads a leaf or asks the
console to start sending. None writes a parameter.

Run:  python probe2_subscribe_wide.py 192.168.128.28
"""

from __future__ import annotations

import socket
import sys
import time
from collections import Counter

sys.path.insert(0, r"Z:\My Drive\CLAUDE WORKS\DEV CAVE 2026\SOUNDTECH PLAYGROUND\.claude\worktrees\project-capabilities-next-steps-8ec61c")

from wing_parser.net.codec import decode, encode  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"
PORT = 2223

CONTROL = "/ch/1/fdr"

# Every plausible subscribe form, including the X32 legacy verb and the
# argument-carrying variants. One run should separate "wrong syntax" from
# "feature absent".
# NOTE: codec.encode adds the leading comma itself, so tags go in bare ("s",
# not ",s"). Passing ",s" made it try to encode "," as a type and raise.
CANDIDATES: list[tuple[str, str | None, tuple]] = [
    ("/*S~", None, ()),
    ("/*S~", "s", ("",)),
    ("/*S~", "i", (1,)),
    ("/*S", "i", (1,)),
    ("/*~", None, ()),
    ("/*~", "i", (1,)),
    ("/xremote", None, ()),
    ("/subscribe", None, ()),
    ("/%0/*S~", None, ()),
    ("/*", "s", ("?",)),
]


def drain(sock: socket.socket, seconds: float) -> list[bytes]:
    out: list[bytes] = []
    started = time.monotonic()
    sock.settimeout(0.3)
    while time.monotonic() - started < seconds:
        try:
            data, _ = sock.recvfrom(65536)
        except socket.timeout:
            continue
        out.append(data)
    return out


def summarise(packets: list[bytes], indent: str = "      ") -> None:
    if not packets:
        print(f"{indent}silent")
        return
    addresses: Counter[str] = Counter()
    sample = None
    for raw in packets:
        try:
            message = decode(raw)
        except Exception as exc:  # noqa: BLE001 - a probe reports, never crashes
            addresses[f"<undecodable: {type(exc).__name__}>"] += 1
            continue
        addresses[message.address] += 1
        if sample is None:
            sample = message
    print(f"{indent}{len(packets)} datagrams, {len(addresses)} distinct addresses")
    for address, count in addresses.most_common(5):
        print(f"{indent}  {count:5d}  {address}")
    if sample is not None:
        print(f"{indent}  sample: {sample.address} {sample.typetag} {sample.args!r}")


def attempt(address: str, typetag: str | None, args: tuple, seconds: float) -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", 0))
    try:
        sock.sendto(encode(address, typetag, args), (HOST, PORT))
        packets = drain(sock, seconds)
        label = f"{address!r}"
        if typetag:
            label += f" {typetag} {args!r}"
        print(f"  {label}")
        summarise(packets)
        return len(packets)
    finally:
        sock.close()


def main() -> None:
    print(f"probe 2 -- subscribe verb discovery against {HOST}:{PORT}\n")

    print("CONTROL (the harness must pass this or nothing below counts)")
    count = attempt(CONTROL, None, (), 2.0)
    if count == 0:
        print("\n  CONTROL SILENT -- harness or network at fault. Stop reading here.")
        return
    print("  control OK\n")

    print("CANDIDATES (6s listen each)")
    for address, typetag, args in CANDIDATES:
        attempt(address, typetag, args, 6.0)
        print()


if __name__ == "__main__":
    main()
