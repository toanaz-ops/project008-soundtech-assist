# WING scene parser — next session

**Date:** 2026-08-22 (revised, after G2a landed) · **Branch:** `main` @ `bfe89dc`
· **State:** 1134 tests passing, 1 skipped (FastMCP, by design), nothing
uncommitted

Paste this whole file as the opening message of the next session. It supersedes
the earlier 2026-08-22 version, whose recommendation was G2a — **G2a is now
done.**

---

## 0. Read this first: is the console back?

**ToanAZ's console went out on a show on 2026-08-22.** Ask whether it is back
before planning anything that needs it. If it is, §5's two experiments take one
sitting between them and should be run **before anything else**, because one of
them tests a requirement he called non-negotiable.

If it is still away, everything in §4 is offline work.

## 1. What this project is

A parser and advisory tool for Behringer WING scenes. It reads a scene — from a
file or from a running console — says what each channel and bus actually is, and
tells you what looks wrong, where "wrong" is **ToanAZ's own judgement**, encoded
in three layers of YAML, not a generic linter.

```
.snap file  ─┐
             ├→ core/ → descriptors/ → query/ → classifier/ → advisory/ → cli/
live console ┘        (showcontext/ attaches a cue sheet alongside)
   net/                (net/watch/ polls a live desk for changes)
                       (showcontext/ingest/ builds a cue sheet from a spreadsheet)
```

Fully offline; `mcp` and `anthropic` are optional extras and stay uninstalled.
**39 base rules across 9 files. 7 Claude skills in `skills/`. 12 probe
scripts.**

## 2. Where things stand

Merged: **Phase 1**, **advisory loop closure**, **rule-set growth**, **G1 show
context**, **C and D — WING over Ethernet**, **C2 live watch**, and — this cycle
— **G2a, assisted ingest**.

Read before touching `showcontext/ingest/`:
- `docs/superpowers/specs/2026-08-22-assisted-ingest-design.md` — the design
  authority
- `docs/handoff/2026-08-22-assisted-ingest-g2a-complete.md` — this cycle's
  outcome, what it taught, and what is still open

Current behaviour:

| | result |
|---|---|
| `doctor user-files/example-Vu.snap` | **22 findings** — pinned in three test files |
| `doctor … --profile small` | 6, plus `[suppressed]` lines |
| `doctor … --show tests/data/example-Vu-show.yaml` | 27 |
| `doctor user-files/factory-scene.snap` | none |
| `doctor --live <ip>` | the same findings the desk's own scene file gives |
| the five real scenes | 0, 13, 13, 1, 17 — pinned in `tests/test_corpus_realfiles.py` |
| `showcontext import` on the fixture | 4 segments, 2 expectations, 4 comments |

## 3. How to use it (PowerShell)

```powershell
python -m wing_parser.cli doctor user-files\example-Vu.snap
python -m wing_parser.cli doctor user-files\example-Vu.snap --show tests\data\example-Vu-show.yaml
python -m wing_parser.cli showcontext import ros.xlsx --map knowledge\toanaz\sheets\abc.yaml -o tonight.yaml
python -m wing_parser.cli showcontext import ros.xlsx --map ...\abc.yaml --scene tonight.snap
python -m pytest tests\
```

Needing a console (see §0):

```powershell
python -m wing_parser.cli net identity 192.168.128.28
python -m wing_parser.cli net watch 192.168.128.28 --until 120
python -m wing_parser.cli doctor --live 192.168.128.28
```

**PowerShell, not Git Bash** — an OSC address starts with `/`, and MSYS rewrites
it into a Windows path.

## 4. The remaining roadmap

**Read [`docs/ROADMAP.md`](../ROADMAP.md) — it is the single source of truth for
what is built and what is left, and it is updated at the end of every cycle.**
Do not re-derive the roadmap here; a table copied by hand each cycle drifts from
the code it describes, which is why that file exists.

The short version: done are Phase 1, A, B, G1, C, D, C2 and **G2a**. Remaining
are **G2b**, **E** (blocked on a metering transport that does not exist yet) and
**F** (depends on everything; do not start it). Each gets its own brainstorm →
spec → plan → implementation cycle; **invoke `superpowers:brainstorming` before
designing any of them.**

