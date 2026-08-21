---
name: wing-watch
description: Use when asked what is changing on a live Behringer WING right now — which fader moved, what was muted or soloed — as opposed to reading a saved .snap file.
---

# Watching a live WING console

Run:

```powershell
python -m wing_parser.cli net watch 192.168.128.28
python -m wing_parser.cli net watch 192.168.128.28 --json --until 120
```

`wing net watch <ip>` reports changes on a running console by polling —
it never subscribes to anything. Add `--interval <seconds>` to change the
polling rate (default `0.25`; a 208-leaf round measured 22 ms, so a quiet
desk leaves the network mostly idle between rounds). Add
`--until <seconds>` to stop automatically; without it, the session runs
until Ctrl+C.

## Why it polls instead of subscribing

A WING console holds only one OSC subscription at a time, and it expires
after 10 seconds. Subscribing would take that slot from WING-Edit,
Companion, or whatever else is already connected. Polling is a plain
request/reply exchange — the same shape as `net get` — so it claims
nothing another client can lose. That is what lets this run alongside
WING-Edit or Companion without displacing them.

## Reading the output

Each line is one change: elapsed time, the strip's name (or its address
if the strip has none), the key, and the before/after values. In
`--json` mode stdout carries JSON and nothing else — a header object
naming what is being watched, then one object per change.

It watches the **effective** values. `$fdr` and `$mute` are the value
*after* DCA contribution and mute-override are folded in, not the
strip's own position — that is what makes pulling a DCA down show up on
every channel it governs, without this watching DCA membership at all.
`$solo` is watched the same "$"-prefixed, read-only way, on
channels/buses/mains/matrices and on DCAs.

## What it cannot do

It samples rather than streams: a change that appears and reverts inside
one round is missed entirely, not just delayed. There are no meters —
the WING exposes none over OSC, measured in
`docs/superpowers/specs/2026-08-21-live-watch-design.md` §2.3 — so this
cannot show gain reduction, PPM, or any other live level, no matter how
fast the polling.

## If the watch-list is incomplete

The list is built from a schema walk of the console, so it only ever
contains addresses that actually exist. If anything failed to resolve,
the session says so at startup rather than silently watching less than
it claims: a `warning:` line on stderr in text mode, an `"unresolved"`
key in the first JSON object in `--json` mode. If that is non-empty,
say so rather than reporting a quiet desk.

## When a console is not reachable

A console that is unreachable or switched off prints `error: <message>`
and exits non-zero. Check the IP with `net identity` first.
