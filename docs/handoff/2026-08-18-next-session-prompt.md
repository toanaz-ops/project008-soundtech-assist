# WING scene parser — next session

**Date:** 2026-08-18 · **Branch:** `main` @ `69ead3f` · **State:** 596 tests
passing, 1 skipped (FastMCP, by design), nothing uncommitted

Paste this whole file as the opening message of the next session. It
supersedes `2026-08-17-next-session-prompt.md`.

---

## 1. What this project is

A parser and advisory tool for Behringer WING `.snap` scene files. It reads a
scene, says what each channel and bus actually is, and tells you what looks
wrong — where "wrong" is **ToanAZ's own judgement**, encoded in three layers of
YAML data, not a generic linter.

```
.snap (JSON)
  → core/         decode into frozen records
  → descriptors/  YAML lookup tables (EQ models, tap points, tags, safes)
  → query/        navigable views: WingScene → Channel / Bus, plus derived
                  properties (in_use, notch_count, receives_ambient, …)
  → showcontext/  NEW: a hand-written cue-sheet YAML loaded beside the scene
  → classifier/   name → role, regex patterns with confidence bands
                  (>=0.8 confident · >=0.4 usable · else unknown)
  → advisory/     three rule layers, deterministic, all YAML data:
                    1. base    39 shipped rules in 9 files
                    2. toanaz  knowledge/toanaz/principles.yaml
                    3. show    knowledge/toanaz/shows/<name>.yaml via --profile
  → cli/          wing analyze | channel | routing | doctor | diff | feedback
                  | showcontext lint
```

Fully offline. `mcp` and `anthropic` are optional extras and stay uninstalled.
`docs/knowledge-base/` is read-only source material the base rules cite.

## 2. Where things stand

Four bodies of work are merged: **Phase 1** (24 tasks), **advisory loop
closure** (6), **sub-project B — rule-set growth** (14, base layer 3 → 32
rules), and — landed 2026-08-17/18 — **sub-project G1 — show context** plus a
follow-up noise-profile cycle.

G1 added `wing_parser/showcontext/`, two rule iterators plus a third for
per-kind expectations, seven rules Q1–Q7, and the CLI surface `doctor --show`,
`feedback --show`, `showcontext lint [--fix]`. Base rules went 32 → **39 across
9 files**.

Two long-standing questions were also closed: G10 is now superseded in the
`small` profile, and the limiter `dyn.mdl` token is documented as
**offline-underivable** — three independent probes, negative, do not go looking
again (`docs/handoff/2026-08-17-limiter-token-probe.md`).

Current behaviour on the real files:

| | result |
|---|---|
| `doctor user-files/example-Vu.snap` | **22 findings** — unchanged by G1, pinned in three test files |
| `doctor … --profile small` | 6, with `[suppressed]` lines for G8 and G10 |
| `doctor … --show tests/data/example-Vu-show.yaml` | 22 + Q1, Q2, Q4, Q5, Q6 |
| `doctor user-files/factory-scene.snap` | none — pinned by test |

**Read before touching anything:**
- `docs/handoff/2026-08-17-input-pipelines-g1-complete.md` — G1's outcome, the
  twelve triaged residuals, and the lessons
- `docs/superpowers/specs/2026-08-17-input-pipelines-design.md` — the design
  authority for show context; §6.1 records decisions made after the first merge,
  §8 designs G2, §11 lists open questions
- `docs/handoff/2026-08-17-rule-set-growth-complete.md` and
  `docs/superpowers/specs/2026-08-16-rule-set-growth-design.md` §8 — killed rule
  families, do not re-mine them

## 3. How to use the tool (PowerShell)

From the repo root. `wing` works if pip-installed (`pip install -e .`);
`python -m wing_parser.cli` always works.

```powershell
python -m wing_parser.cli doctor user-files\example-Vu.snap
python -m wing_parser.cli doctor user-files\example-Vu.snap --profile small
python -m wing_parser.cli doctor user-files\example-Vu.snap --show tests\data\example-Vu-show.yaml
python -m wing_parser.cli showcontext lint tests\data\example-Vu-show.yaml --fix
python -m wing_parser.cli analyze user-files\example-Vu.snap
python -m wing_parser.cli channel user-files\example-Vu.snap 11
python -m wing_parser.cli routing user-files\example-Vu.snap
python -m wing_parser.cli diff old.snap new.snap
python -m pytest tests/
```

