# Rule-set growth (sub-project B) — design

**Date:** 2026-08-16 · **Status:** approved by ToanAZ section-by-section in session ·
**Depends on:** Phase 1 spec (2026-08-13), advisory loop closure (2026-08-16)

Grow the advisory base layer from 3 rules (G8, G7, E6) to ~30, mined from
`docs/knowledge-base/`, and split the monitor role so IEM and wedge stop
sharing one severity. Every rule in this document carries a source citation
that was re-read against the cited line at the time of writing, per the
standing verification rule.

---

## 1. Decisions from ToanAZ (recorded 2026-08-16, this session)

These were asked, not guessed:

| Question | Decision |
|---|---|
| Which sub-project next | **B** — grow the rule set |
| G7 scope (handoff §3.2) | Split `iem` / `wedge` into distinct roles. **IEM without dynamics = error; wedge without dynamics = warning.** Generic `monitor` (MON VOX, MON L/R — flavour unknown) goes with the **warning** branch; error is reserved for a confirmed IEM. |
| G8 + TAP (handoff §3.3) | **Keep G8 matching `mode == POST` only.** Domain fact from ToanAZ: *"Tap trên wing mặc định là pre-fader hoặc pre eq"* — a TAP send draws from a tap point that defaults to pre-fader or pre-EQ, so TAP is not evidence of a post-fader monitor send. Recorded in G8's rationale so nobody re-proposes it. Probe corroborates: no `TAP` send mode appears in either sample file (observed modes: `PRE`, `POST`, `GRP`). |
| Limiter `mdl` token (handoff §3.1) | Still unknown — not tested yet. G7 keeps checking only `dyn.on`. The §7.1 clause of the closure spec stays parked. |
| Rule types to ship | **Both** — structural/safety rules *and* textbook numeric presets. Presets ship at `severity: info`. |
| Event-type gating | Rules carry an `event:` tag (`universal` / `corporate` / `band`). **Default run: everything.** A show profile may declare an `event:`; then base rules tagged with a *different* event are skipped, with a transparency line. Show scale and event type are declared, never derived. |
| Architecture | **PA2** — rules stay YAML; cross-object logic becomes tested Python properties on the query layer; the predicate DSL gains exactly one operator (`starts_with`). No aggregation DSL. |

## 2. What probing the real files changed

Run before design was finalised (`scratchpad/probe_fields.py`, both
`user-files/example-Vu.snap` and `user-files/factory-scene.snap`):

1. **ToanAZ's IEMs are matrices, not buses.** Real file: matrices
   `IEM MC`, `IEM CA SI 1`, `IEM CA SI 2`, `IEM3 BAKUP`, plus `FLOWN`,
   `SUB`, `SIDE`, `CEN`; mains `MAIN FOH`, `LiveStream`, `RECODING`,
   `TB OUT`. The advisory layer currently iterates only `kind == "bus"`
   (16 buses) and `_channel_sends` explicitly skips matrix destinations.
   **Every IEM on this console is invisible to every shipped rule.**
   Fixing that is the highest-value single change in this design.
2. **Insert slots hold console tokens, not plugin names.** Observed values:
   `NONE`, `FX13`. Every knowledge-base rule keyed on a plugin name
   (Clarity VX, smart:EQ, X-FDBK…) is unverifiable from a scene file.
   Killed — see §8.
3. **`tap_point` is `POST_FDR` on all 40 channels of both files, including
   factory defaults.** Any rule keyed on `tap_point` fires on everything or
   nothing. Killed.
4. **`source.mode` observed values are `M` / `ST`** (mono/stereo), not
   `MAIN`/`ALT`. Rules about "channel on ALT input" are blocked until a real
   scene shows the actual token.
5. Bus EQ bands exist on both files (`SHV`, `PEQ`, unshaped); `q` and `gain`
   are populated — notch-geometry rules are viable.
6. `main_sends` is a 4-tuple on every channel (one per main) with `on` and
   `pre` flags — the click/talkback/record rules have a real substrate.

## 3. Architecture changes (the only code in this sub-project)

