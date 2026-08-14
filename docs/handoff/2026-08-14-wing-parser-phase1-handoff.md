# WING scene parser — Phase 1 handoff

**Date:** 2026-08-14 · **Branch:** `feature/wing-parser-phase1`, merged into local `main`
**State:** 17 of 24 tasks complete · 238 tests passing · nothing uncommitted

Paste this whole file as the opening message of the next session.

---

## 1. What this is

A parser and advisory tool for Behringer WING `.snap` scene files. It reads a
scene, tells you what each channel and bus actually is, and — once the advisory
layer lands — tells you what looks wrong about the mix.

The point is not a generic linter. Spec §6 and the memory file
`project-wing-advisory-philosophy` record the actual goal: encode **ToanAZ's own
mixing judgement**, in three layers, with a human-curated feedback loop. Claude
records manual evaluations and proposes YAML edits; ToanAZ decides what is kept.
His worked example, which contradicts the knowledge base's blanket rule G8:

> "mix IEM 1 band, thì iem của guter sẽ send prefader vào trong đó, còn lại toàn
> bộ để post fader"

Long-term he wants an auto-mix layer on top. Spec §14.1 records the split: a
decision tier (Claude, song/cue granularity, seconds are fine) versus a
real-time tier (console DSP, sub-100 ms). Phase 1 builds neither — it builds the
foundation both would sit on.

**Read before touching anything:**
- `docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md` — 15 sections, the design
- `docs/superpowers/plans/2026-08-13-wing-scene-parser-phase1.md` — 24 tasks, the plan you are executing

---

## 2. How to resume

Execution follows **superpowers:subagent-driven-development**: one fresh
implementer subagent per task, a task reviewer after each, a scoped re-review
after each fix round. Invoke the skill; it carries the process rules.

The ledger is the recovery map:

```
.superpowers/sdd/2026-08-13-wing-scene-parser-phase1/progress.md
```

`.superpowers/` is **git-ignored** — the ledger lives on this machine only and
will not survive a fresh clone. It records every task's commits, every ruling,
and 39 deferred Minor findings. Read it before the final review; the whole-branch
review needs that Minor list to triage.

Per-task loop, exactly as run so far:

```bash
"$SKILL/scripts/task-brief" docs/superpowers/plans/2026-08-13-wing-scene-parser-phase1.md N
git rev-parse HEAD > .superpowers/sdd/2026-08-13-wing-scene-parser-phase1/base-task-N.txt
# dispatch implementer (sonnet) with the brief path
"$SKILL/scripts/review-package" docs/superpowers/plans/...phase1.md <BASE> <HEAD>
# dispatch reviewer (sonnet) with brief + report + diff paths
```

where `$SKILL` is
`C:/Users/id_az/.claude/plugins/cache/claude-plugins-official/superpowers/6.2.0/skills/subagent-driven-development`.

Never paste accumulated history into a dispatch. Hand over file paths.

---

## 3. Remaining work

| Task | Title | Notes |
|---|---|---|
| 18 | Rule model, loader, predicates | plan line 5474 |
| 19 | Rule evaluator | 5881 |
| 20 | Three-layer resolver and the base rules | 6152 — G8, G7, E6 land here; **Milestone 4** |
| 21 | Feedback log | 6656 |
| 22 | CLI | 6893 |
| 23 | MCP server | 7365 |
| 24 | Skills, examples, README | 7644 — **Milestone 5** |

Then: whole-branch review on the most capable model, one fix wave, one scoped
re-review, delete the SDD workspace, then `superpowers:finishing-a-development-branch`.

---

## 4. Standing rules from ToanAZ — these are not negotiable

**Modular code, short files.** His words: *"Phải code module hóa, giữ file code
ngắn, nếu dài thì phải đập ra. Đập theo logic, ui, front end, backend, api,
hal."* Concretely: a **~200-line ceiling** per source file, split by
responsibility layer, not by convenience. Command dispatch stays separate from
output rendering; MCP tool definitions stay separate from handler logic. Saved as
memory `feedback-modular-short-files`.

**Never state first-principles audio reasoning as fact.** Saved as
`feedback-flag-unverified-claims`. This session proved why — see §6.

**PowerShell, not bash, for anything handed to him to run.** Saved as
`feedback-powershell-not-bash`.

He verifies claims. Show evidence, not assertions.

---

## 5. Architecture as built

