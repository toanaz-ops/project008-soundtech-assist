"""Probe 9: can walk_schema tell us which STRIPS exist, given it skips $ keys?

schema.py's _expand drops every "$" child, so the watch-list cannot read
$fdr/$mute/$solo out of walk_schema().leaves directly. The proposed fix is
indirect: a strip that owns any ordinary leaf exists, so derive the strip set
from the walk and append the $ keys from config.

This probe checks that the derivation is sound and complete:
  - which /ch, /bus, /main, /mtx, /dca indices does the walk imply?
  - does that match the truth probe 7/8 established (40/16/4/8/16)?
  - how long does the walk take, since it is a watch session's startup cost?

Read-only.

Run:  python -u probe9_stripset.py 192.168.128.28
"""

from __future__ import annotations

import re
import sys
import time
from collections import defaultdict
from pathlib import Path

# The repo root, resolved from this file, so the probe runs from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wing_parser.net.schema import walk_schema  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"
FAMILIES = ("ch", "bus", "main", "mtx", "dca")
TRUTH = {"ch": 40, "bus": 16, "main": 4, "mtx": 8, "dca": 16}

STRIP_RE = re.compile(r"^/(ch|bus|main|mtx|dca)/(\d+)/")


def main() -> None:
    print(f"probe 9 -- strip set from walk_schema against {HOST}\n")

    started = time.monotonic()
    result = walk_schema(HOST)
    elapsed = time.monotonic() - started

    print(f"walk took {elapsed:.2f}s")
    print(f"  {len(result.leaves)} leaves")
    print(f"  {len(result.unresolved_nodes)} unresolved nodes")
    if result.unresolved_nodes:
        for node in result.unresolved_nodes[:5]:
            print(f"      {node}")

    strips: dict[str, set[int]] = defaultdict(set)
    for address in result.leaves:
        match = STRIP_RE.match(address)
        if match:
            strips[match.group(1)].add(int(match.group(2)))

    print("\nstrip set implied by the walk")
    all_ok = True
    for family in FAMILIES:
        found = sorted(strips.get(family, set()))
        count = len(found)
        expected = TRUTH[family]
        contiguous = found == list(range(1, count + 1))
        ok = count == expected and contiguous
        all_ok = all_ok and ok
        flag = "" if ok else "   <-- MISMATCH"
        print(f"  /{family:5s} {count:3d} strips, contiguous={contiguous}  "
              f"(truth {expected}){flag}")

    print()
    if all_ok:
        print("VERDICT: the walk implies exactly the right strip set --")
        print("         deriving $-key addresses from it is sound")
    else:
        print("VERDICT: MISMATCH -- the derivation is not sound as written")

    # A watch-list needs the $ keys appended. Show what that produces.
    keys = {"ch": ("$fdr", "$mute", "$solo"), "bus": ("$fdr", "$mute", "$solo"),
            "main": ("$fdr", "$mute", "$solo"), "mtx": ("$fdr", "$mute", "$solo"),
            "dca": ("$solo",)}
    total = sum(len(strips.get(f, ())) * len(keys[f]) for f in FAMILIES)
    print(f"\nwatch-list this would build: {total} leaves")


if __name__ == "__main__":
    main()