### 3.1 Advisory targets extend to mains and matrices

- New iterator **`output`** in `evaluator.py`: yields every `Bus` object in
  `scene.bus_family()` (buses, auxes, mains, matrices), context key `bus`,
  confidence from `bus.role.confidence`. Existing `bus` iterator is kept
  as-is for backward compatibility; new output-level rules use `output`.
- **`channel.sends` starts yielding matrix destinations.** `_channel_sends`
  currently `continue`s on `dest_kind != "bus"`; it now also yields matrix
  sends, binding the destination `Bus` (kind `matrix`) under the same
  context key `destination_bus`. The key name is kept so G8's `where` and
  message templates work unchanged — G8 simply starts seeing the four IEM
  matrices. Mains are *not* added to `channel.sends`: `main_sends` is a
  different record shape and gets its own iterator.
- New iterator **`channel.main_sends`**: one target per `MainSend`, binding
  `channel`, `main_send`, and `destination_main` (the `Bus` object for that
  main). Confidence from `destination_main.role.confidence`.
- `resolver._monitor_bus_count` counts monitor-role members of
  `scene.bus_family()` instead of `scene.buses()` — a console whose
  monitors are matrices was previously counted as having none. Behaviour
  change is documented in the probe's docstring and covered by a test.

### 3.2 Classifier: the monitor role becomes a hierarchy

`patterns.yaml` `buses:` section changes:

```yaml
- { match: '\biem\d*\b|in\s*ear', kind: monitor.iem,   confidence: 0.95 }
- { match: 'wedge|side\s*fill|sidefill', kind: monitor.wedge, confidence: 0.9 }
- { match: '^side\b',            kind: monitor.wedge,  confidence: 0.85 }
- { match: '^mon\b|monitor',     kind: monitor,        confidence: 0.9 }
```

Channel kinds already use dotted hierarchies (`drums.kick.out`); this
brings bus roles in line. Three call sites compare the role by string
equality and must change in the same commit (the duplicated-logic lesson):

1. `Bus.is_monitor` → `kind == "monitor" or kind.startswith("monitor.")`,
   still gated on `is_confident`.
2. G8's `where` → `destination_bus.role: {starts_with: monitor}`.
3. `_monitor_bus_count` → same prefix test as `is_monitor` (it already
   delegates to `is_monitor`; verify, do not assume).

New patterns, additive:

```yaml
channels:
  - { match: '\bltc\b|time\s*code|\btc\s*in\b', kind: utility.timecode, confidence: 0.9 }
  - { match: 'zoom|teams|\bcaller\b|remote|skype', kind: utility.remote_caller, confidence: 0.85 }
  - { match: '\bpanel\b|\bseat\s*\d', kind: speech.panel, confidence: 0.85 }
  - { match: 'q\s*&\s*a|\bqa\b|\brov(er|ing)\b|audience\s*mic', kind: speech.qa, confidence: 0.8 }
buses:
  - { match: 'mix\s*minus|\bmm\b|\bn-1\b', kind: mix_minus, confidence: 0.85 }
```

(Exact regexes are the implementer's to verify against `classify()`
normalisation — every pattern must be exercised by a test naming a
plausible channel label, including a numbered one, per the `\biem\b`
lesson.)

### 3.3 Predicate DSL: one new operator

`starts_with` joins `OPERATORS` in `predicates.py`: string prefix test,
`False` for non-string values (same defensive shape as `gt`/`lt`). Needed
by `{starts_with: monitor}` and `{starts_with: speech.}`. Loader
validation picks it up from `OPERATORS` automatically; a test proves an
unknown operator still fails at load time.

### 3.4 Derived properties on the query layer

Cross-object logic lives here, per the layering rule in `core/models.py`.
Each property ships with direct unit tests **and a mutation check** (delete
the logic, a test must go red):

