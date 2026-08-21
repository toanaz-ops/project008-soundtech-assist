"""Probe 6: a working change-watcher, by polling. The C2b prototype.

Answers three things at once, and needs a human to move ONE control while it
runs:

  1. does polling actually notice a change, and how fast
  2. does it keep working while WING-Edit is connected (coexistence)
  3. what a change event looks like, which is what the CLI would print

Reads only. It subscribes to nothing and writes nothing, so whatever else is
talking to the desk is undisturbed -- that is the property being demonstrated.

The watch-list is built from what the console SAYS exists, never from a
hard-coded count: probe 5 measured that 24 absent addresses cost 20x the round
time, because the retry ladder hunts for them every round.

Run:  python probe6_watch.py 192.168.128.28 [seconds]
"""

from __future__ import annotations

import sys
import time

sys.path.insert(0, r"Z:\My Drive\CLAUDE WORKS\DEV CAVE 2026\SOUNDTECH PLAYGROUND\.claude\worktrees\project-capabilities-next-steps-8ec61c")

from wing_parser.net.client import WingClient  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"
SECONDS = float(sys.argv[2]) if len(sys.argv) > 2 else 45.0

# Effective values: $fdr and $mute already fold in DCA and mute-override, so a
# DCA move shows up on the channels it governs -- which is what an engineer
# means by "what changed".
WATCH = {
    "ch": ("$fdr", "$mute", "$solo"),
    "bus": ("$fdr", "$mute", "$solo"),
    "main": ("$fdr", "$mute", "$solo"),
    "mtx": ("$fdr", "$mute", "$solo"),
    "dca": ("$solo",),
}


def discover(client: WingClient, family: str, keys: tuple[str, ...]) -> list[str]:
    """Probe upward until a number stops answering, so absent addresses never
    enter the watch-list. Cheap: one request per index, and it stops early."""
    found: list[str] = []
    for index in range(1, 65):
        if client.request(f"/{family}/{index}/{keys[0]}") is None:
            break
        found.extend(f"/{family}/{index}/{key}" for key in keys)
    return found


def main() -> None:
    print(f"probe 6 -- change watcher against {HOST}, {SECONDS:.0f}s\n")

    with WingClient(HOST) as client:
        print("building the watch-list from what the console answers...")
        addresses: list[str] = []
        for family, keys in WATCH.items():
            found = discover(client, family, keys)
            print(f"  /{family:5s} {len(found) // len(keys):3d} present -> {len(found)} leaves")
            addresses.extend(found)
        print(f"  {len(addresses)} leaves total\n")

        def sample() -> dict[str, tuple]:
            result = client.get_many(addresses)
            return {a: tuple(m.args) for a, m in result.replies.items()}

        baseline = sample()
        print(f"baseline taken ({len(baseline)} leaves answered)")
        print(">>> MOVE ONE CONTROL NOW -- a fader, a mute, anything <<<\n")

        rounds = 0
        events = 0
        started = time.monotonic()
        while time.monotonic() - started < SECONDS:
            round_started = time.monotonic()
            current = sample()
            rounds += 1
            for address, after in current.items():
                before = baseline.get(address)
                if before is not None and before != after:
                    events += 1
                    when = time.monotonic() - started
                    # args are (display, normalised, native); display is what
                    # a human reads, and for ,sfi it is also the correct value.
                    old = before[0] if before else "?"
                    new = after[0] if after else "?"
                    print(f"  [{when:6.2f}s] {address:22s} {old!r} -> {new!r}")
            baseline = current
            # Pace the loop so a quiet desk is not polled flat out.
            slept = 0.1 - (time.monotonic() - round_started)
            if slept > 0:
                time.sleep(slept)

        print(f"\n{rounds} rounds in {SECONDS:.0f}s, {events} change events seen")
        if events == 0:
            print("no change seen -- either nothing was moved, or polling missed it")


if __name__ == "__main__":
    main()