**G2b is the recommendation, and it is where the multi-provider question finally
has a real consumer.** G2a deliberately contains no model call. G2b has
two — proposing a mapping from a header sample, and guessing a Vietnamese term
the `cuesheet:` vocabulary lacks — and ToanAZ decided on 2026-08-22: **not this
cycle, but leave the room**, which G2a did by taking its vocabulary lookup as an
injected callable.

What makes it non-trivial is recorded in the G2a spec §13:
`wing_parser/classifier/llm.py` hard-codes Anthropic at three levels. `MODEL`
(`:22`) and `import anthropic` (`:66`, `:74`) are renames.
`client.messages.parse(..., output_format=…)` (`:82-102`) is a
**provider-specific structured-output call** that OpenAI and Gemini each spell
differently. That is the actual content of the question.

**Before starting G2b, do the cheap thing first:** ask ToanAZ for one real
`.xlsx` cue sheet and a seed of twenty Vietnamese terms (see the G2a completion
handoff, §"Open"). G2a was built entirely against an invented fixture, and G2b's
whole job is to guess what that vocabulary lacks — sizing it against a real sheet
costs an hour and changes what G2b should do.

**Metering still needs its own spec.** Measured in the C2 cycle: there is no
meter anywhere in the OSC tree, and `/$stat/ppm` is a setting that did not move
across 20 reads. Metering lives on the native UDP channel — a second transport,
not an extension of `net/`. That is the doorway to E.

## 5. Waiting on the console — schedule these FIRST if it is back

Both are acceptance tests from the live-watch design §4.4, still open. §2.6 of
that spec records why silence is not evidence for either.

1. **Does polling detect a change?** `wing net watch` ran 240 s against the lab
   rack and built its list correctly — 220 leaves, no warnings, exit 0 — but
   **zero change events**, because nobody moved a control. The **loop** is
   proven. **Detection is not.**
2. **Does it coexist with WING-Edit?** Never run. This is the direct test of
   ToanAZ's hard requirement — *"cần song song không đá nhau"*.

Both close in one sitting, with one action:

```powershell
python -m wing_parser.cli net watch 192.168.128.28 --until 120
```

…then move one fader **from WING-Edit** while it runs. Record the actual output
either way. A negative result is written up, not retried into silence.

A third, smaller one: `probe2_subscribe_wide.py` sent ten subscribe forms and
all were silent, but the desk was idle and a *working* subscription would also
have been silent. Redo it with a control being moved.

## 6. Open questions with ToanAZ — do not guess these

1. **The limiter `dyn.mdl` token.** Needs the **complete** list of
   limiter-capable models he would use. Closed as underivable offline after
   three probes (`docs/handoff/2026-08-17-limiter-token-probe.md`).
2. **Is G10's suppression his standing practice?** The rule's `source:` records
   that he *delegated* the call.
3. **`expects:` accepts pattern-derived kinds only.** A kind declared by hand in
   `knowledge/toanaz/classifier.yaml` would be refused. Latent.
4. **Should a gate's `1:3` ratio be modelled as a number?** `Dyn.ratio` is
   `float | None`. Nothing reads it.
5. **Should any advisory rule read `$fdr` instead of `fdr`?** `fdr` is the
   strip's own position (*intent*), `$fdr` the value after DCA and mute-override
   fold in (*result*). His judgement about his own mixing.
6. **A real cue sheet, and a vocabulary seed.** New this cycle — see §4.
7. **Multiple AI providers.** Decided 2026-08-22: not in G2a, leave the room.
   G2b is where it becomes real.

## 7. Standing rules from ToanAZ — not negotiable

**Never assert an unverified claim as fact.** A citation is not verification —
re-read the cited line at the moment of writing, and **open the file the citation
names, not the one you assume**. **Modular code, ~200-line files, split by
responsibility layer.** **PowerShell, not bash.** He verifies claims — show
evidence.

## 8. How to run the work

`superpowers:subagent-driven-development`: one fresh implementer per task, a
reviewer after each, scoped re-review per fix round, one final whole-branch
review on the strongest model. Hand subagents **file paths**, never pasted
history.

Global constraints to copy into every dispatch: deterministic
core/query/advisory/showcontext/net/ingest (no LLM) · offline, `mcp`/`anthropic`
uninstalled, FastMCP test keeps skipping · never fabricate a value the file or
console does not state · rules are YAML with `source:` + `rationale:` · PyYAML
reads, ruamel writes · `docs/knowledge-base/` read-only · `pytest.approx` for
**computed** floats, exact comparison for a value that round-trips unchanged ·
**the unprofiled real file must still yield exactly 22 findings** and the five
real scenes 0, 13, 13, 1, 17.

