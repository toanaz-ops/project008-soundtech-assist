"""Probe 1: does an OSC subscription work, what does it emit, and when does it die?

Read-only. Subscribing makes the console SEND to us; it changes no console state.

Run:  python probe1_subscribe.py 192.168.128.28
"""

from __future__ import annotations

import socket
import sys
import time
from collections import Counter
from pathlib import Path

# The repo root, resolved from this file, so the probe runs from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wing_parser.net.codec import decode, encode  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"
PORT = 2223
LISTEN_SECONDS = 25.0

# Candidate subscribe verbs. The design doc names /*S~ in its out-of-scope
# section; the others are the neighbouring forms worth trying in the same pass
# so one run answers "which syntax does firmware 3.1 accept".
CANDIDATES = [
    ("/*S~", None, ()),
    ("/*S", None, ()),
    ("/*s", None, ()),
]


def listen(sock: socket.socket, seconds: float) -> list[tuple[float, bytes]]:
    """Collect every datagram that arrives within the window, with arrival time."""
    got: list[tuple[float, bytes]] = []
    started = time.monotonic()
    sock.settimeout(0.5)
    while time.monotonic() - started < seconds:
        try:
            data, _ = sock.recvfrom(65536)
        except socket.timeout:
            continue
        got.append((time.monotonic() - started, data))
    return got


def describe(packets: list[tuple[float, bytes]]) -> None:
    if not packets:
        print("      nothing arrived")
        return
    first = packets[0][0]
    last = packets[-1][0]
    print(f"      {len(packets)} datagrams, first at {first:.2f}s, last at {last:.2f}s")

    addresses: Counter[str] = Counter()
    for _, raw in packets:
        try:
            addresses[decode(raw).address] += 1
        except Exception as exc:  # noqa: BLE001 - a probe reports, never crashes
            addresses[f"<undecodable: {type(exc).__name__}>"] += 1
    print(f"      {len(addresses)} distinct addresses; commonest:")
    for address, count in addresses.most_common(8):
        print(f"        {count:6d}  {address}")

    # Where does traffic stop? Bucket arrivals per second so a 10s death is visible.
    buckets: Counter[int] = Counter()
    for when, _ in packets:
        buckets[int(when)] += 1
    line = "  ".join(f"{s}s:{buckets.get(s, 0)}" for s in range(int(last) + 1))
    print(f"      per second: {line}")


def main() -> None:
    print(f"probe 1 -- subscription mechanics against {HOST}:{PORT}")
    print(f"listening {LISTEN_SECONDS}s after each attempt\n")

    for address, typetag, args in CANDIDATES:
        print(f"  send {address!r}")
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind(("", 0))
        try:
            sock.sendto(encode(address, typetag, args), (HOST, PORT))
            describe(listen(sock, LISTEN_SECONDS))
        finally:
            sock.close()
        print()


if __name__ == "__main__":
    main()
