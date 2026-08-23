"""Probe 3: what read-only ($) keys does the console expose, and is any of them a meter?

Probe 2 showed the subscribe verbs are silent -- but an idle console would be
silent even with a working subscription, because a subscription reports
CHANGES and nobody is touching the desk. So this probe asks a different
question, one that needs no change and no write: what does the console say a
node CONTAINS?

Three parts, all read-only:
  A. schema query (,s "?") on representative nodes -- lists their keys
  B. plain GET on every $-prefixed key found, to see which carry live values
  C. two consecutive reads of any candidate meter, 1s apart, to see if it MOVES

Part C is the real test: a meter on a silent desk reads low, but a meter that
is genuinely live differs between two reads far more often than a static
setting does.

Run:  python probe3_meters.py 192.168.128.28
"""

from __future__ import annotations

import socket
import sys
import time
from pathlib import Path

# The repo root, resolved from this file, so the probe runs from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wing_parser.net.client import WingClient  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"

# One of each kind of node, so the probe does not conclude from channels alone.
NODES = ["/ch/1", "/bus/1", "/main/1", "/mtx/1", "/dca/1", "/io/in/LCL/1", ""]


def schema_of(client: WingClient, node: str) -> list[str]:
    """Ask a node to list its keys. Returns [] when the console will not say."""
    reply = client.request(node if node else "/", typetag="s", args=("?",))
    if reply is None:
        return []
    keys: list[str] = []
    for arg in reply.args:
        if isinstance(arg, str):
            keys.extend(part for part in arg.split() if part)
    return keys


def main() -> None:
    print(f"probe 3 -- read-only key discovery against {HOST}\n")

    dollar_keys: list[str] = []

    with WingClient(HOST) as client:
        print("A. schema queries")
        for node in NODES:
            keys = schema_of(client, node)
            label = node if node else "/ (root)"
            if not keys:
                print(f"  {label:16s} no schema reply")
                continue
            marked = [k for k in keys if k.startswith("$")]
            print(f"  {label:16s} {len(keys)} keys, {len(marked)} read-only")
            if marked:
                print(f"      {' '.join(marked)}")
            for key in marked:
                dollar_keys.append(f"{node}/{key}" if node else f"/{key}")

        if not dollar_keys:
            print("\n  no $-prefixed keys anywhere -- stop, there is nothing to meter")
            return

        print(f"\nB. reading {len(dollar_keys)} read-only keys")
        first: dict[str, tuple] = {}
        for address in dollar_keys:
            reply = client.request(address)
            if reply is None:
                print(f"  {address:28s} silent")
                continue
            first[address] = tuple(reply.args)
            print(f"  {address:28s} {reply.typetag} {reply.args!r}")

        if not first:
            print("\n  none answered -- nothing further to test")
            return

        print("\nC. same keys again after 1.5s -- which ones MOVED?")
        time.sleep(1.5)
        moved = []
        for address, before in first.items():
            reply = client.request(address)
            if reply is None:
                continue
            after = tuple(reply.args)
            if after != before:
                moved.append(address)
                print(f"  MOVED  {address:26s} {before!r} -> {after!r}")
        if not moved:
            print("  nothing moved -- no live meter among these keys")


if __name__ == "__main__":
    main()
