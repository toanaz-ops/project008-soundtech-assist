# WING scene parser — next session

**Date:** 2026-08-16 · **Branch:** `main` @ `15cc3f0` · **State:** 406 tests passing, 1 skipped, nothing uncommitted

Paste this whole file as the opening message of the next session.

---

## 1. Where things stand

A parser and advisory tool for Behringer WING `.snap` scene files. It reads a
scene, says what each channel and bus actually is, and tells you what looks wrong
about the mix — where "wrong" is defined by **ToanAZ's own judgement**, encoded in
three layers, not by a generic linter.

Two bodies of work are delivered and merged:

- **Phase 1 spec, 24 tasks** — core decoding, descriptors, query layer,
  classifier, the three-layer advisory engine, feedback log, CLI, MCP server,
  skills and examples.
- **Advisory loop closure, 6 tasks** — the upper two layers were empty and
  unusable; they now work.

Current behaviour on the real file:

| | `user-files/example-Vu.snap` |
|---|---|
| `doctor` | **14** findings — G8×12, G7×1 (bus 7), E6×1 (ch.11) |
| `doctor --profile small` | **2**, with `[suppressed] G8 switched off by show.small.post-monitors-are-deliberate` |
| `factory-scene.snap` | none |

**Read before touching anything:**

- `docs/superpowers/specs/2026-08-13-wing-scene-skill-design.md` — Phase 1 design, 15 sections
- `docs/superpowers/specs/2026-08-16-advisory-loop-closure-design.md` — the advisory closure
- `docs/handoff/2026-08-15-wing-parser-phase2-complete.md` — Phase 1's residuals and lessons
- `docs/handoff/2026-08-16-advisory-loop-closure-complete.md` — this work's residuals and lessons

`.superpowers/` is git-ignored, so both SDD ledgers are gone. Everything that
mattered from them is in those two handoff docs.

---

## 2. The remaining roadmap

Phase 1 spec §14 defers several **independent subsystems**. They are not one
project and must not be planned as one. ToanAZ chose the decomposition below and
picked **A** first, which is now done.

| | Sub-project | Depends on | Size |
|---|---|---|---|
| ~~A~~ | ~~Close the advisory loop~~ | — | **done** |
| **B** | Grow the base rule set from `docs/knowledge-base/` (only G8, G7, E6 exist) | A | medium, mostly data |
| C | OSC read — connect to a live WING, read running state | — | large, new subsystem |
| D | OSC write — push changes back to the console | C | large + show risk |
| E | Audio analysis (LUFS, RT60, SPL) | — | large, needs I/O and hardware |
| F | The decision tier / auto-mix (§14.1) | A, C, G | largest |
| G | Input pipelines (setlist, cue sheet) | — | medium |

Each gets its own spec → plan → implementation cycle. **Invoke
`superpowers:brainstorming` before designing any of them**, and expect to be told
the scope needs decomposing again if the answer is F.

**B is the natural next step** — it is unblocked, it is mostly data work, and
every rule added now inherits the profile mechanism that makes a false positive
suppressible. But ask ToanAZ; do not assume.

---

## 3. Open questions with ToanAZ — do not guess these

**3.1 What `dyn.mdl` does a WING store for a limiter?** Rule G7 used to exclude a
hardcoded list `[LIM, LIMIT, PRECISION_LIM, BRICK]`. Those four strings appear
nowhere — not in either `.snap`, not in any descriptor, not in the knowledge base.
The only dynamics models in real data are `COMP` and `CMB`. G7 now checks only
`bus.dyn.on`, the half that is verifiable. `user-files/WING_Series_Manual_Knowledge_Base.md`
§9.2 names the limiter-capable processors — Even Comp/Lim, 76 Limiter Amp,
Precision Limiter — but those are display names, not the stored token. **He loads a
limiter onto a bus, saves the scene, and reads `mdl`.** The exact clause to add is
in the 2026-08-16 spec §7.1.

**3.2 Should G7 fire on wedges or only on IEM?** Its one surviving finding is
`bus.7 SIDEFILL` — a sidefill, at `severity: error`, against two IEM-scoped
sources. This question now accounts for *all* of G7's output. Options: split `iem`
from `wedge` as distinct roles in `patterns.yaml`; split G7 into two rules at two
severities; or reword the message.

