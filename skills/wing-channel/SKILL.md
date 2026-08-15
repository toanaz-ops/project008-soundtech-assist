---
name: wing-channel
description: Use when asked about one specific channel in a WING .snap file — its EQ, gate, dynamics, high-pass filter, preamp gain, phantom power, polarity, tap point, group membership, or sends.
---

# Detail on one WING channel

Run:

```bash
python -m wing_parser.cli channel <path-to-.snap> <channel-number>
```

## Reading the output

The header line gives the channel's number and its raw name. Below it:

- **type** — the classifier's guess at what the channel is, with a
  confidence and the origin of the guess (`pattern`, `cache`, `llm`, or
  `manual`). Below 1.0 confidence, treat it as a question.
- **fader / muted** — the current fader level and mute state.
- **chain** — the processing block order, for example
  `GATE -> EQ -> DELAY -> INSERT`.
- **tap point** — where in the chain a bus send or matrix taps the signal.
- **scene safe** — whether the channel is protected from scene recalls.
- **DCAs / mute groups** — which DCA and mute group assignments this
  channel belongs to.
- **source** — the physical or virtual input feeding the channel, its
  preamp gain, phantom power, and polarity, or `not patched` if nothing
  feeds it.
- **HPF** — high-pass filter on/off, frequency, and slope.
- **EQ** — the model name and, if a descriptor exists for that model,
  each band's gain, frequency, and Q. If no descriptor is registered for
  the model, the bands are left unparsed rather than guessed at.
- **sends** — only the active sends, each with its destination bus,
  level, and pre/post mode.

## What this does not check

The detail view reads the scene file only. Anything needing measurement
— gain staging in dBFS, LUFS, RT60, real-world latency, gain-reduction
meters — is out of scope and is deliberately not reported. A channel
that looks fully configured here may still be mis-gained; nothing in
this view can tell you that.
