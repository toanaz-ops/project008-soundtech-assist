"""The wave-3 write strings, split out of `texts.py` like the console's.

Namespace `console.write.*`, not `write.*` (W7): the flat table already
holds `changes.*` keys for the journal dock, and a bare `write.*` would
read as a sibling of those while meaning something else entirely.

Every string an operator can see while a packet is about to leave is here,
so the whole vocabulary of the dangerous half of this app is one file a
reviewer can read end to end.

**Marks are limited to what the VENDORED font carries** (D-51): U+2713
`✓`, U+00D7 `×` and plain `!`. IBM Plex Sans has no U+26A0 or U+2717, so
those two came back from a per-machine Windows fallback -- or, on the
no-reply badge, as a replacement box. `tests/test_ui_texts.py` pins it.
"""

from __future__ import annotations

WRITE_TEXTS: dict[str, str] = {
    # -- arming, once per connection (F4) --------------------------------
    "console.write.arm_title": "Arm writing to this console",
    "console.write.reading": "Asking the desk…",
    "console.write.desk": "{name} · {model} · serial {serial}",
    "console.write.identity_failed": (
        "Cannot identify the desk at {host}: {error} — not armed."
    ),
    "console.write.latch": "This desk is NOT running a show right now.",
    "console.write.latch_why": (
        "CLAUDE.md: never during a show without explicit confirmation."
    ),
    "console.write.name_prompt": "Type this console's name to confirm:",
    "console.write.name_wrong": "That is not this console's name.",
    "console.write.name_pending": "Waiting for the console's name…",
    "console.write.arm": "Arm",
    "console.write.armed": "Armed: {name}",
    "console.write.refused": "Refused: {error}",

    # -- the selector (F3) -----------------------------------------------
    "console.write.level": "Apply to console",
    "console.write.manual": "Manual",
    "console.write.delayed": "Delayed",
    "console.write.immediate": "Immediate",

    # -- the journal row's Send button (S2.2) ----------------------------
    "console.write.send": "Send to console",
    "console.write.blocked": "Connect to the console (Ctrl+7) to send this.",
    "console.write.sending": "Sending {address}…",
    "console.write.gate_closed": (
        "The console connection dropped. Nothing was sent."
    ),

    # -- the countdown (F5) ----------------------------------------------
    "console.write.delay_title": "Applying to the console in {seconds} s",
    "console.write.address": "{address}",
    "console.write.countdown": "{remaining} s",
    "console.write.desk_value": "The desk now holds: {value}",
    "console.write.file_value": "The scene file expected: {value}",
    "console.write.after": "It will become: {value}",
    "console.write.mismatch": (
        "! The desk holds {desk}, the scene file expected {file}. "
        "Applying replaces the desk's value."
    ),
    "console.write.no_read": (
        "The desk did not answer a read of this address. It may not exist here."
    ),
    "console.write.apply_now": "Apply now",
    "console.write.extend": "+5 s",
    "console.write.cancel": "Cancel",
    "console.write.cancelled": (
        "Not applied. The scene edit stays — use Undo to drop it too."
    ),

    # -- the three outcomes (F8) -----------------------------------------
    "console.write.sent": "sent ✓ the desk holds {readback}",
    "console.write.clamped": (
        "! the desk holds {readback}, not {after} — the console "
        "clamped it."
    ),
    "console.write.no_reply": (
        "× {address}: the desk did not answer. It may or may not have "
        "landed."
    ),

    # -- the sent ledger (F7, W12) ---------------------------------------
    "console.write.sent_heading": "Sent to console",
    "console.write.ledger_row": "{address}: {desk!r} → {after!r}",
    "console.write.revert": "Revert",
    "console.write.revert_all": "Revert all",
    "console.write.revert_stop": "Stop",
    "console.write.reverting": "Reverting {done}/{total}: {address}",
    "console.write.reverted": "reverted ✓ the desk holds {readback}",
    "console.write.revert_stopped": (
        "Stopped after {done} of {total}. The rest were left as they are."
    ),
    "console.write.revert_cancelled": (
        "Not reverted. The desk keeps the written value."
    ),
    "console.write.revert_unknown": (
        "The desk never said what it held before, so there is nothing to "
        "put back."
    ),
    "console.write.revert_skipped": (
        "Skipped {skipped} row{plural}: the desk never said what it held "
        "before, so there is nothing to put back."
    ),
    "console.write.revert_failed": (
        "The revert run stopped: {error}. The rest were left as they are."
    ),
}
