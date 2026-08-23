"""Probe 4: chase /$stat/ppm and enumerate the root, hunting for a meter over OSC.

Probe 3 found no meter among the $ keys of a channel, bus, main, matrix, DCA or
local input -- but it did find /$stat listing a child called 'ppm', which is
what a Peak Programme Meter would be called. This probe follows that thread and
also lists the root's full key set, which probe 3 only summarised.

Everything here is a read. Nothing is written.

Part C samples one candidate 20 times in 2s: a meter moves between samples even
on a quiet desk (noise floor dither), a static setting does not.

Run:  python probe4_ppm.py 192.168.128.28
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

# The repo root, resolved from this file, so the probe runs from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wing_parser.net.client import WingClient  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"

# Addresses worth trying by name. If WING exposes meters over OSC at all, one
# of these shapes is where a meter would live.
GUESSES = [
    "/$stat/ppm",
    "/$stat/solo",
    "/$stat/lock",
    "/$meters",
    "/meters",
    "/$stat/ppm/1",
    "/ch/1/$ppm",
    "/ch/1/$lvl",
    "/ch/1/$meter",
    "/main/1/$ppm",
]


def keys_of(client: WingClient, node: str) -> list[str]:
    reply = client.request(node, typetag="s", args=("?",))
    if reply is None:
        return []
    out: list[str] = []
    for arg in reply.args:
        if isinstance(arg, str):
            out.extend(part for part in arg.split() if part)
    return out


def main() -> None:
    print(f"probe 4 -- meter hunt against {HOST}\n")

    with WingClient(HOST) as client:
        print("A. every key at the root")
        root = keys_of(client, "/")
        print(f"  {len(root)} keys: {' '.join(root)}\n")

        print("B. /$stat children, read one by one")
        stat_keys = keys_of(client, "/$stat")
        print(f"  {len(stat_keys)} keys: {' '.join(stat_keys)}")
        for key in stat_keys:
            address = f"/$stat/{key}"
            reply = client.request(address)
            shown = f"{reply.typetag} {reply.args!r}" if reply else "silent"
            print(f"    {address:24s} {shown}")

        print("\nC. named guesses")
        alive = []
        for address in GUESSES:
            reply = client.request(address)
            if reply is None:
                print(f"  {address:20s} silent")
                continue
            print(f"  {address:20s} {reply.typetag} {reply.args!r}")
            alive.append(address)

        if not alive:
            print("\n  nothing answered -- no OSC meter address on this firmware")
            return

        print("\nD. sampling each live address 20x over 2s -- does it MOVE?")
        for address in alive:
            seen = []
            for _ in range(20):
                reply = client.request(address)
                if reply is not None:
                    seen.append(tuple(reply.args))
                time.sleep(0.1)
            distinct = len(set(seen))
            verdict = "MOVES" if distinct > 1 else "static"
            print(f"  {address:20s} {distinct} distinct value(s) in {len(seen)} reads -- {verdict}")


if __name__ == "__main__":
    main()
