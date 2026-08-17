# Show context (sub-project G1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the advisory read a hand-written show-context file — segments, the
sources each calls for, and the cues that touch channels — and report where the
paper and the scene disagree.

**Architecture:** A new `wing_parser/showcontext/` package turns a YAML file into
frozen records and a view layer that derives counts against a loaded scene. Two
new iterators (`cue`, `segment`) join the existing advisory engine and yield
nothing when no context is loaded, so every current behaviour is bit-identical.
Seven rules `Q1`–`Q7` are ordinary base-rule YAML.

**Tech Stack:** Python 3.11+, `PyYAML` for reading, `ruamel.yaml` for the one
command that writes, `pytest`.

**Design spec:** `docs/superpowers/specs/2026-08-17-input-pipelines-design.md`.
Read it before Task 1. Sections referenced below as "spec §N".

## Global Constraints

Copy these into every dispatch. They are the project's standing rules.

- `core/`, `query/`, `advisory/` and `showcontext/` are **deterministic — no LLM
  call of any kind**. The only LLM in this codebase is `classifier/llm.py`, and
  G1 does not touch it.
- Fully offline. `mcp` and `anthropic` stay uninstalled; the FastMCP test keeps
  skipping. Do not add a dependency.
- **Never fabricate a value the file does not state.** A missing `time:` means
  the rule stays silent, not that a time is assumed.
- Rules are YAML carrying `source:` and `rationale:`. `wing_parser/advisory/loader.py:49`
  refuses to load a rule missing either.
- `ruamel.yaml` round-trip for anything under `knowledge/` or any file the tool
  writes back. `PyYAML` is read-only.
- `docs/knowledge-base/` is read-only source material.
- `pytest.approx` for float comparisons.
- Modular code, files split by responsibility, roughly 200 lines each.
- PowerShell is the shell. Commit with `git commit -F -` and a heredoc, never
  backticks inside `-m`. Never build a regex or YAML inside a Python heredoc
  (`\b` is a backspace there) — use the Edit tool.
- Tests may print no pytest summary trailer on this machine. Verify with the
  exit code or `--junitxml`, never by reading for a summary line.

---

## File Structure

| File | Responsibility |
|---|---|
| `wing_parser/showcontext/__init__.py` | Public exports: `load_show_context`, `ShowContext` |
| `wing_parser/showcontext/vocabulary.py` | Normalise / repair / refuse a token against a closed vocabulary (spec §3.1) |
| `wing_parser/showcontext/models.py` | Frozen records `Cue`, `Segment`, `ShowContext` |
| `wing_parser/showcontext/loader.py` | YAML → records; structural validation; anomalies |
| `wing_parser/showcontext/view.py` | `CueView` / `SegmentView`; derived counts against a scene |
| `wing_parser/classifier/matcher.py` | **modify** — add public `known_kinds(domain)` |
| `wing_parser/query/scene.py` | **modify** — `load(path, show=...)`, `scene.show` |
| `wing_parser/advisory/evaluator.py` | **modify** — `cue` and `segment` iterators |
| `wing_parser/advisory/base_rules/showcontext.yaml` | Rules Q1–Q7 |
| `wing_parser/cli/__main__.py`, `commands.py`, `render.py` | **modify** — `--show`, `showcontext lint` |

---

### Task 1: The vocabulary resolver

Spec §3.1. This is the only piece with a non-obvious correctness argument, so it
goes first and is tested hardest.

**Files:**
- Create: `wing_parser/showcontext/vocabulary.py`
- Modify: `wing_parser/classifier/matcher.py` (append `known_kinds`)
- Test: `tests/test_showcontext_vocabulary.py`

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `matcher.known_kinds(domain: str) -> tuple[str, ...]`
  - `vocabulary.normalise(token: str) -> str`
  - `vocabulary.levenshtein(a: str, b: str) -> int`
  - `vocabulary.Resolution` — frozen, fields `value: str`, `original: str`, `repaired: bool`
  - `vocabulary.resolve(token: str, vocabulary: tuple[str, ...], *, what: str) -> Resolution`, raising `ValueError` on a tie or a miss
  - `vocabulary.KNOWN_ACTIONS: tuple[str, ...]`, `vocabulary.MIN_REPAIR_LENGTH: int`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_showcontext_vocabulary.py
"""The typo repair is the one piece here with a correctness argument.

Spec section 3.1: repair radius 1 with a uniqueness requirement is safe
only because no two valid kinds sit closer than 2 apart. The first test
pins that premise so the radius cannot go unsafe when the vocabulary
grows.
"""
import itertools

import pytest

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext import vocabulary


def test_the_channel_vocabulary_stays_at_least_two_apart():
    kinds = known_kinds("channels")
    assert len(kinds) >= 30
    closest = min(
        (vocabulary.levenshtein(a, b), a, b)
        for a, b in itertools.combinations(kinds, 2)
    )
    # Measured 2026-08-17: 35 kinds, minimum 2 -- speech.lav <-> speech.qa
    # and speech.mc <-> speech.qa. A minimum of 1 would make radius-1
    # repair ambiguous for a pair of real kinds; re-argue the radius
    # before lowering this.
    assert closest[0] >= 2, f"{closest[1]} and {closest[2]} are {closest[0]} apart"


def test_known_kinds_reads_both_domains_and_is_sorted():
    assert "instrument.keys" in known_kinds("channels")
    assert "monitor.iem" in known_kinds("buses")
    assert list(known_kinds("channels")) == sorted(known_kinds("channels"))
    with pytest.raises(KeyError, match="cymbals"):
        known_kinds("cymbals")


@pytest.mark.parametrize(
    "written",
    ["Instrument.Keys", "  instrument keys  ", "instrument-keys", "INSTRUMENT_KEYS"],
)
def test_normalising_is_not_a_repair(written):
    resolved = vocabulary.resolve(written, known_kinds("channels"), what="kind")
    assert resolved.value == "instrument.keys"
    assert resolved.repaired is False


@pytest.mark.parametrize(
    "typo,expected",
    [
        ("instrument.kyes", "instrument.keys"),
        ("speech.lecturn", "speech.lectern"),
        ("drums.snare.tp", "drums.snare.top"),
    ],
)
def test_a_unique_near_miss_is_repaired_and_flagged(typo, expected):
    resolved = vocabulary.resolve(typo, known_kinds("channels"), what="kind")
    assert resolved.value == expected
    assert resolved.original == typo
    assert resolved.repaired is True


def test_a_tie_refuses_and_names_both_candidates():
    # speech.ma is one edit from speech.mc and one from speech.qa.
    with pytest.raises(ValueError) as caught:
        vocabulary.resolve("speech.ma", known_kinds("channels"), what="kind")
    message = str(caught.value)
    assert "speech.mc" in message and "speech.qa" in message


def test_a_miss_refuses_and_lists_the_vocabulary():
    with pytest.raises(ValueError) as caught:
        vocabulary.resolve("trombone", known_kinds("channels"), what="kind")
    assert "instrument.horns" in str(caught.value)


def test_short_tokens_are_never_repaired():
    # 'fx' is 2 characters; one edit is half the token, so 'fa' must
    # refuse rather than repair. Guards the buses domain and actions.
    with pytest.raises(ValueError):
        vocabulary.resolve("fa", known_kinds("buses"), what="role")


def test_actions_resolve_through_the_same_path():
    assert vocabulary.resolve("Open", vocabulary.KNOWN_ACTIONS, what="action").value == "open"
    assert vocabulary.resolve("recal", vocabulary.KNOWN_ACTIONS, what="action").repaired is True
    with pytest.raises(ValueError):
        vocabulary.resolve("up2", vocabulary.KNOWN_ACTIONS, what="action")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_showcontext_vocabulary.py -q`
Expected: collection error — `wing_parser.showcontext` does not exist.

- [ ] **Step 3: Add `known_kinds` to the matcher**

Append to `wing_parser/classifier/matcher.py`, after `_compiled`:

```python
@lru_cache(maxsize=None)
def known_kinds(domain: str) -> tuple[str, ...]:
    """Every kind a pattern set can produce, sorted and deduplicated.

    `_compiled` returns compiled patterns, which is the wrong shape for a
    caller that wants the vocabulary itself -- show context validates
    `expects:` entries against it (2026-08-17 input-pipelines spec §3).
    """
    doc = yaml.safe_load(_DATA.read_text(encoding="utf-8"))
    if domain not in doc:
        raise KeyError(f"no pattern set named {domain!r} in {_DATA}")
    return tuple(sorted({entry["kind"] for entry in doc[domain]}))
