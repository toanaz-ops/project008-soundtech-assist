# wing-parser — roadmap

**Last updated:** 2026-08-23, live-watch acceptance closed on the real console · **`main` @ `59197b8`** ·
1225 tests passing, 1 skipped (FastMCP, by design)

This file is the **single source of truth** for what this project has built and
what is left. It exists because the roadmap was previously re-derived from
memory in every next-session prompt, and a table copied by hand each cycle drifts
from the code it describes.

**Update this file at the end of every cycle**, in the same commit as that
cycle's completion handoff. A next-session prompt should link here, not restate
it.

---

## 1. What the tool is

A parser and advisory tool for Behringer WING scenes. It reads a scene — from a
`.snap` file or from a running console — says what each channel and bus actually
is, and tells you what looks wrong.

"Wrong" means **ToanAZ's own mixing judgement**, encoded in three layers of YAML.
It is not a generic linter, and that is the point: a rule exists because he
decided it should, and every rule records `source:` and `rationale:` saying who
decided and why.

```
.snap file  ─┐
             ├→ core/ → descriptors/ → query/ → classifier/ → advisory/ → cli/
live console ┘        (showcontext/ attaches a cue sheet alongside)
   net/                (net/watch/ polls a live desk for changes)
                       (showcontext/ingest/ builds a cue sheet from a spreadsheet)
   edit/ + ui/         (desktop app: journal, repairs, PySide findings UI;
                        packaging/wing-ui builds a standalone .exe)
```

## 2. Standing constraints that shape every decision below

These are not preferences. They have each been paid for at least once.

| | |
|---|---|
| **Offline first** | The tool is used in venues where the network is unreliable or absent. `mcp` and `anthropic` are optional extras and stay uninstalled. No test opens a socket to a real console. |
| **Deterministic core** | `core`, `descriptors`, `query`, `advisory`, `showcontext`, `net` and `ingest` never call a model. The **only** model call in the system is an optional classifier fallback for a name the pattern matcher cannot resolve. |
| **Never fabricate** | No value the file or the console does not state. Anything unreadable becomes a visible comment; nothing is dropped silently. |
| **Coexist with the desk** | Anything touching a live console must run alongside WING-Edit and Companion without displacing them. ToanAZ's words: *"cần song song không đá nhau."* |
| **Modular** | ~200-line files, split by responsibility layer. |
| **Evidence, not assertion** | A measurement nobody can re-run is not evidence. `docs/probes/` holds twelve read-only scripts, each mapped to the claim it supports; sub-project H added two more OSC probes in `probes/`. |

Shipped alongside the library: **7 Claude skills** in `skills/` — `wing-analyze`,
`wing-channel`, `wing-diff`, `wing-doctor`, `wing-net`, `wing-routing`,
`wing-watch`. `tests/test_examples.py` pins that set **by name**, so adding one
without documenting it fails with the missing name rather than a count
mismatch. Any sub-project that adds a command should ask whether it also wants a
skill; **G2a did not add one for `showcontext import`**, which is worth revisiting.

## 3. Done

Listed in the order they landed. Each row's spec is the design authority for that
subsystem; each handoff records what it measured and what it left open.

| | Sub-project | What it delivered | Tests at completion |
|---|---|---|---|
| — | **Phase 1** | The `.snap` decoder, descriptors, query layer, classifier and CLI. 24 tasks. | 364 |
| A | **Advisory loop closure** | The rule engine reads YAML; a finding can be fed back on and remembered. 6 tasks. | 406 |
| B | **Rule-set growth** | Base rules **3 → 32**, across 9 files. 14 tasks. | 527 |
| G1 | **Show context** | A cue sheet loads beside a scene; rules Q1–Q7. Base rules **32 → 39**. | 588 |
| H | **Desktop app** | An edit layer (pointer, journal, writer, repairs) plus a PySide UI over the advisory findings; packaged as a standalone `.exe`. Landed on an orphan branch on 2026-08-18 and merged into `main` on 2026-08-23 — it never appeared in this table until then. | 1225 (combined with everything above) |
| C · D | **WING over Ethernet** | OSC read and write; `wing net identity / snapshot`, `doctor --live`, `diff --live-before`. 20 commits. | not recorded in that handoff |
| C2 | **Live watch** | `wing net watch` polls a live desk for changes. | 1055 |
| G2a | **Assisted ingest (deterministic half)** | `wing showcontext import` — an Excel running order becomes a show-context file, entirely offline. | **1134** |

