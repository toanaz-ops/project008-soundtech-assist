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
machine-readable output. Add `--profile <name>` to apply one named
show profile — `<name>` is a `*.yaml` or `*.yml` file's stem in
`knowledge/toanaz/shows/`; nothing in that directory applies unless
named this way, and an unrecognised name raises and lists what
profiles exist. See [The advisory model](#the-advisory-model).

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
  --scene user-files/example-Vu.snap --note "small show, post-fader is the deliberate shortcut"
```

Verdicts are `correct`, `false-positive`, or `irrelevant`. Each call
appends one record to `feedback.jsonl` in the active knowledge
directory (see [Knowledge directory](#knowledge-directory-and-search-order)
below); it never rewrites history. The finding id must match a finding
`doctor` currently reports for that scene — `wing doctor` lists the
current ids. `feedback` also accepts `--profile <name>`, with the same
meaning as on `doctor`, and it matters here for a specific reason:
`feedback` resolves the finding id by re-running the same advisory
rules `doctor` printed, so the two commands must be given the same
`--profile` or an id `doctor` just listed will not resolve — a finding
that a profile's rule supersedes is not among that run's findings at
all.

## The advisory model

`doctor` evaluates rules in three layers, and every finding records
which layer decided it:

- **`base`** — generic industry practice mined from
  `docs/knowledge-base/`, shipped inside the package at
  `wing_parser/advisory/base_rules/*.yaml`. This is the textbook: rules
  like G8 ("a post-fader monitor send lets FOH fader moves change what
  a performer hears"), G7 ("an IEM output should carry a limiter",
  error), or G9 ("a wedge or unspecified monitor output should carry a
  limiter", warning — the same check one severity down, split off
  2026-08-16 because the hearing-injury claim is IEM-scoped) fire
  whenever their condition matches, with no knowledge of any specific
  show.
- **`toanaz`** — ToanAZ's own principles, hand-edited in
  `knowledge/toanaz/principles.yaml`. A principle can `supersede` one
  or more base rules, either unconditionally (`hardness: hard`) or only
  when a stated condition holds (`hardness: flexible`, gated by
  `applies_when`). The shipped file holds no principle yet — nothing
  he does depends on the show alone regardless of what kind of show it
  is — so the worked example of a rule superseding a base rule lives
  one layer down, in `show`. When a principle or show rule suppresses a
  base rule, `doctor` reports the suppression and names the rule that
  did it, rather than silently dropping the finding.
- **`show`** — a named profile for one kind of show, hand-edited as
  `*.yaml` or `*.yml` files in `knowledge/toanaz/shows/` and selected
  with `--profile <name>`, where `<name>` is the file's stem. Nothing
  in that directory applies unless it is named on the command line; an
  unrecognised name raises and lists what profiles exist. The shipped
  `shows/small.yaml` supersedes G8 on a small or easy show: pre-fader
  monitor sends are ToanAZ's norm, especially on a big show, but on a
  small or easy show he deliberately runs them post-fader instead,
  trading monitor independence for setup speed. That profile records
  the deviation as deliberate rather than leaving G8 to re-flag it on
  every check.

Base rules are not beyond question. G7 and G9, for instance, check only
that a monitor output's dynamics processor is switched on
(`bus.dyn.on`), not that the model loaded there is actually a limiter
— the `dyn.mdl` token a WING stores for a limiter is not recorded
anywhere in this repository and must not be guessed, so a monitor
output carrying a compressor that is switched **on** is deliberately
not reported (see
[design spec §7.1](docs/superpowers/specs/2026-08-16-advisory-loop-closure-design.md#71-the-limiter-token)
for the exact clause to add once that token is known). Treat
`doctor`'s output as what the stated rule checks, not as ground truth
— that is exactly what the `toanaz` and `show` layers exist to correct
once a human has looked at the finding and rendered a verdict.

### Monitor role hierarchy

The classifier resolves a bus, aux, main or matrix's role from its name
using the patterns in `wing_parser/classifier/data/patterns.yaml`. A
monitor destination classifies at one of three levels of specificity:

- `monitor` — a generic monitor send (`MON ...`), flavour unspecified.
- `monitor.iem` — an in-ear mix (`IEM1`, `in ear`).
- `monitor.wedge` — a floor wedge or sidefill (`wedge`, `SIDE`,
  `sidefill`).

`Bus.is_monitor` is true for any of the three, confidence permitting.
Rules pick the granularity they actually need:

- **G8** (post-fader monitor send) matches `destination_bus.role` with
  the `starts_with: monitor` predicate operator, so it fires on all
  three kinds alike — a FOH fader move changes what a performer hears
  the same way regardless of which monitor flavour carries it.
- **G7** (no active dynamics, error) fires only on a confidently
  classified `monitor.iem` — the hearing-injury claim in the knowledge
  base is scoped to in-ears.
- **G9** (no active dynamics, warning) fires on `monitor` or
  `monitor.wedge` — the same check, one severity down, for outputs the
  injury claim doesn't cover as directly.

### Rule reference

`doctor` ships 32 base rules across eight files in
`wing_parser/advisory/base_rules/`. Every rule fires at `base` layer
unless a `toanaz` principle or a `show` profile supersedes it (see
above), and an `info`-severity rule is never wrong to see fire — it is
a note, not an alarm. `PB*` and `PC*` are event-scoped **presets**: an
info-tier rule set for one kind of show. With no profile declared, all
rules run, presets included; declaring a profile with an `event` set
switches off base rules tagged with a *different* event (see below).
`N2` ships
`enabled: false` — its rationale (in `naming.yaml`) explains that the
fader-floor discriminator it needs does not reliably separate a
factory-default bus from one genuinely in use, so it stays off rather
than risk noise on an unconfigured console.

| id | severity | event | file | what it flags |
| --- | --- | --- | --- | --- |
| E6 | warning | universal | dynamics.yaml | Gate and automix on the same channel |
| G7 | error | universal | monitors.yaml | IEM output has no active dynamics |
| G8 | warning | universal | monitors.yaml | Monitor send is post-fader |
| G9 | warning | universal | monitors.yaml | Wedge or monitor output has no active dynamics |
| G10 | info | universal | monitors_quality.yaml | IEM output receives no ambient mic |
| G11 | warning | universal | monitors_quality.yaml | More than five narrow notches on a monitor output |
| G12 | info | universal | monitors_quality.yaml | EQ boost above 8 kHz on a house output |
| N1 | info | universal | naming.yaml | Channel is in use but unnamed |
| N2 | info, **disabled** | universal | naming.yaml | Output receives signal but is unnamed |
| PB1 | info (preset) | band | presets_band.yaml | Snare-bottom channel is not polarity inverted |
| PB2 | info (preset) | band | presets_band.yaml | Hi-hat HPF outside the 160-250 Hz window |
| PB3 | info (preset) | band | presets_band.yaml | Ride HPF outside the 200-300 Hz window |
| PB4 | info (preset) | band | presets_band.yaml | Overhead HPF outside the 160-450 Hz window |
| PB5 | info (preset) | band | presets_band.yaml | Kick or bass high-passed above 45 Hz |
| PB6 | info (preset) | band | presets_band.yaml | Click reaches more than two IEM mixes |
| PC1 | info (preset) | corporate | presets_corporate.yaml | Lectern HPF outside the 90-160 Hz window |
| PC2 | info (preset) | corporate | presets_corporate.yaml | Lectern/panel channel missing the low-mid boundary cut |
| PC3 | info (preset) | corporate | presets_corporate.yaml | Lectern/panel channel missing the presence lift |
| PC4 | info (preset) | corporate | presets_corporate.yaml | Lectern gate outside the documented envelope |
| PC5 | info (preset) | corporate | presets_corporate.yaml | Speech compression ratio above 4:1 |
| PC6 | info (preset) | corporate | presets_corporate.yaml | Panel HPF outside the 100-160 Hz window |
| PC7 | info (preset) | corporate | presets_corporate.yaml | MC in an automix group without a weight advantage |
| PC8 | info (preset) | corporate | presets_corporate.yaml | Q&A mic unmuted in the saved scene |
| R1 | error | universal | routing.yaml | Click track reaches a FOH main |
| R2 | error | universal | routing.yaml | Talkback reaches a FOH main |
| R3 | error | universal | routing.yaml | Timecode routed into a mix destination |
| R3M | error | universal | routing.yaml | Timecode routed into a main |
| R4 | warning | universal | routing.yaml | Send to a record destination is post-fader |
| R5 | warning | universal | routing.yaml | Main-send to a record main is post-fader |
| R6 | error | universal | routing.yaml | Remote caller feeds its own mix-minus bus |
| S1 | warning | universal | speech.yaml | Speech channel without a high-pass filter |
| S2 | error | universal | speech.yaml | Music-family channel inside an active automix group |

This table is generated from the shipped YAML, not hand-maintained
prose; to regenerate it against whatever is actually loaded, run:

```bash
python -c "from wing_parser.advisory.loader import load_base_rules; \
[print(r.id, r.severity, r.event, r.title) for r in sorted(load_base_rules(), key=lambda r: r.id)]"
```

The untouched shipped `user-files/example-Vu.snap` currently yields 22
findings under this rule set with no profile; `user-files/factory-scene.snap`
yields 0.

### The event mechanism

Every rule — base, principle, or show — carries an `event` field:
`universal` (the default), `corporate`, or `band`. Of the 32 base
rules, 14 are event-scoped: the eight `presets_corporate.yaml` rules
(PC1-PC8) are `corporate`; the six `presets_band.yaml` rules (PB1-PB6)
are `band`. Everything else is `universal` and always eligible.

A show profile can declare its own event at the top of its YAML file:

```yaml
# knowledge/toanaz/shows/gala.yaml
event: corporate
rules: []
```

When `--profile gala` is passed, `doctor` and `feedback` keep every
`universal` rule plus every rule whose `event` matches the declared
one, and print the rest as a separate transparency line rather than
silently dropping them:

```
  [off-event] PB1 is band-only; profile declares event corporate
```

A profile with no `event:` key at all — like the shipped
`shows/small.yaml` — declares nothing, and every base rule stays
event-eligible; only its `supersedes` entries (see above) suppress
anything. Declaring an unrecognised event value (anything other than
`universal`, `corporate`, or `band`) raises at load time, the same way
an unrecognised `--profile` name does.

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
  `wing_parser/advisory/base_rules/*.yaml` (any filename; every `*.yaml`
  file in that directory — currently eight of them — is loaded
  together). Each entry needs `id`, `title`, `severity` (`error`,
  `warning`, or `info`), a `when.for_each` with a `where` predicate, and
  a `message` template that can reference the bound context
  (`{channel.number}`, `{bus.name}`, and so on). `when.for_each` is one
  of:
  - `channel` — every channel, bound as `channel`.
  - `bus` — every bus, excluding auxes, mains and matrices, bound as
    `bus`.
  - `output` — every summing destination — buses, auxes, mains *and*
    matrices — bound as `bus` regardless of family. This is how G7 and G9
    (both `for_each: output`) see monitor mixes that live on a matrix, not
    just a bus.
  - `channel.sends` — one target per bus or matrix send, **on or off** —
    binding `channel`, `send`, and `destination_bus`. The iterator itself
    applies no `send.on` filter; a rule that only cares about active sends
    must say so in its own `where` clause, the way G8 states
    `send.on: true` explicitly (see `monitors.yaml`) — omitting it is an
    easy trap that fires the rule on a send that is switched off, too.
    This is also G8's route to matrix destinations: the iterator handles
    `send.dest_kind == "matrix"` directly, a different mechanism from the
    `output` iterator above.
  - `channel.main_sends` — one target per channel's send to a main,
    binding `channel`, `main_send`, and `destination_main`.
  - `none` — no targets at all, for a rule that exists only to
    `supersede` another (see the show-profile bullet below).

  A `where` (or `any_of` clause) value is either a bare literal
  (equality) or a single-key operator mapping: `not`, `in`, `not_in`,
  `gt`, `lt`, `is_null`, or `starts_with` (a string-prefix match — G8
  uses `destination_bus.role: {starts_with: monitor}` to catch
  `monitor`, `monitor.iem` and `monitor.wedge` in one clause; see
  [Monitor role hierarchy](#monitor-role-hierarchy)). An unknown
  operator name is a load-time error naming the offending file, not a
  runtime `ValueError`. An optional `event` field (`universal` by
  default, or `corporate`/`band`) scopes the rule to a show profile
  declaring the matching event — see
  [The event mechanism](#the-event-mechanism).
- **Add a principle** — append to the `principles:` list in
  `knowledge/toanaz/principles.yaml`. Give it an `id`, a `hardness`
  (`hard` always active, `flexible` gated by `applies_when`), and a
  `supersedes` list naming the base rule ids it switches off. A
  principle whose only job is to suppress a base rule needs no `when`
  block of its own.
- **Add a show-specific override** — drop a `.yaml` or `.yml` file into
  `knowledge/toanaz/shows/`, using the same rule shape as a base rule.
  The filename (without its extension) becomes the profile name; the
  file is a **named profile**, and nothing in it applies until that
  name is passed as `--profile <name>` to `doctor` or `feedback`. An
  unrecognised `--profile` name raises rather than silently running
  with no profile, and lists what profiles exist. These load with
  `layer: show`, the highest-priority layer. A show rule whose only job
  is to `supersede` a base rule needs no `when` or `message` either —
  the same supersede-only shape "Add a principle" describes above. The
  shipped `knowledge/toanaz/shows/small.yaml` is exactly that: no
  `when:`, no `message:`, just `supersedes: [G8]` and the rationale for
  switching it off.
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
- **Derived properties** — beyond the raw fields a `.snap` file stores,
  a `where` or `message` path can reach a handful of computed
  properties (`wing_parser/query/bus.py`, `wing_parser/query/channel.py`):
  - **Bus** (`bus.<name>`): `role`, `is_monitor`, `notch_count` (EQ bands
    narrow and deep enough to read as feedback notches: `q >= 8`,
    `gain <= -6 dB`), `max_boost_above_8k` (the highest EQ boost above
    8 kHz, or `None` if there isn't one), `receives_ambient` (fed by a
    confidently classified ambient-mic channel), `receives_any` (fed by
    any channel at all).
  - **Channel** (`channel.<name>`): `iem_send_count` (active sends
    landing on a confidently classified `monitor.iem` destination),
    `eq_has_lowmid_cut` (an EQ band pulled down between 200-500 Hz),
    `eq_has_presence_lift` (a band pushed up between 2-4 kHz), `in_use`
    (patched, unmuted, routed somewhere, and fader above -90 dB — the
    discriminator N1 relies on to keep a factory-default scene, every
    fader at the -144 sentinel, from reading as in use).

## MCP server

An [MCP](https://modelcontextprotocol.io) server exposes the same
functionality as the CLI to a tool-calling model (Claude Desktop, Claude
Code, or any other MCP client) over stdio. It is optional and independent
of the core parser — nothing else in this repo imports it, and the CLI
works fully without it.

Install the extra and run the server:

```bash
pip install -e ".[mcp]"
wing-mcp
```

`wing-mcp` is the console script `pyproject.toml` registers for
`wing_parser.mcp.server:main`. If the `mcp` extra is not installed, it
prints `pip install "wing-parser[mcp]"` and exits rather than raising an
import error. Point your MCP client's config at the `wing-mcp` command
(or `python -m wing_parser.mcp.server` from a checkout); how each client
discovers a stdio server is documented by that client, not here.

The server registers five tools, each a thin wrapper over the matching
CLI command and returning plain text rather than raising — the tool
bodies live in `wing_parser/mcp/tools.py`, unit-tested there without a
running server:

| Tool | Same as | Use for |
| --- | --- | --- |
| `wing_analyze` | `analyze` | Scene overview: channel/bus counts, named channels, firmware version |
| `wing_channel` | `channel` | Full detail on one channel: EQ, dynamics, HPF, tap point, sends |
| `wing_diff` | `diff` | Field-by-field comparison of two scene files |
| `wing_routing` | `routing` | Orphans, ALT-sourced, unpatched and unclassified channels |
| `wing_doctor` | `doctor` | Advisory findings, with the deciding rule layer |

Each tool's docstring is what the client reads to decide when to call
it; the table above is a summary, not a substitute for actually trying a
client against it. This project has not verified any particular model's
tool-selection behavior against these descriptions — treat the
descriptions in `tools.py` as a starting point to refine, not a
guarantee a model will always pick the right tool.

## Claude Skills

`skills/` ships five [Claude Skill](https://docs.claude.com/en/docs/claude-code/skills)
directories, one per CLI command family, each a `SKILL.md` with
frontmatter (`name`, `description`) and instructions for running that
command and reading its output:

```
skills/wing-analyze/SKILL.md
skills/wing-channel/SKILL.md
skills/wing-diff/SKILL.md
skills/wing-routing/SKILL.md
skills/wing-doctor/SKILL.md
```

`wing-doctor`'s also documents `wing feedback`, since recording a
verdict is the natural next step after a doctor finding.

To use them with Claude Code, copy or symlink the directories you want
into a skills location Claude Code searches (for example a project's
`.claude/skills/`, per Claude Code's own skill-discovery documentation —
this repo does not install them anywhere by itself). Each skill invokes
the CLI as a subprocess (`python -m wing_parser.cli ...`), so the
package must be installed or importable from wherever the skill runs;
it does not go through the MCP server. As with the MCP tool
descriptions above, this project has not verified that a given model
reliably picks the right skill for a given prompt — the frontmatter
`description` is what a Skills-aware client matches against, and is
worth tuning against your own usage.

## Tests

```bash
python -m pytest
```

## Spec

The full design — architecture, the `.snap` format, the classifier,
the query API, the advisory module, the feedback loop, and the Phase 1
success criteria — is written up at
[`docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md`](docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md).