| Property | On | Returns | Used by |
|---|---|---|---|
| `notch_count` | `Bus` | count of EQ bands with `gain <= -6` and `q >= 8` (shelf bands excluded) | G11 |
| `max_boost_above_8k` | `Bus` | max `gain` over bands with `freq > 8000` and `gain > 0`, else `None` | G12 |
| `receives_ambient` | `Bus` | any confident `utility.ambient` channel has a send with `on == true` to this bus | G10 |
| `receives_any` | `Bus` | any channel send or main-send with `on == true` targets this bus | N2 |
| `iem_send_count` | `Channel` | count of sends with `on == true` whose destination role starts with `monitor.iem` | PB6 |
| `eq_has_lowmid_cut` | `Channel` | any EQ band, 200–500 Hz, `gain < 0` | PC2 |
| `eq_has_presence_lift` | `Channel` | any EQ band, 2–4 kHz, `gain > 0` | PC3 |
| `in_use` | `Channel` | source patched (`not source_ref.is_off`) AND not muted AND at least one send or main-send `on` | N1 |

`resolve_path` already walks properties; no evaluator change is needed for
these.

### 3.5 Event tagging

- `Rule` gains `event: str = "universal"`. Loader and `layers._as_rules`
  validate it against `{"universal", "corporate", "band"}` via the
  `_optional` route (a present-but-blank `event:` must resolve to
  `universal`, not `None` — the six-times defect family).
- A show profile file may carry a top-level `event: corporate` (or `band`).
  When the active profile declares an event, base rules whose `event` is
  neither `universal` nor the declared one are skipped, and the CLI prints
  a transparency line per skipped rule in the same place suppressions are
  reported: `[off-event] PB1 is band-only; profile 'corporate' declares event corporate`.
- No profile → no event filter → everything runs (ToanAZ's chosen default).

### 3.6 File layout

`wing_parser/advisory/base_rules/` grows by domain, each file under the
~200-line ceiling (split further if rationale prose pushes past it):

- `monitors.yaml` — G7, G8, G9 (existing file, edited)
- `monitors_quality.yaml` — G10, G11, G12
- `routing.yaml` — R1, R2, R3, R3M, R4, R5, R6, N1, N2
- `speech.yaml` — S1, S2
- `presets_corporate.yaml` — PC1–PC8
- `presets_band.yaml` — PB1–PB6
- `dynamics.yaml` — E6 (unchanged)

`loader` must discover the new files (verify whether it globs the
directory or lists names; if it lists, the list changes here — and a test
must fail if a YAML file in the directory is not loaded, the
shipped-file-vs-empty-dir lesson).

## 4. Rule inventory — structural (event: universal)

Message texts below are sketches; final wording follows the `any_of`
principle from the closure spec — render fields, do not assert
conclusions. Every rule carries `source:` and `rationale:` in YAML.

### Monitors

**G7 (changed) — IEM output has no active dynamics. `error`.**
`for_each: output`, `where: bus.role: monitor.iem, bus.dyn.on: false`,
`requires_classifier: true`.
Source: Core-Skills-Overview.md §3.4 step 8 (L473): *"Set a hard limiter on
every IEM output — typically −6 to −10 dBFS ceiling — to protect hearing
against patch errors and cable-drop transients. This is non-optional."*
Technical-Rider-Spec.md L295: *"Hearing protection. A feedback burst into
moulds is an injury"*. The existing caveats in G7's rationale (missing
`dyn` block defaults to `on: False`; the model clause parked on §7.1 of the
closure spec) carry over verbatim. On the real file G7 stops firing on
bus 7 SIDEFILL and starts examining matrices 5–8 (IEM MC, IEM CA SI 1/2,
IEM3 BAKUP) — expected findings to be established by probe during
implementation, not asserted here.

**G9 (new) — wedge or unspecified monitor output has no active dynamics.
`warning`.**
Same shape as G7 with `bus.role: {in: [monitor, monitor.wedge]}`.
Rationale records the decision split: the hearing-injury claim is
IEM-scoped in both sources; for a wedge or sidefill the limiter protects
drivers and the room, hence one severity lower. Bus 7 SIDEFILL moves here
(error → warning).

