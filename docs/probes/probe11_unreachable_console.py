r"""Probe 11: what does the tool report when the console is NOT THERE?

Found 2026-08-22 while verifying `diff --live`. This is not about diff, and
not about anything the live-watch cycle built -- it is pre-existing behaviour
from the C/D cycle, reachable from every `--live` surface.

`net identity` gets this right: it says the console did not answer. Every
other `--live` path does not. `_load(None, live=<dead ip>)` returns a scene
object rather than None, and that scene is EMPTY -- so:

    wing doctor --live <dead ip>   ->  "No findings."      exit 0
    wing analyze --live <dead ip>  ->  "0 channels, 0 buses, ..."

To a live-sound engineer, "No findings" reads as "your desk is clean". It
actually means "I never reached your desk". That is the exact failure shape
this project's rules exist to prevent: silent, plausible, and wrong.

Point this at an address with NO WING on it. 10.0.0.1 is the default because
it is a common gateway address that will not answer WING's handshake; any
unused address on your network does the same job. Do NOT point it at a real
console -- a real console would make every check pass and prove nothing.

Read-only: every call here reads, and against a dead address it does not
even do that.

Run:  python -u docs\probes\probe11_unreachable_console.py 10.0.0.1
"""

from __future__ import annotations

import io
import contextlib
import sys

sys.path.insert(0, r"Z:\My Drive\CLAUDE WORKS\DEV CAVE 2026\SOUNDTECH PLAYGROUND\.claude\worktrees\project-capabilities-next-steps-8ec61c")

DEAD = sys.argv[1] if len(sys.argv) > 1 else "10.0.0.1"


def main() -> None:
    print(f"probe 11 -- an unreachable console at {DEAD}\n")

    from wing_parser.cli.commands import _load
    from wing_parser.net.identity import query_identity

    print("A. net identity -- the one path that gets this right")
    try:
        identity = query_identity(DEAD)
        print(f"   returned {identity!r}  <-- unexpected; is something answering?")
    except Exception as exc:  # noqa: BLE001 - a probe reports, never crashes
        print(f"   raised {type(exc).__name__}: {exc}")
        print("   correct: it says the console did not answer")

    print("\nB. _load(live=...) -- what every --live command actually uses")
    captured = io.StringIO()
    with contextlib.redirect_stderr(captured):
        scene = _load(None, live=DEAD)
    complaint = captured.getvalue().strip()
    print(f"   stderr said: {complaint or '(nothing)'}")
    print(f"   returned None?  {scene is None}")

    if scene is None:
        print("\nVERDICT: _load reports the failure. Nothing to fix here --")
        print("         if this repo still carries this probe, delete it.")
        return

    channels = len(scene.channels())
    buses = len(scene.buses())
    findings = len(scene.advisory.run(None))

    print(f"   scene it built: {channels} channels, {buses} buses")
    print(f"   advisory on that scene: {findings} findings")

    print()
    print("VERDICT: BUG CONFIRMED. An unreachable console yields an EMPTY")
    print("         scene, not an error. Downstream:")
    print(f"           doctor --live {DEAD}  would print 'No findings.'")
    print(f"           analyze --live {DEAD} would print '{channels} channels'")
    print("         Both read as a healthy desk. Neither reached one.")
    print()
    print("         net/identity.py already knows how to say 'no reply'.")
    print("         The live snapshot path does not consult it, or discards")
    print("         what it says. Fixing it means touching code the")
    print("         live-watch plan deliberately froze -- so it is ToanAZ's")
    print("         call, not a change to slip in.")


if __name__ == "__main__":
    main()