A show-context file is hand-written YAML: `segments`, each with optional
`time:`, an `expects:` list of classifier kinds, and `cues:` naming channels and
DCAs. The worked example is `tests/data/example-Vu-show.yaml`; the format is
spec §3. Typos in `expects:` and `action:` are repaired only when provably
unambiguous — case and separators silently, a one-edit near-miss loudly, a tie
refused. That radius rests on a **measured** minimum distance of 2 across the 35
channel kinds, pinned by a test; do not widen it without re-measuring.

## 4. The remaining roadmap

Phase 1 spec §14 defers independent subsystems. Done: A (advisory loop), B (rule
growth), G1 (show context). Remaining — each gets its own brainstorm → spec →
plan → implementation cycle; **invoke `superpowers:brainstorming` before
designing any of them**:

| | Sub-project | Depends on | Size |
|---|---|---|---|
| G2 | Assisted ingest: Excel/Sheets and PDF/photo → a G1 show-context file | G1 | medium; already designed in spec §8 |
| C | OSC read — connect to a live WING, read running state | — | large, new subsystem |
| D | OSC write — push changes back to the console | C | large + show risk |
| E | Audio analysis (LUFS, RT60, SPL) | — | large, needs I/O + hardware |
| F | Decision tier / auto-mix | A, C, G | largest — expect to decompose again |

G2, C and E are unblocked. **Ask ToanAZ which; do not assume.** G2 is the
natural next step — it is the half of sub-project G that makes the other half
usable without hand-typing a cue sheet, and its design is already written.

## 5. Open questions with ToanAZ — do not guess these

1. **The limiter `dyn.mdl` token.** Load a limiter onto a bus, save, hand over
   the `.snap`. Needs the **complete** list of limiter-capable models he would
   use — a missing member makes G7 fire on a protected IEM, the exact failure
   the rule exists to prevent. Closed as underivable offline; only he can answer.
2. **Is G10's suppression his standing practice?** `shows/small.yaml` supersedes
   it on the probed ground that the rig carries no ambient mic at all, but the
   rule's own `source:` records that he *delegated* the call rather than making
   it. Confirm or revert.
3. **`expects:` accepts pattern-derived kinds only** (spec §11.4). A kind
   declared by hand in `knowledge/toanaz/classifier.yaml` bypasses the check and
   is consulted *first* by the classifier — so a manually declared kind would be
   refused by `expects:` even though his channels carry it. Latent today (that
   file is `channels: {}`). The fix is not free: unioning the two vocabularies
   would invalidate the minimum-distance-2 measurement the typo radius rests on.
4. **MCP has no `show` parameter** (spec §11.5). `wing_doctor` cannot load a show
   context, so a Claude session on the MCP surface cannot see Q1–Q7 at all.
   Close it or decline it deliberately.
5. Twelve Minor residuals, all triaged safe-to-defer with reasons, in the G1
   handoff. None load-bearing; fix opportunistically.

## 6. Standing rules from ToanAZ — not negotiable

**Never assert an unverified claim as fact.** A citation is not verification —
re-read the cited line at the moment of writing, and open the file it actually
names, not the one you assume. Where the answer depends on how he works, ask.
**Modular code, ~200-line files, split by responsibility layer.** **PowerShell,
not bash,** for anything handed to him. He verifies claims — show evidence.

## 7. How to run the work

`superpowers:subagent-driven-development`: one fresh implementer per task, a
reviewer after each, scoped re-review per fix round, one final whole-branch
review on the strongest model. Hand subagents **file paths**, never pasted
history. Global constraints to copy into every dispatch: deterministic
core/query/advisory/showcontext (no LLM) · offline, `mcp`/`anthropic`
uninstalled, FastMCP test keeps skipping · never fabricate a value the file does
not state · rules are YAML with `source:` + `rationale:` · PyYAML reads, ruamel
writes · `docs/knowledge-base/` read-only · `pytest.approx` for floats · every
Finding records its layer · **the unprofiled real file must still yield exactly
22 findings**.

