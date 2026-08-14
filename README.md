# wing-parser

Read and analyse Behringer WING `.snap` scene files: parse the format,
classify what each channel and bus actually is, and run an advisory
layer that flags likely misconfigurations. It runs fully offline.

## Phase 1 scope

Phase 1 covers reading a saved `.snap` file and reasoning about it. It
does **not** connect to a live console over OSC, write changes back to
a console, or analyse audio (LUFS, RT60, SPL, real-world latency,
gain-reduction metering). Everything the tool reports is derived from
the scene file's own JSON — channel names, fader positions, routing,
processing chains, EQ and dynamics settings — never from a measurement
you would need a live signal to take. A clean report from `doctor`
means nothing in the file looked wrong; it does not mean the mix
sounds right.

## Install

```bash
pip install -e ".[dev,llm,mcp]"
```

`dev` pulls in `pytest` and `pytest-cov` for running the test suite.
`llm` and `mcp` are both optional and independent of each other and of
the core tool — see [Offline guarantee](#offline-guarantee) below.

## CLI commands

Every command is invoked as `python -m wing_parser.cli <command> ...`
(or `wing <command> ...` once installed, via the `wing` console script).

### `analyze` — overview of a scene

```bash
python -m wing_parser.cli analyze user-files/example-Vu.snap
```

```
example-Vu.snap  [snapshot.11 / Wing-Edit 3.3.x]
  40 channels, 16 buses, 4 mains, 8 matrices
  3 live channels (unmuted, fader above -inf)
  34 named channels:
  -  1  Mic 1 VOX IEM1            -inf  speech.vocal
  -  2  Mic 2 VOX IEM2            -inf  speech.vocal
  ...
```

### `channel` — full detail on one channel

```bash
python -m wing_parser.cli channel user-files/example-Vu.snap 8
```

Prints the channel's inferred source type and confidence, fader and
mute state, processing chain order, tap point, scene-safe flag, DCA and
mute-group membership, preamp source (gain, phantom, polarity), HPF,
EQ bands (only if a descriptor exists for that EQ model), and every
active send with its destination bus, level, and pre/post mode.

### `routing` — how signal flows through the scene

```bash
python -m wing_parser.cli routing user-files/example-Vu.snap
```

Lists live orphans (feeding nothing), ALT-sourced channels, unpatched
channels, live-but-unnamed channels, and any channel or bus name the
classifier could not identify at all — with a pointer to declare it
manually in `knowledge/toanaz/classifier.yaml` instead of guessing.

### `doctor` — advisory findings

```bash
python -m wing_parser.cli doctor user-files/example-Vu.snap
```

Runs the three-layer advisory rules (see below) and prints each
finding's rule id, target, deciding layer, and confidence when the
rule depended on a name-based classification. Add `--json` for
machine-readable output. See [The advisory model](#the-advisory-model).

### `diff` — what changed between two scenes

```bash
python -m wing_parser.cli diff user-files/factory-scene.snap user-files/example-Vu.snap
```

Prints every changed field as a dotted path (`ch.1.eq.bands.1.gain`)
with its before and after value, and a magnitude for numeric fields.
`--limit N` caps how many print (default 50); the count of total
differences is always the true total.

### `feedback` — record a verdict on a finding

```bash
python -m wing_parser.cli feedback G8:ch.8.send.8 --verdict false-positive \
  --scene user-files/example-Vu.snap --note "shared band IEM, guitar is the exception"
```

Verdicts are `correct`, `false-positive`, or `irrelevant`. Each call
appends one record to `feedback.jsonl` in the active knowledge
directory (see [Knowledge directory](#knowledge-directory-and-search-order)
below); it never rewrites history. The finding id must match a finding
`doctor` currently reports for that scene — `wing doctor` lists the
current ids.

## The advisory model

`doctor` evaluates rules in three layers, and every finding records
which layer decided it:

- **`base`** — generic industry practice mined from
  `docs/knowledge-base/`, shipped inside the package at
  `wing_parser/advisory/base_rules/*.yaml`. This is the textbook: rules
  like G8 ("a post-fader monitor send lets FOH fader moves change what
  a performer hears") or G7 ("a monitor bus should carry a limiter")
  fire whenever their condition matches, with no knowledge of any
  specific show.
- **`toanaz`** — ToanAZ's own principles, hand-edited in
  `knowledge/toanaz/principles.yaml`. A principle can `supersede` one
  or more base rules, either unconditionally (`hardness: hard`) or only
  when a stated condition holds (`hardness: flexible`, gated by
  `applies_when`). For example, a shared-band-IEM principle can
  supersede G8 — the generic rule says every post-fader monitor send is
  suspect, but a working engineer's practice may be that only the
  guitarist needs a pre-fader send and everyone else tracks FOH on
  purpose. When a principle suppresses a base rule, `doctor` reports
  the suppression and names the rule that did it, rather than silently
  dropping the finding.
- **`show`** — one-off overrides for a single show, dropped as
  `*.yaml` or `*.yml` files in `knowledge/toanaz/shows/`.

Base rules are not beyond question. G7, for instance, checks a bus's
dynamics model against a hardcoded list of limiter identifiers; only
`COMP` and `CMB` appear as dynamics models anywhere in the sample
files, so G7 currently fires on every monitor bus it evaluates. Treat
`doctor`'s output as what the stated rule checks, not as ground truth
— that is exactly what the `toanaz` and `show` layers exist to correct
once a human has looked at the finding and rendered a verdict.

### Knowledge directory and search order

`knowledge/toanaz/` holds `principles.yaml`, `classifier.yaml` (manual
name-to-type declarations, checked before the pattern matcher and the
LLM fallback), `feedback.jsonl` (the verdict log), and a `shows/`
directory for per-show rule files. Its location resolves in this
order, implemented in `wing_parser/config.py`:

1. An explicit override argument, where the API accepts one.
2. The `WING_KNOWLEDGE_DIR` environment variable.
3. The first existing directory among a fixed search list:
   the in-repo `knowledge/toanaz/`, then `~/.config/wing-skill/`, then
   `~/wing-skill/`.
4. If none of those exist, the in-repo default is used (and created on
   first write).

The in-repo default is deliberate: these principles are a long-lived
asset, and git history shows how the judgement behind them evolved.
Setting `WING_KNOWLEDGE_DIR` once moves the whole set elsewhere with no
code change — this is exactly how the test suite and the runnable
examples in `examples/` isolate themselves from the real knowledge
directory.

## Offline guarantee

Parsing and rule evaluation are strictly deterministic — the file
format decoder, the descriptors, the query layer, and the rule engine
never call a model. The **only** model call anywhere in the system is
an optional classifier fallback (`wing_parser/classifier/llm.py`), used
only for a channel or bus name the pattern matcher in
`wing_parser/classifier/matcher.py` cannot resolve on its own.

That fallback is unavailable, and every command still runs to
completion, when any of the following hold:

- `WING_DISABLE_LLM` is set to anything other than empty, `0`, `false`,
  `no`, or `off` (case-insensitive) — the explicit kill switch.
- `ANTHROPIC_API_KEY` is not set.
- The optional `anthropic` package (the `llm` extra) is not installed.
- The network is unreachable, or the API call otherwise fails for any
  reason, including a model safety refusal.

In every one of those cases the name in question degrades to a
`kind: unknown, confidence: 0.0` classification rather than raising —
this tool is written for venues where the network is unreliable or
absent. Names the pattern matcher already resolves (most of them, in
practice) are completely unaffected either way.

## Extending the rules without touching Python

Everything below is plain YAML; no code change or restart of anything
is required beyond re-running the command.

- **Add a rule** — new base rules go in
  `wing_parser/advisory/base_rules/*.yaml` (any filename; both
  `monitors.yaml` and `dynamics.yaml` are loaded together). Each entry
  needs `id`, `title`, `severity` (`error`, `warning`, or `info`), a
  `when.for_each` (`channel`, `bus`, or `channel.sends`) with a `where`
  predicate, and a `message` template that can reference the bound
  context (`{channel.number}`, `{bus.name}`, and so on).
- **Add a principle** — append to the `principles:` list in
  `knowledge/toanaz/principles.yaml`. Give it an `id`, a `hardness`
  (`hard` always active, `flexible` gated by `applies_when`), and a
  `supersedes` list naming the base rule ids it switches off. A
  principle whose only job is to suppress a base rule needs no `when`
  block of its own.
- **Add a show-specific override** — drop a `.yaml` or `.yml` file into
  `knowledge/toanaz/shows/`, using the same rule shape as a base rule.
  These load with `layer: show`, the highest-priority layer.
- **Add a descriptor** — the descriptors under
  `wing_parser/descriptors/data/*.yaml` interpret encoded fields the
  console stores as raw numbers or short codes. For example,
  `eq_models.yaml` maps an EQ model id to its band layout; a model with
  no entry there yields `bands=None` and a `descriptor_missing`
  anomaly rather than a fabricated value, which is deliberate — only
  `STD` and `PULSAR` currently appear in either sample file, so no
  other model's layout has been verified against real data.
- **Declare a name manually** — if the classifier keeps guessing wrong
  (or refusing to guess) at a channel or bus name, add it directly
  under `channels:` or `buses:` in `knowledge/toanaz/classifier.yaml`.
  A manual entry is checked before the pattern matcher and the LLM
  fallback, so it always wins and costs nothing to resolve again.

## Tests

```bash
python -m pytest
```

## Spec

The full design — architecture, the `.snap` format, the classifier,
the query API, the advisory module, the feedback loop, and the Phase 1
success criteria — is written up at
[`docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md`](docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md).
