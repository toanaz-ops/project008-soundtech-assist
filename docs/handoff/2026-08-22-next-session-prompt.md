# WING scene parser — next session

**Date:** 2026-08-22 · **Branch:** `main` @ `8fe87ae` · **State:** 1055 tests
passing, 1 skipped (FastMCP, by design), nothing uncommitted

Paste this whole file as the opening message of the next session. It supersedes
`2026-08-21-next-session-prompt.md`.

---

## 0. Read this first: the console is away

**ToanAZ's console went out on a show on 2026-08-22.** Until it is back on the
network, nothing that needs a live desk can run.

**Do not open the session by planning console-dependent work.** Two acceptance
tests are waiting on hardware (§5), and they are the *last* thing to schedule,
not the first. Everything in §4's roadmap can be designed and built offline;
pick from there.

If he says the console is back, §5's two experiments take one sitting between
them and should be run before anything else, because one of them tests a
requirement he called non-negotiable.

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
```

Fully offline otherwise; `mcp` and `anthropic` are optional extras and stay
uninstalled. **39 base rules across 9 files. 7 skills. 11 probe scripts.**

## 2. Where things stand

Merged: **Phase 1** (24 tasks), **advisory loop closure** (6), **rule-set
growth** (14, base 3 → 32), **G1 show context** (32 → 39), **C and D — WING over
Ethernet**, and — this cycle — **C2, live watch**.

Read before touching `net/watch/`:
- `docs/superpowers/specs/2026-08-21-live-watch-design.md` — the design
  authority. §2.6 lists what is measured *and not proven*; do not promote a line
  from there into a fact without re-measuring.
- `docs/handoff/2026-08-22-live-watch-complete.md` — this cycle's outcome, the
  defect it fixed, what is still open, and what it taught.

Current behaviour:

| | result |
|---|---|
| `doctor user-files/example-Vu.snap` | **22 findings** — pinned in three test files |
| `doctor … --profile small` | 6, plus `[suppressed]` lines for G8 and G10 |
| `doctor … --show tests/data/example-Vu-show.yaml` | 27 (22 + Q1, Q2, Q4, Q5, Q6) |
| `doctor user-files/factory-scene.snap` | none |
| `doctor --live <ip>` | the same findings the desk's own scene file gives |
| the five real scenes | 0, 13, 13, 1, 17 — pinned in `tests/test_corpus_realfiles.py` |

**ToanAZ's five real scenes are now tracked in git** — `CAI LUONG`,
`GIAQUY_WING`, `LIVE`, `OCHESTRA`, `Snapshot1`, all `snapshot.9` from WING Edit
3.0. He confirmed on 2026-08-21 that this repo is private and he wants them in,
knowing it writes channel and artist names permanently into history.

## 3. How to use it (PowerShell)

```powershell
python -m wing_parser.cli doctor user-files\example-Vu.snap
python -m wing_parser.cli doctor user-files\example-Vu.snap --profile small
python -m wing_parser.cli doctor user-files\example-Vu.snap --show tests\data\example-Vu-show.yaml
python -m wing_parser.cli diff user-files\factory-scene.snap user-files\example-Vu.snap
python -m pytest tests\
```

Needing a console (see §0 — it is away):

```powershell
python -m wing_parser.cli net identity 192.168.128.28
python -m wing_parser.cli net snapshot 192.168.128.28 -o today.snap
python -m wing_parser.cli net watch 192.168.128.28 --until 120
python -m wing_parser.cli doctor --live 192.168.128.28
python -m wing_parser.cli diff --live-before 192.168.128.28 saved.snap
```

**PowerShell, not Git Bash** — an OSC address starts with `/`, and MSYS rewrites
it into a Windows path, so `/ch/1/fdr` silently becomes
`C:/Program Files/Git/ch/1/fdr`.

## 4. The remaining roadmap — all of it is offline work

Done: A (advisory loop), B (rule growth), G1 (show context), C (OSC read),
D (OSC write), **C2 (live watch)**. Remaining — each gets its own brainstorm →
spec → plan → implementation cycle; **invoke `superpowers:brainstorming` before
designing any of them**:

| | Sub-project | Depends on | Size | Needs the console? |
|---|---|---|---|---|
| G2 | Assisted ingest: Excel/Sheets and PDF/photo → a show-context file | G1 | medium; designed in the G1 spec §8 | **no** |
| E | Audio analysis (LUFS, RT60, SPL) | — | large | eventually |
| F | Decision tier / auto-mix | A, C, D, G | largest — expect to decompose again | eventually |

**G2 is the recommendation while the desk is away.** It is fully offline, its
design is already written, and it is the half of sub-project G that makes G1
usable without hand-typing a cue sheet. It is also where ToanAZ's stated wish
for **multiple AI providers, not only Claude** (2026-08-21) first has a real
consumer — `classifier/llm.py` is currently the only place a model participates,
and it hard-codes Anthropic at three levels: the `MODEL` constant, the
`import anthropic`, and `client.messages.parse(..., output_format=...)`, which is
a provider-specific structured-output call. Abstracting that is a design question
worth putting to him, not a rename.

**Metering now needs its own spec.** Measured this cycle (live-watch design
§2.3): there is no meter anywhere in the OSC tree, and `/$stat/ppm` is a setting
that did not move across 20 reads. Metering lives on the native UDP channel — a
second transport, not an extension of `net/`. That is the doorway to E.

**Ask ToanAZ which; do not assume.**

## 5. Waiting on the console — schedule these LAST

Both are acceptance tests from the live-watch design §4.4, and both are still
open. §2.6 of that spec records why silence is not evidence for either.

1. **Does polling detect a change?** (§2.6(2)) `wing net watch` ran 240 s against
   the lab rack and built its list correctly — `watching 220 leaves (40 ch,
   16 bus, 4 main, 8 mtx, 16 dca)`, no unresolved warning, exit 0, and 220
   matches `probe9_stripset.py`'s prediction exactly. But **zero change events**,
   because nobody moved a control during the window. The **loop** is proven
   against a real console. **Detection is not.**
2. **Does it coexist with WING-Edit?** (§2.6(3)) Never run. This is the direct
   test of ToanAZ's hard requirement — *"cần song song không đá nhau"* — so it
   matters more than its size.

Both close in one sitting, with one action:

```powershell
python -m wing_parser.cli net watch 192.168.128.28 --until 120
```

…then move one fader **from WING-Edit** while it runs. Record the actual output
either way. A negative result is written up, not retried into silence — the
limiter-token probe is the precedent.

A third, smaller one: `probe2_subscribe_wide.py` sent ten subscribe forms and
all were silent, but the desk was idle and a *working* subscription would also
have been silent. That experiment needs redoing with a control being moved
before anyone concludes subscription is unavailable.

## 6. Open questions with ToanAZ — do not guess these

1. **The limiter `dyn.mdl` token.** Needs the **complete** list of
   limiter-capable models he would use — a missing member makes G7 fire on a
   protected IEM, the exact failure the rule exists to prevent. Closed as
   underivable offline after three probes
   (`docs/handoff/2026-08-17-limiter-token-probe.md`).
2. **Is G10's suppression his standing practice?** `shows/small.yaml` supersedes
   it, but the rule's own `source:` records that he *delegated* the call.
3. **`expects:` accepts pattern-derived kinds only.** A kind declared by hand in
   `knowledge/toanaz/classifier.yaml` would be refused. Latent today.
4. **Should a gate's `1:3` ratio be modelled as a number?** `Dyn.ratio` is
   `float | None` and `None` for the `a:b` form. Nothing reads it.
5. **Should any advisory rule read `$fdr` instead of `fdr`?** New this cycle.
   Live-watch design §2.2 establishes the two differ: `fdr` is the strip's own
   position (*intent*), `$fdr` is the value after DCA contribution and
   mute-override fold in (*result*). A rule about what the audience actually
   hears may want the second. This is his judgement about his own mixing, not a
   technical call.
6. **Multiple AI providers** (2026-08-21). See §4 — it has no real consumer until
   G2.

~~7. MCP has no `show` or `live` parameter.~~ **Closed this cycle.**

## 7. Standing rules from ToanAZ — not negotiable

**Never assert an unverified claim as fact.** A citation is not verification —
re-read the cited line at the moment of writing, and **open the file the citation
names, not the one you assume**. Where the answer depends on how he works, ask.
**Modular code, ~200-line files, split by responsibility layer.** **PowerShell,
not bash.** He verifies claims — show evidence.

## 8. How to run the work

`superpowers:subagent-driven-development`: one fresh implementer per task, a
reviewer after each, scoped re-review per fix round, one final whole-branch
review on the strongest model. Hand subagents **file paths**, never pasted
history.

Global constraints to copy into every dispatch: deterministic
core/query/advisory/showcontext/net (no LLM) · offline, `mcp`/`anthropic`
uninstalled, FastMCP test keeps skipping · never fabricate a value the file or
console does not state · rules are YAML with `source:` + `rationale:` · PyYAML
reads, ruamel writes · `docs/knowledge-base/` read-only · `pytest.approx` for
**computed** floats, exact comparison for a value that round-trips unchanged ·
every Finding records its layer · **the unprofiled real file must still yield
exactly 22 findings**.

## 9. What the C2 cycle taught

- **Every task's brief contained at least one real defect, and the implementer
  found it — nine tasks, nine finds.** A test answered by a fixture it never
  mentioned, so it asserted nothing. A docstring claiming `$name` exists
  everywhere when `/dca/N` has none. A spec naming `--for`, which cannot be an
  argparse dest because `args.for` is a syntax error. A helper that discarded
  error detail a pre-existing test depended on. None was visible on re-reading.
- **Three tests turned out to assert nothing, and all three were green.** Green
  is the best camouflage, because nobody audits a passing test. The only
  reliable check is to ask "if this broke, would it go red?" and then *break it*.
- **The whole-branch review earned its cost for the third cycle running,** and in
  the same shape every time: a defect spanning two files no single task's diff
  contained. This time MCP discarded a warning a later task had only just taught
  the loader to emit, so a partial console read looked complete — the same harm
  that task had just fixed, inverted. Both halves were correct when written.
- **The most valuable find came from a typo.** `10.0.0.1` was typed to smoke-test
  `diff --live`, and the impossible output — 76 differences against a console
  that does not exist — exposed a shipped defect: `doctor --live <wrong-ip>`
  printed `No findings.` To a working engineer that reads as *your desk is
  clean*. It meant *I never reached your desk*.
- **Correct code with a false description is this project's recurring shape.**
  It hit `read_labels` this cycle and Q6 in the G1 cycle. No test runs a
  docstring, so a wrong explanation survives every green suite indefinitely.

## 10. Domain facts established with ToanAZ — do not re-derive

TB = talkback · Side = sidefill, a sidefill is a monitor · HEADSET bus is
input-side · pre-fader is his norm, show scale is declared not derived · buses
1–6 subgroups, 7–10 monitors, 11–16 FX on the real file · `RECODING` typo stays
unclassified by design · TAP sends default pre-fader or pre-EQ, which is why G8
matches `POST` only · **his IEMs are matrices** 5–8, all with `dyn.on: true` ·
SIDE/SUB/FLOWN/CEN are matrices; mains are MAIN FOH / LiveStream / RECODING /
TB OUT · automix lives in `postins` · channel EQ builds from raw key `eq`, **not**
`peq` · bus/channel EQ parses exactly 6 bands · IEM = error, wedge = warning for
the no-dynamics rule.

From C/D: the `dyn` block has **two shapes** (the aux-input shape has
`cmode/cpeak/depth/fast`, and is where `CMB` lives); the FX rack's `mdl` is a
**third** namespace. The `.snap` `type` id tracks WING-Edit's version, not the
console: 3.0 → `snapshot.9`, 3.2.1 → `snapshot.10`, 3.3.3 → `snapshot.11`.

New from C2:

- **`$`-prefixed keys are read-only and readable over OSC**, and are absent from
  `.snap`. Per family: `/ch/N` has `$col $name $icon $solo $sololed $presolo
  $fdr $mute $muteovr`; bus/main/mtx the same minus `$presolo`; **`/dca/N` has
  only `$solo $sololed`** — no `$name`, no `$fdr`.
- **`$fdr` and `$mute` are EFFECTIVE values**, after DCA and mute-override.
- **Only ONE OSC subscription exists console-wide, and it expires after 10 s.**
  This is why the watcher polls: subscribing would displace whatever else held
  it. Whether WING-Edit is among those is **unverified** (§5).
- **A schema query reply is line-oriented**, giving name, type and range —
  `lock int [0 .. 1]`. Splitting on whitespace shreds it into phantom keys.
  `net/schema.py` parses by line; reuse it.
- **`walk_schema` skips every `$` child**, so a watch-list cannot read them from
  it. It supplies the strip *set*; the `$` keys come from
  `net/watch/data/watchlist.yaml`.
- **An absent address costs ~20× a present one** — the retry ladder hunts for it
  every round. Watch-lists must contain only addresses that exist.

## 11. Environment

PowerShell is the shell. **`git commit -F -` with a heredoc — never backticks
inside `-m`**, the shell evaluates the enclosed word and silently deletes it from
the message (this is in the standing notes and still caught me twice this cycle).
Never build regex or a string with escapes in a Python heredoc — use the editing
tools. **Redirecting a Python script's output needs `python -u`**, or buffered
stdout leaves the log empty until exit, which reads exactly like a hang.
`ruamel.yaml` installed; `anthropic`/`mcp` not, by design. Tests may print no
pytest summary trailer — use the exit code. **The repo lives on a Google Drive
path and git can be slow** — wait rather than interrupting. Excluded from git:
`user-files/WING-Edit.exe`, the WING manual PDFs.

`docs/probes/` holds eleven read-only scripts with a README mapping each to the
claim it supports. **A measurement nobody can re-run is not evidence** — if you
measure something, leave the script behind.

## 12. First move

1. **Do not schedule console work.** The desk is out on a show (§0).
2. Ask ToanAZ which sub-project from §4. **G2 is the recommendation** — fully
   offline, already designed, and the natural home for the multi-provider
   question he raised.
3. If he brings an answer to any question in §6, apply it first — items 1, 2 and
   4 are small edits.
4. When the console returns, run §5's two experiments before anything else.
5. Invoke `superpowers:brainstorming` before designing anything.
