# Sub-project G1 — show context — outcome and residuals

**Date:** 2026-08-17 · **Branch** `claude_desk/next-session-handoff-bc5fa5`,
24 commits from `1ff104b` to `6b7fdaa` · **588 tests passing, 1 skipped**
(FastMCP, by design) · final whole-branch review clean

## What shipped

**Two long-standing questions closed first.**

- **G10's verdict.** `knowledge/toanaz/shows/small.yaml` now supersedes G10 as
  well as G8. Probed first: `example-Vu.snap` has 34 named channels and not one
  classifies `utility.ambient`, so the four G10 findings name a microphone the rig
  does not own. Opt-in — an unprofiled `doctor` still reports all 22 findings,
  `--profile small` goes 10 → 6. The rule's `source:` records that this was
  derived from the file and delegated in-session, **not** stated by ToanAZ as
  standing practice; confirm before treating it as such.
- **The limiter `dyn.mdl` token — closed as offline-underivable.** Three
  independent probes, all negative, written up with reproduction commands in
  `docs/handoff/2026-08-17-limiter-token-probe.md`. Do not spend a fourth session
  on it. Two schema facts found on the way: the `dyn` block has **two shapes**
  (the aux-input shape has `cmode/cpeak/depth/fast` and no `ratio/att/rel`, and is
  where `CMB` actually lives), and the FX rack's `mdl` is a **third** namespace
  (`C5-CMB`, `DOUBLE`, `NONE`). The older "models observed are COMP and CMB" line
  in G7's rationale was imprecise and is corrected.

**Sub-project G1 — show context.** A hand-written cue-sheet YAML loads beside the
scene; seven rules report where the paperwork and the console disagree.

- New package `wing_parser/showcontext/`: `vocabulary.py`, `models.py`,
  `loader.py`, `view.py`, `rewrite.py`.
- Two iterators (`cue`, `segment`) in the existing engine, yielding **nothing**
  when no context is loaded — which is what keeps the 22-finding contract intact.
- **39 base rules across 9 files** (was 32 across 8): Q1-Q7 added. Q7 ships
  `enabled: false`.
- CLI: `doctor --show`, `feedback --show`, `showcontext lint [--fix]`.
- Contract pinned in `tests/test_showcontext_realfile.py`: the fixture yields
  Q1, Q2, Q4, Q5, Q6 with raw-file evidence beside every row.

## Decided this cycle — do not re-litigate

- **Typo repair radius is 1, under Damerau-Levenshtein, with a uniqueness
  requirement.** Measured, not chosen: the minimum pairwise distance across the 35
  `channels` kinds is 2 (`speech.lav`↔`speech.qa`, `speech.mc`↔`speech.qa`). A
  distance-2 code detects one error but cannot correct one, so radius 2 could
  rewrite a Q&A mic into an MC mic. `test_the_channel_vocabulary_stays_at_least_two_apart`
  pins that **premise**, so the radius cannot silently go unsafe when the
  vocabulary grows. Damerau was adopted mid-cycle (a transposition is the
  commonest typo) and the measurement was re-run under it — unchanged.
- **Every derivation is a count, matched `{gt: 0}`, never a collection.** The
  predicate language has no emptiness operator, and `{not: []}` is always true in
  Python because `() != []`. A tuple-returning property would produce a rule that
  sits silent forever with no test able to catch it.
- **Q4/Q5 must not set `requires_classifier`.** That flag gates on the target's
  own confidence and a segment is not a classified object. The threshold lives
  inside the derivation, at `HIGH`, where `Bus.receives_ambient` puts it.
- **`--fix` reports only true repairs, not normalisation.** `resolved.repaired`,
  not a string comparison — otherwise `--fix` would rewrite tokens `lint`'s own
  output never mentioned.
- **PyYAML reads, ruamel writes.** `showcontext lint --fix` round-trips so the
  engineer's comments and ordering survive.

## Pending — ToanAZ decided, implementation not started

Recorded in spec §6.1. This is the next piece of work, and it is not optional:
the final review said the branch should not merge with this undecided, and the
decision is made but unbuilt.

1. **Q4 and Q5 aggregate to one finding per expected kind**, naming which
   segments call for it. Today they fire per segment, so a fifteen-segment sheet
   listing `expects: [instrument.horns, …]` throughout yields fifteen identical Q4
   warnings — and Q5 is worse, because his scenes are templates (34 named, 3 live)
   so nearly every expected kind is parked before doors. Spec §2 already rejected
   a fourth rule family for exactly this reason. Needs a **show-level iterator**
   rather than the per-segment one — architectural, not a tweak.
2. **Q6 drops to `info` and says "redundant", not "two cues disagree".** A caller
   restating "mics open" at the top of a segment is correct practice. While
   rewording, fix an overstatement: the rationale claims closing an
   already-closed channel is a contradiction, but the state walk treats an unseen
   channel as neither open nor closed, so that case is silent — right behaviour,
   wrong description.

## Residuals — triaged by the final review, none load-bearing

Safe to defer, with the review's reasons:

