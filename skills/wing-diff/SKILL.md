---
name: wing-diff
description: Use when asked what changed between two WING scenes -- saved .snap files, a running console, or one of each.
---

# Comparing two WING scenes

Run:

```powershell
python -m wing_parser.cli diff <before-file> <after-file>
```

`diff` takes a file **list**, not two fixed positionals: it needs exactly
two sides, and each side comes from either a file in that list or a
`--live-*` flag. Add `--live-before <ip>` and/or `--live-after <ip>` to
read a running console for that side instead of a file:

```powershell
python -m wing_parser.cli diff --live-before 192.168.128.28 last-night.snap
python -m wing_parser.cli diff --live-before 192.168.128.28 --live-after 192.168.128.30
```

The first form compares the console directly against a saved file and
takes exactly one file argument (for the side `--live-before` did not
supply); the second compares two consoles and takes no file arguments at
all.

Add `--limit <n>` to change how many differences print (default 50); the
diff itself always computes the full set, it just truncates the display.

## Reading the output

The first line gives the total number of differences found. Each
difference line is a dotted field path — for example
`ch.1.eq.bands.1.gain` — followed by the value in `<before-file>`, an
arrow, and the value in `<after-file>`. A numeric field also prints a
`(delta ...)` showing the magnitude of the change.

The path encodes exactly where the change lives: `ch.<n>.<field>` for a
channel field, `bus.<n>.<field>` for a bus, and so on through the same
structure the `analyze` and `channel` commands use. When you only care
about one kind of change — fader moves, EQ moves, routing changes —
filter the printed paths by suffix, for example everything ending in
`.fader_dB`.

Comparing a factory default scene against a show scene is a good way to
see everything a show file customized; comparing two versions of the
same show scene shows what actually moved between soundchecks.

## What this does not check

It reports that a value changed, not whether the change was correct or
whether it affected what anyone heard. Anything needing measurement —
gain staging in dBFS, LUFS, RT60, real-world latency, gain-reduction
meters — is out of scope and is deliberately not reported.