```
core/        format decoding — stdlib + PyYAML + ruamel only, imports nothing above it
descriptors/ YAML descriptor tables
query/       scene views: Channel, Bus, routing, diff        (may import classifier/)
classifier/  matcher -> cache -> optional model              (the only LLM in the system)
advisory/    rule engine                                     (Tasks 18-20, not built)
cli/ mcp/    interfaces                                      (Tasks 22-23, not built)
```

Global constraints, copied verbatim into every reviewer dispatch:

- ~200 lines per source file, split by responsibility layer
- `core/` may import only stdlib, PyYAML and ruamel; never from layers above it
- Parser and advisory engine are **deterministic** — no LLM in `core/`, `query/`, `advisory/`
- The tool **runs fully offline**; with no key, no network, or the kill switch set, only unresolvable names degrade to `unknown`
- Never fabricate EQ band values — an unknown `eq.mdl` yields `bands=None` plus a `descriptor_missing` anomaly
- `-144` becomes `float("-inf")` in `core/normalizer.py`, at the data layer
- Descriptors and advisory rules are YAML data, not Python
- **Files under `knowledge/` are written with `ruamel.yaml` round-trip, never `yaml.safe_dump`** — PyYAML drops comments at parse time and would erase ToanAZ's annotations
- Every `Finding` records its deciding layer (`base` / `toanaz` / `show`)
- Every advisory rule YAML carries `source:` and `rationale:`
- Do not move or rewrite `docs/knowledge-base/`
- Float comparisons in tests use `pytest.approx`
- License MIT

---

## 6. What this session actually taught

**Read this section before writing any task brief.** It is the highest-value
part of the handoff.

### The plan is the bottleneck, not the implementers

Of ~14 Important findings raised by reviewers, **11 were defects in the plan
document**, not in implementer work. The implementers rendered a flawed brief
faithfully. Budget review effort accordingly: scrutinise the brief before
dispatch, not the diff after.

### The recurring defect families

1. **Defaults that don't fire when expected.** `.get(k, default)` returns `None`
   when the key exists with a null value. Bareword `OFF:` in YAML 1.1 parses as
   boolean `false`. Prefix matching by dict insertion order shadows longer keys.
2. **Allowlists derived from the thing they validate.** A test that enumerates
   sections from the same constant the code reads proves nothing. Derive coverage
   from the *file*.
3. **Knowledge recorded in one document and not carried into the model.** Spec
   §2.2 noted `MX<n>` matrix send keys; the `Send` record ignored them, and
   `main.send` has *only* matrix keys, so the obvious `isdigit()` filter would
   have left every main with zero sends.
4. **Mathematically correct, domain wrong.** `_magnitude` returned `None` for
   `-inf → -7.9`, ranking the biggest audible change below a 1 dB trim.
5. **Regex word boundaries against numbered names.** `\biem\b` has no boundary
   between `M` and `3`, so `IEM1`/`IEM2`/`IEM3` never matched while `IEM`,
   `IEM 1` and `IEM-1` did. Same flaw hit `\bhs\b` against `HS4`. Both are real
   names in the real file. **Check every `\b…\b` pattern against the numbered
   form.**
6. **Trusting the other side to be well-formed.** A model answering `"high"`
   instead of `0.9`; a model answering `"Unknown"` instead of `"unknown"`; a user
   typing `WING_DISABLE_LLM=0` meaning "on". Three different boundaries, one
   mistake: treating untrusted input as already normalised.
7. **Silent-write hazards.** `yaml.safe_dump` erasing all eight comment lines of
   a human-edited file; a non-atomic `open(w)` truncating the durable cache on a
   crash mid-write.

### Two performance traps, both measured

- `cache.lookup()` re-reads and re-parses the whole knowledge file per call, and
  since Task 15 that parse is a ruamel round-trip. **200-entry cache: 50 per-name
  lookups = 3379 ms; one load plus 50 in-memory lookups = 65 ms.** At 1000
  entries the per-name form reaches ~17 s. The file is designed to grow one entry
  per name ever seen, so it degrades exactly in proportion to use. `Classifier`
  now loads once, lazily. **Watch for this pattern again in Tasks 18–21** — the
  rule loader and the feedback log read YAML the same way.
- Six of the 40 channels are unnamed. Without a blank-name guard each one fell
  through to a model call and landed in `unresolved` as an empty string.

### The measurement habit that caught them

