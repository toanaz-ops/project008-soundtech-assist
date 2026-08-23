"""Probe 8: is break-on-first-silence discovery flaky? Run it 6 times and see.

Probe 6 reported /main as 0 present. Probe 7 then read /main/1/$fdr 10 times
out of 10 successfully, so the address is not absent. The remaining suspect is
a single dropped UDP datagram: discovery breaks on the FIRST silence, so one
lost packet truncates an entire family to zero and says nothing about it.

If that is right, repeating the identical walk will not give the identical
answer. A design that cannot reproduce its own inventory cannot be trusted to
build a watch-list.

Read-only.

Run:  python probe8_flaky.py 192.168.128.28
"""

from __future__ import annotations

import sys
from collections import defaultdict
from pathlib import Path

# The repo root, resolved from this file, so the probe runs from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wing_parser.net.client import WingClient  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"
FAMILIES = ["ch", "bus", "main", "mtx", "dca"]
ATTEMPTS = 6

# Truth, established by probe 7 part D for /main and by `wing analyze` for the
# rest: 40 channels, 16 buses, 4 mains, 8 matrices, 16 DCAs.
EXPECTED = {"ch": 40, "bus": 16, "main": 4, "mtx": 8, "dca": 16}


def count_break_on_silence(client: WingClient, family: str) -> int:
    """The naive walk probe 6 used: stop at the first address that is quiet."""
    total = 0
    for index in range(1, 65):
        if client.request(f"/{family}/{index}/$fdr" if family != "dca"
                          else f"/{family}/{index}/$solo") is None:
            break
        total += 1
    return total


def main() -> None:
    print(f"probe 8 -- is break-on-first-silence reproducible? {HOST}")
    print(f"{ATTEMPTS} attempts; truth = {EXPECTED}\n")

    seen: dict[str, list[int]] = defaultdict(list)
    for attempt in range(1, ATTEMPTS + 1):
        row = []
        with WingClient(HOST) as client:
            for family in FAMILIES:
                count = count_break_on_silence(client, family)
                seen[family].append(count)
                mark = "" if count == EXPECTED[family] else "  <-- WRONG"
                row.append(f"{family}={count}{mark}")
        print(f"  attempt {attempt}: " + "  ".join(row))

    print("\nsummary")
    any_wrong = False
    for family in FAMILIES:
        counts = seen[family]
        distinct = sorted(set(counts))
        wrong = [c for c in counts if c != EXPECTED[family]]
        if wrong:
            any_wrong = True
        print(f"  /{family:5s} expected {EXPECTED[family]:3d}  saw {distinct}  "
              f"{len(wrong)}/{len(counts)} wrong")
    print()
    print("VERDICT: break-on-first-silence is UNRELIABLE" if any_wrong
          else "VERDICT: reproduced correctly every time in this run")


if __name__ == "__main__":
    main()