### Where each one's paperwork lives

| | spec | plan | completion handoff |
|---|---|---|---|
| Phase 1 | `2026-08-13-wing-scene-skill-design.md` | `2026-08-13-wing-scene-parser-phase1.md` | `2026-08-15-wing-parser-phase2-complete.md` |
| A | `2026-08-16-advisory-loop-closure-design.md` | `2026-08-16-advisory-loop-closure.md` | `2026-08-16-advisory-loop-closure-complete.md` |
| B | `2026-08-16-rule-set-growth-design.md` | `2026-08-16-rule-set-growth.md` | `2026-08-17-rule-set-growth-complete.md` |
| G1 | `2026-08-17-input-pipelines-design.md` | `2026-08-17-input-pipelines-g1.md` and `2026-08-17-g1-noise-profile.md` | `2026-08-17-input-pipelines-g1-complete.md` |
| H | `2026-08-18-desktop-app-design.md` | `2026-08-18-desktop-app.md` | `2026-08-18-desktop-app-complete.md` |
| C · D | `2026-08-21-wing-net-design.md` | — | `2026-08-21-wing-net-complete.md` |
| C2 | `2026-08-21-live-watch-design.md` | `2026-08-21-live-watch.md` | `2026-08-22-live-watch-complete.md` |
| G2a | `2026-08-22-assisted-ingest-design.md` | `2026-08-22-assisted-ingest-g2a.md` | `2026-08-22-assisted-ingest-g2a-complete.md` |

Specs are in `docs/superpowers/specs/`, plans in `docs/superpowers/plans/`,
handoffs in `docs/handoff/`.

## 4. Not done

```
        ┌─────────────────────────────────────────┐
  A ────┤                                         │
  B ────┤                                         ├──→  F  (decision tier / auto-mix)
  C,D ──┤                                         │      largest; decompose again
  G1 ───┴──→ G2a ──→ G2b                          │
                                                  │
        E  (audio analysis) ──────────────────────┘
           needs a second transport first
```

| | Sub-project | Depends on | Size | Console? |
|---|---|---|---|---|
| **G2b** | The assisted half of ingest: a model proposes a column mapping from a header sample, and guesses cue-sheet terms the vocabulary lacks | G2a | medium | no |
| **E** | Audio analysis — LUFS, RT60, SPL | a metering transport | large | eventually |
| **F** | Decision tier / auto-mix | A, B, C, D, G | largest | eventually |

Each gets its own **brainstorm → spec → plan → implementation** cycle. Invoke
`superpowers:brainstorming` before designing any of them.

### G2b — the recommended next piece

The sequenced execution order for everything below lives in
`docs/superpowers/plans/2026-08-23-next-steps.md`.

G2a deliberately contains **no model call**. It reads a spreadsheet through a
mapping file ToanAZ writes by hand, and resolves Vietnamese performer terms
through a vocabulary he curates. G2b removes the typing, in the two places where
judgement is genuinely required:

1. **Proposing the column mapping.** Every producer sends a different layout,
   with the header row often not row 1. Reading an arbitrary spreadsheet's
   *structure* is a judgement task; G2a made ToanAZ do it once per client. G2b
   offers to do it from a ~20-line header sample and hand him a mapping to
   check — a small, reviewable artifact, not 200 rows through a model.
2. **Guessing a term the `cuesheet:` vocabulary lacks**, and offering to record
   the answer permanently — the pattern `classifier/llm.py` and
   `classifier/cache.py` already establish.

**G2b is where the multi-provider question becomes real.** ToanAZ asked on
2026-08-21 for the design to admit providers other than Anthropic, and decided on
2026-08-22: *not in G2a, but leave the room.* G2a left it by taking its
vocabulary lookup as an injected callable.

What makes it non-trivial, recorded so G2b's brainstorm starts from it:
`wing_parser/classifier/llm.py` hard-codes Anthropic at three levels. `MODEL`
(`:22`) and `import anthropic` (`:66`, `:74`) are renames.
`client.messages.parse(..., output_format=…)` (`:82-102`) is a
**provider-specific structured-output call** that OpenAI and Gemini each spell
differently. That is the actual content of the question.