1. `known_kinds` duplicates `_compiled`'s YAML-load and KeyError guard — four
   lines, both `lru_cache`d.
2. `vocabulary.levenshtein` computes **Damerau**-Levenshtein; the docstring says
   so, the name does not. Rename to `edit_distance` next time the file is touched.
3. Segment-id duplicate detection folds case only; cue ids also collapse
   whitespace, so segment `"S 1"` vs `"S1"` is undetected. It also propagates:
   `SegmentView.target_name` does not strip, so a spaced id yields a feedback id
   the user must shell-quote. Fix both halves together.
4. `view.py`'s gap arithmetic has no floor at zero. Q7's placeholder `{lt: 0}`
   would match a negative gap from backwards times — inert only because Q7 is
   disabled, and its rationale documents the trap for whoever enables it.
5. `scene.channel_map()` returns a fresh dict copy per `CueView` property access.
6. Q2's and Q5's first citations are thin rather than fabricated — the review
   re-read `Core-Skills-Overview` §1.1 and confirmed the cited row exists as
   described. Trim the decorative half so a future reader is not sent there
   expecting an argument for a severity.
7. `render.lint_hint()` always says "run again with `--fix`" whenever any anomaly
   exists, even a `time:`-only one that `apply_repairs` never touches.
8. `rewrite.py` walks the schema a second time and emits repairs in a different
   format from the loader's; nothing keeps the two walks in sync. One test — after
   `--fix`, reloading reports no repair anomaly — would retire this and two more.
9. `dark_expects_text` has no direct assertion anywhere; if it returned `""`, Q5's
   message would read "expects ; channels of that kind exist" and every test would
   still pass.
10. Cue time is parsed twice — `loader` validates and discards the number, `view`
    imports `loader._parse_time` to parse the string again. Store the seconds on
    `Cue` instead.
11. `ShowContext.path`, `Cue.note`, `Segment.time` and `parse_show_context` are
    all written or exported and never read. `Segment.time` is documented in the
    README as supported.
12. `feedback --show` loads the context — and therefore silently applies typo
    repairs — without printing the anomalies `doctor` prints.

## Open questions

1. **`expects:` accepts pattern-derived kinds only.** `known_kinds` reads
   `classifier/data/patterns.yaml`, but a kind declared by hand in
   `knowledge/toanaz/classifier.yaml` bypasses it and is consulted *first* by the
   classifier. So the moment ToanAZ follows the README's own "declare a name
   manually" instruction with a new kind, `expects:` will refuse a kind his
   channels legitimately carry. Latent today — that file is `channels: {}`. The
   fix is not free: unioning those kinds in would invalidate the
   minimum-distance-2 measurement the repair radius rests on.
2. **MCP has no `show` parameter.** `wing_doctor` in `wing_parser/mcp/tools.py`
   cannot load a show context, so a Claude session on that surface cannot see
   Q1-Q7 at all. Close it or decline it deliberately.
3. **G2 — assisted ingest — is designed but unbuilt** (spec §8). His cue sheets
   arrive as Excel/Sheets and as PDF or phone photo. The design puts the LLM at
   the boundary only, behind `WING_DISABLE_LLM` and the optional `anthropic`
   extra, writing a G1-format file he reviews. Import must never invent a cue.
4. Still open from earlier cycles: the limiter `dyn.mdl` token (see above) and
   whether G10's suppression reflects standing practice.

## What this cycle taught

- **Seven defects in the plan and briefs were caught by implementers, and not one
  of them was visible on re-reading.** A metric that could not satisfy its own
  test case; an error escaping unwrapped; the same false claim about channel 31
  in two briefs; two citations naming the wrong section; a proposal to collapse
  two `except` branches that would have changed a user-visible message. Each
  surfaced only when someone *executed* the brief — ran the code, ran the test,
  opened the file. Separating the planner from the implementer is what made them
  findable.
- **The final whole-branch review earned its cost again, in the same shape as
  last cycle.** `doctor --show --json` emitted non-JSON because the anomaly print
  sat before the `--json` branch: the flag lives in `__main__.py`, the print in
  `commands.py`, and no single task's diff held both. Last cycle it was `wing
  channel` labelling a matrix send as "bus". Both were invisible to every
  per-task review by construction, not by carelessness.
- **A rule can ship claiming a check it cannot perform.** Q3 promised to catch a
  DCA that is "not built" while its predicate only detects a number outside 1-16 —
  and all 16 exist in both sample files. Q1 has the same in-range limitation and
  is *honestly titled*, which is the whole difference. When writing a rule, state
  what the predicate does, then check the title against it.
- **Verify a citation by opening the file it names, not the file you assume.** One
  implementer concluded a real citation was fabricated because it read the plan
  where the spec was meant — the plan's own lines 18-19 define the alias. The act
  of checking needs checking too.
- **A test that passes without ever being shown to fail may assert nothing.** Two
  implementers proved theirs by reverting the production code and capturing the
  red output. Q7's disabled-rule test was rewritten with deliberately backwards
  cue times so the predicate *would* match if the rule were ever evaluated —
  without that, `== []` proved nothing about `enabled: false`.
