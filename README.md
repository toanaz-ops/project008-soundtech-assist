# wing-parser

Read and analyse Behringer WING scenes: parse the format, classify what
each channel and bus actually is, and run an advisory layer that flags
likely misconfigurations. It reads a saved `.snap` file or a console on
the network, and needs no network for anything else.

## Scope

Everything the tool reports is derived from **what the scene states** —
channel names, fader positions, routing, processing chains, EQ and
dynamics settings — read either from a `.snap` file or from a live desk
over OSC. It is never derived from a measurement you would need a live
audio signal to take.

So it does **not** analyse audio: no LUFS, RT60, SPL, real-world
latency or gain-reduction metering. Metering does not live in the OSC
tree at all — it is on the console's native UDP channel, a second
transport this tool does not yet speak. See
[docs/ROADMAP.md](docs/ROADMAP.md).

A clean report from `doctor` means nothing in the scene looked wrong.
It does not mean the mix sounds right.

**What is built and what is planned:** [docs/ROADMAP.md](docs/ROADMAP.md)
is the single source of truth.

## Install

```bash
pip install -e ".[dev,llm,mcp,ui]"
```

`dev` pulls in `pytest` and `pytest-cov` for running the test suite.
`llm`, `mcp` and `ui` are all optional and independent of each other and
of the core tool — see [Offline guarantee](#offline-guarantee) below.
`ui` pulls in PySide6 for the [desktop app](#desktop-app).

## Desktop app

```powershell
wing-ui user-files\example-Vu.snap
```

or `python -m wing_parser.ui user-files\example-Vu.snap`. Both accept
`--profile <name>`, the same profiles `doctor` takes. Without PySide6
installed the command prints one line naming the extra and exits 1; the
CLI and the engine are unaffected by its absence.

The window is the advisory report. Findings fill the left pane, errors
first, filterable by severity and by layer. Selecting one shows, on the
right, the rule's title, the message, the rule's **rationale and source
verbatim**, and its evidence — the rationale is on screen because it is
the argument you are being asked to accept or reject.

**Verdicts.** Three buttons under the detail — Correct, False positive,
Irrelevant — write straight to the same `feedback.jsonl` that
`wing feedback` writes, with an optional note. The running tally for the
selected rule is shown above them, because a rule rejected seven times
is the evidence that a standing principle should be written. Nothing is
learned automatically; a human still writes the principle.

**Repairs.** Where the rule's own predicate determines a single value,
the detail panel offers one button that applies it. Where it does not —
any rule stating a frequency window, a count, or a choice between two
defensible fixes — there is **no button**, and the panel says so. That
absence is deliberate: a button that guesses is worse than no button.
**11 of the 39 base rules** carry one today, including five of the seven
`error`-severity rules — the routing errors (click or talkback into a
FOH main, timecode into any mix destination, a remote caller feeding
its own mix-minus), both record-feed rules, the missing speech
high-pass, an unmuted Q&A mic, a post-fader monitor send, and snare
polarity. They are declared in
[`wing_parser/edit/data/repairs.yaml`](wing_parser/edit/data/repairs.yaml),
each with a rationale, and each with a test proving it removes its own
finding **and no other**.

**Editing is never destructive.** Edits are held as a journal, not
applied to the loaded document. The Changes dock lists them with their
before and after values, Undo drops the last, and **Save As is the only
save** — it always writes a new file and never touches the one you
opened. Saving does not clear the journal, so you can save more than one
variant from the same edits.

### Building a standalone `.exe`

```powershell
pip install pyinstaller
pyinstaller packaging\wing-ui.spec --noconfirm
```

The result is a single `dist\wing-ui.exe` (about 66 MB) with no Python
installation required on the machine that runs it.

**Copy it off the Google Drive path before running it.** Launched from
`Z:\My Drive\...`, the executable did not start within two minutes —
`Start-Process` itself blocked. Copied to local disk it starts in a few
seconds. A one-file bundle has to unpack about 66 MB before its first
line of code runs, and doing that across a synced network path is the
difference. This is a property of where the file sits, not of the build.

**Where your judgements live, and why it differs when frozen.** A
PyInstaller bundle unpacks itself into a temporary directory and
**deletes that directory when the app closes**. Everything in
`knowledge/toanaz/` — `feedback.jsonl`, `principles.yaml`, `shows/` — is
either written by you or edited by you, so resolving it inside the
bundle would throw away every verdict you recorded, silently, on close.

So a frozen build keeps that set in `%USERPROFILE%\.config\wing-skill`
instead, seeded once from the copy shipped inside the executable and
never overwritten afterwards. **Help → "Where my judgements are
stored…"** names the exact path on any run. Setting `WING_KNOWLEDGE_DIR`
still overrides everything, frozen or not.

Run from a repository checkout, nothing changes: the in-repo
`knowledge/toanaz/` is used exactly as before.

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

`--live-before <ip>` and `--live-after <ip>` each read a live console
for that side instead of a file. `diff` still takes exactly one file
per side that a `--live-*` flag did not supply — so
`diff --live-before 192.168.128.28 last-night.snap` compares the
console directly against `last-night.snap`, and
`diff --live-before A --live-after B` compares two consoles and takes
no file arguments at all:

```powershell
python -m wing_parser.cli diff --live-before 192.168.128.28 last-night.snap
```

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
  every check. It supersedes G10 for the same reason: the rig it
  describes carries no ambient mic at all, so "no ambient mic reaches
  this IEM" names a microphone that does not exist and offers nothing
  to act on. Both suppressions are opt-in — an unprofiled `doctor` run
  still prints every G8 and G10 finding.

Base rules are not beyond question. G7 and G9, for instance, check only
that a monitor output's dynamics processor is switched on
(`bus.dyn.on`), not that the model loaded there is actually a limiter
— the `dyn.mdl` token a WING stores for a limiter is not recorded
anywhere in this repository and must not be guessed, so a monitor
output carrying a compressor that is switched **on** is deliberately
not reported (see
[design spec §7.1](docs/superpowers/specs/2026-08-16-advisory-loop-closure-design.md#71-the-limiter-token)
for the exact clause to add once that token is known, and
[the 2026-08-17 probe](docs/handoff/2026-08-17-limiter-token-probe.md)
for why no source on this machine can supply it — the sample files
exercise the model enum with a single value, `COMP`). Treat
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

`doctor` ships 39 base rules across nine files in
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
| Q1 | warning | universal | showcontext.yaml | Cue names a channel the scene does not have |
| Q2 | info | universal | showcontext.yaml | Cue names a channel that carries no name |
| Q3 | warning | universal | showcontext.yaml | Cue names a DCA number the console does not have |
| Q4 | warning | universal | showcontext.yaml | Expected source kind has no channel for it, once per kind across every segment naming it |
| Q5 | info | universal | showcontext.yaml | Expected source kind's channels are all parked, once per kind across every segment naming it |
| Q6 | info | universal | showcontext.yaml | Cue repeats a channel state an earlier cue already set |
| Q7 | warning, **disabled** | universal | showcontext.yaml | Two cues sit closer together than the operation needs |
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
`universal` (the default), `corporate`, or `band`. Of the 39 base
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

### Show context

Everything above reads a **static** scene: one snapshot, no notion of
when a channel is supposed to be live. A show context adds the time
axis — the cue sheet's own claims about which sources the show calls
for and which channels each cue touches — so `doctor` can check the
paperwork against the console instead of the console against itself.
It catches three failures a purely static read cannot see: a cue
naming a channel the scene does not have (or one that exists but
carries no name), an expected source kind with no confidently
classified channel anywhere in the scene (or one whose channels exist
but are all parked) — reported once per kind, naming every segment
that calls for it, since the scene is static and the answer cannot
differ between segments — and one cue redundantly repeating a
channel state an earlier cue already set.

A show context is a hand-written YAML file, loaded beside the scene —
it is never inferred from the `.snap` file itself:

```yaml
show: "Tiệc cuối năm Sơn Hải"
date: 2026-09-14

segments:
  - id: S2
    title: "Band set 1 — Bài 1: Nắng"
    time: "T+00:18:00"          # optional, ROS column 1 format
    expects: [drums.kick, instrument.bass, instrument.keys]
    cues:
      - id: "SQ 8"
        action: open             # open | close | up | down | recall
        channels: [13, 25, 29]
        dcas: [2]
        time: "T+00:18:04"       # optional
```

`expects:` draws on the classifier's own kind vocabulary
(`instrument.keys`, not free text), so Q4 is set subtraction —
checked once per expected kind against the whole scene, not per
segment — rather than a second layer of name-guessing. `time:` is
optional at both levels; a file that never states one gets silence
from Q7 rather than an assumed time. Channel state is derived by
walking every segment's cues in file order and keeping an open/closed
book per channel — only `open` and `close` move that book, so a level
move (`up`/`down`) on a closed channel leaves it untouched rather than
registering as a repeat, and what `recall` does to a given channel is
not knowable from the cue sheet alone.

Pass the file with `--show <file>` on `doctor`, combinable with
`--profile`:

```bash
python -m wing_parser.cli doctor user-files/example-Vu.snap --show tonight.yaml --profile small
```

`feedback` also accepts `--show <file>`, and it matters for the same
reason it matters for `--profile` (see above): `feedback` resolves a
finding id by re-running the same rules `doctor` printed, so a
Q-finding id `doctor` just listed will not resolve unless `feedback`
is given the same `--show` file — the id belongs to that specific run,
not to the scene in general.

`showcontext lint <file> [--fix]` checks a show context on its own,
with no scene involved, and is worth running before doors because the
file is hand-typed and the alternative is discovering a typo while the
band is waiting. Without `--fix` the file is never written, no matter
what lint finds; `--fix` writes repairs back through `ruamel.yaml`,
preserving comments and formatting.

`expects:` and `action:` values are checked against a closed
vocabulary, with three tiers of tolerance:

- **Normalise** — case and separator differences (`-`, `_`, space →
  `.`) are unified silently. The result either is a valid kind or it
  is not; this is not a guess.
- **Repair** — a token at Damerau-Levenshtein distance 1 from
  **exactly one** known kind is rewritten to it and reported as an
  anomaly (`show context: 'instrument.kyes' read as
  'instrument.keys'`), never silently. Tokens under 4 characters are
  never repaired — the vocabulary's minimum pairwise distance is 2, so
  distance 1 is provably unambiguous whenever exactly one candidate
  exists.
- **Refuse** — a tie (distance 1 from two or more kinds) or a miss (no
  candidate within distance 1) raises, naming the file, the line, and
  every candidate it found (`did you mean 'speech.mc' or
  'speech.qa'?`). Ambiguity is never resolved by picking one.

Q1-Q7 live in `wing_parser/advisory/base_rules/showcontext.yaml` and
are included in the [rule reference](#rule-reference) table above.
Every one of them yields nothing unless a show context is loaded with
`--show` — the `cue` and `segment` iterators they depend on are empty
otherwise, which is what keeps `doctor`'s behaviour on an unprofiled,
show-less run bit-identical to before this feature existed. **Q7 ships
`enabled: false`**: no source in this repository states how long a mic
change, a scene recall, or a patch change takes on ToanAZ's rig, and
he chose (2026-08-17) to wait for a real number rather than accept a
placeholder. Its rationale in `showcontext.yaml` records exactly what
switching it on requires.

### Building a show context from a producer's spreadsheet

Hand-typing the YAML above does not scale to a fifteen-segment running
order. `showcontext import` reads a producer's Excel sheet and writes
the show context for you:

```powershell
python -m wing_parser.cli showcontext import ros.xlsx --map knowledge\toanaz\sheets\abc.yaml -o tonight.yaml
python -m wing_parser.cli showcontext import ros.xlsx --map knowledge\toanaz\sheets\abc.yaml --scene tonight.snap -o tonight.yaml
```

Write one mapping file per producer, naming the sheet, the header row,
and which column means what. Columns are given either by letter
(`columns:`) or by the text in the header cell (`headers:`) — never
both for the same field. A letter may name a column whose header cell
is **blank**: an unlabelled notes or STT column is common on a real
running order, and it is exactly what `headers:` cannot express. Only a
letter past the last column holding anything is refused, and the error
names that column.

**An imported file has no cues**, because a running order does not
carry them, and most of Q1-Q7 only iterate cues. Only **Q4** ("show
expects a source with no channel for it") and **Q5** ("...whose
channels are all parked") ever fire on a freshly imported file — the
other five stay silent until cues exist. A file that produces two
rules' worth of findings is not one that produced all seven; do not
read a quiet `doctor` run against an imported file as a clean bill of
health for Q1, Q2, Q3 or Q6.

Pass `--scene` and every segment whose expected kinds match a channel
already in that scene gets a commented-out cue proposal naming those
channels. Just stripping the `#` from it does nothing useful — `cues:
[]` is still sitting there right below, and the loader reads that
empty list and silently ignores everything else, since an unrecognised
key is not an error. The proposal's own comment says exactly which
lines to delete and that the rest **replaces** `cues: []`, not sits
beside it; follow it literally, and Q1, Q2 and Q6 come to life for that
segment, and Q3 once a DCA is named — Q7 stays off regardless, since it
ships `enabled: false` (see above) and no cue, proposed or otherwise,
can revive a disabled rule.

Anything the importer cannot read — a row with no title, a performer
it does not recognise — is kept in the file as a comment rather than
silently dropped, and the last line reconciles the counts: how many
data rows came in, how many became segments, **how many expectations
those segments carry**, how many rows and how many performer fragments
were kept as comments, and how many blank rows were skipped. Nothing is
dropped and nothing is guessed.

Read the expectation count. A mapping with no `performers:` is legal
and gives every segment an empty `expects:` — the row counts then look
exactly like a correct import's, and `doctor --show` on that file finds
precisely what it finds with no `--show` at all. `0 expectation(s)` is
the one place that shows up.

Two rows carrying the same id are not passed through either: the second
becomes `S1-2`, and the file says so in a comment on that segment. A
repeated id would otherwise be refused by the loader on the very next
`doctor --show`, and — with `--scene` — would print one segment's
channels above another's.

Vietnamese cue-sheet terms live in the `cuesheet:` section of
`knowledge/toanaz/classifier.yaml`. The importer checks it before
falling back to the pattern matcher; unlike channel and bus
classification elsewhere in this tool, there is no LLM step here — the
importer never calls a model. The section ships empty — add a term
once and every later import knows it; whatever is not yet in it
becomes a comment, not a guess.

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

## Talking to a live console

Everything above reads a `.snap` file. `wing_parser/net/` reads the same
scene from a console over OSC (UDP 2223) instead, and writes back to it.

```powershell
python -m wing_parser.cli net identity 192.168.128.28
python -m wing_parser.cli net snapshot 192.168.128.28 -o today.snap
python -m wing_parser.cli net get 192.168.128.28 /ch/1/fdr
python -m wing_parser.cli net set 192.168.128.28 /ch/1/fdr -6.0 --confirm
python -m wing_parser.cli net toggle 192.168.128.28 /ch/1/mute --confirm
python -m wing_parser.cli net push 192.168.128.28 show.snap --confirm
```

`analyze`, `routing`, `channel` and `doctor` each take `--live <ip>` in
place of a file:

```powershell
python -m wing_parser.cli doctor --live 192.168.128.28
python -m wing_parser.cli doctor --live 192.168.128.28 --profile small
```

`--live` changes only where the `RawScene` comes from. The query layer,
the classifier, the advisory rules and the show context are the same code
on the same data, so a live desk and a saved file produce the same
findings.

### How it reads

Two pipelined phases, both re-run on every snapshot:

1. **shape** — a breadth-first `,s ?` walk of the address tree
2. **values** — one GET per leaf, in batches of 200

The shape is never cached, because the tree is dynamic: a `dyn` block set
to `GATE` exposes different parameters than one set to `COMP`. A whole
console is about 25 000 leaves and reads in a few seconds.

### Writing

`set`, `toggle` and `push` send nothing without `--confirm`. With it, the
console's name, model and serial are echoed first, and every write is
verified by reading the value back — necessary because an out-of-range
write is silently clamped and still reports success. `WING_WRITE_ALLOW_SERIAL`
pins writes to one console when set.

`push` separates **landed**, **mismatched** and **absent**. Absent means
the leaf does not exist on that console — a rack with no StageConnect
device has no `/io/in/SC/*` — which is hardware, not failure.

### Watching for changes

```powershell
python -m wing_parser.cli net watch 192.168.128.28
python -m wing_parser.cli net watch 192.168.128.28 --json --until 120
```

`net watch` reports changes on a running console by **polling**, never
subscribing. A console holds only one OSC subscription at a time and it
expires after 10 seconds, so subscribing would take that slot from
whatever holds it — WING-Edit, Companion, or whatever else is already
connected (whether WING-Edit itself uses the OSC subscription at all is
unmeasured — design doc §2.6(3)). Polling is a plain request/reply
exchange, the same shape as `net get`, and consumes no shared resource,
so it cannot displace another client. It watches the *effective* `$fdr`,
`$mute` and `$solo` on channels/buses/mains/matrices, and `$solo` on
DCAs — for `$fdr`/`$mute`, effective means DCA contribution and
mute-override are already folded in, so pulling a DCA down surfaces on
every channel it governs. See `skills/wing-watch/SKILL.md` for the
gotchas: it samples rather than streams, so a change that appears and
reverts inside one round is missed, and there are no meters at all over
OSC (measured in `docs/superpowers/specs/2026-08-21-live-watch-design.md`
§2.3).

### What is not here

Realtime subscription, metering, and the native binary interface on port
2222. See `docs/superpowers/specs/2026-08-21-wing-net-design.md`, which is
the design authority and records what was measured against a real console
rather than taken from documentation.

## Offline guarantee

`wing net` and `--live` talk to a console by design; everything else runs
with no network at all, and **no test in the suite opens a socket to one**
— the live paths are tested against a loopback fake.

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

The desktop app and the edit layer add nothing to this. Neither opens a
socket of any kind, and `wing_parser/edit/` does not import Qt either —
both facts are pinned by tests, the second by importing the package in a
clean subprocess and asserting no PySide6 module was loaded.

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
  shipped `knowledge/toanaz/shows/small.yaml` is exactly that: two
  rules, neither with a `when:` or a `message:`, carrying
  `supersedes: [G8]` and `supersedes: [G10]` and the rationale for
  switching each off. A profile may hold as many such rules as the show
  needs; each one names its own `supersedes` list.
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

`wing_analyze`, `wing_channel`, `wing_routing` and `wing_doctor` each
take an optional `live` parameter — a console's IP, read instead of
`path`, the same as the CLI's `--live`. `wing_doctor` also takes
`profile` and `show`, matching `--profile` and `--show`. `wing_diff`
takes only `before`/`after` file paths and has no `live` parameter of
its own; comparing a live console needs the CLI's
`diff --live-before`/`--live-after`, or a `net snapshot` first.

Each tool's docstring is what the client reads to decide when to call
it; the table above is a summary, not a substitute for actually trying a
client against it. This project has not verified any particular model's
tool-selection behavior against these descriptions — treat the
descriptions in `tools.py` as a starting point to refine, not a
guarantee a model will always pick the right tool.

## Claude Skills

`skills/` ships seven [Claude Skill](https://docs.claude.com/en/docs/claude-code/skills)
directories, one per CLI command family, each a `SKILL.md` with
frontmatter (`name`, `description`) and instructions for running that
command and reading its output:

```
skills/wing-analyze/SKILL.md
skills/wing-channel/SKILL.md
skills/wing-diff/SKILL.md
skills/wing-routing/SKILL.md
skills/wing-doctor/SKILL.md
skills/wing-net/SKILL.md
skills/wing-watch/SKILL.md
```

`wing-doctor`'s also documents `wing feedback`, since recording a
verdict is the natural next step after a doctor finding. `wing-net`
covers both the `wing net` group and the `--live` flag, since both are
ways of pointing the same analysis at a console instead of a file.
`wing-watch` covers `net watch` on its own, since watching a running
console for changes is a different task from a single read or write.

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
