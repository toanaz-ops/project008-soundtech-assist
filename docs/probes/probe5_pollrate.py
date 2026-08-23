"""Probe 5: how fast can a watch-list be polled? This sets C2b's latency floor.

Pure reads. Nothing is written and nothing is subscribed, so this cannot
disturb any other client on the desk -- which is the whole point of the polling
design.

Three watch-list sizes are timed, each three times, because one run of a UDP
batch is not a measurement. What matters for the design is the round time: a
change is noticed, worst case, one round after it happens.

Run:  python probe5_pollrate.py 192.168.128.28
"""

from __future__ import annotations

import statistics
import sys
import time
from pathlib import Path

# The repo root, resolved from this file, so the probe runs from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wing_parser.net.client import WingClient  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"

# The effective-value keys probe 3 found. These are what "who moved what"
# actually needs: $fdr and $mute already fold in DCA and mute-override.
CH_KEYS = ["$fdr", "$mute", "$solo"]
ROUNDS = 3


def watchlist(channels: int) -> list[str]:
    out = []
    for n in range(1, channels + 1):
        for key in CH_KEYS:
            out.append(f"/ch/{n}/{key}")
    return out


def time_one(client: WingClient, addresses: list[str]) -> tuple[float, int, int]:
    started = time.monotonic()
    result = client.get_many(addresses)
    elapsed = time.monotonic() - started
    return elapsed, len(result.replies), len(result.unresolved)


def main() -> None:
    print(f"probe 5 -- polling rate against {HOST}")
    print(f"watch keys per channel: {' '.join(CH_KEYS)}\n")

    with WingClient(HOST) as client:
        print(f"{'channels':>9}  {'leaves':>7}  {'median s':>9}  {'per round':>10}  missing")
        for channels in (8, 40, 40 + 8):
            addresses = watchlist(channels)
            times = []
            missing = 0
            for _ in range(ROUNDS):
                elapsed, got, lost = time_one(client, addresses)
                times.append(elapsed)
                missing = max(missing, lost)
            median = statistics.median(times)
            rate = f"{1 / median:.1f}/s" if median > 0 else "n/a"
            print(f"{channels:>9}  {len(addresses):>7}  {median:>9.3f}  {rate:>10}  {missing}")

        print("\nfull-console reference: how long is a whole-desk read?")
        print("  (not run here -- `wing net snapshot` already measures it)")


if __name__ == "__main__":
    main()
