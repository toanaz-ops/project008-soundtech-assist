# WING scene parser — Phase 2 complete

**Date:** 2026-08-15 · **Branch:** `claude_desk/wing-parser-phase1-handoff-467f0f`
**State:** 24 of 24 tasks complete · 364 tests passing, 1 skipped · wheel builds

Tasks 18–24 added the advisory rule engine (rule model, predicate language,
loader, evaluator, three-layer resolver, three base rules), the append-only
feedback log, the CLI, the MCP server, and the documentation layer.

The engine's first real output, on `user-files/example-Vu.snap`: **17 findings** —
G8 twelve times, G7 four times on buses 7–10, E6 once on channel 11.

This file exists because the SDD ledger that carried this work
(`.superpowers/sdd/…/progress.md`) is git-ignored and is deleted at merge. Two
things in it must survive: the questions still open with ToanAZ, and the triage
of 52 deferred Minor findings.

---

## 1. Open questions for ToanAZ

None of these block the code. All five change YAML data, not Python.

### 1.1 What is a limiter's `dyn.mdl` on a real WING?

Rule G7 decides fire/don't-fire with `not_in: [LIM, LIMIT, PRECISION_LIM, BRICK]`.
Those four strings appear **nowhere** — not in either `.snap`, not in any
descriptor, not in `docs/knowledge-base/`. The only dynamics models in real data
are `COMP` (71 in example-Vu, 68 in factory) and `CMB` (5).

So **G7 currently cannot not-fire.** It emits `severity: error` on every monitor
bus, forever, and no test can catch it because no sample file contains a limiter.

Partial answer already found from a source: `user-files/WING_Series_Manual_Knowledge_Base.md`
§9.2 names the limiter-capable processors — **Even Comp/Lim** (Neve 33609 style,
L193), **76 Limiter Amp** (UREI 1176 style, L195), **Precision Limiter** (digital
peak brickwall, L202). Those are display names, not the stored token. A scan of
`WING-Edit.exe` found `COMP`, `CMB`, `LIM`, `LIMIT` and `LIMITER` as strings but
no co-located enum table, so nothing proves `LIM` is a `dyn.mdl` value.

**Load a limiter onto a bus, save the scene, and read what `mdl` says.** Do not
let anyone guess this token.

### 1.2 Should G7 fire on wedges, or only on IEM?

Three of G7's four findings land on `SIDEFILL`, `MON L` and `MON R` — near-certainly
wedges — carrying the message *"Every in-ear mix needs a hard limiter for hearing
protection."* Both cited sources scope to IEM only, and Core-Skills treats wedges
separately, prescribing ring-out plus a 6 dB send cut rather than limiting. The
predicate only establishes `bus.role == monitor`; it never establishes IEM.

Three ways out: split `iem` from `wedge` as distinct roles in `patterns.yaml`;
split G7 into two rules at two severities; or reword the message. Which matches
how you work?

### 1.3 What `applies_when` should supersede G8?

All twelve G8 findings are your own documented practice — *"mix IEM 1 band, thì
iem của guter sẽ send prefader vào trong đó, còn lại toàn bộ để post fader."*
This is the case the three-layer design exists for, arriving live.

The blocker is that `CONDITIONS` currently holds only `monitor_bus_count` and
`channel_count`. Spec §6.3's own canonical example uses `iem_mix_count` and
`band_has_guitar`, neither of which exists. A principle naming an unknown
condition now **raises** rather than silently never firing (fixed in the final
wave), so the typo case is separated from this genuine gap — but the gap is real.
Which probes do you actually need?

Sub-question: G8 ignores send level, so a `POST` send sitting at `-144` with
`on: true` is still reported as a live monitor send. Worth a level condition?

### 1.4 Three rules under-reach, and the predicate language can't express it

- **G7** checks `dyn.model` but not `dyn.on` — a limiter loaded but bypassed
  passes silently. That is a false negative on a hearing-protection rule.
- **E6** checks `gate.range_dB` but not `hold_ms`, though its own rationale
  states the pair conjointly (≤6 dB **with** ≥200 ms).
- **G8** matches only `mode == POST` and ignores `TAP`, which the design spec
  documents as drawn from the channel's tap point.

All three need an `OR`. `all_match` is AND-only **by design** — the plan's own
docstring says anything needing real logic belongs in a Python rule rather than a
bigger DSL. So this is a scope decision: extend the predicate language, add
Python rules alongside YAML ones, or split each into two rules.

### 1.5 The below-gate question, now with the measurement you asked for

You declined a blanket confidence raise and said to revisit once the cost of
skipping was visible. It is, and it is narrower than the Phase 1 handoff assumed.

`evaluate()` gates `requires_classifier` rules at `LOW` (0.4) and skips **zero**
targets on the real file. `Bus.is_monitor` gates at `HIGH` (0.8), and buses 1–6
(`MIC`, `MUSIC`, `DRUM`, `BAND`, `HEADSET`, `STRING`) all sit at subgroup **0.60**.

The two thresholds therefore bite in exactly one place: `_monitor_bus_count`,
which is the only shipped `CONDITIONS` probe and so the sole gate on the entire
`toanaz` layer. That is a narrow surface — but it is the layer your own principles
live in, which makes it the one place it matters most.

---

## 2. The 52 deferred Minor findings, triaged

The final whole-branch review read the full list and ruled on all of them. Struck
and pre-merge items are already handled; what remains is below.

### Fix soon — not blocking, but real