**3.3 G8 matches only `mode == POST` and ignores `TAP`**, which the design spec
documents as drawn from the channel's tap point. A `TAP` send on a post-fader tap
point *is* a post-fader monitor send.

**3.4 The below-gate threshold.** `evaluate()` gates `requires_classifier` rules at
`LOW` (0.4) and skips nothing on the real file; `Bus.is_monitor` gates at `HIGH`
(0.8) and the six 0.60 source subgroups sit under it. The two bite in exactly one
place: `_monitor_bus_count`, the only shipped `CONDITIONS` probe.

---

## 4. Standing rules from ToanAZ — not negotiable

**Never assert an unverified claim as fact.** Saved as memory
`feedback-flag-unverified-claims`. **A citation is not verification** — re-read
the cited line at the moment you write the claim. Where the answer depends on how
he actually works, ask; a wrong guess corrupts the judgement layer the project
exists to encode.

**Modular code, short files.** *"Phải code module hóa, giữ file code ngắn, nếu dài
thì phải đập ra. Đập theo logic, ui, front end, backend, api, hal."* A ~200-line
ceiling per source file, split by responsibility layer, not by convenience.

**PowerShell, not bash**, for anything handed to him to run.

He verifies claims. Show evidence, not assertions.

---

## 5. How to run the work

Execution follows **`superpowers:subagent-driven-development`**: one fresh
implementer per task, a reviewer after each, a scoped re-review after each fix
round. Invoke the skill; it carries the process rules. Hand subagents **file
paths**, never pasted history.

Global constraints, copied into every dispatch:

- ~200 lines per source file, split by responsibility layer
- `core/` imports only stdlib, PyYAML and ruamel; never from a layer above it
- Parser and advisory engine are **deterministic** — no LLM in `core/`, `query/`, `advisory/`
- The tool **runs fully offline**; `mcp` and `anthropic` are optional extras and stay uninstalled, so the FastMCP build test must keep skipping
- Never fabricate a value the file does not state
- Descriptors and advisory rules are YAML data, not Python
- Files under `knowledge/` are written with `ruamel.yaml` round-trip, never `yaml.safe_dump` — PyYAML drops his comments
- Every `Finding` records its deciding layer; every rule YAML carries `source:` and `rationale:`
- Never move or edit anything under `docs/knowledge-base/`
- Float comparisons in tests use `pytest.approx`

---

## 6. What the last two bodies of work actually taught

**Read this before writing any task brief.** It is the highest-value part.

### The plan is the bottleneck — and so is whoever writes the briefs

Phase 1: 11 of ~14 Important findings were defects in the plan, not in
implementer work. The advisory closure went further — **three of its defects were
mine**, statements I put into a brief without running or reading them, which
implementers then transcribed faithfully:

- a docstring claiming a mechanism `evaluate()` does not have
- a test assertion contradicted by a transparency line the CLI already printed
- a documentation sentence false for *every* id the shipped profile lists

The implementers were right to transcribe, and right when they pushed back.
Budget review effort on the brief before dispatch, not the diff after.

### Fixing a false claim where it was reported is not fixing it

A wrong sentence about `any_of` propagated from a brief into source, a test
docstring, the spec and the plan. The first fix round caught two of five copies.
The lesson was written down — and then **not applied two tasks later**, when a
retracted reading deleted from `principles.yaml` survived verbatim in the README
and a `SKILL.md`, the documents a reader meets *first*. **Grep the whole tree.**

### Run every assertion against the real file before dispatching

This found three fatal defects in one task alone: a rule filtering on bare `mode`
and `on` keys that resolve against the context dict and match nothing; a bareword
`on:` key that YAML 1.1 turns into boolean `True`, killing `resolve_path` on
`True.split(".")`; and two tests asserting a rule stays silent on a file where it
genuinely fires. One Python one-liner against `user-files/example-Vu.snap` is
worth more than any amount of re-reading the plan.

### The defects that hide are the ones the harness structurally cannot see