Before dispatching each task, run its assertions against the real file. It found
wrong expected values in Tasks 12, 13, and 17, and both performance traps. One
Python one-liner against `user-files/example-Vu.snap` is worth more than any
amount of re-reading the plan.

### Mutation-test the tests

Task 14 shipped a `_rank` tiebreak that all 30 tests passed *with the logic
removed*. A test that passes without the code it covers is worth nothing.
When a component is load-bearing, delete it temporarily and confirm a test goes red.

---

## 7. Domain facts established with ToanAZ — do not re-derive these

| Fact | Source |
|---|---|
| `TB` = talkback | his words |
| `Flown` = flown array speaker | his words |
| `Side` = sidefill speakers — and a sidefill is a **monitor**, the band hears it | his words |
| `Cen` = center speaker | his words |
| A bus named `HEADSET` is "input headset mic, hoac group all headset mic" — **input-side, a subgroup, not a monitor send** | his correction of my wrong assumption |
| Dugan automix is not AI | spec §15 |
| Polar pattern is not selected by frequency range | spec §15, memory `feedback-flag-unverified-claims` |

I got the headset one backwards by reasoning from first principles. Ask him.

### The real file, `user-files/example-Vu.snap`

- Buses 1–6 are source subgroups: MIC, MUSIC, DRUM, BAND, HEADSET, STRING
- Buses 7–10 are monitors: SIDEFILL, MON VOX, MON L, MON R
- Buses 11–16 are FX: ROOM, HALL, DELAY, HAHA, DRUM FX, BAND FX
- Channel 8 `M8 MC` → `speech.mc`; channel 13 `Kick In ` → `drums.kick.in`; channel 11 `HS4` → `speech.headset`
- 6 channels unnamed; 3 live channels; 23 unpatched channels
- Still unresolved by design: `My Lap` ×2 (genuinely ambiguous), `RECODING` (a typo in his file — reporting it beats guessing at misspellings)

---

## 8. Open questions

**Below-gate bus subgroups.** All six source subgroups sit at confidence 0.6,
below the 0.8 gate, so any rule keyed on bus role will skip them silently. ToanAZ
declined a blanket raise. **Revisit once the advisory rules exist and the cost of
skipping is visible** — that is the right moment to ask, not before.

**Prompt taxonomy drift.** `llm.py`'s `_PROMPT` hardcodes a kind list in Python
that has already drifted from `patterns.yaml` (`drums.ride`, `drums.pad`,
`instrument.guitar`, `instrument.strings`, `instrument.horns`,
`unknown.bare_mic` are in the YAML but not the prompt). The taxonomy now lives in
two places. Consider sourcing the list from `patterns.yaml` at prompt-build time.

**39 deferred Minor findings** are itemised in the ledger. The whole-branch review
must triage them; do not let them evaporate.

---

## 9. Environment notes

- **PowerShell is the shell.** Backticks in a `git commit -m` string swallow
  words; use `git commit -F -` with a **quoted** heredoc.
- **Never build regex or YAML replacements in a Python heredoc.** `\b` in a
  non-raw Python string is a backspace character, not a word boundary. This
  silently desynced the plan from the shipped YAML three times in one session.
  Use the Edit tool for file edits; it has no escaping layer.
- `anthropic` is **not installed**. That is fine — the fallback is optional by
  design and every test fakes it. Do not install it to "verify" `_ask`.
- `ruamel.yaml` **is** installed (0.19.1) and is a hard dependency.
- Model id is `claude-opus-5`. `client.messages.parse(..., output_format=Model)`
  → `.parsed_output` is correct; the `output_format` deprecation applies to
  `messages.create()`, which takes `output_config.format`. Verified against the
  `claude-api` skill — do not re-research it.
- Excluded from git and large: `user-files/WING-Edit.exe` (94 MB),
  `user-files/User-Manual_WING-series_*.pdf` (20 MB).

---

## 10. First move in the new session

1. Invoke `superpowers:subagent-driven-development`.
2. Read the ledger at `.superpowers/sdd/2026-08-13-wing-scene-parser-phase1/progress.md`.
3. `task-brief` for Task 18, then **read it and check every assertion against
   `user-files/example-Vu.snap` before dispatching anything.**
4. Continue the loop. Do not stop between tasks. Stop only for a plan-mandated
   finding, a BLOCKED implementer, or a genuine domain question for ToanAZ.
