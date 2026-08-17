# WING scene parser — next session

**Date:** 2026-08-17 · **Branch:** `main` @ `f5655ee` · **State:** 527 tests
passing, 1 skipped (FastMCP, by design), nothing uncommitted

Paste this whole file as the opening message of the next session. It
supersedes `2026-08-16-next-session-prompt.md`.

---

## 1. What this project is — the big picture

A parser and advisory tool for Behringer WING `.snap` scene files. It reads
a scene, says what each channel and bus actually is, and tells you what
looks wrong about the mix — where "wrong" is defined by **ToanAZ's own
judgement**, encoded in three layers, not by a generic linter.

The pipeline, end to end:

```
.snap (JSON)
  → core/        decode into frozen records (ChannelData, BusData, Send…)
  → descriptors/ YAML lookup tables (EQ models, tap points, tags, safes)
  → query/       navigable views: WingScene → Channel / Bus, plus derived
                 properties (in_use, notch_count, receives_ambient, …)
  → classifier/  name → role, regex patterns with confidence bands
                 (>=0.8 confident · >=0.4 usable · else unknown)
  → advisory/    three rule layers, deterministic, all YAML data:
                   1. base      32 shipped rules mined from docs/knowledge-base/
                   2. toanaz    knowledge/toanaz/principles.yaml (standing overrides)
                   3. show      knowledge/toanaz/shows/<name>.yaml via --profile
                 higher layers supersede base rules; profiles may declare
                 event: corporate|band to switch off other-event presets
  → cli/         wing analyze | channel | routing | doctor | diff | feedback
  → feedback     wing feedback logs ToanAZ's verdicts to knowledge/toanaz/feedback.jsonl
```

Everything runs fully offline. `mcp` and `anthropic` are optional extras
and stay uninstalled. `docs/knowledge-base/` is the read-only source
material the base rules cite.

## 2. Where things stand

Three bodies of work are delivered and merged:

- **Phase 1** (24 tasks): decoding, descriptors, query, classifier, the
  three-layer advisory engine, feedback log, CLI, MCP server, skills.
- **Advisory loop closure** (6 tasks): the upper two layers work; profiles
  suppress base rules with a printed `[suppressed]` line.