**G8 (changed) — post-fader monitor send. `warning`, unchanged text except:**
`where: destination_bus.role: {starts_with: monitor}` and the iterator now
yields matrix destinations. Rationale gains two recorded facts: the TAP
decision from §1 (with ToanAZ's quote), and that matrix sends became
visible on 2026-08-16. `knowledge/toanaz/shows/small.yaml` supersedes G8
already; unchanged.

**G10 (new) — IEM output receives no ambient mic. `info`,
`requires_classifier: true`.**
`for_each: output`, `where: bus.role: monitor.iem, bus.receives_ambient: false`.
Source: Core-Skills L471: *"For IEM, supply ambient mics … Without
ambience, performers over-sing because they cannot hear the room."*;
Technical-Rider-Spec L292 marks ambient mics into every IEM mix `[R]`.
Info, not warning: a small show may deliberately run IEM without ambience;
the profile mechanism exists for exactly this.

**G11 (new) — more than 5 narrow notches on a monitor-family output.
`warning`.**
`for_each: output`, `where: bus.role: {starts_with: monitor},
bus.notch_count: {gt: 5}`.
Sources disagree on notch geometry and count and the rationale must say
so: Core-Skills L470 says Q 20–30, −6 to −12 dB, 2–3 modes maximum;
Live-Entertainment-Shows L554–556 says Q ≈ 8–10, depth 6–12 dB, five is
the typical maximum, *"beyond that, more notches are indicative of a
placement problem, not an EQ problem"*; Risk-Contingency-Matrix L88 says
Q 8–12, 3–6 dB. **Chosen values: a "notch" is `q >= 8` and `gain <= -6`
(the loosest bound all three call a notch), and the threshold is > 5 (the
loosest maximum)** — the permissive envelope, so a finding means every
source agrees something is wrong. The message points at the physical
cause, quoting the Live-Ent line.

**G12 (new) — EQ boost above 8 kHz on a house output. `info`.**
`for_each: output`, `where: bus.role: {in: [main, pa_zone]},
bus.max_boost_above_8k: {not: null}`.
Source: AI-Plugins-In-Live-Sound L490–492: *"Do not EQ it back in at the
console — you will only overdrive the HF drivers for the front rows. Use a
delay zone with its own HF trim instead."* Rationale must record the
tension with the same document's L486 house-curve row (*"+2 dB above
8 kHz"* for small-format live band): L490 is about compensating air
absorption in a large room, L486 about voicing a small rig — which is why
this ships at `info`, not `warning`.

### Routing

**R1 — click routed to a FOH main. `error`, classifier-gated.**
`for_each: channel.main_sends`, `where: channel.source_type: utility.click,
main_send.on: true, destination_main.role: main`.
Source: Technical-Rider-Spec L175: *"To monitors only, hard-muted at FOH"*.

**R2 — talkback routed to a FOH main. `error`, classifier-gated.**
Same shape, `channel.source_type: utility.talkback`.
Source: Technical-Rider-Spec L180: *"Stage left, **not** in FOH mains"*.
The destination role test is what keeps this correct on the real file: main
4 `TB OUT` classifies as `talkback`, not `main`, so a talkback channel
feeding it is fine; only a main whose role is `main` (e.g. `MAIN FOH`)
triggers.

**R3 / R3M — timecode channel routed to any output. `error`,
classifier-gated.**
Rule ids must be unique, so this ships as two rules sharing one rationale:
**R3** on `channel.sends` (`send.on: true`) and **R3M** on
`channel.main_sends` (`main_send.on: true`), both with
`channel.source_type: utility.timecode`.
Source: Live-Entertainment-Shows L46: *"It rides on balanced audio cable
(XLR) and sounds like audio noise — never patch it through a normal audio
channel."*

**R4 — send to a record destination is post-fader. `warning`,
classifier-gated.**
`for_each: channel.sends`, `where: destination_bus.role: record,
send.on: true, send.mode: POST`.
**R5 — main-send to a record main is post-fader. `warning`.**
`for_each: channel.main_sends`, `where: destination_main.role: record,
main_send.on: true, main_send.pre: false`.
Source for both: Technical-Rider-Spec L260: *"**Record feed is pre-fader
[R]** — post-gain, pre-fader, pre-EQ. A FOH fader move must not damage the
archive."* Known limitation, recorded in the rationale: the real file's
record main is named `RECODING` — a typo that stays unclassified by
design (Phase 1 decision), so R5 stays silent there until the scene is
saved with a fixable name. Reporting the unclassified name is the
existing tool behaviour and the correct one.

**R6 — remote-caller channel feeds a mix-minus bus. `error`,
classifier-gated.**
`for_each: channel.sends`, `where: channel.source_type:
utility.remote_caller, destination_bus.role: mix_minus, send.on: true`.
Source: Technical-Rider-Spec L208: *"Ch15 must be fed a bus that excludes
itself. Without it the remote caller hears their own voice delayed by the
platform round trip and stops talking. This is the single most common
corporate audio failure."*; L879: *"No bus = no show, this is
non-negotiable."* The general form ("every caller must *have* a mix-minus
bus") is not decidable from names alone and is listed in §8; this narrow
form — a bus explicitly named mix-minus receiving the very channel it
exists to exclude — is unambiguous.

### Speech and automix

**S1 — speech channel with the high-pass filter off. `warning`,
classifier-gated.**
`for_each: channel`, `where: channel.source_type: {starts_with: speech.},
channel.filter.low_cut_on: false`.
Source: Core-Skills L690: *"**Non-negotiable rule:** every speech channel
gets an HPF. A lectern mic with no HPF, in a room with typical HVAC,
wastes 6–10 dB of usable headroom on inaudible rumble and reduces gain
before feedback for no benefit."* L752 nominates *"Configuration audit"*
as the measurement — the source itself says this is a file-inspectable
rule.

**S2 — music-family channel inside an automix group. `error`,
classifier-gated.**
`for_each: channel`, `where: channel.post_insert.automix_group:
{not: null}`, `any_of:` source_type `in [utility.playback, utility.click]` /
`starts_with: instrument.` / `starts_with: drums.`.
Source: AI-Plugins L385–386: *"Do not put a music channel (playback,
walk-in, a performing instrument) into an automix group. Sustained
broadband content wins the gain-sharing fight permanently and ducks all
speech mics."* Corroborated by Core-Skills L711 and Corporate-B2B L657
(whose lectern-mic hedge is quoted in the rationale as the reason lectern
channels are *not* in this rule's scope). Checks `post_insert` because
that is where WING automix lives (Corporate-B2B L646 puts Automix in
INS 2); the rationale records this mapping as an assumption to re-verify
if a future scene shows an automix token in `pre_insert`.

### Naming

**N1 — channel in use but unnamed. `info`.**
`for_each: channel`, `where: channel.in_use: true, channel.name: ""`.
**N2 — output receiving signal but unnamed. `info`.**
`for_each: output`, `where: bus.receives_any: true, bus.name: ""`.
Source: Risk-Contingency-Matrix L135: *"undocumented setups are the real
failure here"*; L362 (sign-off row 52). **Acceptance constraint: the
factory scene must stay finding-free** — it is the reference
nothing-configured state, and 8 of its channels have patched sources with
main sends on. The `in_use` property definition (§3.4) must be tuned
against the factory file (candidate discriminators: fader at −∞, all
faders at default) and the chosen discriminator recorded in the property's
docstring with the probe evidence. If no discriminator cleanly separates
"factory default" from "in use", N1/N2 ship disabled (`enabled: false`)
with the reason in the YAML — an honest silence beats noise on every
factory scene.

## 5. Rule inventory — presets (all `severity: info`, all classifier-gated)

Textbook starting values. Deviation is information, never an error — the
sources themselves call them *"starting point"* values.

### event: corporate (PC1–PC8)

| ID | Fires when | Source (verified) |
|---|---|---|
| PC1 | `speech.lectern` channel: `low_cut_on: false` or `low_cut_hz` outside 90–160 | Corporate-B2B L545: HPF *"100 Hz, 12 dB/oct (raise to 120 Hz for a boomy male voice)"*; Core-Skills L679 gives 100–150 Hz for lectern gooseneck — the window spans both |
| PC2 | `speech.lectern` or `speech.panel` channel with EQ on and `eq_has_lowmid_cut: false` | Corporate-B2B L546: *"−3 to −4 dB, 300 Hz, Q 1.4"* (lectern); L678: *"−3 dB @ 250 Hz, Q 1.4"* (panel table) |
| PC3 | `speech.lectern` or `speech.panel` channel with EQ on and `eq_has_presence_lift: false` | Corporate-B2B L547: *"+2 to +3 dB, 3 kHz, Q 1.0 — the biggest single STI improvement available"*; L679: *"+2 dB @ 3.5 kHz"* |
| PC4 | `speech.lectern` channel with `gate.on: true` and (`range_dB > 12` or `threshold_dB > -40`) | Corporate-B2B L549: threshold −48 dBFS, range 12 dB, *"**Prefer automix over gating** … keep range shallow so it never chatters"*. ROS L274 confirms −60 dB threshold practice for panel goosenecks; the rationale records both numbers and that the rule bounds only the lectern case |
| PC5 | `speech.*` channel with `dyn.on: true` and `ratio > 4` | Core-Skills L438: *"compression 2:1 to 3:1 with 3–6 dB gain reduction on peaks for speech"*; Corporate-B2B L550/L680 both 3:1 |
| PC6 | `speech.panel` channel: `low_cut_on: false` or `low_cut_hz` outside 100–160 | Corporate-B2B L677: *"120 Hz, 12 dB/oct (table mics pick up more LF than lectern mics)"* |
| PC7 | `speech.mc` channel with `automix_group` set and `automix_weight: {lt: 3.0}` (the DSL has no `lte`; a null weight fails `lt` and stays silent, which is correct — an absent weight is not a stated value) | Corporate-B2B L648: *"raise the moderator +3 to +6 dB so they can always cut in"*; L681 *"(moderator +4 dB)"*. Uses the existing `speech.mc` role as the moderator/host proxy; the rationale says so explicitly |
| PC8 | `speech.qa` channel with `muted: false` | Core-Skills L499: *"Killed by default, opened only during Q&A"*; L741: *"Q&A mic feeds back instantly"*. Rationale records the stated exception — a scene saved *during* Q&A legitimately trips this; that is what `info` and profiles are for |

### event: band (PB1–PB6)

| ID | Fires when | Source (verified) |
|---|---|---|
| PB1 | `drums.snare.bottom` channel with `effective_polarity: false` | Technical-Rider-Spec L153: *"**Polarity invert**"* (bolded in both riders, L1070). Uses `effective_polarity` (channel XOR source), not the raw flag |
| PB2 | `drums.hihat` channel: `low_cut_on: false` or `low_cut_hz` outside 160–250 | Technical-Rider-Spec L154: *"HPF 200 Hz"*; Core-Skills L685 snare row 100–150 Hz shows these are per-instrument numbers, not one speech blanket |
| PB3 | `drums.ride` channel: `low_cut_on: false` or `low_cut_hz` outside 200–300 | Technical-Rider-Spec L160: *"HPF 250 Hz"* |
| PB4 | `drums.overhead` channel: `low_cut_on: false` or `low_cut_hz` outside 160–450 | Core-Skills L686: *"Overheads / cymbals — 200–400 Hz, 12–18 dB/oct — Reject kick and tom bleed"* |
| PB5 | `drums.kick` or `instrument.bass` channel with `low_cut_on: true` and `low_cut_hz > 45` | Core-Skills L687: *"Kick / bass — Off, or 30 Hz — Protect sub drivers from DC/subsonic only"* — the one row where HPF-off is correct; only a *high* corner is flagged |
| PB6 | `utility.click` channel with `iem_send_count > 2` | Live-Entertainment-Shows internal conflict, recorded: L609 *"Drummer only"* vs L635 *"audible to drummer and bassist only"*. Chosen threshold: > 2 (the permissive reading). The unconditional half — click to a FOH main — is R1 at `error` |

## 6. Expected behaviour on the sample files

To be established by running, not asserted here — the plan must include a
task that probes both files per rule and writes the expected-findings
table into the test suite (the run-every-assertion lesson). Facts already
known from this session's probe:

- Factory scene: all names empty → every classifier-gated rule silent; the
  only threat is N1/N2, whose acceptance constraint is §4.
- Real file: G7's bus-7 finding moves to G9 as a warning; matrices 5–8
  enter G7's domain; `doctor --profile small` keeps suppressing G8.
- `RECODING` stays unclassified (typo, by design) — R5 silent.
- No `utility.timecode`, `utility.remote_caller`, `mix_minus`,
  `speech.panel`, `speech.qa` names exist in either file — R3, R6, PC6–PC8
  must be proven silent there and exercised by synthetic fixtures.

## 7. Testing

- Per-rule: one synthetic fixture that fires it, one that must not,
  including the boundary value (`gt`/`lt` are strict).
- Per-property (§3.4): direct unit tests plus a mutation check — with the
  property's logic replaced by a constant, at least one test goes red.
- Real-file table: `tests/` gains an expected-findings test over both
  sample files asserting the full `(rule_id, target)` set, so any rule
  change that shifts real-file behaviour is a visible diff.
- Loader: a test that every `*.yaml` under `base_rules/` is loaded
  (shipped-file-vs-empty-dir lesson), and that `event:` validation rejects
  an unknown value and defaults a blank one to `universal`.
- The FastMCP build test keeps skipping; `mcp`/`anthropic` stay
  uninstalled.
- After G7/G8/G9 land: grep the whole tree (`README`, `skills/`, examples,
  handoff docs excluded as historical records) for stale claims about G7's
  severity or scope — the fix-where-reported lesson.

## 8. Killed and blocked (do not re-mine)

**Killed by probe evidence (this session):**

| Candidate family | Evidence |
|---|---|
| Plugin-name rules (Clarity VX / smart:EQ / X-FDBK latency, CPU budgets, IEM-safe lists) | Insert slots hold `NONE`/`FX13` — console tokens, no plugin names in a scene file |
| ALT-input-to-IEM rules | No `ALT` token; observed `source.mode` ∈ {`M`, `ST`} |
| `tap_point`-keyed rules (automix pre-fader placement, Direct-Out contradiction) | `POST_FDR` on all 80 channels of both files including factory |
| Phantom-by-mic-class (except name-matched ribbons — deferred, not killed: no ribbon names in sample data to verify against) | Scene has no mic models; real file shows phantom on 0 channels |

**Blocked on missing fields or identity** (would need parser/schema work,
out of scope here): scene-safe flags, PFL/solo routing, automix group
depth and global enable, DCA fader levels, stereo-pair and spare-mirrors-
primary symmetry (pair identity undecidable from names in general),
NOM/open-mic counts (needs meters to mean anything), multi-scene diffs,
user-button mappings, INS1/INS2 slot identity.

**Parked on ToanAZ** (§1): the limiter `mdl` token — G7's second clause.

## 9. Documentation and knowledge updates in scope

- `README.md` and `skills/` rule tables: new rules, new severity split,
  the `event:` mechanism, the `output` iterator.
- Handoff docs are historical records and are not edited.
- The TAP domain fact and the IEM-as-matrix fact go into the G8/G7 YAML
  rationales (source: `ToanAZ, 2026-08-16`), which is where domain facts
  live per the three-layer design.
- `knowledge/` files remain ruamel round-trip only.

## 10. Constraints carried from the handoff (§5), restated for the plan

~200 lines per source file, split by responsibility layer · `core/`
imports stdlib+YAML only · advisory/query/core stay deterministic, no LLM ·
fully offline; `mcp`/`anthropic` optional and uninstalled · never
fabricate a value the file does not state · rules are YAML data with
`source:` and `rationale:` · every `Finding` records its layer ·
`docs/knowledge-base/` is read-only · float comparisons via
`pytest.approx` · PowerShell for anything handed to ToanAZ.