| Item | What |
|---|---|
| T10-a + T7-a | Spec §3.1 promises anomalies are collected rather than raised, so a partly-malformed file still yields output. Two places break that: `WingScene.__init__` calls `.items()` on `ae.ch` while the validator tolerates a same-length list, and an unguarded `float()` on an EQ band value raises instead of yielding an anomaly. Phase 2 added a third layer that inherits the same crash. |
| T16-a | `llm.py`'s `_PROMPT` hardcodes a kind list that has **already drifted** from `patterns.yaml` (`drums.ride`, `drums.pad`, `instrument.guitar`, `instrument.strings`, `instrument.horns`, `unknown.bare_mic` are in the YAML, not the prompt). A live divergence, not a latent one. Source the list from `patterns.yaml` at prompt-build time. |

### Closed as unreachable

**T22-4** — `render.changes` used `if change.magnitude`, so a real `0.0` would
render like `None`. Two reviewers tried and neither could construct a reachable
case: it needs two numerically-different values whose difference is exactly zero.

### Let stand, explicitly — 40 items

Recorded so nobody re-litigates them. Three worth naming as deliberate rather
than tired:

- **T14-a** — a genuine full tie in `_rank` falls back to `patterns.yaml` list
  order. This does **not** violate the determinism constraint: it is deterministic
  for a fixed file, and no current pattern pair reaches that path.
- **T18-3** — `resolve_path` collapses "missing branch" and "present but null"
  into one `None`. Safe in the direction the shipped rules use it: E6's
  `not: null` fails **closed** on a typo'd path. It would only bite a rule using
  `is_null: true`, and none does.
- **T9-a** — resolved during the final wave: `core.normalizer.int_keyed` is no
  longer dead code, and `build_dcas`/`build_mute_groups` now use it.

The remaining 37 are documentation nits, redundant-but-harmless tests, and latent
guards with no reachable trigger.

---

## 3. What Phase 2 taught, beyond Phase 1's lessons

Phase 1 recorded that the plan is the bottleneck: 11 of ~14 Important findings
were plan defects. Phase 2 confirmed it and added a sharper edge.

**The controller is part of the bottleneck.** In Task 20's first fix round I told
an implementer that `Corporate-B2B-Events.md` contradicts itself — that its §4.1
lectern gate row "gives 12 dB range with no mention of automix" — without opening
the line. It reads *"Prefer automix over gating (see 4.4). If gating, keep range
shallow so it never chatters."* It mentions automix twice and cross-references
§4.4. The false claim shipped into a rule's `rationale:` as fact and was caught
only because a reviewer read the source I had cited but not read. **A citation is
not verification.** Memory `feedback-flag-unverified-claims` now records this as
the fourth instance, and the first that was not about audio at all.

**The pre-flight kept paying.** Running each task's assertions against the real
file before dispatch found three fatal defects in Task 20 alone — G8 filtering on
bare `mode`/`on` keys that resolve against the context dict and match nothing
(and a bareword `on:` key that YAML 1.1 turns into boolean `True`, killing
`resolve_path` on `True.split(".")`), plus two E6 tests asserting silence on a
file where E6 genuinely fires.

**The defects that hide are the ones the test harness structurally cannot see.**
Task 23's two Criticals were both invisible to all nine of its tests: `_guard`
wrapped with `*args, **kwargs` and hand-copied `__name__`/`__doc__` instead of
using `functools.wraps`, so every MCP tool would have registered with an unusable
JSON schema — and direct Python calls work fine, which is exactly why nothing
caught it. The transport is not exercisable here, so defects only the transport
would reveal need a proxy test.

**Duplicated error handling drifts, three times.** The CLI and MCP error handlers
were separate copies of one idea. Task 22 widened the CLI's catch to `OSError`;
the MCP copy still caught `FileNotFoundError` and crashed on a directory. The
final wave found a third instance — a non-mapping `when:` escaping both.

**A near-miss is not a margin.** The `dest_kind` guard in `evaluator.py` had no
test and the whole suite passed with it deleted. It is inert on the real file by
one boolean: channels 39 `BOH Talk` and 40 `FOH Tak` both send `POST` to **MX8**,
colliding exactly with monitor bus 8 `MON VOX`, saved only by `on=False`. Switch
one on mid-show — an entirely ordinary thing — and removing the guard fabricates
*"Channel 39 (BOH Talk) sends post-fader to bus 8 (MON VOX)"*: a phantom monitor
warning about a talkback mic, indistinguishable from a true finding.

---

## 4. Domain facts established — do not re-derive

Carried forward from Phase 1, unchanged: `TB` = talkback · `Flown` = flown array ·
`Side` = sidefill, **and a sidefill is a monitor** · `Cen` = center speaker · a bus
named `HEADSET` is **input-side**, a subgroup, not a monitor send · Dugan automix
is not AI · polar pattern is not selected by frequency range.

Added in Phase 2, all measured on `user-files/example-Vu.snap`:

- Channel 11 `HS4` carries an active gate at **40 dB range, 10 ms hold** *and* an
  active post insert on automix group `X`. E6's first real catch, and a genuine
  one — a 40 dB gate ahead of a Dugan is a switch, not a noise reducer.
- Seven channels (1, 2, 3, 5, 6, 7, 8) carry automix group `X` with the insert
  **off** and a gate over 6 dB. They are exactly the false positives E6's
  `post_insert.on` check exists to prevent.
- Channels in the 0.4–0.8 confidence band: only channel 11 `HS4`
  (`speech.headset`, 0.70) and channel 24 `SPD ` (`drums.pad`, 0.75).
- All four monitor buses classify at **0.90**; all six source subgroups at **0.60**.
- Bus 8 `MON VOX` dynamics: `Dyn(on=True, model='COMP', threshold_dB=-15.0, …)`.
  Bus 7 `SIDEFILL` has `dyn.on=False`.