## 8. What the G1 cycle taught

- **Seven defects in the plan and briefs were caught by implementers, and none
  was visible on re-reading.** A metric that could not satisfy its own test case;
  an error escaping unwrapped; the same false claim about channel 31 in two
  briefs; two citations naming the wrong section; a proposal to collapse two
  `except` branches that would have changed a user-visible message. Each surfaced
  only when someone *executed* the brief.
- **The final whole-branch review earned its cost twice.** `doctor --show --json`
  emitted non-JSON because the anomaly print sat before the `--json` branch — the
  flag in `__main__.py`, the print in `commands.py`, no task's diff holding both.
  The cycle before, it was `wing channel` labelling a matrix send as "bus".
- **A rule can ship claiming a check it cannot perform.** Q3 promised to catch a
  DCA that is "not built" while its predicate only detects a number outside 1–16
  — and all 16 exist in both sample files. Q1 has the same limitation and is
  *honestly titled*, which is the whole difference.
- **Q6's rationale took three attempts to be true** — overstated, then
  understated, then exact — while the code was right every time. Every wrong
  version was caught by *running* the state walk, not reading it, including the
  second, which rested on a correct analysis that answered only half the question.
- **An instruction an implementer may cite in its report belongs in the brief,
  not only in the dispatch.** A reviewer sees brief, report and diff — never the
  dispatch — so a dispatch-only instruction quoted back looks fabricated, and a
  careful reviewer will say so.

## 9. Domain facts established with ToanAZ — do not re-derive

TB = talkback · Side = sidefill, a sidefill is a monitor · HEADSET bus is
input-side · pre-fader is his norm, show scale is declared not derived · buses
1–6 subgroups, 7–10 monitors, 11–16 FX on the real file · `RECODING` typo stays
unclassified by design · TAP sends default pre-fader or pre-EQ, which is why G8
matches `POST` only · **his IEMs are matrices** 5–8, all with `dyn.on: true` ·
SIDE/SUB/FLOWN/CEN are matrices; mains are MAIN FOH / LiveStream / RECODING / TB
OUT · automix lives in `postins` (`mode: AUTO_X` → group, `w` → weight) ·
channel EQ builds from raw key `eq`, **not** `peq` · bus/channel EQ parses
exactly 6 bands · IEM = error, wedge/generic monitor = warning for the
no-dynamics rule.

New from G1: the `dyn` block has **two shapes** — the aux-input shape has
`cmode/cpeak/depth/fast` and no `ratio/att/rel`, and is where `CMB` lives — and
the FX rack's `mdl` is a **third** namespace (`C5-CMB`, `DOUBLE`, `NONE`).
Channels 1–40 all exist on `example-Vu.snap` with **no gap**; 31–36 are
blank-named; 41 is the first absent number; DCAs run 1–16 in both sample files.

## 10. Environment

PowerShell is the shell; `git commit -F -` with a heredoc, never backticks in
`-m`. Never build regex or YAML in a Python heredoc (`\b` = backspace); use the
Edit tool. `ruamel.yaml` installed; `anthropic`/`mcp` not, by design. Tests may
print no pytest summary trailer — use the exit code or `--junitxml`. **The repo
lives on a Google Drive path and git/ripgrep can take minutes or appear to
hang** — wait rather than interrupting, then verify with `git log --oneline -1`.
Excluded from git: `user-files/WING-Edit.exe`, the WING manual PDFs.

## 11. First move

1. Ask ToanAZ which sub-project from §4. **G2 is the recommendation** — it makes
   G1 usable without hand-typing a cue sheet, and spec §8 already designs it —
   but let him pick.
2. If he brings the limiter `mdl` token, a verdict on G10, or an answer on the
   `expects:` vocabulary question, apply those first; the first two are small
   YAML edits.
3. Invoke `superpowers:brainstorming` before designing anything.
