---
name: wing-routing
description: Use when asked how signal flows through a WING scene — orphaned channels, ALT-sourced channels, unpatched or unnamed channels, and anything the classifier could not identify.
---

# Routing map of a WING scene

Run:

```bash
python -m wing_parser.cli routing <path-to-.snap>
```

## Reading the output

The header line gives the live channel count — unmuted with a fader
above `-inf`. Below it:

- **orphans** — live channels that feed no bus, main, or matrix. A live
  orphan is signal being processed but never sent anywhere.
- **alt-sourced channels** — channels whose input comes from an ALT
  source rather than the input they are named for.
- **unpatched channels** — channels with no physical or virtual source
  connected at all.
- **live but unnamed** — channels that are live but were never given a
  name, which is often a sign a channel was activated without being
  set up.

If any channel or bus names could not be matched to a known source
type, they are listed separately at the end with a pointer to declare
them manually in `knowledge/toanaz/classifier.yaml` rather than have
the classifier guess.

## What this does not check

The routing map reads the scene file only. Anything needing measurement
— gain staging in dBFS, LUFS, RT60, real-world latency, gain-reduction
meters — is out of scope and is deliberately not reported. A channel
that is patched and routed correctly here may still be silent at the
stage box; nothing in this view can tell you that.
