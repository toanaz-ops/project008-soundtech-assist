# Sub-project G2a — assisted ingest (deterministic half) — complete

**Date:** 2026-08-22 · **Branch:** merged to `main` @ `bfe89dc` (fast-forward,
18 commits) · **State:** 1134 tests, `pytest` exit 0, both invariance gates hold

## What shipped

`wing showcontext import` — an offline importer that turns an event producer's
Excel running order into a show-context YAML file.

```powershell
python -m wing_parser.cli showcontext import ros.xlsx --map knowledge\toanaz\sheets\abc.yaml -o tonight.yaml
python -m wing_parser.cli showcontext import ros.xlsx --map ...\abc.yaml --scene tonight.snap -o tonight.yaml
```

Five modules under `wing_parser/showcontext/ingest/`, one direction, no module
calling back up:

| module | lines | responsibility |
|---|---|---|
| `sheet.py` | 155 | spreadsheet → rows of text. Interprets nothing. The only module that knows `openpyxl` exists. |
| `mapping.py` | **201** | per-client mapping file → resolved column letters. Refuses every ambiguity. |
| `build.py` | 198 | rows + an injected vocabulary lookup → `Segment` records + comments. Opens no file of its own. |
| `propose.py` | 64 | `--scene`: a commented-out cue skeleton |
| `emit.py` | 117 | records → YAML with comments, via `ruamel` |

`mapping.py` is **one line over** the ~200 guideline. Left as-is rather than
split mid-cycle; it is the largest because refusing an ambiguity means
explaining it, and every one of its errors prints the real alternatives.

Also: a third domain `cuesheet:` in `knowledge/toanaz/classifier.yaml` for
Vietnamese running-order terms, reusing the existing atomic write and
comment-preserving round-trip. It **ships empty** — see §"Open, needs ToanAZ".

## What it actually does for a show

An imported file activates **two of the seven** show-context rules, and the
README and the command's own summary both say so:

| | fires on an imported file? |
|---|---|
| Q4 "Show expects a source with no channel for it" | **yes** |
| Q5 "Show expects a source whose channels are all parked" | **yes** |
| Q1, Q2, Q3, Q6 | no — cue-gated. The file is a skeleton to add cues into. |
| Q7 | **never** — ships `enabled: false` (`showcontext.yaml:166`) |

Q7 was discovered mid-cycle to be disabled; the spec had claimed uncommenting a
cue would revive it. It cannot. `evaluator.evaluate` returns `[]` unconditionally
for a disabled rule (`evaluator.py:158-160`).

## Measured, not assumed

```
pytest exit 0 · 1134 collected (was 1056) · 1 pre-existing warning, by design
doctor user-files/example-Vu.snap        -> 22 findings   (unchanged)
the five real scenes                     -> 0, 13, 13, 1, 17   (unchanged)
```

Both gates were re-run on the **merged** `main`, not only on the branch.

The fixture import, end to end:

```
# imported 5 data row(s) -> 4 segment(s) carrying 2 expectation(s),
# 1 row(s) and 3 performer fragment(s) kept as comments, 1 blank row(s) skipped
```

## What this cycle taught

**Every task's brief contained a real defect, and the implementer found it —
in six of eight tasks.** The C2 cycle reported nine finds in nine tasks; this
one is the same shape at a similar rate. None was visible on re-reading the
brief; each was found by opening the file the brief made a claim about.

**Ten instances of one defect shape: correct code carrying a false
description.** Every one was caught in review, none by a test — because no test
runs a docstring, an error message, or a line of user-facing instructions. The
tenth arrived *inside the spec amendment written to remove such claims*, which is
the most useful data point in the list. A sentence asserting that two things
match is a sentence that must be checked by opening both.

**The whole-branch review earned its cost for the fourth cycle running, in the
same shape every time: a defect spanning files no single task's diff contained.**
This time it was segment-id uniqueness. `build.py` generated ids only for blank
cells; `loader.py:104` refuses duplicates; `propose.py` keys its proposals by id
and so was last-write-wins. The importer could write a file the project's own
loader rejects while exiting 0 — and `--scene` could attach channel 25, "Bass",
to a segment expecting `instrument.guitar`. A fabricated claim in the one place
ToanAZ is meant to act on literally.

**The blind spot had a shape, and it was in the tests.** Every propose and emit
test used a *single* segment with id `S1`. Eight passing task gates could not see
a collision because no test ever built two segments. When a whole class of defect
survives every gate, look at what shape the fixtures share.

**Reviewers that ran the code found what reviewers that read it did not.** The
strongest findings this cycle came from reviewers who executed a
proof-of-concept: rendering a proposal and stripping its `#` to see what the
loader made of it, or feeding a `.xlsx` that was really a text file. Reading
found wording; running found behaviour.

**A silent no-op is worse than visible junk.** The `--scene` proposal used to say
"uncomment to make this a cue". Doing that literally produced YAML that parses
without error and does nothing — `loader.py` ignores unknown keys, so nothing
warns. Visible junk gets fixed at the desk; a silent no-op is found during the
show.

## Open, needs ToanAZ

1. **No real cue sheet has ever been read.** The whole feature was built against
   a fixture invented from ToanAZ's description of his sheets. Dropping one real
   `.xlsx` into `tests/data/` and regenerating would be the highest-value hour
   available. It may change the mapping fields.
2. **The `cuesheet:` vocabulary ships empty.** Only loanwords the existing
   `patterns.yaml` already catches (`guitar`, `bass`, `piano`) resolve today;
   everything else becomes a comment — correct behaviour, but a seed of the
   twenty terms he meets most would make the first run useful. This is his
   judgement about his own work.
3. **`show:` derives from the spreadsheet's filename.** Nothing downstream reads
   it, so it is cosmetic, but `RunningOrder_Copy_v3(1).xlsx` becomes the label.
   `mapping.py` parses a `source:` field that nothing consumes — using it here is
   the obvious fix if he wants one.

## Deferred, with reasons

- `classifier/llm.py:45`'s `_DOMAIN_WORD` has no `"cuesheet"` entry. Harmless
  today (`.get(domain, "channel")`, and `anthropic` is uninstalled). **G2b must
  add it** — that is where cue-sheet terms first reach a model.
- `cli/commands.py` is 301 lines, over the guideline. It was 257 before this
  cycle. Splitting the showcontext handlers into their own module is its own task.
- Commit `fc8b93c` does not stand alone: it calls `read.last_column` before
  `sheet.py` has the field. The tip is green and the branch landed as a unit, but
  `git bisect` would mis-blame it.
- `docs/handoff/2026-08-17-input-pipelines-g1-complete.md:74` names
  `_channels_of`, renamed to `channels_of` this cycle. Left alone deliberately: a
  dated handoff is a record of what was true on its date.

## Where the evidence lives

`.superpowers/sdd/2026-08-22-assisted-ingest-g2a/` (git-ignored) holds the
per-task briefs, implementer reports, review packages and the progress ledger
for this cycle. It is scratch and `git clean -fdx` will destroy it; everything
load-bearing is in this file, the spec, and the commit messages.