- **Sub-project B — rule-set growth** (14 tasks, merged 2026-08-17): base
  layer grew 3 → **32 rules** in 8 YAML files; the engine now sees mains
  and matrices (ToanAZ's IEMs are matrices 5–8 and were invisible before);
  monitor role split into `monitor.iem` / `monitor.wedge` / `monitor`;
  `event:` tagging; 8 derived query-layer properties; `starts_with`
  operator. Outcome and residuals: `2026-08-17-rule-set-growth-complete.md`.

Current behaviour on the real files:

| | result |
|---|---|
| `doctor user-files/example-Vu.snap` | **22 findings** — G8×12, G10×4, E6, G9(bus.7), PB1(ch.16), PB2(ch.21), PB4(ch.22), PB5(ch.13) |
| `doctor … --profile small` | 10, with `[suppressed] G8 …` |
| `doctor user-files/factory-scene.snap` | none — pinned by test |

The full 22-row contract is pinned in `tests/test_advisory_realfile.py`
with a regeneration command in its docstring.

**Read before touching anything:**
- `docs/superpowers/specs/2026-08-16-rule-set-growth-design.md` — this
  cycle's design, incl. §8 killed/blocked families (do not re-mine them)
- `docs/handoff/2026-08-17-rule-set-growth-complete.md` — residuals
- `docs/handoff/2026-08-16-advisory-loop-closure-complete.md` and
  `docs/handoff/2026-08-15-wing-parser-phase2-complete.md` — older lessons

## 3. How to use the tool (PowerShell)

From the repo root. `wing` works if the package is pip-installed
(`pip install -e .`); `python -m wing_parser.cli` always works.

```powershell
python -m wing_parser.cli doctor user-files\example-Vu.snap
python -m wing_parser.cli doctor user-files\example-Vu.snap --profile small
python -m wing_parser.cli doctor user-files\example-Vu.snap --json
python -m wing_parser.cli analyze user-files\example-Vu.snap
python -m wing_parser.cli channel user-files\example-Vu.snap 11
python -m wing_parser.cli routing user-files\example-Vu.snap
python -m wing_parser.cli diff old.snap new.snap
python -m wing_parser.cli feedback "G10:matrix.5" --verdict wrong --scene user-files\example-Vu.snap --note "small rig, no ambient by choice"
python -m pytest tests/
```

(`feedback` verdict choices are defined in `wing_parser/advisory/feedback.py`
`VERDICTS`; finding ids print in doctor output as `RULE:target`.)

To silence a rule for a kind of show: add a rule with `supersedes: [ID]`
to `knowledge/toanaz/shows/<name>.yaml` and run with `--profile <name>` —
`shows/small.yaml` is the worked example. A profile may also declare
`event: corporate` (or `band`) to switch off the other event's presets.

## 4. The remaining roadmap

Phase 1 spec §14 defers independent subsystems. Done: A (advisory loop),
B (rule growth). Remaining — each gets its own brainstorm → spec → plan →
implementation cycle; **invoke `superpowers:brainstorming` before designing
any of them**:

| | Sub-project | Depends on | Size |
|---|---|---|---|
| C | OSC read — connect to a live WING, read running state | — | large, new subsystem |
| D | OSC write — push changes back to the console | C | large + show risk |
| E | Audio analysis (LUFS, RT60, SPL) | — | large, needs I/O + hardware |
| F | Decision tier / auto-mix | A, C, G | largest — expect to decompose again |
| G | Input pipelines (setlist, cue sheet) | — | medium |

C and G are unblocked. **Ask ToanAZ which; do not assume.**

## 5. Open questions with ToanAZ — do not guess these

1. **The limiter `dyn.mdl` token** (open since Phase 1, §3.1 of the old
   handoff): he loads a limiter onto a bus, saves, reads `mdl`. Unlocks
   G7's second clause — the exact edit is in the closure spec §7.1.
2. **Are the four G10 findings real advice for his rig?** No ambient mic
   feeds any IEM matrix on `example-Vu.snap`. If that is a deliberate
   small-rig choice, the designed answer is `supersedes: [G10]` in a show
   profile — one YAML block, not a code change.
3. Residuals list in `2026-08-17-rule-set-growth-complete.md` — none are
   load-bearing; fix opportunistically or when he complains.

## 6. Standing rules from ToanAZ — not negotiable

**Never assert an unverified claim as fact.** A citation is not
verification — re-read the cited line at the moment of writing. Where the
answer depends on how he works, ask. **Modular code, ~200-line files, split
by responsibility layer.** **PowerShell, not bash,** for anything handed to
him. He verifies claims — show evidence.

## 7. How to run the work

`superpowers:subagent-driven-development`: one fresh implementer per task,
a reviewer after each, scoped re-review per fix round, one final
whole-branch review on the strongest model. Hand subagents **file paths**,
never pasted history. Global constraints to copy into every dispatch:
deterministic core/query/advisory (no LLM) · offline, `mcp`/`anthropic`
uninstalled, FastMCP test keeps skipping · never fabricate a value the file
does not state · rules are YAML with `source:` + `rationale:` · ruamel
round-trip for `knowledge/` files · `docs/knowledge-base/` read-only ·
`pytest.approx` for floats · every Finding records its layer.

## 8. What sub-project B taught (on top of the older lessons)

- **Probe the real file before designing, not just before dispatching.**
  One probe script killed three whole rule families the knowledge-base
  mining had produced (plugin-name rules — slots hold `FX13`/`NONE`;
  ALT-input rules — no such token; tap-point rules — `POST_FDR` on all 80
  channels including factory). The spec's §8 records them so nobody
  re-mines.
- **The plan's raw-key claims must be probed too.** The plan said channel
  EQ lives under `peq`; it lives under `eq` — an implementer caught it by
  reading `build_channel.py` instead of trusting the brief, and the
  controller carried the correction into every later dispatch via the
  ledger.
- **Derive inventories live, never from memory.** The controller told a
  docs implementer "19 rules"; the real count was 32. The dispatch's
  "derive it with `load_base_rules()`" instruction is what kept the wrong
  number out of the README.
- **An honest disable beats a noisy rule.** N2 (unnamed output) could not
  meet the factory-silence constraint (factory buses 9–16 sit at fader 0),
  so it ships `enabled: false` with the probed values quoted in its
  rationale — the pre-agreed fallback, executed instead of silently
  weakening semantics.
- **Reviews earn their cost.** Per-task reviewers caught a mutation-blind
  boundary test and two false README claims; the final whole-branch review
  caught a cross-task defect no per-task review could see (`wing channel`
  labelling matrix sends as "bus" — the renderer was outside every task's
  diff until the end).

## 9. Domain facts established with ToanAZ — do not re-derive

Everything in the old handoff §7 still holds (TB = talkback · Side =
sidefill, a sidefill is a monitor · HEADSET bus is input-side · pre-fader
is his norm; show scale is declared, not derived · buses 1–6 subgroups,
7–10 monitors, 11–16 FX on the real file · `RECODING` typo stays
unclassified by design). New this cycle:

- **TAP sends default pre-fader or pre-EQ on a WING** (ToanAZ 2026-08-16) —
  why G8 matches `POST` only. Recorded in G8's rationale.
- **His IEMs are matrices** (5–8: IEM MC, IEM CA SI 1/2, IEM3 BAKUP); SIDE,
  SUB, FLOWN, CEN are also matrices; mains are MAIN FOH / LiveStream /
  RECODING / TB OUT. All four IEM matrices carry `dyn.on: true`.
- WING automix lives in `postins`: `mode: AUTO_X` → group, `w` → weight.
- Bus/channel EQ parses exactly 6 bands (low/1–4/high; shelf shapes
  `leq`/`heq`); channel EQ builds from raw key `eq`, not `peq`.
- IEM = error, wedge/generic monitor = warning for the no-dynamics rule —
  his severity decision, 2026-08-16.

## 10. Environment

PowerShell is the shell; `git commit -F -` with a heredoc, never backticks
in `-m`. Never build regex/YAML in a Python heredoc (`\b` = backspace);
use the Edit tool. `ruamel.yaml` installed; `anthropic`/`mcp` not, by
design. Tests may print no pytest summary trailer on this machine — use
exit code or `--junitxml`. Excluded from git: `user-files/WING-Edit.exe`,
the WING manual PDFs.

## 11. First move

1. Ask ToanAZ which sub-project from §4 (C and G are the unblocked
   candidates — C connects to the real console, G feeds show context into
   the advisory; recommend based on what he wants next, then let him pick).
2. If he brings the limiter `mdl` token or a verdict on G10, apply those
   first — both are small YAML edits.
3. Invoke `superpowers:brainstorming` before designing anything.
