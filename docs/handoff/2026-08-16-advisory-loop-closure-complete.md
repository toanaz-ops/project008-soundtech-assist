# Advisory loop closure — complete

**Date:** 2026-08-16 · **Branch:** `feature/advisory-loop-closure`
**State:** 6 of 6 tasks complete · 406 tests passing, 1 skipped · wheel builds

Spec: `docs/superpowers/specs/2026-08-16-advisory-loop-closure-design.md`
Plan: `docs/superpowers/plans/2026-08-16-advisory-loop-closure.md`

The three-layer advisory design now does the job it was built for. Before this
branch the upper two layers were empty and unusable; `knowledge/toanaz/` now
holds real content and `--profile small` switches G8 off for the shows where
ToanAZ deviates from it on purpose.

| | `example-Vu.snap` |
|---|---|
| `doctor` | **14** findings — G8×12, G7×1 (bus 7), E6×1 (ch.11) |
| `doctor --profile small` | **2** — G7 and E6, with `[suppressed] G8 switched off by show.small.post-monitors-are-deliberate` |
| `factory-scene.snap` | none |

This file exists because the SDD ledger is git-ignored and is deleted at merge.

---

## 1. What asking ToanAZ changed

The Phase 2 handoff carried four open questions built on a misreading of his
worked example. Asking him directly collapsed most of the anticipated work:

- **Pre-fader is his norm, not his exception.** Post-fader monitor sends are a
  deliberate trade of monitor independence for setup speed on a small or easy
  show. So **G8 is correct for him** and its twelve findings flag a conscious
  choice. The earlier framing of "twelve false positives" was wrong.
- **Show scale is declared, not derived.** He knows before he builds the scene.
  That removed the entire anticipated `CONDITIONS` taxonomy — no probe, no scene
  analysis, no threshold to argue about.
- **The per-channel pre/post split is a show-time judgement** the tool must not
  try to make.
- **Declaring a profile costs one flag.**

## 2. Open questions — status

| | Question | Status |
|---|---|---|
| 1 | What `dyn.mdl` does a WING store for a limiter? | **Still open.** G7 now checks only `bus.dyn.on`, the verifiable half. Spec §7.1 has the exact clause to add. |
| 2 | Should G7 fire on wedges or only IEM? | **Still open, and now sharper** — G7's single surviving finding is `bus.7 SIDEFILL`, a sidefill at `severity: error` against two IEM-scoped sources. This question now accounts for *all* of G7's output rather than a quarter of it. |
| 3 | What `applies_when` should supersede G8? | **Resolved.** None needed — scale is declared, so `shows/small.yaml` does it with a flag. |
| 4 | Three rules under-reach for want of an `OR` | **Mostly resolved.** `any_of` shipped; E6 gained its hold clause, G7 its verifiable half. **G8 still matches only `POST` and ignores `TAP`.** |
| 5 | The below-gate threshold | **Unchanged.** `evaluate()` gates at LOW (0.4) and skips nothing; `is_monitor` gates at HIGH (0.8) and the six 0.60 subgroups sit under it. Bites in exactly one place: `_monitor_bus_count`. |

## 3. Deferred minors, triaged by the final review

**Can stand, with reasons on record:**

- `commands.py` calls `scene.advisory.suppressed()` outside `_run_advisory`'s
  try. Unreachable today — `_run_advisory` runs first and returns 1 — and
  `test_an_unknown_profile_exits_cleanly` drives that path, so a reorder fails
  loudly in CI rather than silently. Fold it in if you touch the file anyway.
- `build_channel.py`'s `hold_ms=float(raw.get("hld", 0.0))` and
  `build_blocks.py`'s `dyn.on` default. E6's new `hold_ms < 200` clause and
  G7's `dyn.on: false` clause both now *select on* a defaulted value, so a
  missing key would fire rather than stay quiet — the opposite of the old
  range-only predicate's behaviour. Measured: every channel in both sample files
  carries `hld`, every dyn block carries `on`, and `factory-scene.snap` yields
  nothing. Both rationales document the treatment. Fixing it properly ripples
  `float | None` through the records and the renderer.
- `small.yaml` vs `small.yml` for one profile name resolves silently to `.yaml`.
  Not a regression; one docstring sentence closes it.

**Worth doing next time in that area:**

- `skills/wing-doctor/SKILL.md`'s layer legend still calls `show` "a one-off
  override for this specific show" — the pre-branch conception. The README
  bullet was rewritten; this one was missed.
- `README.md` points at the 2026-08-13 spec as "the full design" with no marker
  that its worked example carries the retracted guitarist reading. One hop from
  live docs.
- `README.md`'s base-layer bullet still glosses G7 as "a monitor bus should
  carry a limiter", unqualified, above the paragraph that correctly narrows it.

## 4. What this branch taught

**A rule's `OR` can invert a parser default's safety.** `hold_ms` defaults to
`0.0`. Under the old `range > 6` predicate that meant *don't fire*; the moment a
`hold < 200` clause pointed at the same default it meant *fire*, and render a
number the file never stated. A default is only safe relative to the comparison
aimed at it.

**Fixing a false claim where it was reported is not fixing it.** A wrong
sentence about `any_of` propagated from a brief into source, a test docstring,
the spec and the plan; the first fix round caught two of five copies. The lesson
was recorded — and then not applied two tasks later, when a retracted reading
deleted from `principles.yaml` survived verbatim in the README and a SKILL.md,
i.e. in the documents a reader meets *first*. Grep the tree, always.

**Three of this branch's defects were controller errors** — statements I put in
a brief without running or reading them, which implementers then transcribed
faithfully. One claimed a mechanism the evaluator does not have; one asserted a
CLI output that a transparency line contradicted; one wrote an unqualified
documentation claim that is false for every id the shipped profile lists. The
implementers were right to transcribe, and right when they pushed back.

**The tests that mattered were the ones proven by mutation.** Three passed for
the wrong reason and were only caught by deleting the code they covered: an
empty-`any_of` guard whose sibling `isinstance` check already did the work, a
first-match guarantee that a single matching clause could not distinguish, and a
shipped-file test that passed identically against an empty temp directory
because an absent file and `principles: []` both yield `[]`.
