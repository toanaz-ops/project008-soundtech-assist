r"""Probe 10: does every strip family answer a bare `name` leaf, as well as `$name`?

`net/watch/poller.py`'s `read_labels` reads the ordinary `name` leaf rather
than `$name`, and its docstring says both exist. That claim was measured on
2026-08-21 -- but as a throwaway inline command, leaving nothing anyone could
re-run. A Task 3 implementer flagged exactly that: the citation had no primary
source in the repo, which by this project's own standard makes it not evidence.
This script is the missing artifact.

Why `name` and not `$name`: `name` is the key the .snap carries, so a label
printed by a watch session matches what every other command prints for the
same strip. `$name` is read-only (2026-08-21-live-watch-design.md S2.1's
table) and absent from .snap (2026-08-21-WING-NET-design.md S2.2, the OTHER
design doc -- live-watch's own S2.2 is about effective values and says
nothing about .snap).

Read-only.

Run:  python -u docs\probes\probe10_name_leaves.py 192.168.128.28
"""

from __future__ import annotations

import sys
from pathlib import Path

# The repo root, resolved from this file, so the probe runs from any cwd.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from wing_parser.net.client import WingClient  # noqa: E402

HOST = sys.argv[1] if len(sys.argv) > 1 else "192.168.128.28"

# One strip per family that read_labels can be pointed at.
FAMILIES = ("ch", "bus", "main", "mtx", "dca")


def main() -> None:
    print(f"probe 10 -- bare `name` vs `$name`, against {HOST}\n")

    # Tracked separately, because only one of them bears on read_labels.
    # A silent `name` would break it; a silent `$name` does not, since
    # read_labels never reads `$name`. The 2026-08-21 run found exactly
    # that case -- /dca/1/$name silent -- and a verdict that lumped the two
    # together would have said "read_labels needs revisiting" when what
    # actually needed revising was one sentence of its docstring.
    plain_all = True
    dollar_all = True
    with WingClient(HOST) as client:
        print(f"  {'address':22s} {'name':>22s}   {'$name':>22s}")
        for family in FAMILIES:
            plain = client.request(f"/{family}/1/name")
            dollar = client.request(f"/{family}/1/$name")
            if plain is None:
                plain_all = False
            if dollar is None:
                dollar_all = False
            shown_plain = "SILENT" if plain is None else f"{plain.typetag} {plain.args!r}"
            shown_dollar = "SILENT" if dollar is None else f"{dollar.typetag} {dollar.args!r}"
            print(f"  /{family}/1{'':14s} {shown_plain:>22s}   {shown_dollar:>22s}")

    print()
    if plain_all:
        print("VERDICT on read_labels' CODE: sound -- every family answers a")
        print("  bare `name`, which is the only leaf read_labels reads.")
    else:
        print("VERDICT on read_labels' CODE: BROKEN -- a family does not answer")
        print("  `name`, so that strip can never be labelled. Revisit the code.")

    if dollar_all:
        print("VERDICT on `$name`: present on every family probed.")
    else:
        print("VERDICT on `$name`: NOT universal. Any docstring or rule saying")
        print("  otherwise is wrong -- but read_labels does not read `$name`,")
        print("  so this is a documentation defect, not a code one.")

    print()
    print("Note: a blank value is normal, not a failure. The lab rack sits on")
    print("factory-scene.snap, which names no strip at all -- which is exactly")
    print("why events.format_change falls back to the strip address.")


if __name__ == "__main__":
    main()