Both of Task 23's Criticals were invisible to all nine of its tests. `_guard`
wrapped with `*args, **kwargs` and hand-copied `__name__`, so every MCP tool would
have registered with an unusable JSON schema — and direct Python calls work fine,
which is exactly why nothing caught it. When a surface cannot be exercised, its
defects need a proxy test.

### Mutation, not reading, is what proves a test

Green suites concealed: a `_rank` tiebreak all 30 tests passed with the logic
deleted; a `dest_kind` guard the whole suite passed without; an empty-`any_of`
guard whose sibling `isinstance` check already did the work; a first-match
guarantee a single matching clause could not distinguish; and a shipped-file test
that passed identically against an empty temp directory. If a component is
load-bearing, delete it and confirm something goes red.

### A default is only safe relative to the comparison aimed at it

`hold_ms` defaults to `0.0`. Under `range > 6` that meant *don't fire*. The moment
a `hold < 200` clause pointed at the same default it meant *fire*, and render a
number the file never stated. Adding an `OR` to a rule silently inverted a
parser default's safety direction.

### Duplicated logic drifts — three times, same two files

The CLI and MCP error handlers were separate copies of one idea; the copy shipped
broken twice. `loader.py` and `layers.py` read the same `when:` block two ways.
When you fix one, check its twin in the same commit.

### Recurring defect families, each seen more than once

1. Defaults that don't fire — `.get(k, default)` returns `None` for a
   present-but-null key; a bareword `on:`/`off:` parses as boolean. **Six times.**
2. Allowlists derived from the thing they validate.
3. Knowledge in one document not carried into the model.
4. Mathematically correct, domain wrong.
5. Regex word boundaries against numbered names — `\biem\b` never matches `IEM3`.
6. Trusting the other side of a boundary to be well-formed.
7. Silent skips, where a caller cannot tell "nothing found" from "never checked".
8. Duplicated logic that drifts.
9. Tests that pass with the code they cover deleted.

---

## 7. Domain facts established with ToanAZ — do not re-derive

`TB` = talkback · `Flown` = flown array · `Side` = sidefill, **and a sidefill is a
monitor** · `Cen` = center speaker · a bus named `HEADSET` is **input-side**, a
subgroup, not a monitor send · Dugan automix is not AI · polar pattern is not
selected by frequency range.

**Pre-fader is his norm**, especially on a big show. Post-fader monitor sends are a
deliberate trade of monitor independence for setup speed on a small or easy show.
So G8 is correct for him, and show scale is **declared**, not derived. The
per-channel pre/post split is a show-time judgement the tool must not try to make.

On `example-Vu.snap`: buses 1–6 are source subgroups (MIC, MUSIC, DRUM, BAND,
HEADSET, STRING), 7–10 monitors (SIDEFILL, MON VOX, MON L, MON R), 11–16 FX. 40
channels, 3 live, 23 unpatched, 6 unnamed. `My Lap` ×2 and `RECODING` stay
unclassified by design — `RECODING` is a typo in his file, and reporting it beats
guessing at misspellings. Channel 11 `HS4` carries an active gate at 40 dB range
with 10 ms hold *and* an active automix insert: E6's one real catch.

---

## 8. Environment

- **PowerShell is the shell.** Backticks in a `git commit -m` string swallow words; use `git commit -F -` with a quoted heredoc.
- **Never build regex or YAML in a Python heredoc.** `\b` in a non-raw string is a backspace. Use the Edit tool.
- `ruamel.yaml` is installed and is a hard dependency. `anthropic` and `mcp` are **not** installed, by design — do not install them to "verify" anything.
- Model id is `claude-opus-5`. `client.messages.parse(..., output_format=Model)` → `.parsed_output` is correct; the `output_format` deprecation applies to `messages.create()`. Verified against the `claude-api` skill — do not re-research it.
- Excluded from git and large: `user-files/WING-Edit.exe` (94 MB), `user-files/User-Manual_WING-series_*.pdf` (20 MB).

---

## 9. First move

1. Ask ToanAZ which sub-project from §2, recommending **B** with the reasoning.
2. Invoke `superpowers:brainstorming` — do not start designing before it.
3. If any of §3's questions have been answered, apply them first: they are YAML
   data changes, not code, and each one is small.
