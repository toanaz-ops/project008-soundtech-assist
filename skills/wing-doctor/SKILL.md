---
name: wing-doctor
description: Use when asked to check, review, audit, or find problems in a Behringer WING .snap scene file — runs the advisory rules and reports likely misconfigurations with the rule layer that decided each one.
---

# Checking a WING scene for problems

Run:

```bash
python -m wing_parser.cli doctor <path-to-.snap>
```

Add `--json` when you need to process the findings rather than show them.
Add `--profile <name>` to apply one named show profile — `<name>` is a
`*.yaml` or `*.yml` file's stem in `knowledge/toanaz/shows/`; nothing
there applies unless named this way, and an unrecognised name raises
and lists what profiles exist.

## Reading the output

Each finding carries:

- **rule id** — one of the 32 shipped base rules (`G8`, `G7`, `G9`, `E6`,
  `R1`-`R6`/`R3M`, `S1`, `S2`, `N1`, `N2`, `G10`-`G12`, and the
  event-scoped presets `PC1`-`PC8`/`PB1`-`PB6`), or a `toanaz`/`show`
  layer rule id.
- **target** — `ch.8.send.8`, `bus.8`
- **layer** — which rule layer decided:
  - `base` — generic industry practice mined from the knowledge base
  - `toanaz` — ToanAZ's personal principles, which override base rules
  - `show` — a named profile for one kind of show
- **confidence** — present only when the rule depended on inferring what a
  channel or bus is from its name. Below 1.0, word the finding as a
  question rather than an assertion.

Rules switched off by a higher layer are listed as `[suppressed]` with the
rule that switched them off. That line is information, not a problem.

If `--profile <name>` names a show that declares an `event` (`corporate`
or `band`), any base rule tagged for a *different* event is listed as
`[off-event]` instead of being silently dropped — for example
`[off-event] PB1 is band-only; profile declares event corporate`. That
line is also information, not a problem: it just means the rule did not
apply to this kind of show.

## What this does not check

The advisory reads the scene file only. Anything needing measurement —
gain staging in dBFS, LUFS, RT60, real-world latency, gain-reduction
meters — is out of scope and is deliberately not reported. Do not infer
from a clean report that those are fine.

## Recording a verdict

When ToanAZ says a finding is wrong, record it:

```bash
python -m wing_parser.cli feedback G8:ch.8.send.8 --verdict false-positive \
  --scene <path-to-.snap> --note "small show, post-fader is the deliberate shortcut"
```

Verdicts are `correct`, `false-positive`, `irrelevant`. They append to
`knowledge/toanaz/feedback.jsonl`. Read that log across several shows to
spot a pattern worth turning into a principle in
`knowledge/toanaz/principles.yaml`.

`feedback` also accepts `--profile <name>`. Give it the same profile
`doctor` was run under: `feedback` resolves the finding id by
re-running the same advisory rules `doctor` printed, so the two
commands must be given the same `--profile` or an id `doctor` just
listed will not resolve — a finding that a profile's rule supersedes
is not among that run's findings at all.
