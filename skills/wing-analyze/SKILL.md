---
name: wing-analyze
description: Use when asked for an overview of a Behringer WING .snap scene file — channel count, names, levels, inferred source types, firmware version, and parser anomalies.
---

# Overview of a WING scene

Run:

```bash
python -m wing_parser.cli analyze <path-to-.snap>
```

## Reading the output

The first two lines give the file's firmware type id and label (for
example `snapshot.11 / Wing-Edit 3.3.x`) and the channel/bus/main/matrix
counts, followed by how many channels are live — unmuted with a fader
above `-inf`.

Each named channel then gets one line: its number, its name, its fader
level, and its inferred source type as `<kind> <confidence>` — a
classifier guess, not a fact read verbatim from the file. A low
confidence means the name did not match any known pattern closely; treat
that guess as a question, not an assertion. Unnamed channels are
omitted from this list, not silently dropped from the channel count.

If the file has anomalies — fields the parser could not fully interpret,
such as a dynamics or EQ model with no descriptor — they are listed at
the end with the affected location and a detail string. An anomaly means
the parser is telling you it fell back rather than guessed.

## What this does not check

The overview reads the scene file only. Anything needing measurement —
gain staging in dBFS, LUFS, RT60, real-world latency, gain-reduction
meters — is out of scope and is deliberately not reported. A clean
overview does not mean the mix sounds correct, only that the file
parsed without incident.