**Do the cheap thing before starting G2b** (see §5, items 1 and 2). G2a was built
entirely against an invented fixture, and G2b's whole job is to guess what the
vocabulary lacks. Sizing it against a real sheet costs an hour and changes what
G2b should be.

### E — blocked on a transport that does not exist yet

**Metering needs its own spec before E can start.** Measured in the C2 cycle
(live-watch design §2.3): there is **no meter anywhere in the OSC tree**, and
`/$stat/ppm` is a setting that did not move across 20 reads. Metering lives on
the console's native UDP channel — **a second transport, not an extension of
`net/`**. That transport is the doorway to E, and it is a sub-project in itself.

### F — do not start it yet

It depends on everything, including the half of G that is not built. Expect to
decompose it again when the time comes.

## 5. Open, and only ToanAZ can close it

These are judgement calls about his own work, or facts only a live console can
supply. **Do not guess them.**

1. **A real cue sheet has never been read.** G2a was built entirely against a
   fixture invented from his description. One real `.xlsx` dropped into
   `tests/data/` is the highest-value hour available, and may change the mapping
   fields. *(New 2026-08-22.)*
2. **The `cuesheet:` vocabulary ships empty.** Only loanwords `patterns.yaml`
   already catches (`guitar`, `bass`, `piano`) resolve; everything else becomes
   a comment — correct, but a seed of the twenty terms he meets most would make
   the first run useful. *(New 2026-08-22.)*
3. **The limiter `dyn.mdl` token.** Needs the **complete** list of
   limiter-capable models he would use; a missing member makes G7 fire on a
   protected IEM, the exact failure the rule exists to prevent. Closed as
   underivable offline after three probes
   (`docs/handoff/2026-08-17-limiter-token-probe.md`).
4. **Is G10's suppression his standing practice?** `shows/small.yaml` supersedes
   it, but the rule's own `source:` records that he *delegated* the call.
5. **Should any advisory rule read `$fdr` instead of `fdr`?** `fdr` is the
   strip's own position (*intent*); `$fdr` is the value after DCA contribution
   and mute-override fold in (*result*). A rule about what the audience actually
   hears may want the second.
6. **Should a gate's `1:3` ratio be modelled as a number?** `Dyn.ratio` is
   `float | None` and `None` for the `a:b` form. Nothing reads it. Latent.
7. **`expects:` accepts pattern-derived kinds only.** A kind declared by hand in
   `knowledge/toanaz/classifier.yaml` would be refused. Latent.

## 6. Waiting on hardware — NOTHING

**Closed 2026-08-23**, one sitting with the console back from its show
(WING-GIAQUY, fw 3.1). Full details:
`docs/handoff/2026-08-23-live-watch-acceptance-complete.md`.

1. **Detection: proven.** 120 s of watch against the real desk, ~150 change
   events, every fader drag and solo press driven from WING-Edit reported
   within ~250 ms.
2. **Coexistence with WING-Edit: proven.** WING-Edit stayed connected and was
   the source of every change while the poller ran all 220 leaves.
3. **Subscribe verbs: negative, closed as underivable.** All ten candidate
   verbs silent while controls were actively moving, with a passing control
   GET proving the harness. Polling is the only mechanism.

One operational lesson survived the session: `walk_schema` can transiently
lose whole top-level families under burst probing (first run watched only 16
leaves with seven families unresolved; seconds later everything resolved).
It reports unresolved visibly rather than hiding them — so if a watch opens
with unresolved families, **rerun before believing the list is small**.

## 7. How a cycle runs

`superpowers:brainstorming` → spec → `superpowers:writing-plans` → plan →
`superpowers:subagent-driven-development`: one fresh implementer per task, a
reviewer after each, a scoped re-review per fix round, and one whole-branch
review on the strongest model at the end.

Two findings from the G2a cycle are worth carrying into every future one:

- **The whole-branch review has earned its cost four cycles running**, and in the
  same shape every time: a defect spanning files that no single task's diff
  contained. Budget for it; it is not optional polish.
- **Ten instances of one defect shape landed in G2a alone** — correct code
  carrying a false description. Every one was caught in review and **none by a
  test**, because no test runs a docstring, an error message, or a line of
  user-facing instructions. Tell every implementer that a claim about another
  module must be checked by opening that module, and tell every reviewer it may
  **run** the code, not only read it.