**Two things worth copying from the G2a cycle:**

- Tell every implementer that a docstring or comment making a claim about
  another module must be checked **by opening that module**. Ten instances of a
  false description over correct code landed this cycle; every one was caught in
  review and none by a test.
- Tell every reviewer it may **run** the thing, not only read it. This cycle's
  strongest findings all came from a reviewer that executed a proof-of-concept.

## 9. Domain facts established with ToanAZ — do not re-derive

TB = talkback · Side = sidefill, a sidefill is a monitor · HEADSET bus is
input-side · pre-fader is his norm · buses 1–6 subgroups, 7–10 monitors, 11–16 FX
on the real file · `RECODING` typo stays unclassified by design · TAP sends
default pre-fader or pre-EQ, which is why G8 matches `POST` only · **his IEMs are
matrices** 5–8, all with `dyn.on: true` · SIDE/SUB/FLOWN/CEN are matrices; mains
are MAIN FOH / LiveStream / RECODING / TB OUT · automix lives in `postins` ·
channel EQ builds from raw key `eq`, **not** `peq` · bus/channel EQ parses exactly
6 bands · IEM = error, wedge = warning for the no-dynamics rule.

From C/D: the `dyn` block has **two shapes**; the FX rack's `mdl` is a **third**
namespace. The `.snap` `type` id tracks WING-Edit's version: 3.0 → `snapshot.9`,
3.2.1 → `snapshot.10`, 3.3.3 → `snapshot.11`.

From C2: `$`-prefixed keys are read-only and readable over OSC, absent from
`.snap` · `$fdr` and `$mute` are **effective** values · **only ONE OSC
subscription exists console-wide, and it expires after 10 s** — which is why the
watcher polls · a schema query reply is line-oriented · `walk_schema` skips every
`$` child · **an absent address costs ~20× a present one**.

**New from G2a:**

- **Q7 ships `enabled: false`** (`showcontext.yaml:166`), and
  `evaluator.evaluate` returns `[]` unconditionally for a disabled rule
  (`evaluator.py:158-160`). No cue revives it. Anything claiming otherwise is
  stale.
- **`channels` is a field of `Cue`, not of `Segment`.** A `Segment` carries
  `id / title / time / expects / cues`.
- **`Segment.time` is read by nothing.** One hit repo-wide for `.time`:
  `view.py:226`, and that is `cue.time`, serving Q7 — which is disabled.
- **`loader.py:104` refuses duplicate segment ids, case-insensitively.** Any
  producer of show-context files must enforce that itself.
- **`cache.lookup` re-reads and re-parses the whole knowledge file every call.**
  `resolve.py:31-40` carries the measurement: 50 lookups, 3.4 s versus 65 ms.
  Load once.
- **`patterns.yaml` is entirely English and console abbreviations.** A Vietnamese
  running order matches almost none of it, which is why `cuesheet:` exists as a
  separate domain.

## 10. Environment

PowerShell is the shell. **`git commit -F -` with a heredoc — never backticks
inside `-m`.** Never build regex or a string with escapes in a Python heredoc.
**Redirecting a Python script's output needs `python -u`.** Tests may print no
pytest summary trailer — **use the exit code**. Exactly one warning is expected
and pre-existing. **The repo lives on a Google Drive path and git and pytest are
slow** — a full suite run takes minutes; wait rather than interrupting, and run
it in the **foreground**: four agents stalled this cycle waiting on a background
watcher. `ruamel.yaml` and `openpyxl` installed; `anthropic`/`mcp` not, by
design. Excluded from git: `user-files/WING-Edit.exe`, the WING manual PDFs.

`docs/probes/` holds twelve read-only scripts with a README mapping each to the
claim it supports. **A measurement nobody can re-run is not evidence.**

## 11. First move

1. Ask whether the console is back. If yes, run §5 before anything else.
2. Otherwise ask ToanAZ for **one real `.xlsx` cue sheet** and a **seed of
   Vietnamese terms** (§4). Both are cheap and both change what G2b should be.
3. Then ask which sub-project. **G2b is the recommendation.**
4. If he brings an answer to any question in §6, apply it first.
5. Invoke `superpowers:brainstorming` before designing anything.