```

- [ ] **Step 4: Write the vocabulary module**

Create `wing_parser/showcontext/__init__.py` as an empty file for now, and
`wing_parser/showcontext/vocabulary.py`:

```python
"""Resolve a hand-typed token against a closed vocabulary.

Repairing a near-miss against a closed vocabulary is not the same act as
mapping free text: this one is decidable, and every failure is visible.
The radius is a measurement, not a preference -- see the 2026-08-17
input-pipelines spec §3.1. The channel vocabulary's minimum pairwise
distance is 2, which detects a single error but cannot correct one, so
repair happens at radius 1 and only when exactly one candidate sits
there. A tie is refused, never resolved by picking.
"""

from __future__ import annotations

from dataclasses import dataclass

KNOWN_ACTIONS: tuple[str, ...] = ("open", "close", "up", "down", "recall")

# Below this length a single edit is too large a fraction of the token to
# call a typo. No channel kind is this short (the shortest is
# `drums.pad`, 9), but `fx` in the buses domain is, and so is `up`.
MIN_REPAIR_LENGTH = 4


@dataclass(frozen=True)
class Resolution:
    value: str
    original: str
    repaired: bool


def normalise(token: str) -> str:
    """Case, padding and separator differences are not guesses.

    The result is either a member of the vocabulary or it is not, so
    this collapses without needing to be reported.
    """
    cleaned = token.strip().lower()
    for separator in ("-", "_", " ", "\t"):
        cleaned = cleaned.replace(separator, ".")
    while ".." in cleaned:
        cleaned = cleaned.replace("..", ".")
    return cleaned.strip(".")


def levenshtein(a: str, b: str) -> int:
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            current.append(
                min(previous[j] + 1, current[j - 1] + 1, previous[j - 1] + (ca != cb))
            )
        previous = current
    return previous[-1]


def resolve(token: str, vocabulary: tuple[str, ...], *, what: str) -> Resolution:
    cleaned = normalise(token)
    if cleaned in vocabulary:
        return Resolution(value=cleaned, original=token, repaired=False)

    if len(cleaned) >= MIN_REPAIR_LENGTH:
        near = sorted(word for word in vocabulary if levenshtein(cleaned, word) == 1)
        if len(near) == 1:
            return Resolution(value=near[0], original=token, repaired=True)
        if len(near) > 1:
            raise ValueError(
                f"unknown {what} {token!r}: did you mean "
                + " or ".join(repr(word) for word in near)
                + "? One edit away from more than one, so it is not repaired."
            )

    raise ValueError(
        f"unknown {what} {token!r}; expected one of: " + ", ".join(vocabulary)
    )
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_showcontext_vocabulary.py -q`
Expected: all pass. If `test_the_channel_vocabulary_stays_at_least_two_apart`
fails, **stop** — the vocabulary has drifted and the radius must be re-argued
before continuing.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/showcontext/ wing_parser/classifier/matcher.py tests/test_showcontext_vocabulary.py
git commit -F - <<'EOF'
Add the show-context vocabulary resolver

Radius-1 repair with a uniqueness requirement, plus a test pinning the
premise it rests on: no two channel kinds are closer than 2 apart, so
a distance-1 ball contains at most one kind. A tie refuses and names
both candidates rather than picking.
EOF
```

---

### Task 2: Records and loader

**Files:**
- Create: `wing_parser/showcontext/models.py`, `wing_parser/showcontext/loader.py`
- Modify: `wing_parser/showcontext/__init__.py`
- Test: `tests/test_showcontext_loader.py`

**Interfaces:**
- Consumes: `vocabulary.resolve`, `vocabulary.KNOWN_ACTIONS`, `matcher.known_kinds`
- Produces:
  - `models.Cue(id: str, action: str, channels: tuple[int, ...], dcas: tuple[int, ...], time: str | None, note: str)`
  - `models.Segment(id: str, title: str, time: str | None, expects: tuple[str, ...], cues: tuple[Cue, ...])`
  - `models.ShowContext(show: str, date: str | None, segments: tuple[Segment, ...], anomalies: tuple[str, ...], path: Path | None)`
  - `loader.load_show_context(path: str | Path) -> ShowContext`
  - `loader.parse_show_context(doc: dict, where_from: Path) -> ShowContext`
  - Re-exported from `wing_parser.showcontext` as `load_show_context`, `ShowContext`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_showcontext_loader.py
import pytest
import yaml

from wing_parser.showcontext import load_show_context

GOOD = {
    "show": "Tiec cuoi nam",
    "date": "2026-09-14",
    "segments": [
        {
            "id": "S1",
            "title": "MC welcome",
            "expects": ["speech.mc"],
            "cues": [{"id": "SQ 1", "action": "open", "channels": [8]}],
        },
        {
            "id": "S2",
            "title": "Band set",
            "expects": ["instrument.kyes"],
            "cues": [
                {"id": "SQ 2", "action": "Open", "channels": [29], "dcas": [2],
                 "time": "T+00:18:04"},
                {"id": "SQ 3", "action": "close", "channels": [29]},
            ],
        },
    ],
}


def _write(tmp_path, doc, name="show.yaml"):
    path = tmp_path / name
    path.write_text(yaml.safe_dump(doc, allow_unicode=True), encoding="utf-8")
    return path


def test_a_good_file_loads_into_records(tmp_path):
    context = load_show_context(_write(tmp_path, GOOD))
    assert context.show == "Tiec cuoi nam"
    assert [s.id for s in context.segments] == ["S1", "S2"]
    assert context.segments[1].cues[0].channels == (29,)
    assert context.segments[1].cues[0].dcas == (2,)
    assert context.segments[1].cues[0].action == "open"      # 'Open' normalised
    assert context.segments[0].cues[0].time is None


def test_a_repaired_kind_is_applied_and_reported(tmp_path):
    context = load_show_context(_write(tmp_path, GOOD))
    assert context.segments[1].expects == ("instrument.keys",)
    assert any("instrument.kyes" in note and "instrument.keys" in note
               for note in context.anomalies)


