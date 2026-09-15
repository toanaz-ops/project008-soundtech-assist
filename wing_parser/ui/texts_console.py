"""The Console page's strings, split out of `texts.py` (wave 2).

Same rule, same table, one file down: `texts.py` crossed the ~200-line
ceiling `test_ui_house_style.py:173` enforces, and the Console page --
a whole page of live-desk vocabulary, still growing through tasks 12-13
-- is the one part of that table naming a single responsibility.
`texts.py` merges this dict into `TEXTS`, so `text("console.pull")` is
reached exactly as every other key is.
"""

from __future__ import annotations

CONSOLE_TEXTS: dict[str, str] = {
    "console.address": "Console",
    "console.address_hint": "IP address or hostname",
    "console.connect": "Connect",
    "console.disconnect": "Disconnect",
    "console.cancel": "Cancel",
    "console.lamp": "●",
    "console.identity": "{name} · {model} · firmware {firmware}",
    "console.connecting": "Asking {host} who it is...",
    "console.cancelled": "Cancelled — nothing was read.",
    "console.timeout": (
        "No reply from {host} within {seconds} s — check the address "
        "and that the desk is on this network."
    ),
    "console.failed": "Cannot reach {host}: {error}",
    "console.busy": "A console call is already running — cancel it or wait.",
    "console.no_address": "Type a console address first — an IP or a name.",
    "console.discovery": "Discovery",
    "console.discover": "Discover",
    "console.rerun": "Rerun",
    "console.discovering": "Walking the schema tree...",
    "console.walk_cancelled": "Cancelled — nothing was walked.",
    "console.walk_timeout": (
        "No reply from {host} within {seconds} s while walking the "
        "schema."
    ),
    "console.walk_busy": (
        "A schema walk is already running — cancel it or wait."
    ),
    "console.walk_failed": "Could not walk the schema at {host}: {error}",
    "console.inventory": "{total} leaves ({breakdown})",
    "console.unresolved_banner": (
        "Unresolved: {families} — would watch {total} leaves; rerun "
        "before believing the list is small."
    ),
    "console.snapshot": "Snapshot",
    "console.pull": "Pull",
    "console.pulling": "Reading the whole console from {host}...",
    "console.pull_cancelled": "Cancelled — nothing was pulled.",
    "console.pull_timeout": (
        "No reply from {host} within {seconds} s while pulling the scene."
    ),
    "console.pull_busy": (
        "A console read is already running — cancel it or wait."
    ),
    "console.pull_failed": "Could not pull the scene from {host}: {error}",
    "console.incomplete_banner": (
        "{report} — the scene is loaded and usable, but it is not the "
        "whole desk."
    ),
    "console.scene_loaded": "Scene loaded — {findings} finding(s).",
    "console.open_doctor": "Open Doctor",
    "console.export": "Export to .snap...",
    "console.export_title": "Export the pulled scene",
    "console.exported": "Exported to {file}",
    "console.export_failed": "Could not write {file}: {error}",
    "console.watch": "Watch",
    "console.start": "Start watch",
    "console.stop": "Stop",
    "console.reconnect": "Reconnect",
    "console.interval": "Interval",
    "console.interval_suffix": " s",
    "console.col.time": "Time (s)",
    "console.col.strip": "Strip",
    "console.col.key": "Key",
    "console.col.change": "Change",
    # Two value cells, formatted where every other value cell is: a
    # repr, so "0" and 0 never read the same, and the arrow is language
    # like any other glyph.
    "console.event_time": "{seconds:.2f}",
    "console.event_change": "{before!r} → {after!r}",
    "console.watching": "Watching {host} — {total} leaves.",
    "console.watch_rate": "{rate:.2f} events/s · {elapsed:.1f} s elapsed",
    "console.stopping": "Stopping — the watch ends after this round.",
    "console.watch_stopped": (
        "Watch ended — {events} event(s) over {rounds} round(s)."
    ),
    "console.watch_cancelled": (
        "Watch stopped — the events above stay on screen."
    ),
    "console.watch_lost": (
        "Lost {host}: {error} — the events above are real. Reconnect to "
        "carry on."
    ),
    "console.no_watch_list": (
        "Discover the console first — a watch needs the leaf list."
    ),
}
