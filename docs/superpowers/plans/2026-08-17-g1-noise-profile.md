# G1 noise profile Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make Q4, Q5 and Q6 read sensibly on a real fifteen-segment cue sheet
instead of on a two-segment fixture.

**Architecture:** Q4 and Q5 move from a per-segment target to a per-expected-kind
target, which needs one new iterator and one new view class. Q6 keeps its target
and predicate and changes only severity and wording.

**Tech Stack:** Python 3.11+, PyYAML, `pytest`.

**Design authority:** `docs/superpowers/specs/2026-08-17-input-pipelines-design.md`
**§6.1**, which records ToanAZ's decisions of 2026-08-17. This plan implements
that section; it does not reopen it.

## Why

Both decisions came out of the final whole-branch review of G1, and ToanAZ
settled them directly.

**Q4/Q5 duplicate per segment.** `SegmentView._channels_of` reads the static
scene, so a missing horns channel is missing for every segment. A sheet listing
`expects: [instrument.horns, …]` across fifteen segments yields fifteen identical
Q4 warnings. Q5 is worse in frequency: his scenes are templates — 34 named
channels, 3 live — so nearly every expected kind is parked before doors, and Q5
fires on every segment naming it. Spec §2 already rejected a fourth rule family
for exactly this reason ("would fire constantly on channels that are simply
parked"); Q5 inherits that failure mode from the other direction.

**Q6 calls redundancy a contradiction.** A show caller restating "mics open" at
the top of a segment is correct practice, not a fault.

## Global Constraints

- `core/`, `query/`, `advisory/` and `showcontext/` are deterministic — **no LLM
  call of any kind**. No new dependency. Fully offline.
- **Never fabricate a value a file does not state.** Probe before asserting.
- Rules are YAML carrying `source:` and `rationale:`. `wing_parser/advisory/loader.py:49`
  refuses either missing, and a test asserts every base rule's `source` contains
  the literal `docs/knowledge-base/` and its `rationale` exceeds 40 characters.
- `docs/knowledge-base/` is read-only.
- **With no show context loaded, behaviour stays bit-identical.** The unprofiled
  sample file must still yield exactly 22 findings. Any new iterator yields
  nothing when `scene.show is None`.
- Derivations that answer "how many" are counts matched `{gt: 0}`; derivations
  that answer "is it" are booleans matched with a plain `true`. Never a
  collection — the predicate language has no emptiness operator and `{not: []}`
  is always true in Python because `() != []`.
- Modular code, roughly 200 lines per file.
- The shell is PowerShell on Windows. Commit with `git commit -F -` and a
  heredoc — never backticks inside `-m`.
- Never build YAML or a regex inside a Python heredoc (`\b` is a backspace
  there). Use Write/Edit for file content.
- This machine may print no pytest summary trailer. Verify with the exit code, or
  `--junitxml=junit.xml` and read the `<testsuite …>` attributes.
- **Slow network drive (Google Drive).** `git status`, `git commit` and ripgrep
  can take minutes or appear to hang. If a git command seems stuck, wait rather
  than interrupting, then verify with `git log --oneline -1`. One `git add`, one
  `git commit`. Prefer Read/Edit/Write over shell `cat`/`sed`/`grep`.

Baseline before this plan: **588 tests, 0 failures, 0 errors, 1 skipped** (the
skip is a FastMCP test, by design).

---

## File Structure

| File | Change |
|---|---|
| `wing_parser/showcontext/view.py` | add `ExpectationView` and `build_expectations`; later remove the four now-dead segment-level expect properties |
| `wing_parser/query/scene.py` | add `show_expectations()` beside `show_segments()` |
| `wing_parser/advisory/evaluator.py` | add the `expects` iterator to `ITERATORS` |
| `wing_parser/advisory/base_rules/showcontext.yaml` | rewrite Q4 and Q5 onto the new target; change Q6's severity and wording |
| `tests/test_showcontext_view.py` | tests for `ExpectationView`; drop the segment-level expect tests when those properties go |
| `tests/test_showcontext_iterators.py` | the `expects` iterator, including the empty case |
| `tests/test_showcontext_rules.py` | Q4/Q5 target and Q6 severity |
| `tests/test_showcontext_realfile.py` | regenerate `EXPECTED_Q` and re-justify every row |
| `README.md` | Q4/Q5/Q6 rows and the show-context subsection |

---

### Task 1: `ExpectationView` and the `expects` iterator

Build the new target shape and wire it in. **No rule changes in this task** — the
new iterator exists and is tested, but nothing consumes it yet, so the suite stays
green at this commit.

**Files:**
- Modify: `wing_parser/showcontext/view.py`, `wing_parser/query/scene.py`,
  `wing_parser/advisory/evaluator.py`
- Test: `tests/test_showcontext_view.py`, `tests/test_showcontext_iterators.py`

**Interfaces:**
- Consumes: `ShowContext`, `Segment`, a loaded `WingScene`, `HIGH` from
  `wing_parser.classifier.matcher`
- Produces:
  - `view.ExpectationView` with `.kind: str`, `.segments_text: str`,
    `.target_name: str`, `.is_unmet: bool`, `.is_dark: bool`
  - `view.build_expectations(context, scene) -> tuple[ExpectationView, ...]`
  - `scene.show_expectations() -> tuple[ExpectationView, ...]`, empty when
    `scene.show is None`
  - iterator name `"expects"` in `ITERATORS`, binding `{"expectation": view}`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_showcontext_view.py
def test_one_expectation_per_distinct_kind_across_segments(scene):
    context = _context(
        Segment(id="S1", expects=("instrument.horns", "instrument.keys")),
        Segment(id="S2", expects=("instrument.horns",)),
    )
    found = view.build_expectations(context, scene)
    assert [e.kind for e in found] == ["instrument.horns", "instrument.keys"]


def test_an_expectation_names_every_segment_that_calls_for_it(scene):
    context = _context(
        Segment(id="S1", expects=("instrument.horns",)),
        Segment(id="S3", expects=("instrument.horns",)),
    )
    horns = view.build_expectations(context, scene)[0]
    assert horns.segments_text == "S1, S3"
    assert horns.target_name == "expects.instrument.horns"


def test_a_kind_with_no_channel_is_unmet_and_not_dark(scene):
    context = _context(Segment(id="S1", expects=("instrument.horns",)))
    horns = view.build_expectations(context, scene)[0]
    assert horns.is_unmet is True
    assert horns.is_dark is False


def test_a_kind_whose_channels_are_all_parked_is_dark_and_not_unmet(scene):
    # Channels 29 "Key 1" and 30 "Key 2" classify instrument.keys at 0.9 and
    # both read in_use False on this file. Probe before trusting.
    context = _context(Segment(id="S1", expects=("instrument.keys",)))
    keys = view.build_expectations(context, scene)[0]
    assert keys.is_unmet is False
    assert keys.is_dark is True


def test_expectations_are_empty_when_no_segment_expects_anything(scene):
    context = _context(Segment(id="S1"))
    assert view.build_expectations(context, scene) == ()
```

```python
# append to tests/test_showcontext_iterators.py
def test_the_expects_iterator_is_registered():
    assert "expects" in ITERATORS


def test_without_a_context_the_expects_iterator_yields_nothing(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)
    assert list(targets_for(scene, "expects")) == []
    assert scene.show_expectations() == ()


def test_with_a_context_expects_targets_carry_the_kind_in_their_name(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    path = tmp_path / "expects.yaml"
    path.write_text(yaml.safe_dump({"show": "t", "segments": [
        {"id": "S1", "expects": ["instrument.horns"]}]}), encoding="utf-8")
    scene = WingScene.load(vu_path, show=path)
    targets = list(targets_for(scene, "expects"))
    assert [t.name for t in targets] == ["expects.instrument.horns"]
    assert set(targets[0].context) == {"expectation"}
    assert targets[0].confidence == 1.0
```

- [ ] **Step 2: Run them to verify they fail**

Run: `python -m pytest tests/test_showcontext_view.py tests/test_showcontext_iterators.py -q`
Expected: `AttributeError` on `build_expectations`, and `"expects" not in ITERATORS`.

- [ ] **Step 3: Add `ExpectationView` and `build_expectations` to `view.py`**

Place them after `SegmentView` and before `build`. `_channels_of` currently lives
on `SegmentView`; the kind-level view needs the same logic, so **lift it to a
module-level helper** `_channels_of(scene, kind)` and have `SegmentView` call it,
rather than copying it. Verbatim duplication of a logic block is a review defect
in this repo.

```python
class ExpectationView:
    """One expected source kind, across every segment that calls for it.

    Q4 and Q5 used to iterate segments, which meant a kind missing from the
    scene was reported once per segment naming it -- fifteen identical
    warnings on a fifteen-segment sheet, because the scene is static and
    the answer cannot differ between segments. ToanAZ's decision, 2026-08-17
    (spec section 6.1): report once per kind and name the segments.

    `is_unmet` and `is_dark` are booleans, not counts: at this granularity
    the question is "is it", not "how many". Rules match them with a plain
    `true`. They are mutually exclusive by construction -- unmet means no
    confidently-classified channel of the kind exists at all, dark means
    some exist and none is in use.
    """

    def __init__(self, kind: str, segment_ids: tuple[str, ...], scene) -> None:
        self.kind = kind
        self._segment_ids = segment_ids
        self._scene = scene

    @property
    def segments_text(self) -> str:
        return ", ".join(self._segment_ids)

    @property
    def target_name(self) -> str:
        return f"expects.{self.kind}"

    @property
    def is_unmet(self) -> bool:
        return not _channels_of(self._scene, self.kind)

    @property
    def is_dark(self) -> bool:
        channels = _channels_of(self._scene, self.kind)
        return bool(channels) and not any(c.in_use for c in channels)


def build_expectations(context: ShowContext, scene) -> tuple[ExpectationView, ...]:
    """One view per distinct expected kind, in first-seen order.

    Segment order is the file's order, so the first segment to name a kind
    determines where it appears -- deterministic without sorting, and it
    reads the way the sheet reads.
    """
    seen: dict[str, list[str]] = {}
    for segment in context.segments:
        for kind in segment.expects:
            seen.setdefault(kind, []).append(segment.id)
    return tuple(
        ExpectationView(kind, tuple(ids), scene) for kind, ids in seen.items()
    )
```

The module-level helper, lifted from `SegmentView._channels_of` unchanged in
behaviour:

```python
def _channels_of(scene, kind: str) -> tuple:
    """Only confidently-classified channels count.

    Same threshold Bus.receives_ambient uses: a weak guess must not satisfy
    an expectation, or the rule silently stops firing on the thing it
    exists to catch.
    """
    return tuple(
        channel for channel in scene.channels()
        if channel.source_type.kind == kind
        and channel.source_type.confidence >= HIGH
    )
```

Note the first test expects `["instrument.horns", "instrument.keys"]` for a
segment declaring them in that order — first-seen order, not sorted. If the
implementation sorts, that test fails; keep first-seen and let the test hold.

- [ ] **Step 4: Add `show_expectations()` to `scene.py`**

Mirror `show_segments()` exactly, including its cache-and-short-circuit shape:

```python
    def show_expectations(self) -> tuple:
        """Expectation views, built once. Empty when no context is loaded."""
        if self.show is None:
            return ()
        if self._show_expectations is None:
            self._show_expectations = show_view.build_expectations(self.show, self)
        return self._show_expectations
```

and initialise `self._show_expectations: tuple | None = None` in `__init__`
beside `self._show_segments`.

- [ ] **Step 5: Add the iterator to `evaluator.py`**

```python
def _expectations(scene) -> Iterator[Target]:
    """One target per expected kind. Yields nothing without a show context."""
    for expectation in scene.show_expectations():
        yield Target(
            name=expectation.target_name,
            context={"expectation": expectation},
            confidence=1.0,
        )
```

and add `"expects": _expectations,` to `ITERATORS`, keeping `"none"` last as it
is now.

- [ ] **Step 6: Run the new tests, then the full suite**

Run: `python -m pytest tests/test_showcontext_view.py tests/test_showcontext_iterators.py -q`
Expected: pass.

Run: `python -m pytest tests/ -q --junitxml=junit.xml`
Expected: exit 0, `failures="0" errors="0" skipped="1"`. Test count rises by 8;
no existing test changes behaviour, because no rule uses the new iterator yet.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/showcontext/view.py wing_parser/query/scene.py wing_parser/advisory/evaluator.py tests/
git commit -F - <<'EOF'
Add a per-kind expectation target

Q4 and Q5 report once per segment today, which means a kind missing from
a static scene is reported once per segment naming it. ToanAZ decided
(spec 6.1) to report once per kind and name the segments instead. This
adds the target shape and its iterator; the rules move in the next
commit, so nothing changes behaviour yet.

_channels_of is lifted from SegmentView to module level rather than
copied, so the kind-level and segment-level views cannot drift.
EOF
```

---

### Task 2: Move Q4 and Q5 onto it, soften Q6, and re-pin the contract

**Files:**
- Modify: `wing_parser/advisory/base_rules/showcontext.yaml`,
  `wing_parser/showcontext/view.py` (remove the dead segment-level properties),
  `tests/test_showcontext_view.py`, `tests/test_showcontext_rules.py`,
  `tests/test_showcontext_realfile.py`, `README.md`

**Interfaces:** consumes Task 1's `ExpectationView` and the `expects` iterator.

- [ ] **Step 1: Rewrite Q4 and Q5**

Both change `for_each` to `expects`, match a boolean, and name the kind and the
segments in the message. Keep each `source:` exactly as it is — the citations were
verified during the G1 cycle and are not in scope here. Amend each `rationale:`
to record the aggregation and why, citing spec §6.1.

```yaml
  - id: Q4
    title: "Show expects a source with no channel for it"
    severity: warning
    source: >
      [KEEP THE EXISTING source: BLOCK VERBATIM]
    rationale: >
      [KEEP THE EXISTING TEXT, then append:] Reported once per expected
      kind rather than once per segment: the scene is static, so a kind
      with no channel is missing for every segment naming it, and
      per-segment reporting turned one fact into fifteen identical
      warnings on a fifteen-segment sheet. ToanAZ's decision, 2026-08-17,
      spec section 6.1. The message names the segments so the aggregation
      loses nothing.
    when:
      for_each: expects
      where:
        expectation.is_unmet: true
    message: >
      Segments {expectation.segments_text} expect {expectation.kind}, and no
      confidently-classified channel of that kind exists in the scene.
```

Q5 the same shape, with `expectation.is_dark: true`, `severity: info`, and a
message naming the kind, the segments, and that channels exist but none is in use.

- [ ] **Step 2: Soften Q6**

Change `severity: warning` to `severity: info`. Reword the title, message and
rationale so all three say **redundant**, not *contradiction* or *disagree*:

- title: something like "Cue repeats a channel state an earlier cue already set"
- message: name the cue, the segment, the action and the channels, and say the
  earlier cues already left them in that state
- rationale: a show caller restating "mics open" at the top of a segment is
  correct practice, not a fault — ToanAZ confirmed 2026-08-17, spec §6.1 — so this
  is `info`: worth seeing when reading a sheet, never an alarm. **Also fix the
  overstatement §6.1 names:** the existing rationale claims closing an
  already-closed channel is caught, but the state walk treats a channel it has
  never seen as neither open nor closed, so closing a channel the sheet never
  opened is silent. That is right — a sheet may describe a desk that started with
  things open — and the rationale must say so rather than claim a check it does
  not perform.

The property name `contradiction_count` may stay: it is internal, no rule text
depends on it, and renaming it would widen this diff for no behavioural gain.
Say in your report that you considered it and why you left it.

- [ ] **Step 3: Remove the now-dead segment-level properties**

`SegmentView._unmet_expects`, `unmet_expect_count`, `unmet_expects_text`,
`_dark_expects`, `dark_expect_count`, `dark_expects_text` have no remaining
consumer once Q4 and Q5 move. **Grep to confirm** before deleting — rules, tests
and `render.py` all count as consumers. Delete them and the tests that covered
them, since their behaviour is now covered by the `ExpectationView` tests.

`SegmentView._channels_of` becomes unused too if nothing else calls it; check and
remove it if so, keeping the module-level `_channels_of` Task 1 introduced.

- [ ] **Step 4: Update the rule tests**

In `tests/test_showcontext_rules.py`, Q4 and Q5 now fire on `expects.<kind>`
targets, not `segment.S1`. Update the existing Q4/Q5 tests' expected targets, and
keep the test that proves Q4 and Q5 are mutually exclusive — it is still true and
still worth pinning. Update Q6's expected severity to `info`.

- [ ] **Step 5: Regenerate and re-justify the real-file contract**

Run the regeneration command in `tests/test_showcontext_realfile.py`'s docstring.
Paste the output into `EXPECTED_Q`.

Expected changes: Q4's target becomes `expects.instrument.horns`, Q5's becomes
`expects.instrument.keys`, Q6's severity becomes `info`. Q1, Q2 and Q6's targets
are unchanged.

**Then re-justify every row against the real file, as the existing comments do.**
If the generated output differs from what this plan predicts, that disagreement is
the finding — report it rather than editing the fixture until it matches. The
existing per-row evidence comments must be updated where the row changed, not left
describing the old shape.

Keep `test_the_q2_message_is_rendered_not_a_bare_triple` passing unedited, and
keep its `all("{" not in f.message ...)` assertion — with two rewritten messages
in this diff, that check is doing real work.

- [ ] **Step 6: Update the README**

The rule table's Q4, Q5 and Q6 rows: severity and description. Q6 is now `info`.
Q4 and Q5 fire per expected kind, not per segment — the table's "fires when"
column must say so. Check whether the `### Show context` subsection describes
per-segment behaviour anywhere and correct it if so.

Do not re-derive the rule count; it is unchanged at 39 across 9 files. Confirm
that with `load_base_rules()` rather than trusting this sentence.

- [ ] **Step 7: Run the suite and commit**

Run: `python -m pytest tests/ -q --junitxml=junit.xml`
Expected: exit 0, `failures="0" errors="0" skipped="1"`.

```bash
git add wing_parser/ tests/ README.md
git commit -F - <<'EOF'
Aggregate Q4/Q5 per kind and drop Q6 to info

ToanAZ's decisions from the G1 final review, spec 6.1. Q4 and Q5 now
report once per expected kind, naming the segments that call for it,
instead of repeating one static-scene fact per segment. Q6 says
"redundant" at info rather than "two cues disagree" at warning, because
a caller restating "mics open" at the top of a segment is correct
practice.

Q6's rationale also stops claiming it catches closing an already-closed
channel: the state walk treats an unseen channel as neither open nor
closed, so that case is silent -- right behaviour, wrong description.

The four segment-level expect properties are removed rather than left
dead.
EOF
```

---

## Self-Review

**Spec coverage.** §6.1's two decisions map to Task 1 + Task 2 Step 1 (Q4/Q5
aggregation) and Task 2 Step 2 (Q6 severity, wording, and the overstatement fix).
Nothing else in §6.1 requires work.

**Placeholders.** Task 2 Step 1 deliberately says "KEEP THE EXISTING source: BLOCK
VERBATIM" rather than reproducing it: those citations were verified line-by-line
during the G1 cycle, and retyping them here is how a verified citation becomes an
unverified one. `EXPECTED_Q` is generated in Step 5, with the same
disagreement-is-the-finding rule the G1 plan used.

**Type consistency.** `ExpectationView`'s five members are defined in Task 1 and
consumed by name in Task 2's rule YAML (`expectation.is_unmet`,
`expectation.is_dark`, `expectation.kind`, `expectation.segments_text`) and in the
target name `expects.<kind>`. `build_expectations` is defined in Task 1 and called
only from `scene.show_expectations()`.

**One thing a reviewer should check hard.** Task 1 lifts `_channels_of` from
`SegmentView` to module level while `SegmentView` still uses it, then Task 2 may
delete `SegmentView`'s remaining callers. If Task 1's lift changed behaviour —
the `HIGH` threshold, the `source_type.kind` comparison — Q4 and Q5 would silently
change what satisfies an expectation. The lift must be behaviour-identical.