def test_an_unresolvable_kind_raises_naming_the_file(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1", "expects": ["trombone"]}]}
    path = _write(tmp_path, doc)
    with pytest.raises(ValueError) as caught:
        load_show_context(path)
    assert path.name in str(caught.value)
    assert "S1" in str(caught.value)


def test_a_duplicate_segment_id_raises(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1"}, {"id": "s1"}]}
    with pytest.raises(ValueError, match="duplicate segment id"):
        load_show_context(_write(tmp_path, doc))


def test_duplicate_cue_ids_within_a_segment_raise_even_across_whitespace(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open"}, {"id": "SQ1", "action": "close"}]}]}
    with pytest.raises(ValueError, match="duplicate cue id"):
        load_show_context(_write(tmp_path, doc))


def test_a_malformed_time_is_an_anomaly_not_an_exception(tmp_path):
    doc = {"show": "x", "segments": [{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "time": "quarter past"}]}]}
    context = load_show_context(_write(tmp_path, doc))
    assert context.segments[0].cues[0].time is None
    assert any("quarter past" in note for note in context.anomalies)


def test_a_missing_file_raises_naming_the_path(tmp_path):
    with pytest.raises(ValueError, match="nope.yaml"):
        load_show_context(tmp_path / "nope.yaml")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_showcontext_loader.py -q`
Expected: `ImportError` on `load_show_context`.

- [ ] **Step 3: Write the records**

Create `wing_parser/showcontext/models.py`:

```python
"""Frozen records for one show's context.

Deliberately dumb. Everything derived lives in view.py, resolved against
a scene; a record here states only what the file said.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class Cue:
    id: str
    action: str
    channels: tuple[int, ...] = ()
    dcas: tuple[int, ...] = ()
    time: str | None = None
    note: str = ""


@dataclass(frozen=True)
class Segment:
    id: str
    title: str = ""
    time: str | None = None
    expects: tuple[str, ...] = ()
    cues: tuple[Cue, ...] = ()


@dataclass(frozen=True)
class ShowContext:
    show: str
    date: str | None = None
    segments: tuple[Segment, ...] = ()
    anomalies: tuple[str, ...] = field(default_factory=tuple)
    path: Path | None = None
```

- [ ] **Step 4: Write the loader**

Create `wing_parser/showcontext/loader.py`:

```python
"""Read a show-context YAML file into records.

Structural problems raise, naming the file and the segment: a duplicate
id or an unresolvable kind means the document says something the tool
cannot act on, and finding that out on show day beats acting on a guess.
A malformed optional field becomes an anomaly instead -- `time:` feeds
only Q7, which ships disabled, and failing the other six rules over one
mistyped clock cell is the wrong trade (spec section 7).
"""

from __future__ import annotations

from pathlib import Path

import yaml

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext import vocabulary
from wing_parser.showcontext.models import Cue, Segment, ShowContext

# "T-12:00" or "T+1:04:30" -- the ROS column-1 format from
# docs/knowledge-base/04-templates-and-matrices/Master-Run-Of-Show-ROS.md.
# Parsed by hand rather than by regex; the repo bans building regexes in
# generated code and this is simple enough not to need one.


def _parse_time(text: str) -> int | None:
    """Show-relative time to signed seconds, or None if unreadable."""
    if not isinstance(text, str) or len(text) < 2 or text[0] not in "Tt":
        return None
    sign = text[1]
    if sign not in "+-":
        return None
    parts = text[2:].split(":")
    if not 2 <= len(parts) <= 3:
        return None
    try:
        numbers = [int(part) for part in parts]
    except ValueError:
        return None
    if any(number < 0 for number in numbers):
        return None
    while len(numbers) < 3:
        numbers.insert(0, 0)
    hours, minutes, seconds = numbers
    total = hours * 3600 + minutes * 60 + seconds
    return -total if sign == "-" else total


def _numbers(raw, where: str, field: str) -> tuple[int, ...]:
    if raw is None:
        return ()
    if not isinstance(raw, list):
        raise ValueError(f"{where}: {field} must be a list, not {type(raw).__name__}")
    out: list[int] = []
    for item in raw:
        if not isinstance(item, int) or isinstance(item, bool):
            raise ValueError(f"{where}: {field} entry {item!r} is not a whole number")
        out.append(item)
    return tuple(out)


def parse_show_context(doc: dict, where_from: Path) -> ShowContext:
    if not isinstance(doc, dict):
        raise ValueError(f"{where_from}: the file must be a mapping at the top level")

    anomalies: list[str] = []
    kinds = known_kinds("channels")
    segments: list[Segment] = []
    seen_segments: set[str] = set()

    for entry in doc.get("segments") or []:
        if not isinstance(entry, dict):
            raise ValueError(f"{where_from}: each segment must be a mapping")
        segment_id = str(entry.get("id") or "").strip()
        if not segment_id:
            raise ValueError(f"{where_from}: a segment is missing its 'id'")
        if segment_id.lower() in seen_segments:
            raise ValueError(f"{where_from}: duplicate segment id {segment_id!r}")
        seen_segments.add(segment_id.lower())
        where = f"{where_from}: segment {segment_id}"

        expects: list[str] = []
        for written in entry.get("expects") or []:
            resolved = vocabulary.resolve(str(written), kinds, what="kind")
            if resolved.repaired:
                anomalies.append(
                    f"{where}: expects {resolved.original!r} read as {resolved.value!r}"
                )
            expects.append(resolved.value)

        cues: list[Cue] = []
        seen_cues: set[str] = set()
        for raw_cue in entry.get("cues") or []:
            if not isinstance(raw_cue, dict):
                raise ValueError(f"{where}: each cue must be a mapping")
            cue_id = str(raw_cue.get("id") or "").strip()
            if not cue_id:
                raise ValueError(f"{where}: a cue is missing its 'id'")
            collapsed = "".join(cue_id.split()).lower()
            if collapsed in seen_cues:
                raise ValueError(f"{where}: duplicate cue id {cue_id!r}")
            seen_cues.add(collapsed)

            action = vocabulary.resolve(
                str(raw_cue.get("action") or ""), vocabulary.KNOWN_ACTIONS, what="action"
            )
            if action.repaired:
                anomalies.append(
                    f"{where}, cue {cue_id}: action {action.original!r} "
                    f"read as {action.value!r}"
                )

            written_time = raw_cue.get("time")
            seconds = _parse_time(written_time) if written_time is not None else None
            if written_time is not None and seconds is None:
                anomalies.append(
                    f"{where}, cue {cue_id}: time {written_time!r} is not "
                    "T+H:MM:SS or T-MM:SS and was ignored"
                )

            cues.append(Cue(
                id=cue_id,
                action=action.value,
                channels=_numbers(raw_cue.get("channels"), where, "channels"),
                dcas=_numbers(raw_cue.get("dcas"), where, "dcas"),
                time=written_time if seconds is not None else None,
                note=str(raw_cue.get("note") or ""),
            ))

        segment_time = entry.get("time")
        if segment_time is not None and _parse_time(segment_time) is None:
            anomalies.append(f"{where}: time {segment_time!r} is not readable and was ignored")
            segment_time = None

        segments.append(Segment(
            id=segment_id,
            title=str(entry.get("title") or ""),
            time=segment_time,
            expects=tuple(expects),
            cues=tuple(cues),
        ))

    return ShowContext(
        show=str(doc.get("show") or where_from.stem),
        date=str(doc["date"]) if doc.get("date") else None,
        segments=tuple(segments),
        anomalies=tuple(anomalies),
        path=where_from,
    )


def load_show_context(path: str | Path) -> ShowContext:
    where_from = Path(path)
    if not where_from.is_file():
        raise ValueError(f"no show context file at {where_from}")
    try:
        doc = yaml.safe_load(where_from.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ValueError(f"{where_from}: invalid YAML: {exc}") from exc
    return parse_show_context(doc, where_from)
```

Then set `wing_parser/showcontext/__init__.py`:

```python
"""Show context: what the paper says the show does."""

from wing_parser.showcontext.loader import load_show_context, parse_show_context
from wing_parser.showcontext.models import Cue, Segment, ShowContext

__all__ = ["load_show_context", "parse_show_context", "Cue", "Segment", "ShowContext"]
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `python -m pytest tests/test_showcontext_loader.py -q`
Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/showcontext/ tests/test_showcontext_loader.py
git commit -F - <<'EOF'
Read show-context YAML into frozen records

Hard errors for structure -- duplicate ids, unresolvable kinds and
actions -- naming the file and the segment. Soft for the optional
clock: a malformed time becomes an anomaly and the cue keeps running,
because time feeds only the one rule that ships disabled.
EOF
```

---

### Task 3: The view layer and its derived counts

Spec §5. Every derivation is a **count**, matched with `gt: 0`, because the
predicate language has no emptiness operator and a tuple-returning property
tested as `{not: []}` is always true.

**Files:**
- Create: `wing_parser/showcontext/view.py`
- Test: `tests/test_showcontext_view.py`

**Interfaces:**
- Consumes: `models.ShowContext`, a loaded `WingScene`
- Produces:
  - `view.build(context: ShowContext, scene) -> tuple[SegmentView, ...]`
  - `SegmentView`: `.id`, `.title`, `.cues -> tuple[CueView, ...]`, `.unmet_expect_count`, `.unmet_expects_text`, `.dark_expect_count`, `.dark_expects_text`
  - `CueView`: `.id`, `.action`, `.segment_id`, `.target_name`, `.missing_channel_count`, `.missing_channels_text`, `.unnamed_channel_count`, `.unnamed_channels_text`, `.missing_dca_count`, `.missing_dcas_text`, `.contradiction_count`, `.contradictions_text`, `.seconds_after_previous`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_showcontext_view.py
"""Derived counts, resolved against the real sample scene.

Every expected number below was read off user-files/example-Vu.snap,
not assumed: channel 29 is "Key 1" (instrument.keys), channel 31 is
absent from the file entirely, and channel 4 is named "Mic 4".
"""
import pytest

from wing_parser import WingScene
from wing_parser.showcontext import view
from wing_parser.showcontext.models import Cue, Segment, ShowContext


@pytest.fixture
def scene(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    return WingScene.load(vu_path)


def _context(*segments):
    return ShowContext(show="t", segments=tuple(segments))


def test_a_cue_naming_an_absent_channel_counts_it(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(29, 31)),)))
    cue = view.build(context, scene)[0].cues[0]
    assert cue.missing_channel_count == 1
    assert "31" in cue.missing_channels_text
    assert cue.unnamed_channel_count == 0


def test_a_cue_naming_a_present_but_unnamed_channel_counts_it(scene):
    # Channels 31-36 are absent; 33 is not. Use a channel the file has
    # with an empty name -- probe before pinning if this changes.
    named = {c.number for c in scene.channels() if c.name.strip()}
    blank = sorted({c.number for c in scene.channels()} - named)
    assert blank, "sample file has no unnamed channel; re-probe this test"
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(blank[0],)),)))
    cue = view.build(context, scene)[0].cues[0]
    assert cue.unnamed_channel_count == 1
    assert cue.missing_channel_count == 0


def test_a_cue_naming_an_absent_dca_counts_it(scene):
    highest = max(scene.dcas) if scene.dcas else 0
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", dcas=(highest + 1,)),)))
    assert view.build(context, scene)[0].cues[0].missing_dca_count == 1


def test_opening_an_already_open_channel_is_a_contradiction(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(29,)),
        Cue(id="SQ 2", action="open", channels=(29,)),)))
    cues = view.build(context, scene)[0].cues
    assert cues[0].contradiction_count == 0
    assert cues[1].contradiction_count == 1
    assert "29" in cues[1].contradictions_text


def test_a_level_move_does_not_touch_the_open_book(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="up", channels=(29,)),
        Cue(id="SQ 2", action="open", channels=(29,)),)))
    assert [c.contradiction_count for c in view.build(context, scene)[0].cues] == [0, 0]


def test_state_carries_across_segments(scene):
    context = _context(
        Segment(id="S1", cues=(Cue(id="SQ 1", action="open", channels=(29,)),)),
        Segment(id="S2", cues=(Cue(id="SQ 2", action="open", channels=(29,)),)),
    )
    segments = view.build(context, scene)
    assert segments[1].cues[0].contradiction_count == 1


def test_an_expected_kind_with_no_channel_is_unmet(scene):
    context = _context(Segment(id="S1", expects=("instrument.horns",)))
    segment = view.build(context, scene)[0]
    assert segment.unmet_expect_count == 1
    assert "instrument.horns" in segment.unmet_expects_text


def test_an_expected_kind_whose_channels_are_all_parked_is_dark(scene):
    # Channel 29 "Key 1" classifies instrument.keys and is at -inf on
    # this file, so the kind is present but not in use.
    context = _context(Segment(id="S1", expects=("instrument.keys",)))
    segment = view.build(context, scene)[0]
    assert segment.unmet_expect_count == 0
    assert segment.dark_expect_count == 1


def test_seconds_between_timed_cues(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(29,), time="T+00:18:00"),
        Cue(id="SQ 2", action="close", channels=(29,), time="T+00:18:04"),)))
    cues = view.build(context, scene)[0].cues
    assert cues[0].seconds_after_previous is None
    assert cues[1].seconds_after_previous == pytest.approx(4.0)


def test_an_untimed_cue_yields_no_gap(scene):
    context = _context(Segment(id="S1", cues=(
        Cue(id="SQ 1", action="open", channels=(29,), time="T+00:18:00"),
        Cue(id="SQ 2", action="close", channels=(29,)),)))
    assert view.build(context, scene)[0].cues[1].seconds_after_previous is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_showcontext_view.py -q`
Expected: `ImportError` on `wing_parser.showcontext.view`.

- [ ] **Step 3: Write the view**

Create `wing_parser/showcontext/view.py`:

```python
"""What the show context means once a scene is loaded beside it.

Derivations are exposed as counts, never as collections. The predicate
language has no emptiness operator, so a tuple-returning property would
have to be written `{not: []}` in a rule -- which is always true in
Python, since `() != []`. The rule would sit silent forever and no test
against a stub would catch it. Counts match with `gt: 0`, the shape
`Bus.notch_count` already uses.

Each count has a `*_text` twin so a finding can name the actual channel
numbers instead of reporting "3".
"""

from __future__ import annotations

from wing_parser.classifier.matcher import HIGH
from wing_parser.showcontext.loader import _parse_time
from wing_parser.showcontext.models import Cue, Segment, ShowContext

# Only these two move the open/closed book. A level move on a closed
# channel is not a contradiction, and what a recall does to any given
# channel is not knowable from a cue sheet (spec section 3).
STATE_ACTIONS = {"open": True, "close": False}


def _listed(numbers: tuple[int, ...]) -> str:
    return ", ".join(str(n) for n in numbers)


class CueView:
    def __init__(self, cue: Cue, segment_id: str, scene,
                 contradictions: tuple[int, ...], gap: float | None) -> None:
        self._cue = cue
        self._scene = scene
        self.segment_id = segment_id
        self._contradictions = contradictions
        self._gap = gap

    @property
    def id(self) -> str:
        return self._cue.id

    @property
    def action(self) -> str:
        return self._cue.action

    @property
    def target_name(self) -> str:
        return f"cue.{self.segment_id}.{''.join(self._cue.id.split())}"

    @property
    def _present(self) -> dict[int, object]:
        return self._scene.channel_map()

    @property
    def missing_channels(self) -> tuple[int, ...]:
        present = self._present
        return tuple(n for n in self._cue.channels if n not in present)

    @property
    def missing_channel_count(self) -> int:
        return len(self.missing_channels)

    @property
    def missing_channels_text(self) -> str:
        return _listed(self.missing_channels)

    @property
    def unnamed_channels(self) -> tuple[int, ...]:
        present = self._present
        return tuple(
            n for n in self._cue.channels
            if n in present and not present[n].name.strip()
        )

    @property
    def unnamed_channel_count(self) -> int:
        return len(self.unnamed_channels)

    @property
    def unnamed_channels_text(self) -> str:
        return _listed(self.unnamed_channels)

    @property
    def missing_dcas(self) -> tuple[int, ...]:
        return tuple(n for n in self._cue.dcas if n not in self._scene.dcas)

    @property
    def missing_dca_count(self) -> int:
        return len(self.missing_dcas)

    @property
    def missing_dcas_text(self) -> str:
        return _listed(self.missing_dcas)

    @property
    def contradiction_count(self) -> int:
        return len(self._contradictions)

    @property
    def contradictions_text(self) -> str:
        return _listed(self._contradictions)

    @property
    def seconds_after_previous(self) -> float | None:
        return self._gap


class SegmentView:
    def __init__(self, segment: Segment, scene, cues: tuple[CueView, ...]) -> None:
        self._segment = segment
        self._scene = scene
        self.cues = cues

    @property
    def id(self) -> str:
        return self._segment.id

    @property
    def title(self) -> str:
        return self._segment.title

    @property
    def target_name(self) -> str:
        return f"segment.{self._segment.id}"

    def _channels_of(self, kind: str) -> tuple:
        """Only confidently-classified channels count.

        Same threshold Bus.receives_ambient uses: a weak guess must not
        satisfy an expectation, or the rule silently stops firing on the
        thing it exists to catch.
        """
        return tuple(
            channel for channel in self._scene.channels()
            if channel.source_type.kind == kind
            and channel.source_type.confidence >= HIGH
        )

    @property
    def unmet_expects(self) -> tuple[str, ...]:
        return tuple(k for k in self._segment.expects if not self._channels_of(k))

    @property
    def unmet_expect_count(self) -> int:
        return len(self.unmet_expects)

    @property
    def unmet_expects_text(self) -> str:
        return ", ".join(self.unmet_expects)

    @property
    def dark_expects(self) -> tuple[str, ...]:
        found = []
        for kind in self._segment.expects:
            channels = self._channels_of(kind)
            if channels and not any(channel.in_use for channel in channels):
                found.append(kind)
        return tuple(found)

    @property
    def dark_expect_count(self) -> int:
        return len(self.dark_expects)

    @property
    def dark_expects_text(self) -> str:
        return ", ".join(self.dark_expects)


def build(context: ShowContext, scene) -> tuple[SegmentView, ...]:
    """Walk every cue in file order, keeping the open/closed book."""
    state: dict[int, bool] = {}
    previous_seconds: int | None = None
    segments: list[SegmentView] = []

    for segment in context.segments:
        cues: list[CueView] = []
        for cue in segment.cues:
            wanted = STATE_ACTIONS.get(cue.action)
            contradictions: list[int] = []
            if wanted is not None:
                for number in cue.channels:
                    if state.get(number) == wanted:
                        contradictions.append(number)
                    state[number] = wanted

            seconds = _parse_time(cue.time) if cue.time else None
            gap = (
                float(seconds - previous_seconds)
                if seconds is not None and previous_seconds is not None
                else None
            )
            if seconds is not None:
                previous_seconds = seconds

            cues.append(CueView(cue, segment.id, scene, tuple(contradictions), gap))
        segments.append(SegmentView(segment, scene, tuple(cues)))

    return tuple(segments)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `python -m pytest tests/test_showcontext_view.py -q`
Expected: all pass. If `test_an_expected_kind_whose_channels_are_all_parked_is_dark`
fails, re-probe channel 29's classification and fader on the sample file and fix
the test's stated evidence — do not weaken the assertion.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/showcontext/view.py tests/test_showcontext_view.py
git commit -F - <<'EOF'
Derive show-context counts against a loaded scene

Counts, not collections: the predicate language has no emptiness
operator and `{not: []}` is always true against a tuple, so a
collection-returning property would produce a rule that never fires.

Only open and close move the open/closed book; a level move on a closed
channel is not a contradiction, and a recall's effect on a given
channel is not knowable from the paper.
EOF
```

---

### Task 4: Attach the context to the scene and iterate it

The invariance test in this task is the load-bearing one for the whole feature.

**Files:**
- Modify: `wing_parser/query/scene.py:67-69` (the `load` classmethod), `wing_parser/query/scene.py:23-65` (`__init__`)
- Modify: `wing_parser/advisory/evaluator.py:100-107` (`ITERATORS`)
- Test: `tests/test_showcontext_iterators.py`

**Interfaces:**
- Consumes: `load_show_context`, `view.build`
- Produces:
  - `WingScene.load(path, show: str | Path | None = None)`
  - `scene.show: ShowContext | None`
  - `scene.show_segments() -> tuple[SegmentView, ...]` (empty when no context)
  - iterator names `"cue"` and `"segment"` in `ITERATORS`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_showcontext_iterators.py
import pytest
import yaml

from wing_parser import WingScene
from wing_parser.advisory.evaluator import ITERATORS, targets_for


@pytest.fixture
def show_file(tmp_path):
    path = tmp_path / "tonight.yaml"
    path.write_text(yaml.safe_dump({
        "show": "t",
        "segments": [{"id": "S1", "expects": ["speech.mc"],
                      "cues": [{"id": "SQ 1", "action": "open", "channels": [8]}]}],
    }), encoding="utf-8")
    return path


def test_both_iterators_are_registered():
    assert "cue" in ITERATORS and "segment" in ITERATORS


def test_without_a_context_both_iterators_yield_nothing(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path)
    assert scene.show is None
    assert list(targets_for(scene, "cue")) == []
    assert list(targets_for(scene, "segment")) == []


def test_with_a_context_targets_carry_the_expected_names(vu_path, show_file, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path, show=show_file)
    assert [t.name for t in targets_for(scene, "cue")] == ["cue.S1.SQ1"]
    assert [t.name for t in targets_for(scene, "segment")] == ["segment.S1"]
    cue_target = next(iter(targets_for(scene, "cue")))
    assert set(cue_target.context) == {"cue", "segment"}
    assert cue_target.confidence == 1.0


def test_the_unprofiled_real_file_contract_is_untouched(vu_path, monkeypatch):
    """The load-bearing test: adding show context must not move a
    single existing finding. 22 rows are pinned in
    tests/test_advisory_realfile.py; assert the count here so a
    regression in this subsystem is caught in this subsystem's file."""
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert len(WingScene.load(vu_path).advisory.run()) == 22
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `python -m pytest tests/test_showcontext_iterators.py -q`
Expected: `test_both_iterators_are_registered` fails; the `show=` keyword raises
`TypeError`.

- [ ] **Step 3: Attach the context to the scene**

In `wing_parser/query/scene.py`, add the import:

```python
from wing_parser.showcontext import ShowContext, load_show_context
from wing_parser.showcontext import view as show_view
```

Change `__init__`'s signature and add two lines at the end of it:

```python
    def __init__(self, raw: RawScene, show: ShowContext | None = None) -> None:
```

```python
        self.classifier = Classifier()
        self.show: ShowContext | None = show
        self._show_segments: tuple | None = None
```

Replace the `load` classmethod:

```python
    @classmethod
    def load(cls, path: str | Path, show: str | Path | None = None) -> "WingScene":
        """`show` names a show-context YAML file; without one, the cue and
        segment iterators yield nothing and behaviour is unchanged."""
        context = load_show_context(show) if show is not None else None
        return cls(load_raw(path), context)

    def show_segments(self) -> tuple:
        """Segment views, built once. Empty when no context is loaded."""
        if self.show is None:
            return ()
        if self._show_segments is None:
            self._show_segments = show_view.build(self.show, self)
        return self._show_segments
```

- [ ] **Step 4: Add the iterators**

In `wing_parser/advisory/evaluator.py`, add after `_nothing`:

```python
def _cues(scene) -> Iterator[Target]:
    """One target per cue. Yields nothing when no show context is loaded,
    which is what keeps every existing finding unchanged."""
    for segment in scene.show_segments():
        for cue in segment.cues:
            yield Target(
                name=cue.target_name,
                context={"cue": cue, "segment": segment},
                confidence=1.0,
            )


def _segments(scene) -> Iterator[Target]:
    for segment in scene.show_segments():
        yield Target(
            name=segment.target_name,
            context={"segment": segment},
            confidence=1.0,
        )
```

and extend the table:

```python
ITERATORS: dict[str, Callable[[Any], Iterator[Target]]] = {
    "channel": _channels,
    "channel.sends": _channel_sends,
    "channel.main_sends": _channel_main_sends,
    "bus": _buses,
    "output": _outputs,
    "cue": _cues,
    "segment": _segments,
    "none": _nothing,
}
```

- [ ] **Step 5: Run the new tests, then the whole suite**

Run: `python -m pytest tests/test_showcontext_iterators.py -q`
Expected: all pass.

Run: `python -m pytest tests/ -q --junitxml=junit.xml`
Expected: exit code 0. Read `junit.xml`'s `<testsuite …>` attributes for the
counts — this machine may print no summary trailer. `failures="0" errors="0"`
and `skipped="1"`.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/query/scene.py wing_parser/advisory/evaluator.py tests/test_showcontext_iterators.py
git commit -F - <<'EOF'
Attach show context to the scene and iterate it

Iterators take only (scene), so the context hangs off the scene rather
than changing every iterator's signature. Both new iterators yield
nothing when no context is loaded -- the same shape as _nothing -- and
a test pins the unprofiled real-file count at 22 to prove it.
EOF
```

---

### Task 5: Rules Q1–Q3, the cue side

**Files:**
- Create: `wing_parser/advisory/base_rules/showcontext.yaml`
- Test: `tests/test_showcontext_rules.py`

**Interfaces:**
- Consumes: the `cue` iterator, `CueView`'s count properties
- Produces: rule ids `Q1`, `Q2`, `Q3` loadable by `load_base_rules()`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_showcontext_rules.py
import pytest
import yaml

from wing_parser import WingScene
from wing_parser.advisory.loader import load_base_rules


def _show(tmp_path, segments):
    path = tmp_path / "tonight.yaml"
    path.write_text(yaml.safe_dump({"show": "t", "segments": segments}), encoding="utf-8")
    return path


@pytest.fixture
def fire(vu_path, tmp_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")

    def run(segments, rule_id):
        scene = WingScene.load(vu_path, show=_show(tmp_path, segments))
        return [f for f in scene.advisory.run() if f.rule_id == rule_id]

    return run


def test_the_cue_rules_load_with_source_and_rationale():
    """Q1-Q3 only. The all-seven assertion lands in Task 7, once every
    rule exists -- a test that fails for two tasks is a broken gate, not
    a pending one."""
    rules = {r.id: r for r in load_base_rules() if r.id.startswith("Q")}
    assert {"Q1", "Q2", "Q3"} <= set(rules)
    for rule in rules.values():
        assert rule.source.strip() and rule.rationale.strip()


def test_q1_fires_on_a_cue_naming_an_absent_channel(fire):
    found = fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "channels": [8, 31]}]}], "Q1")
    assert [f.target for f in found] == ["cue.S1.SQ1"]
    assert "31" in found[0].message
    assert found[0].severity == "warning"


def test_q1_stays_silent_when_every_channel_is_present(fire):
    assert fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "channels": [8]}]}], "Q1") == []


def test_q3_fires_on_an_absent_dca(fire):
    found = fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "dcas": [99]}]}], "Q3")
    assert [f.target for f in found] == ["cue.S1.SQ1"]
    assert "99" in found[0].message
```

- [ ] **Step 2: Run it to verify it fails**

Run: `python -m pytest tests/test_showcontext_rules.py -q`
Expected: `test_the_q_rules_load_with_source_and_rationale` fails — no Q rules.

- [ ] **Step 3: Write the rules**

Create `wing_parser/advisory/base_rules/showcontext.yaml`:

```yaml
# Rules that compare the show's paperwork with the scene. Every one of
# them yields nothing unless a show context is loaded with --show,
# because the cue and segment iterators are empty without one.
rules:
  - id: Q1
    title: "Cue names a channel the scene does not have"
    severity: warning
    source: >
      docs/knowledge-base/04-templates-and-matrices/Master-Run-Of-Show-ROS.md
      section 1.2, Audio Cue column: "State the channel or DCA number,
      never 'open her mic' -- the console has numbers, use them."
    rationale: >
      The ROS standard requires the audio cue to name a console number,
      which makes the number checkable. A cue calling a channel the scene
      does not contain is either a stale cue sheet or a scene loaded from
      the wrong show; both are found in seconds before doors and in the
      worst possible way after them.
    when:
      for_each: cue
      where:
        cue.missing_channel_count: {gt: 0}
    message: >
      Cue {cue.id} in segment {segment.id} names channel(s)
      {cue.missing_channels_text}, which the scene does not contain.

  - id: Q2
    title: "Cue names a channel that carries no name"
    severity: info
    source: >
      docs/knowledge-base/04-templates-and-matrices/Master-Run-Of-Show-ROS.md
      section 1.2, Audio Cue column; Core-Skills-Overview.md section 1.1
      on department cue sheets carrying only that department's cues.
    rationale: >
      The channel exists, so the cue is not wrong -- but an unnamed
      channel is one nobody else at the desk can identify under pressure,
      and a cue sheet that calls it is relying on one person's memory.
      Info, not warning: this is a labelling job, not a fault.
    when:
      for_each: cue
      where:
        cue.unnamed_channel_count: {gt: 0}
    message: >
      Cue {cue.id} in segment {segment.id} names channel(s)
      {cue.unnamed_channels_text}, which exist but carry no name.

  - id: Q3
    title: "Cue names a DCA the scene does not configure"
    severity: warning
    source: >
      docs/knowledge-base/04-templates-and-matrices/Master-Run-Of-Show-ROS.md
      section 1.2, Audio Cue column, worked example "SQ 8 GO -- CH3 open,
      DCA2 up".
    rationale: >
      Same failure as Q1 on the other half of the cue's vocabulary. A DCA
      move is the fastest lever on the desk during a show; calling one
      that is not built means the operator reaches for a fader that does
      nothing.
    when:
      for_each: cue
      where:
        cue.missing_dca_count: {gt: 0}
    message: >
      Cue {cue.id} in segment {segment.id} names DCA(s)
      {cue.missing_dcas_text}, which the scene does not configure.
```

- [ ] **Step 4: Run the whole file, then the suite**

Run: `python -m pytest tests/test_showcontext_rules.py -q`
Expected: pass — this task's tests assert only that Q1–Q3 exist, so the file is
green at the end of this task, not two tasks later.

Run: `python -m pytest tests/ -q --junitxml=junit.xml`
Expected: exit 0.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/base_rules/showcontext.yaml tests/test_showcontext_rules.py
git commit -F - <<'EOF'
Add Q1-Q3: cue references the scene cannot satisfy

The ROS standard already requires the Audio Cue column to name console
numbers rather than people, which is exactly what makes these
checkable. Q2 is info: an unnamed channel is a labelling job, not a
fault.
EOF
```

---

### Task 6: Rules Q4–Q5, the segment side

**Files:**
- Modify: `wing_parser/advisory/base_rules/showcontext.yaml` (append)
- Modify: `tests/test_showcontext_rules.py` (append)

**Interfaces:**
- Consumes: the `segment` iterator, `SegmentView`'s count properties
- Produces: rule ids `Q4`, `Q5`

- [ ] **Step 1: Write the failing tests**

Append to `tests/test_showcontext_rules.py`:

```python
def test_q4_fires_when_an_expected_kind_has_no_channel(fire):
    found = fire([{"id": "S1", "expects": ["instrument.horns"]}], "Q4")
    assert [f.target for f in found] == ["segment.S1"]
    assert "instrument.horns" in found[0].message


def test_q4_stays_silent_when_the_kind_is_present(fire):
    assert fire([{"id": "S1", "expects": ["instrument.keys"]}], "Q4") == []


def test_q5_fires_when_the_kind_is_present_but_parked(fire):
    # Every instrument.keys channel on the sample file sits at -inf.
    found = fire([{"id": "S1", "expects": ["instrument.keys"]}], "Q5")
    assert [f.target for f in found] == ["segment.S1"]
    assert found[0].severity == "info"


def test_q5_does_not_double_report_a_kind_q4_already_flagged(fire):
    assert fire([{"id": "S1", "expects": ["instrument.horns"]}], "Q5") == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_showcontext_rules.py -q -k "q4 or q5"`
Expected: fail — no Q4/Q5 rules.

- [ ] **Step 3: Append the rules**

```yaml
  - id: Q4
    title: "Segment expects a source with no channel for it"
    severity: warning
    source: >
      docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md
      section 1.1, on the department cue sheet carrying that department's
      cues; docs/knowledge-base/04-templates-and-matrices/Master-Run-Of-Show-ROS.md
      section 1.3 step 3, the department pass.
    rationale: >
      The paperwork says this part of the show has a source; the scene
      has no channel confidently classified as it. Either an input is
      unpatched or the scene predates the latest ROS revision. Only
      channels classified at or above the confident band count -- a weak
      name guess must not satisfy an expectation, or the rule quietly
      stops catching the thing it exists for. Same threshold
      Bus.receives_ambient uses.
    when:
      for_each: segment
      where:
        segment.unmet_expect_count: {gt: 0}
    message: >
      Segment {segment.id} ({segment.title}) expects
      {segment.unmet_expects_text}, and no confidently-classified channel
      of that kind exists in the scene.

  - id: Q5
    title: "Segment expects a source whose channels are all parked"
    severity: info
    source: >
      docs/knowledge-base/02-event-ops-framework/Core-Skills-Overview.md
      section 1.1; the in_use definition probed for N1 in the 2026-08-16
      rule-set-growth spec section 4.
    rationale: >
      The channel is there but is unpatched, muted, unrouted, or has its
      fader below the -90 dB floor. On a scene built ahead of doors that
      is normal, which is why this is info and not warning; it is a
      checklist line, not an alarm. Reuses Channel.in_use rather than
      defining a second liveness test, so it cannot drift from N1's.
    when:
      for_each: segment
      where:
        segment.dark_expect_count: {gt: 0}
    message: >
      Segment {segment.id} ({segment.title}) expects
      {segment.dark_expects_text}; channels of that kind exist but none
      is in use.
```

- [ ] **Step 4: Run to verify they pass**

Run: `python -m pytest tests/test_showcontext_rules.py -q -k "q4 or q5"`
Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/base_rules/showcontext.yaml tests/test_showcontext_rules.py
git commit -F - <<'EOF'
Add Q4-Q5: the show calls for a source the scene cannot supply

Neither sets requires_classifier: that flag gates on the target's own
confidence and a segment is not a classified object. The confidence
test lives where the classification does, inside the derivation, at the
same HIGH threshold receives_ambient uses.
EOF
```

---

### Task 7: Q6 and the disabled Q7

**Files:**
- Modify: `wing_parser/advisory/base_rules/showcontext.yaml` (append)
- Modify: `tests/test_showcontext_rules.py` (append)

**Interfaces:**
- Consumes: `CueView.contradiction_count`, `CueView.seconds_after_previous`
- Produces: rule ids `Q6`, `Q7` (Q7 with `enabled: false`)

- [ ] **Step 1: Write the failing tests**

```python
def test_q6_fires_on_a_second_open_of_the_same_channel(fire):
    found = fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "channels": [8]},
        {"id": "SQ 2", "action": "open", "channels": [8]}]}], "Q6")
    assert [f.target for f in found] == ["cue.S1.SQ2"]


def test_every_q_rule_now_exists():
    from wing_parser.advisory.loader import load_base_rules
    rules = {r.id for r in load_base_rules() if r.id.startswith("Q")}
    assert rules == {"Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7"}


def test_q7_ships_disabled_and_therefore_never_fires(fire):
    from wing_parser.advisory.loader import load_base_rules
    q7 = next(r for r in load_base_rules() if r.id == "Q7")
    assert q7.enabled is False
    assert "threshold" in q7.rationale.lower()
    assert fire([{"id": "S1", "cues": [
        {"id": "SQ 1", "action": "open", "channels": [8], "time": "T+00:10:00"},
        {"id": "SQ 2", "action": "close", "channels": [8], "time": "T+00:10:01"}]}],
        "Q7") == []
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_showcontext_rules.py -q -k "q6 or q7"`
Expected: fail.

- [ ] **Step 3: Append the rules**

```yaml
  - id: Q6
    title: "Cue contradicts the state the earlier cues left"
    severity: warning
    source: >
      docs/knowledge-base/04-templates-and-matrices/Master-Run-Of-Show-ROS.md
      section 2.4 on point numbering, and section 1.3 step 6, rehearsal
      markup reconciled the same evening.
    rationale: >
      Walking the cues in file order gives every channel an open/closed
      book; opening one already open, or closing one already closed,
      means two cues disagree about the state of the desk. Usually a cue
      inserted during rehearsal that was never reconciled. Only open and
      close move the book -- a level move on a closed channel is not a
      contradiction, and what a recall does to a given channel is not
      knowable from the cue sheet.
    when:
      for_each: cue
      where:
        cue.contradiction_count: {gt: 0}
    message: >
      Cue {cue.id} in segment {segment.id} runs "{cue.action}" on
      channel(s) {cue.contradictions_text}, which earlier cues already
      left in that state.

  - id: Q7
    title: "Two cues sit closer together than the operation needs"
    severity: warning
    enabled: false
    source: >
      No source. ToanAZ deferred the threshold on 2026-08-17 rather than
      accept a placeholder; the 2026-08-17 input-pipelines spec section
      6 records the decision.
    rationale: >
      A cue gap shorter than the operation between them takes is a cue
      that will be called late. Shipped disabled because no source in
      this repository states how long a mic change, a scene recall or a
      patch change takes on ToanAZ's rig, and a threshold nobody can cite
      is a threshold that produces noise. To switch it on: get one number
      per action from him, put them in a descriptor file, add the
      comparison to the `where` block below, and set enabled: true. The
      derivation it needs already exists and is tested --
      CueView.seconds_after_previous, which is None unless both cues
      carry a readable time. This is the N2 precedent: an honest disable
      beats a noisy rule.
    when:
      for_each: cue
      where:
        cue.seconds_after_previous: {lt: 0}
    message: >
      Cue {cue.id} in segment {segment.id} is
      {cue.seconds_after_previous} s after the previous timed cue.
```

- [ ] **Step 4: Run the whole rules file, then the suite**

Run: `python -m pytest tests/test_showcontext_rules.py -q`
Expected: all pass, including `test_the_q_rules_load_with_source_and_rationale`.

Run: `python -m pytest tests/ -q --junitxml=junit.xml`
Expected: exit 0, `failures="0" errors="0" skipped="1"`.

- [ ] **Step 5: Commit**

```bash
git add wing_parser/advisory/base_rules/showcontext.yaml tests/test_showcontext_rules.py
git commit -F - <<'EOF'
Add Q6, and Q7 disabled with the switch-on recipe in its rationale

Q7 has no citable threshold, so it ships enabled: false rather than
inventing one -- the N2 precedent. Its rationale names exactly what is
missing and what to do when the number arrives; the derivation it needs
already exists and is tested.
EOF
```

---

### Task 8: `--show` on `doctor` and `feedback`

**Files:**
- Modify: `wing_parser/cli/__main__.py:33-41` (doctor), `:49-59` (feedback)
- Modify: `wing_parser/cli/commands.py` (`_load`, `doctor`, `feedback`)
- Test: `tests/test_cli_showcontext.py`

**Interfaces:**
- Consumes: `WingScene.load(path, show=...)`
- Produces: `--show <path>` on both subcommands

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_cli_showcontext.py
import yaml

from wing_parser.cli.__main__ import main


def _show(tmp_path):
    path = tmp_path / "tonight.yaml"
    path.write_text(yaml.safe_dump({"show": "t", "segments": [
        {"id": "S1", "cues": [{"id": "SQ 1", "action": "open", "channels": [31]}]}]}),
        encoding="utf-8")
    return path


def test_doctor_with_show_reports_a_q_finding(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert main(["doctor", str(vu_path), "--show", str(_show(tmp_path))]) == 0
    assert "Q1" in capsys.readouterr().out


def test_doctor_without_show_reports_no_q_finding(vu_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert main(["doctor", str(vu_path)]) == 0
    assert "Q1" not in capsys.readouterr().out


def test_a_bad_show_path_exits_one_and_names_the_file(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    assert main(["doctor", str(vu_path), "--show", str(tmp_path / "nope.yaml")]) == 1
    assert "nope.yaml" in capsys.readouterr().err


def test_show_anomalies_are_printed(vu_path, tmp_path, capsys, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    path = tmp_path / "typo.yaml"
    path.write_text(yaml.safe_dump({"show": "t", "segments": [
        {"id": "S1", "expects": ["instrument.kyes"]}]}), encoding="utf-8")
    main(["doctor", str(vu_path), "--show", str(path)])
    out = capsys.readouterr().out
    assert "instrument.kyes" in out and "instrument.keys" in out
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_cli_showcontext.py -q`
Expected: `unrecognized arguments: --show`.

- [ ] **Step 3: Wire the argument**

In `wing_parser/cli/__main__.py`, add to **both** the `doctor` and `feedback`
subparsers, before their `set_defaults`:

```python
    node.add_argument(
        "--show",
        default=None,
        help="a show-context YAML file: segments, expected sources and cues",
    )
```

- [ ] **Step 4: Pass it through the commands**

In `wing_parser/cli/commands.py`, change `_load` to take the context and report a
load failure the same way a bad scene is reported. Find the existing `_load` and
give it a `show` parameter:

```python
def _load(path, show=None):
    try:
        return WingScene.load(path, show=show)
    except (OSError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return None
```

Then in `doctor`, replace the first line and print any anomalies before the
findings:

```python
def doctor(args) -> int:
    scene = _load(args.file, getattr(args, "show", None))
    if scene is None:
        return 1
    if scene.show is not None:
        for note in scene.show.anomalies:
            print(f"show context: {note}")
```

and in `feedback`, replace its `_load` call:

```python
    scene = _load(args.scene, getattr(args, "show", None))
```

Check the existing `_load` body before editing — if it already catches a
different exception set, widen it rather than replacing it, and keep its
existing message shape.

- [ ] **Step 5: Run the CLI tests, then the suite**

Run: `python -m pytest tests/test_cli_showcontext.py tests/test_cli.py -q`
Expected: pass.

Run: `python -m pytest tests/ -q --junitxml=junit.xml`
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/cli/ tests/test_cli_showcontext.py
git commit -F - <<'EOF'
Accept --show on doctor and feedback

feedback needs the flag for the same reason it needs --profile: it
resolves a finding id by re-running the rules doctor printed, so a
Q-finding id will not resolve unless both commands are given the same
context. Repairs made while reading the file print above the findings.
EOF
```

---

### Task 9: `showcontext lint [--fix]`

The one command worth having beyond `doctor`: the file is hand-written, and the
alternative is finding the typo while the band waits.

**Files:**
- Create: `wing_parser/showcontext/rewrite.py`
- Modify: `wing_parser/cli/__main__.py`, `wing_parser/cli/commands.py`
- Test: `tests/test_showcontext_lint.py`

**Interfaces:**
- Consumes: `load_show_context`, `vocabulary.resolve`
- Produces:
  - `rewrite.apply_repairs(path: Path) -> tuple[str, ...]` — rewrites the file in
    place through `ruamel.yaml`, returning the repairs made
  - CLI `wing showcontext lint <file> [--fix]`, handler `commands.showcontext_lint`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_showcontext_lint.py
from wing_parser.cli.__main__ import main

GOOD = """\
show: Tiec cuoi nam
segments:
  # the band set
  - id: S2
    expects: [instrument.kyes]
    cues:
      - id: SQ 2
        action: open
        channels: [29]
"""


def test_lint_reports_repairs_without_touching_the_file(tmp_path, capsys):
    path = tmp_path / "tonight.yaml"
    path.write_text(GOOD, encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    assert main(["showcontext", "lint", str(path)]) == 0
    assert "instrument.keys" in capsys.readouterr().out
    assert path.read_text(encoding="utf-8") == before


def test_fix_rewrites_the_file_and_keeps_comments(tmp_path, capsys):
    path = tmp_path / "tonight.yaml"
    path.write_text(GOOD, encoding="utf-8")
    assert main(["showcontext", "lint", str(path), "--fix"]) == 0
    after = path.read_text(encoding="utf-8")
    assert "instrument.keys" in after
    assert "instrument.kyes" not in after
    assert "# the band set" in after


def test_lint_exits_one_on_an_unrepairable_file(tmp_path, capsys):
    path = tmp_path / "bad.yaml"
    path.write_text("show: x\nsegments:\n  - id: S1\n    expects: [trombone]\n",
                    encoding="utf-8")
    assert main(["showcontext", "lint", str(path)]) == 1
    assert "trombone" in capsys.readouterr().err
```

- [ ] **Step 2: Run to verify they fail**

Run: `python -m pytest tests/test_showcontext_lint.py -q`
Expected: `invalid choice: 'showcontext'`.

- [ ] **Step 3: Write the rewriter**

Create `wing_parser/showcontext/rewrite.py`:

```python
"""Write repairs back into a show-context file.

ruamel round-trip, not PyYAML dump: the file is hand-written and carries
the author's comments and ordering, and a tool that silently reformats
the document it was asked to spell-check has taken something away.
"""

from __future__ import annotations

from pathlib import Path

from ruamel.yaml import YAML

from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext import vocabulary


def apply_repairs(path: str | Path) -> tuple[str, ...]:
    where_from = Path(path)
    yaml = YAML()
    yaml.preserve_quotes = True
    with where_from.open(encoding="utf-8") as handle:
        doc = yaml.load(handle) or {}

    kinds = known_kinds("channels")
    repairs: list[str] = []

    for segment in doc.get("segments") or []:
        expects = segment.get("expects")
        if expects is not None:
            for index, written in enumerate(expects):
                resolved = vocabulary.resolve(str(written), kinds, what="kind")
                if resolved.value != str(written):
                    repairs.append(f"{written!r} -> {resolved.value!r}")
                    expects[index] = resolved.value
        for cue in segment.get("cues") or []:
            written = cue.get("action")
            if written is None:
                continue
            resolved = vocabulary.resolve(
                str(written), vocabulary.KNOWN_ACTIONS, what="action"
            )
            if resolved.value != str(written):
                repairs.append(f"{written!r} -> {resolved.value!r}")
                cue["action"] = resolved.value

    if repairs:
        with where_from.open("w", encoding="utf-8") as handle:
            yaml.dump(doc, handle)
    return tuple(repairs)
```

- [ ] **Step 4: Wire the subcommand**

In `wing_parser/cli/__main__.py`, after the `feedback` parser:

```python
    node = sub.add_parser("showcontext", help="work with a show-context file")
    inner = node.add_subparsers(dest="showcontext_command", required=True)
    lint = inner.add_parser("lint", help="check a show-context file on its own")
    lint.add_argument("file")
    lint.add_argument("--fix", action="store_true",
                      help="write the repairs back into the file")
    lint.set_defaults(handler=commands.showcontext_lint)
```

In `wing_parser/cli/commands.py`:

```python
def showcontext_lint(args) -> int:
    from wing_parser.showcontext import load_show_context
    from wing_parser.showcontext.rewrite import apply_repairs

    try:
        context = load_show_context(args.file)
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for note in context.anomalies:
        print(note)
    if args.fix:
        for repair in apply_repairs(args.file):
            print(f"fixed: {repair}")
    elif context.anomalies:
        print("run again with --fix to write these into the file")
    if not context.anomalies:
        print(f"{args.file}: {len(context.segments)} segments, nothing to repair")
    return 0
```

- [ ] **Step 5: Run the lint tests, then the suite**

Run: `python -m pytest tests/test_showcontext_lint.py -q`
Expected: pass.

Run: `python -m pytest tests/ -q --junitxml=junit.xml`
Expected: exit 0.

- [ ] **Step 6: Commit**

```bash
git add wing_parser/showcontext/rewrite.py wing_parser/cli/ tests/test_showcontext_lint.py
git commit -F - <<'EOF'
Add showcontext lint, with --fix writing through ruamel

Round-trip rather than dump: the file is hand-written and carries the
author's comments and ordering. Without --fix nothing is written.
EOF
```

---

### Task 10: The real-file contract and the README

**Files:**
- Create: `tests/data/example-Vu-show.yaml`, `tests/test_showcontext_realfile.py`
- Modify: `README.md`
- Test: as above

**Interfaces:**
- Consumes: everything
- Produces: a pinned contract for the sample scene plus a show context

- [ ] **Step 1: Write the show context and the contract test**

Create `tests/data/example-Vu-show.yaml`. Every channel number below must be
**read off the file first** — run
`python -m wing_parser.cli analyze user-files/example-Vu.snap` and use its
listing. Do not copy numbers from this plan without checking them:

```yaml
# A show context for user-files/example-Vu.snap, written by hand to pin
# the contract. Channel numbers verified against `wing analyze` output.
show: "example-Vu contract fixture"
segments:
  - id: S1
    title: "MC welcome"
    expects: [speech.mc]
    cues:
      - id: "SQ 1"
        action: open
        channels: [8]
  - id: S2
    title: "Band set"
    expects: [instrument.keys, instrument.horns]
    cues:
      - id: "SQ 2"
        action: open
        # 99 is absent (the file stops at 40) -> Q1. 31 exists but carries
        # no name -> Q2. Q2 has no other end-to-end test in the suite, and
        # render() leaves a bad {path} token visible instead of raising, so
        # without this row a typo in Q2's message would reach a show
        # unnoticed. Verify 31 is still blank-named before pinning.
        channels: [25, 29, 31, 99]
      - id: "SQ 3"
        action: open
        channels: [29]
```

```python
# tests/test_showcontext_realfile.py
"""The show-context contract on the real sample file.

Regenerate with:
python - <<'EOF'
import os; os.environ["WING_DISABLE_LLM"] = "1"
from wing_parser import WingScene
scene = WingScene.load("user-files/example-Vu.snap",
                       show="tests/data/example-Vu-show.yaml")
for f in sorted((f for f in scene.advisory.run() if f.rule_id.startswith("Q")),
                key=lambda f: (f.rule_id, f.target)):
    print(f'    ("{f.rule_id}", "{f.target}", "{f.severity}"),')
EOF
"""
import pytest

from wing_parser import WingScene

SHOW = "tests/data/example-Vu-show.yaml"

EXPECTED_Q = [
    # Fill from the regeneration command above, then justify each row
    # here with the evidence, the way tests/test_advisory_realfile.py
    # does. Channel 99 does not exist -> Q1 on SQ 2. Channel 31 exists
    # with a blank name -> Q2 on SQ 2. Channel 29 is opened twice -> Q6
    # on SQ 3. instrument.horns has no channel -> Q4 on S2.
    # instrument.keys exists but is parked -> Q5 on S2.
    #
    # Assert on the rendered message of at least one row, not only on
    # (rule_id, target, severity): render() leaves an unresolvable
    # {dotted.path} visible rather than raising, so a mistyped message
    # path produces a finding nobody's test catches.
]


def test_the_show_context_contract(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    scene = WingScene.load(vu_path, show=SHOW)
    got = sorted((f.rule_id, f.target, f.severity)
                 for f in scene.advisory.run() if f.rule_id.startswith("Q"))
    assert got == sorted(EXPECTED_Q)


def test_the_same_scene_without_context_yields_no_q_findings(vu_path, monkeypatch):
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    found = WingScene.load(vu_path).advisory.run()
    assert not [f for f in found if f.rule_id.startswith("Q")]
    assert len(found) == 22
```

- [ ] **Step 2: Run the regeneration command and fill `EXPECTED_Q`**

Run the command in the docstring. Paste its output into `EXPECTED_Q`. Then, for
each row, verify the claim against the raw file or `wing analyze` and write the
evidence as a comment — a row nobody checked is a row that pins a bug.

- [ ] **Step 3: Run the contract test**

Run: `python -m pytest tests/test_showcontext_realfile.py -q`
Expected: pass.

- [ ] **Step 4: Document it in the README**

Add a `### Show context` subsection after the profile documentation. Derive the
rule inventory live — do not count by hand:

```bash
python -c "from wing_parser.advisory.loader import load_base_rules; rules=load_base_rules(); print(len(rules)); print(sorted(r.id for r in rules))"
```

The README currently says "`doctor` ships 32 base rules across eight files"
(README.md:196). Update both numbers from that command's output, add Q1–Q7 to
the rule table with their severities and file, and document `--show`,
`showcontext lint --fix`, and the show-context file format with the same worked
example the spec uses.

- [ ] **Step 5: Run the whole suite one final time**

Run: `python -m pytest tests/ -q --junitxml=junit.xml`
Expected: exit 0, `failures="0" errors="0" skipped="1"`.

- [ ] **Step 6: Commit**

```bash
git add tests/ README.md
git commit -F - <<'EOF'
Pin the show-context contract and document it

The paired test is the point: the same scene with the context yields
the Q findings, without it yields none and still totals 22. Rule counts
in the README derived with load_base_rules(), not counted by hand --
the controller got that wrong last cycle by one order of tedium.
EOF
```

---

## Self-Review

**Spec coverage.** §1 scope → Tasks 1–10 are G1 only; G2 is untouched, as
designed. §2's three failure families → Q1/Q2/Q3 (Task 5), Q4/Q5 (Task 6),
Q6/Q7 (Task 7). §3 format → Task 2. §3.1 typo tiers → Task 1, with the
`--fix` half in Task 9. §4 plumbing → Task 4. §5 counts → Task 3. §6 rules →
Tasks 5–7. §7 CLI and error handling → Tasks 8 and 9. §9 testing, including the
invariance test and the minimum-distance guard → Tasks 1, 4 and 10. §8 (G2) is
deliberately unimplemented. §10 and §11 need no tasks.

**Placeholders.** One deliberate blank remains: `EXPECTED_Q` in Task 10, which
cannot be written in advance because it must be generated from a live run and
then justified row by row. Task 10 steps 1–2 spell out how to fill it and
require evidence per row. Everywhere else, code is given in full.

**Type consistency.** `Resolution(value, original, repaired)` is produced in
Task 1 and consumed in Tasks 2 and 9 under those names. `load_show_context`
returns `ShowContext` in Task 2 and is called that way in Tasks 4 and 9.
`view.build(context, scene) -> tuple[SegmentView, ...]` in Task 3 matches
`scene.show_segments()` in Task 4. Every property named in a rule's `where`
block in Tasks 5–7 (`missing_channel_count`, `unnamed_channel_count`,
`missing_dca_count`, `unmet_expect_count`, `dark_expect_count`,
`contradiction_count`, `seconds_after_previous`) is defined in Task 3, as is
every `*_text` twin used in a message. `_parse_time` is defined in Task 2's
loader and imported by Task 3's view.

**Fixed during the pre-flight scan.** The first draft had Task 5 assert all
seven Q ids, which would have left that test red until Task 7 — a broken gate,
not a pending one, and it would have failed Task 5's and Task 6's reviews for a
defect neither task could fix. Task 5 now asserts `{"Q1","Q2","Q3"} <= ids`;
the exact-set assertion is Task 7's. Every task's suite is green at its own
commit.
