r"""Probe 10: does every strip family answer a bare `name` leaf, as well as `$name`?

`net/watch/poller.py`'s `read_labels` reads the ordinary `name` leaf rather
than `$name`, and its docstring says both exist. That claim was measured on
2026-08-21 -- but as a throwaway inline command, leaving nothing anyone could
re-run. A Task 3 implementer flagged exactly that: the citation had no primary
source in the repo, which by this project's own standard makes it not evidence.
This script is the missing artifact.

Why `name` and not `$name`: `name` is the key the .snap carries, so a label
printed by a watch session matches what every other command prints for the
same strip. `$name` is read-only and absent from .snap (design doc S2.2).

Read-only.

Run:  python -u docs\probes\probe10_name_leaves.py 192.168.128.28
"""

from __future__ import annotations

import sys

sys.path.insert(0, r"Z:\My Drive\CLAUDE WORKS\DEV CAVE 2026\SOUNDTECH PLAYGROUND\.claude\worktrees\project-capabilities-next-steps-8ec61c")

from wing_parser.net.client import WingClient  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"

# One strip per family that read_labels can be pointed at.
FAMILIES = ("ch", "bus", "main", "mtx", "dca")


def main() -> None:
    print(f"probe 10 -- bare `name` vs `$name`, against {HOST}\n")

    both = True
    with WingClient(HOST) as client:
        print(f"  {'address':22s} {'name':>22s}   {'$name':>22s}")
        for family in FAMILIES:
            plain = client.request(f"/{family}/1/name")
            dollar = client.request(f"/{family}/1/$name")
            if plain is None or dollar is None:
                both = False
            shown_plain = "SILENT" if plain is None else f"{plain.typetag} {plain.args!r}"
            shown_dollar = "SILENT" if dollar is None else f"{dollar.typetag} {dollar.args!r}"
            print(f"  /{family}/1{'':14s} {shown_plain:>22s}   {shown_dollar:>22s}")

    print()
    if both:
        print("VERDICT: every family answers BOTH `name` and `$name` --")
        print("         read_labels' docstring claim holds")
    else:
        print("VERDICT: at least one family did NOT answer -- the docstring")
        print("         claim is wrong and read_labels needs revisiting")

    print()
    print("Note: a blank value is normal, not a failure. The lab rack sits on")
    print("factory-scene.snap, which names no strip at all -- which is exactly")
    print("why events.format_change falls back to the strip address.")


if __name__ == "__main__":
    main()
