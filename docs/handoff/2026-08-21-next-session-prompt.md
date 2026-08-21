# WING scene parser — next session

**Date:** 2026-08-21 · **Branch:** `claude_desk/behringer-wing-ethernet-mixer-5de617`
**State:** 994 tests passing, 1 skipped (FastMCP, by design), nothing uncommitted

Paste this whole file as the opening message of the next session. It supersedes
`2026-08-18-next-session-prompt.md`.

---

## 1. What this project is

A parser and advisory tool for Behringer WING scenes. It reads a scene, says
what each channel and bus actually is, and tells you what looks wrong — where
"wrong" is **ToanAZ's own judgement**, encoded in three layers of YAML, not a
generic linter.

```
.snap file  ─┐
             ├→ core/  → descriptors/ → query/ → classifier/ → advisory/ → cli/
live console ┘         (showcontext/ attaches a cue sheet alongside)
   net/
```

The newest half is `net/`: the same analysis pointed at a **running console**
over OSC instead of a file. Fully offline otherwise; `mcp` and `anthropic` are
optional extras and stay uninstalled.

## 2. Where things stand

Merged: **Phase 1** (24 tasks), **advisory loop closure** (6), **rule-set
growth** (14, base 3 → 32 rules), **G1 show context** (base 32 → 39), and — this
cycle — **sub-projects C and D, WING over Ethernet**.

Read before touching `net/`:
- `docs/superpowers/specs/2026-08-21-wing-net-design.md` — the design authority.
  Every protocol claim was measured against a real console; where the official
  document disagrees, the spec says so and says which is which.
- `docs/handoff/2026-08-21-wing-net-complete.md` — outcome, the five findings
  that each cost an experiment, and the open questions.

Current behaviour:

| | result |
|---|---|
| `doctor user-files/example-Vu.snap` | **22 findings** — pinned in three test files |
| `doctor … --profile small` | 6, plus `[suppressed]` lines for G8 and G10 |
| `doctor … --show tests/data/example-Vu-show.yaml` | 22 + Q1, Q2, Q4, Q5, Q6 |
| `doctor user-files/factory-scene.snap` | none |
| `doctor --live <ip>` | the same findings the desk's own scene file gives |

## 3. How to use it (PowerShell)

```powershell
python -m wing_parser.cli doctor user-files\example-Vu.snap
python -m wing_parser.cli doctor --live 192.168.128.28
python -m wing_parser.cli net identity 192.168.128.28
python -m wing_parser.cli net snapshot 192.168.128.28 -o today.snap
python -m wing_parser.cli net get 192.168.128.28 /ch/1/fdr
python -m wing_parser.cli net set 192.168.128.28 /ch/1/fdr -6.0 --confirm
python -m pytest tests/
```

**PowerShell, not Git Bash** — an OSC address starts with `/`, and MSYS rewrites
it into a Windows path, so `/ch/1/fdr` silently becomes
`C:/Program Files/Git/ch/1/fdr`.

## 4. The remaining roadmap

Done: A (advisory loop), B (rule growth), G1 (show context), **C (OSC read)**,
**D (OSC write)**. Remaining — each gets its own brainstorm → spec → plan →
implementation cycle; **invoke `superpowers:brainstorming` before designing any
of them**:

| | Sub-project | Depends on | Size |
|---|---|---|---|
| G2 | Assisted ingest: Excel/Sheets and PDF/photo → a show-context file | G1 | medium; already designed in the G1 spec §8 |
| E | Audio analysis (LUFS, RT60, SPL) | — | large; the doorway is the native metering channel, now reachable |
| F | Decision tier / auto-mix | A, C, D, G | largest — expect to decompose again |

**Ask ToanAZ which; do not assume.** C and D landing changes the calculus: F is
now unblocked for the first time, and E's transport half is understood.

## 5. Open questions — do not guess these

1. **The limiter `dyn.mdl` token.** Still open from earlier cycles: needs the
   **complete** list of limiter-capable models he would use. Closed as
   underivable offline (`docs/handoff/2026-08-17-limiter-token-probe.md`).
2. **Is G10's suppression his standing practice?** `shows/small.yaml` supersedes
   it, but the rule's own `source:` records that he *delegated* the call.
3. **`expects:` accepts pattern-derived kinds only** — a hand-declared kind in
   `knowledge/toanaz/classifier.yaml` would be refused. Latent today.
4. **MCP has no `show` parameter, and now no live parameter either.** A Claude
   session on the MCP surface can see neither Q1–Q7 nor a console. Close it or
   decline it deliberately.
5. **Should a gate's `1:3` ratio be modelled as a number?** New this cycle.
   `Dyn.ratio` is `float | None` and `None` for the `a:b` form. Nothing reads it.
6. **Which `type` id does a live rack write?** Unmeasured. `snapshot.11` is
   assumed and marked as an assumption in `snapshot.py`. **To settle it: with
   WING-Edit connected, save a scene and read its `type`.** WING-Edit cannot be
   driven by the automation here — portable exe, not Start-menu registered.

## 6. Standing rules from ToanAZ — not negotiable

**Never assert an unverified claim as fact.** A citation is not verification —
re-read the cited line at the moment of writing. Where the answer depends on how
he works, ask. **Modular code, ~200-line files, split by responsibility layer.**
**PowerShell, not bash.** He verifies claims — show evidence.

## 7. What this cycle taught

- **Every serious defect was found by running, not by reading.** A subagent
  justified skipping socket rotation with an argument that was sound on an empty
  desk and wrong the moment the desk held a scene; the walk silently lost 901 of
  5330 nodes. The same reasoning was in the spec, in my own words.
- **A plausible value can be silently wrong.** `,sfi` replies carry a 0-based
  *index* as the native value; taking it would have corrupted 1066 leaves while
  looking entirely reasonable. Only a push-then-read-back experiment exposed it.
- **Reference files can hide a bug indefinitely.** `build_dyn` could not parse a
  gate's `"1:3"` ratio, and neither sample file contains a gate on a strip, so
  991 tests passed over it. A default console broke it on 7 of 8 aux strips.
- **The fix that works is rarely the first plausible one.** Poisoned-socket
  recovery took three attempts — rotate per round, then bisect the chunk, then
  rotate per chunk — and only the third worked. Each was measured, not argued.

## 8. Environment

PowerShell is the shell; `git commit -F -` with a heredoc, never backticks in
`-m`. Never build regex or a string with escapes in a Python heredoc — use the
editing tools. `ruamel.yaml` installed; `anthropic`/`mcp` not, by design. Tests
may print no pytest summary trailer — use the exit code or `--junitxml`. **The
repo lives on a Google Drive path and git can be slow** — wait rather than
interrupting. Excluded from git: `user-files/WING-Edit.exe`, the WING manual
PDFs.

**The lab console `WING-GIAQUY` at `192.168.128.28` was left on
`factory-scene.snap`** — `doctor --live` reports no findings, matching the file.
A cross-console push leaves ~3200 leaves absent (a WEDIT layer this rack has
never had) and ~110 mismatched by one quantisation step; both are expected and
explained in the spec, not failures.

## 9. First move

1. Ask ToanAZ which sub-project from §4.
2. If he brings an answer to any question in §5, apply it first — items 1, 2 and
   5 are small edits.
3. Invoke `superpowers:brainstorming` before designing anything.
