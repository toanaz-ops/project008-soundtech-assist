# GUI wave 4 — better cue-sheet import — implementation plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `superpowers:subagent-driven-development` (recommended)
> or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** A real cue sheet (a corporate rundown or a concert running order) comes out of the Import wizard
with most performer cells read through an editable, AI-assisted vocabulary of sets and terms; the wizard
gains a scene cross-check step, and the app gains an in-app vocabulary editor, an AI assistant that
proposes changes for approval, a lint surface for existing show-context files, and an AI diagnosis surface
on the Mapping step. Everything is reachable from buttons in `wing-ui` — nothing new is CLI-only.

**Architecture:** Two non-Qt modules carry the new matching logic — `showcontext/ingest/keywords.py` (fold
+ whole-word match, no I/O) and `classifier/vocabulary.py` (defaults + his edits + tombstones + nested-set
expansion, reading/writing through `cache.py`'s existing atomic write). `build.resolve_fragment` composes
them with the existing pattern matcher. A new `classifier/vocab_changes.py` validates the AI assistant's
proposed edits before anything is written. A new `classifier/provider_errors.py` gives every provider-call
surface (Settings, Try AI, the assistant) one shared failure vocabulary. On top: a Vocabulary window (Sets
+ Terms tabs + an Assistant tab), a redesigned Terms step, a new Scene-cross-check step, a lint dialog off
the Pick step, and a Try-AI panel on the Mapping step.

**Tech Stack:** Python 3.12+, PySide6, pytest (`QT_QPA_PLATFORM=offscreen`), ruamel.yaml, PyInstaller.
**Spec:** `docs/superpowers/specs/2026-09-26-gui-import-wave4-design.md` — F1–F14 and W1–W6 in §2, data and
matching §3, Terms step §4, scene cross-check §5, lint §6, AI diagnosis §7, Vocabulary window + assistant
§8, tests §9, task sketch §10, out of scope §11, the defaults draft §A. Every "why" below points at a
section there rather than repeating it.

## How to start (branching)

Cut the branch from `main` (the design-spec docs already landed there via PR #10, `1b60da5` is `HEAD`
per this worktree's `feat/gui-import-wave4` branch): `git worktree add <path> -b feat/gui-import-wave4 main`
if not already checked out — this worktree already has it checked out; skip the `git worktree add` if you
are continuing in it. Open the PR with base `main` and paste Task 1's measured baseline into the body.

## Global Constraints

Every task's requirements implicitly include this section.

- Every `wing_parser/ui/*.py` file ≤ 200 lines; split before exceeding (`tests/test_ui_house_style.py:173`,
  `CEILING = 200`, enforces this).
- Every UI change has a Qt test that builds the real `MainWindow` (or the real page/dialog it changes) and
  drives the buttons; Qt tests use `timeout=2` where a `CallRunner`/`ButtonRunner` is involved (pass
  `timeout=0` through the runner in tests, per the existing pattern in `tests/test_ui_settings.py` and
  `tests/test_ui_import_page.py` — never wait a real network timeout).
- **Full-suite tally is read from `--junitxml`, not the terminal summary.** Run from the worktree root with
  `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`
  and read `tests=`, `failures=`, `errors=`, `skipped=` off the `<testsuite>` element — Qt teardown can eat
  the terminal's own `N passed` line. Before trusting the venv, verify it imports THIS worktree:
  `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -c "import wing_parser; print(wing_parser.__file__)"`
  must print a path inside this worktree, not the main checkout — the shared venv's editable install
  points at whichever checkout last ran `pip install -e`. If it prints the main checkout's path, run
  `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pip install -e ".[ui,ingest,llm,llm-openai]"`
  from this worktree's root before Task 1.
- No hex colours outside `wing_parser/ui/theme/`; every user-facing string goes through `text("...")`
  defined in `texts.py` or a `texts_*.py` merged into it — a new `texts_import.py` is fine and is what this
  wave uses for every new string (W1: English, like every existing string).
- UTF-8 explicitly on every file read and write (`encoding="utf-8"`).
- No API key in code, tests, fixtures or logs; every AI-surface test uses a fake provider — never a real
  SDK, never a real network call.
- Nothing in this wave writes to a live console; no file this wave touches imports `wing_parser.net.write`
  or `wing_parser.ui.live_write`, and `tests/test_ui_live_is_read_only.py`'s allow-list stays exactly
  `{"live_write.py"}` — unchanged by this wave.
- `git add` with explicit paths only; one commit per task minimum; commit messages end with
  `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Implementers are sonnet subagents; each task is self-contained below — it repeats the context it needs
  rather than saying "same as task N".
- A folded key is produced by exactly one function, `keywords.fold` (Task 1) — nowhere else in this wave
  reimplements diacritic stripping or whole-word matching.

## Sequencing

**1** has no dependency. **2** depends on 1 (`vocabulary.py` imports `keywords.Term`/`keywords.fold`).
**3** depends on 2 (`build.resolve_fragment` takes a `Vocabulary`-shaped object). **4** is independent of
1–3 and may run in parallel with them. **5** depends on 2 (reads/writes through `vocabulary.py`) and on 4
(the Assistant tab's failure line, added in 6, needs `provider_errors.py` to exist first — 5 itself does
not call a provider, only 6 does). **6** depends on 2, 4 and 5 (the Assistant tab is added inside the
window 5 built). **7** depends on 2, 3 and 6 (Terms step's "AI: propose" button calls into 6's flow). **8**
depends on 3 (needs `Resolution`-shaped segments) and is otherwise independent of 5–7. **9**'s lint half
depends on nothing new (`load_show_context`/`apply_repairs` already exist); its Try-AI half depends on 4.
**10** is last, after everything above merges to `main`.

**Files this wave creates:** `showcontext/ingest/keywords.py` (no Qt) · `classifier/vocabulary.py` (no Qt)
· `classifier/data/cuesheet_defaults.yaml` · `classifier/provider_errors.py` (no Qt) ·
`classifier/vocab_changes.py` (no Qt) · `ui/texts_import.py` (no Qt) · `ui/vocabulary_window.py` ·
`ui/vocabulary_sets_tab.py` · `ui/vocabulary_terms_tab.py` · `ui/vocabulary_set_dialog.py` ·
`ui/vocabulary_term_dialog.py` · `ui/vocabulary_assistant.py` · `ui/terms_row.py` · `ui/scene_step.py` ·
`ui/lint_dialog.py` · `ui/mapping_try_ai.py` · one test file per module above, plus the acceptance and
contract-test edits named in Task 3.

---

### Task 1: `keywords.py` — fold and whole-word match, pure

**Files:**
- Create: `wing_parser/showcontext/ingest/keywords.py`, `tests/test_keywords.py`

Read `wing_parser/classifier/normalize.py` (the existing, shallower `clean()` — casefold and whitespace
only, no diacritic stripping, used by the "channels"/"buses" domains and untouched by this wave) before
writing anything, so the new `fold()` is not confused with it. `keywords.fold` is only for the cuesheet
domain (§3.4).

**Interfaces:**
- Consumes: nothing.
- Produces:
  ```python
  # wing_parser/showcontext/ingest/keywords.py
  @dataclass(frozen=True)
  class Term:
      key: str                  # the term's own text, NOT pre-folded
      kinds: tuple[str, ...]
      ignored: bool
      match: str                # "exact" | "word"

  @dataclass(frozen=True)
  class Resolution:
      kinds: tuple[str, ...]
      ignored: bool

  def fold(text: str) -> str: ...
  def match(text: str, terms: Sequence[Term]) -> Resolution: ...
  ```
  Task 2's `vocabulary.Vocabulary.effective()` returns `tuple[Term, ...]` (sets already expanded into
  `kinds`); Task 3's `build.resolve_fragment(fragment, vocabulary)` calls `keywords.match(fragment,
  vocabulary.effective())` and falls through to the pattern matcher when it returns an empty, non-ignored
  `Resolution`.

- [ ] **Step 1: Write the failing tests** — `tests/test_keywords.py`

```python
"""Spec §3.4-3.5: diacritic-folded whole-word matching, no I/O.

fold() is the ONE place this wave strips a Vietnamese tone mark -- every
other module that needs a folded key calls this, never reimplements it
(Global Constraints). match() is steps 1-2 of the lookup order (S3.3):
whole-fragment equality for match="exact" terms, then whole-word
substring scanning for match="word" terms, with longest-wins containment
and ignore-only-when-nothing-else-matched (S3.5).
"""
from __future__ import annotations

from wing_parser.showcontext.ingest.keywords import Resolution, Term, fold, match

# -- fold -----------------------------------------------------------------


def test_fold_casefolds_and_collapses_whitespace():
    assert fold("  Ca Sĩ   Nữ  ") == "ca si nu"


def test_fold_strips_tone_marks_but_keeps_the_base_letter():
    assert fold("phát biểu") == "phat bieu"


def test_fold_turns_d_stroke_into_a_plain_d_after_casefold():
    assert fold("BLĐ") == fold("Bld") == fold("bld") == "bld"


def test_fold_turns_punctuation_into_a_single_space():
    assert fold("check-in, mời!") == "check in moi"


def test_fold_of_empty_or_none_is_empty():
    assert fold("") == ""
    assert fold(None) == ""


# -- match: exact ----------------------------------------------------------


def test_an_exact_term_must_equal_the_whole_fragment():
    terms = (Term(key="MC", kinds=("speech.mc",), ignored=False, match="exact"),)
    assert match("MC", terms) == Resolution(("speech.mc",), False)
    assert match("Mời MC", terms) == Resolution((), False)


# -- match: word, single hit -------------------------------------------------


def test_a_word_term_matches_as_a_whole_word_inside_a_longer_fragment():
    terms = (Term(key="trống", kinds=("drums.kick",), ignored=False, match="word"),)
    assert match("Mời trống lên sân khấu", terms) == Resolution(("drums.kick",), False)


def test_a_word_term_does_not_match_inside_a_longer_word():
    terms = (Term(key="band", kinds=("instrument.guitar",), ignored=False, match="word"),)
    assert match("bandana", terms) == Resolution((), False)


def test_a_multi_word_phrase_key_matches_as_one_bounded_phrase():
    terms = (Term(key="lên sân khấu", kinds=("utility.playback",), ignored=False,
                  match="word"),)
    assert match("Mời BLĐ lên sân khấu quay số", terms) == Resolution(
        ("utility.playback",), False)


# -- match: word, several hits in one cell (S3.5) ---------------------------


def test_several_word_terms_in_one_fragment_union_their_kinds_first_seen():
    terms = (
        Term(key="BLĐ", kinds=("speech.handheld",), ignored=False, match="word"),
        Term(key="lên sân khấu", kinds=("utility.playback",), ignored=False, match="word"),
        Term(key="quay số", kinds=("speech.mc", "utility.playback"), ignored=False,
             match="word"),
    )
    result = match("Mời BLĐ lên sân khấu quay số", terms)
    assert result.kinds == ("speech.handheld", "utility.playback", "speech.mc")
    assert result.ignored is False


def test_a_shorter_hit_wholly_inside_a_longer_hit_is_dropped():
    """'trống' loses to 'dàn trống' when both match the same fragment."""
    terms = (
        Term(key="trống", kinds=("drums.kick",), ignored=False, match="word"),
        Term(key="dàn trống", kinds=("drums.overhead",), ignored=False, match="word"),
    )
    assert match("dàn trống điện tử", terms) == Resolution(("drums.overhead",), False)


# -- ignore (F5, S3.5) -------------------------------------------------------


def test_ignore_wins_only_when_nothing_else_matched():
    terms = (Term(key="hoa tươi", kinds=(), ignored=True, match="word"),)
    assert match("tặng hoa tươi", terms) == Resolution((), True)


def test_a_non_ignore_hit_beats_an_ignore_hit_in_the_same_fragment():
    terms = (
        Term(key="hoa tươi", kinds=(), ignored=True, match="word"),
        Term(key="trao giải", kinds=("speech.mc",), ignored=False, match="word"),
    )
    result = match("trao giải và tặng hoa tươi", terms)
    assert result.kinds == ("speech.mc",) and result.ignored is False


def test_no_term_matches_at_all_is_an_empty_non_ignored_resolution():
    assert match("tốp múa", ()) == Resolution((), False)


def test_an_empty_fragment_matches_nothing():
    assert match("   ", (Term(key="x", kinds=("a",), ignored=False, match="word"),)
                 ) == Resolution((), False)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_keywords.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.showcontext.ingest.keywords'`

- [ ] **Step 3: Write the minimal implementation** — `wing_parser/showcontext/ingest/keywords.py`

```python
"""Fold Vietnamese text and match it against a closed set of terms.

Spec §3.4-3.5. `fold()` is the ONE diacritic-stripping function this wave
uses -- `classifier/normalize.py:clean()` is a shallower, pre-existing
function (casefold + whitespace only) used by the "channels"/"buses"
domains and left untouched; conflating the two would silently change how
console-strip names classify.

`match()` implements steps 1-2 of the lookup order (design spec S3.3):
whole-fragment equality against `match="exact"` terms, then whole-word
substring scanning against `match="word"` terms. Step 3 (patterns.yaml)
and step 4 (give up) are `build.resolve_fragment`'s job, not this
module's -- this file does no I/O and knows nothing about a console
strip or a scene.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass

_PUNCTUATION = re.compile(r"[^\w\s]", re.UNICODE)
_WHITESPACE = re.compile(r"\s+")


@dataclass(frozen=True)
class Term:
    """One resolved vocabulary entry. `key` is kept as originally typed
    (not folded) so a caller can still show it; every comparison folds
    both sides through `fold()` at match time."""

    key: str
    kinds: tuple[str, ...]
    ignored: bool
    match: str  # "exact" | "word"


@dataclass(frozen=True)
class Resolution:
    kinds: tuple[str, ...]
    ignored: bool


def fold(text: str) -> str:
    """NFC -> casefold -> strip combining marks -> đ/Đ -> d -> punctuation
    to space -> collapse whitespace (design spec S3.4).

    Casefold runs BEFORE the NFD decomposition that exposes combining
    marks, so "BLĐ" and "bld" both end up "bld": casefold already lowers
    "Đ" to "đ", and "đ" (U+0111) has no NFD decomposition of its own --
    it is a distinct Latin letter, not a base letter plus a combining
    stroke -- which is why it needs its own explicit replace after the
    generic combining-mark strip removes tone marks.
    """
    if not text:
        return ""
    normalised = unicodedata.normalize("NFC", text)
    cased = normalised.casefold()
    decomposed = unicodedata.normalize("NFD", cased)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    recomposed = unicodedata.normalize("NFC", stripped).replace("\u0111", "d")
    despaced = _PUNCTUATION.sub(" ", recomposed)
    return _WHITESPACE.sub(" ", despaced).strip()


def _contains_word(haystack: str, needle: str) -> bool:
    """Is folded `needle` a whole-word (or whole-phrase) hit in `haystack`?

    Both are already folded by the caller. `re.escape` keeps a
    multi-word needle's internal space literal, and the look-around
    bounds match a single word OR a phrase without over-matching inside
    a longer word ("band" must not hit "bandana", spec S3.4).
    """
    if not needle:
        return False
    pattern = r"(?<!\w)" + re.escape(needle) + r"(?!\w)"
    return re.search(pattern, haystack) is not None


def match(text: str, terms: Sequence[Term]) -> Resolution:
    """Steps 1-2 of the lookup order (S3.3). Empty, non-ignored when
    neither step hits -- the caller tries patterns.yaml next."""
    folded_text = fold(text)
    if not folded_text:
        return Resolution((), False)

    for term in terms:
        if term.match == "exact" and fold(term.key) == folded_text:
            return Resolution(term.kinds, term.ignored)

    word_hits = [
        term for term in terms
        if term.match == "word" and _contains_word(folded_text, fold(term.key))
    ]
    if not word_hits:
        return Resolution((), False)

    # Longest-wins containment (S3.5): drop a hit whose folded key is a
    # proper substring of a longer hit's folded key.
    kept = []
    for term in word_hits:
        folded_key = fold(term.key)
        if any(
            folded_key != fold(other.key) and folded_key in fold(other.key)
            for other in word_hits
        ):
            continue
        kept.append(term)

    kinds: list[str] = []
    any_non_ignore = False
    for term in kept:
        if term.ignored:
            continue
        any_non_ignore = True
        for kind in term.kinds:
            if kind not in kinds:
                kinds.append(kind)

    if any_non_ignore:
        return Resolution(tuple(kinds), False)
    if kept:
        return Resolution((), True)  # ignore wins only when nothing else matched
    return Resolution((), False)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_keywords.py -v`
Expected: PASS, all 15 tests.

- [ ] **Step 5: Show the trickiest test red once** — temporarily change the containment check's `in`
      to `==` (so nothing is ever dropped as contained) and confirm
      `test_a_shorter_hit_wholly_inside_a_longer_hit_is_dropped` fails with both kinds present; restore.
      Paste the failure into the task report.

- [ ] **Step 6: Run the full suite once, for the baseline**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`
Read `tests=`/`failures=`/`errors=`/`skipped=` off `dist-reports/suite.xml`'s `<testsuite>` element and
paste them into the task report and the PR body — this is the wave's baseline.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/showcontext/ingest/keywords.py tests/test_keywords.py && git commit -m "$(cat <<'EOF'
feat(ingest): add keywords.fold/match for the cuesheet vocabulary

Spec S3.4-3.5: diacritic-folded whole-word matching, no I/O. Task 2's
vocabulary.py will expand sets into Term.kinds and hand this module a
flat tuple to match against.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** that `classifier/normalize.py:clean()` really does NOT strip diacritics
(confirms `keywords.fold` is a genuinely new function, not a duplicate); that no other file in this repo
already defines a Vietnamese diacritic-fold (`grep -rn "unicodedata" wing_parser/` before this task should
show nothing under `showcontext/` or `classifier/`).

---

### Task 2: `cache.py`'s new domain, `vocabulary.py`, and the shipped defaults

**Files:**
- Modify: `wing_parser/classifier/cache.py` (159 lines)
- Create: `wing_parser/classifier/vocabulary.py`, `wing_parser/classifier/data/cuesheet_defaults.yaml`,
  `tests/test_classifier_vocabulary.py`

Read `wing_parser/classifier/cache.py` in full first — `DOMAINS`, `_SEED`, `_read`/`_write` (the atomic
round-trip this task's writes reuse), `_one`/`load` (the Classification-shaped parsing this task must not
break for the existing "channels"/"buses" domains, and must not choke on for "cuesheet"'s NEW entry shape).

**Why `cache.load()` needs a small fix, not just a new domain.** `cache.load()` iterates every domain and
calls `_one(domain, key, entry, path)` on every entry, which raises `ValueError` unless the entry has both
`kind:` and `confidence:`. A wave-4 term (`{kinds: [...], match: word, origin: default}`) has neither key.
The CLI wizard's `guess.offer_terms` → `cache.remember(term, "cuesheet", classification)` keeps writing the
OLD single-`kind`+`confidence` shape forever (out of scope for this wave, §11) — so the `cuesheet` domain
holds a **permanent mix** of old- and new-shape entries, and `cache.load()` is called elsewhere (anything
that calls `cache.lookup(name, "channels", ...)` calls `load()` internally, parsing ALL domains as a side
effect) — so the day a single new-shape term is written, every caller of `cache.load()` for ANY domain
would start raising. Task 2 fixes this by having `load()` skip (not error on) an entry lacking `kind:`/
`confidence:` **only** for the `cuesheet` domain, and skip **all** `cuesheet_sets` entries from its
Classification view (they never have that shape) — `channels`/`buses` keep their existing strict behaviour
unchanged, so a malformed entry there still raises exactly as before.

**Interfaces:**
- Consumes: `wing_parser.showcontext.ingest.keywords.Term`/`.fold` (Task 1);
  `wing_parser.classifier.matcher.known_kinds("channels")` (existing).
- Produces:
  ```python
  # wing_parser/classifier/cache.py — additions
  DOMAINS = ("channels", "buses", "cuesheet", "cuesheet_sets")   # was 3, now 4

  def read_raw(directory: Path | None = None) -> Any: ...   # the live ruamel doc, unfiltered
  def write_raw(doc: Any, directory: Path | None = None) -> None: ...

  # wing_parser/classifier/vocabulary.py
  @dataclass(frozen=True)
  class SetEntry:
      key: str; label: str; kinds: tuple[str, ...] = (); sets: tuple[str, ...] = ()
      origin: str = "default"; shadows_default: bool = False; deleted: bool = False
      @property
      def display_origin(self) -> str: ...   # "default, edited" when shadows_default and origin != "default"

  @dataclass(frozen=True)
  class TermEntry:
      key: str; kinds: tuple[str, ...] = (); sets: tuple[str, ...] = (); ignore: bool = False
      match: str = "word"; origin: str = "default"; shadows_default: bool = False
      deleted: bool = False
      @property
      def display_origin(self) -> str: ...

  class UnknownKindError(ValueError): ...
  class UnknownSetError(ValueError): ...
  class CycleError(ValueError):
      def __init__(self, path: tuple[str, ...]): ...   # .path

  class Vocabulary:
      @classmethod
      def load(cls, directory: Path | None = None) -> "Vocabulary": ...
      def sets(self) -> tuple[SetEntry, ...]: ...          # visible (non-deleted), sorted by key
      def terms(self) -> tuple[TermEntry, ...]: ...
      def expand_set(self, key: str) -> tuple[str, ...]: ...     # recursive, depth-first, first-seen, deduped
      def effective(self) -> tuple[keywords.Term, ...]: ...      # every visible term, sets expanded
      def put_set(self, key, *, label, kinds=(), sets=(), origin="manual") -> None: ...
      def put_term(self, key, *, kinds=(), sets=(), ignore=False, match="word", origin="manual") -> None: ...
      def delete_set(self, key: str) -> None: ...
      def delete_term(self, key: str) -> None: ...
      def reset_set(self, key: str) -> None: ...
      def reset_term(self, key: str) -> None: ...
  ```
  Task 3's `build.resolve_fragment(fragment, vocabulary)` calls `vocabulary.effective()`. Task 5's
  Vocabulary window calls `sets()`/`terms()`/`put_*`/`delete_*`/`reset_*` directly. Task 6's
  `vocab_changes.validate` calls `put_set`'s/`put_term`'s own validation helpers indirectly by checking
  against the same `known_kinds`/`sets()` before ever calling `put_*`.

- [ ] **Step 1: Write the failing tests for `cache.py`'s fix** — append to `tests/test_classifier_cache.py`
      (read that file's existing fixtures — a `directory` tmp_path fixture already exists there; reuse it,
      do not invent a second one)

```python
def test_domains_now_include_cuesheet_sets(directory):
    from wing_parser.classifier import cache

    assert cache.DOMAINS == ("channels", "buses", "cuesheet", "cuesheet_sets")
    loaded = cache.load(directory)
    assert loaded["cuesheet_sets"] == {}


def test_load_does_not_choke_on_a_wave_4_shaped_cuesheet_term(directory):
    """A term with `kinds:`/`match:` and no `confidence:` must not raise --
    it is invisible to load()'s Classification view, not an error."""
    from wing_parser.classifier import cache

    doc = cache.read_raw(directory)
    doc["cuesheet"]["trống"] = {"kinds": ["drums.kick"], "match": "word", "origin": "default"}
    cache.write_raw(doc, directory)

    loaded = cache.load(directory)  # must not raise
    assert "trống" not in loaded["cuesheet"]


def test_load_still_raises_on_a_malformed_channels_entry(directory):
    """Unchanged strictness for the two original domains."""
    import pytest
    from wing_parser.classifier import cache

    doc = cache.read_raw(directory)
    doc["channels"]["broken strip"] = {"kind": "instrument.guitar"}  # no confidence:
    cache.write_raw(doc, directory)

    with pytest.raises(ValueError, match="missing required key 'confidence'"):
        cache.load(directory)


def test_load_still_reads_an_old_shape_cuesheet_entry_as_classification(directory):
    """The CLI wizard's guess.offer_terms keeps writing this shape forever
    (out of scope, spec §11) -- load() must keep seeing it."""
    from wing_parser.classifier import cache
    from wing_parser.classifier.matcher import Classification

    cache.remember("ca sĩ nữ", "cuesheet",
                   Classification(kind="speech.vocal", confidence=0.9, origin="g2b-assisted"),
                   directory=directory)
    loaded = cache.load(directory)
    assert loaded["cuesheet"]["ca sĩ nữ"].kind == "speech.vocal"


def test_read_raw_and_write_raw_round_trip_a_cuesheet_sets_entry(directory):
    from wing_parser.classifier import cache

    doc = cache.read_raw(directory)
    doc["cuesheet_sets"]["drum kit"] = {
        "label": "Drum kit", "kinds": ["drums.kick.in", "drums.tom"], "origin": "manual",
    }
    cache.write_raw(doc, directory)

    reloaded = cache.read_raw(directory)
    assert reloaded["cuesheet_sets"]["drum kit"]["label"] == "Drum kit"
```

- [ ] **Step 2: Run the tests to verify they fail**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_classifier_cache.py -k "cuesheet_sets or wave_4 or old_shape or malformed_channels" -v`
Expected: FAIL — `AssertionError` on `DOMAINS` (still 3-tuple), `AttributeError: module 'wing_parser.classifier.cache' has no attribute 'read_raw'`.

- [ ] **Step 3: Fix `cache.py`** — three surgical edits, nothing else in the file changes

Change the `DOMAINS` line and `_SEED`:

```python
DOMAINS = ("channels", "buses", "cuesheet", "cuesheet_sets")

_SEED = """\
# Cached and manually declared classifications.
#
# Keys are normalized names (trimmed, whitespace-collapsed, casefolded).
# Anything written here is read before the pattern matcher runs, so a
# manual entry always wins and a name only ever costs one classification
# in its lifetime.
#
# Comments you add here survive every rewrite -- annotate freely.
#
# origin: manual | llm | pattern | cache
channels: {}
buses: {}
# cuesheet: terms as they appear on a printed running order, in any
# language, mapped to the same kinds the channels domain uses. A cue
# sheet and a console strip are different naming domains -- nobody
# labels a strip "ca si nu", and no director writes "HS4" -- so a term
# lives here and not in channels.
#
# Two shapes coexist here on purpose (wave 4): the CLI wizard's assisted
# guessing still writes {kind, confidence, origin}; the Vocabulary window
# and its AI assistant write {kinds/sets/ignore, match, origin} -- see
# classifier/vocabulary.py. cache.load() only ever parses the first shape.
cuesheet: {}
# cuesheet_sets: named bundles of kinds a term can point at ("Drum kit"),
# editable from the same Vocabulary window. classifier/vocabulary.py owns
# this domain entirely; cache.load() never parses it.
cuesheet_sets: {}
"""
```

Change `load()` to skip non-Classification-shaped entries for `cuesheet`/`cuesheet_sets` only:

```python
_STRICT_DOMAINS = ("channels", "buses")


def load(directory: Path | None = None) -> dict[str, dict[str, Classification]]:
    doc = _read(directory)
    path = _path(directory)
    result: dict[str, dict[str, Classification]] = {}
    for domain in DOMAINS:
        raw = doc.get(domain) or {}
        if domain in _STRICT_DOMAINS:
            result[domain] = {key: _one(domain, key, entry, path) for key, entry in raw.items()}
        else:
            # cuesheet's pre-wave-4 entries ({kind, confidence, ...}) still
            # parse as Classification; a wave-4 term/set entry has neither
            # key and belongs to vocabulary.py, not this view (cache.py
            # docstring above _SEED).
            result[domain] = {
                key: _one(domain, key, entry, path)
                for key, entry in raw.items()
                if "kind" in entry and "confidence" in entry
            }
    return result
```

Add the two raw-access functions at the end of the file:

```python
def read_raw(directory: Path | None = None) -> Any:
    """The live document, unfiltered -- vocabulary.py's own domains
    (`cuesheet`, `cuesheet_sets`) carry a richer shape than `_one()` can
    parse, so it reads and writes through this pair instead of `load()`/
    `remember()`. Mutate the result and pass it to `write_raw` to keep
    every hand-added comment in classifier.yaml (same contract as `_read`/
    `_write`, just under a name another module in this package may call)."""
    return _read(directory)


def write_raw(doc: Any, directory: Path | None = None) -> None:
    _write(doc, directory)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_classifier_cache.py -v`
Expected: PASS, including every pre-existing test in that file (the strict-domain path is untouched).

- [ ] **Step 5: Commit the `cache.py` fix on its own**

```bash
git add wing_parser/classifier/cache.py tests/test_classifier_cache.py && git commit -m "$(cat <<'EOF'
feat(classifier): add cuesheet_sets domain; load() tolerates wave-4 shape

cache.load() previously raised on any cuesheet entry lacking kind:/
confidence:. A wave-4 term/set has neither -- load() now skips (does not
error on) that shape for cuesheet/cuesheet_sets only; channels/buses keep
their existing strict validation. New read_raw/write_raw give
vocabulary.py raw access to both domains through the same atomic write.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** that `_one()`'s two required-key check (`for required in ("kind",
"confidence")`) is unchanged (confirms the "channels"/"buses" strictness claim above); that `_read()`/
`_write()` are still the only two functions touching the temp-file-then-`os.replace` atomic write (`cache.py:90-108`)
— `read_raw`/`write_raw` must not duplicate that logic.

---

- [ ] **Step 6: Write the shipped defaults** — `wing_parser/classifier/data/cuesheet_defaults.yaml`

Transcribed from spec Appendix A (F14: ships as drafted, ToanAZ corrects afterwards in the Vocabulary
window). The set named "Speech, handheld" in the design table is given the folded-friendly key `handheld`
here — a set KEY containing a comma cannot be referenced inside a YAML flow list (`sets: [speech, handheld]`
would parse as two elements, not one) — its `label:` keeps the exact display text from the design table.

```yaml
# Shipped defaults for the cuesheet vocabulary (design spec 2026-09-26 §A).
# Never edited at runtime -- a person's own edits and tombstones live in
# classifier.yaml's cuesheet/cuesheet_sets domains (vocabulary.py merges
# the two). Concert rows are marked in the design doc as NOT checked
# against a real file (F4); ToanAZ corrects them in the Vocabulary window,
# not here (F14).

sets:
  drum kit:
    label: Drum kit
    kinds: [drums.kick.in, drums.kick.out, drums.snare.top, drums.snare.bottom,
            drums.tom, drums.hihat, drums.overhead]
  band:
    label: Band
    sets: [drum kit]
    kinds: [speech.vocal, instrument.guitar, instrument.bass, instrument.keys]
  handheld:
    label: "Speech, handheld"
    kinds: [speech.handheld]
  award moment:
    label: Award moment
    kinds: [speech.mc, utility.playback]

terms:
  # -- corporate (from the two real sheets ToanAZ dropped 2026-08-24) ----
  mc: {kinds: [speech.mc], match: word}
  dẫn chương trình: {kinds: [speech.mc], match: word}
  blđ: {sets: [handheld], match: word}
  ban lãnh đạo: {sets: [handheld], match: word}
  phát biểu: {kinds: [speech.lectern], match: word}
  đại diện: {sets: [handheld], match: word}
  khách mời: {sets: [handheld], match: word}
  giám đốc: {kinds: [speech.lectern], match: word}
  trao giải: {sets: [award moment], match: word}
  vinh danh: {sets: [award moment], match: word}
  quay số: {sets: [award moment], match: word}
  tặng kỉ niệm chương: {sets: [award moment], match: word}
  lên sân khấu: {kinds: [utility.playback], match: word}
  loto: {kinds: [speech.handheld, utility.playback], match: word}
  band nhạc: {sets: [band], match: word}
  nhạc nhẹ: {kinds: [utility.playback], match: word}
  hoa tươi: {ignore: true, match: word}
  huy chương: {ignore: true, match: word}
  chụp hình: {ignore: true, match: word}
  quay phim: {ignore: true, match: word}
  check in: {ignore: true, match: word}
  phòng ban: {ignore: true, match: word}
  tiết mục: {ignore: true, match: word}
  # -- concert (drafted, NOT checked against a real file -- F4) ----------
  ca sĩ: {kinds: [speech.vocal], match: word}
  vocal: {kinds: [speech.vocal], match: word}
  hát: {kinds: [speech.vocal], match: word}
  band: {sets: [band], match: word}
  trống: {sets: [drum kit], match: word}
  drum: {sets: [drum kit], match: word}
  dàn trống: {sets: [drum kit], match: word}
  guitar điện: {kinds: [instrument.guitar.electric], match: word}
  guitar thùng: {kinds: [instrument.guitar.acoustic], match: word}
  bass: {kinds: [instrument.bass], match: word}
  keyboard: {kinds: [instrument.keys], match: word}
  piano: {kinds: [instrument.keys], match: word}
  kèn: {kinds: [instrument.horns], match: word}
  violin: {kinds: [instrument.strings], match: word}
  backing track: {kinds: [utility.playback], match: word}
  beat: {kinds: [utility.playback], match: word}
  playback: {kinds: [utility.playback], match: word}
```

- [ ] **Step 7: Write the failing tests for `vocabulary.py`** — `tests/test_classifier_vocabulary.py`

```python
"""Spec §3.2-3.3: defaults + his edits + tombstones + nested sets.

Every fixture uses an isolated `directory` (tmp_path) so no test reads
or writes the real knowledge/ directory -- see conftest.py's session
autouse fixture, which already isolates config.knowledge_dir() but NOT
an explicit directory= argument, so tests here pass one explicitly.
"""
from __future__ import annotations

import pytest

from wing_parser.classifier import cache, vocabulary as vocab


@pytest.fixture
def directory(tmp_path):
    return tmp_path


# -- defaults load with no user file at all ---------------------------------


def test_the_shipped_defaults_load_with_an_empty_classifier_yaml(directory):
    v = vocab.Vocabulary.load(directory)
    keys = {s.key for s in v.sets()}
    assert "drum kit" in keys and "band" in keys
    terms = {t.key: t for t in v.terms()}
    assert terms["mc"].kinds == ("speech.mc",)
    assert terms["mc"].origin == "default"
    assert terms["mc"].match == "word"


def test_every_shipped_default_kind_is_one_patterns_yaml_can_produce(directory):
    from wing_parser.classifier.matcher import known_kinds

    known = set(known_kinds("channels"))
    v = vocab.Vocabulary.load(directory)
    for term in v.effective():
        for kind in term.kinds:
            assert kind in known, f"{term.key!r} names unknown kind {kind!r}"


# -- nested sets (F13) --------------------------------------------------------


def test_band_expands_to_its_own_kinds_plus_drum_kits_nested_ones(directory):
    v = vocab.Vocabulary.load(directory)
    expanded = v.expand_set("band")
    for kind in ("drums.kick.in", "drums.tom", "speech.vocal", "instrument.guitar"):
        assert kind in expanded


def test_editing_drum_kit_changes_what_band_expands_to(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_set("drum kit", label="Drum kit", kinds=("drums.pad",))
    reloaded = vocab.Vocabulary.load(directory)
    assert reloaded.expand_set("band") == ("drums.pad", "speech.vocal",
                                           "instrument.guitar", "instrument.bass",
                                           "instrument.keys")


def test_a_cycle_is_refused_at_write_naming_the_path(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_set("loop a", label="Loop A", sets=("band",))
    with pytest.raises(vocab.CycleError) as exc:
        v.put_set("band", label="Band", sets=("drum kit", "loop a"))
    assert "band" in str(exc.value) and "loop a" in str(exc.value)


def test_a_cycle_already_on_disk_expands_once_and_does_not_loop(directory):
    """Reached only by hand-editing classifier.yaml -- the loader must
    tolerate it, not crash every fragment behind it (design spec S3.2)."""
    doc = cache.read_raw(directory)
    doc.setdefault("cuesheet_sets", {})
    doc["cuesheet_sets"]["loop a"] = {"label": "Loop A", "sets": ["loop b"], "origin": "manual"}
    doc["cuesheet_sets"]["loop b"] = {"label": "Loop B", "sets": ["loop a"], "kinds": ["speech.mc"],
                                      "origin": "manual"}
    cache.write_raw(doc, directory)

    v = vocab.Vocabulary.load(directory)
    assert v.expand_set("loop a") == ("speech.mc",)  # terminates, no RecursionError


def test_a_term_pointing_at_a_deleted_set_resolves_to_its_remaining_kinds(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("solo term", kinds=("speech.lectern",), sets=("band",), match="word")
    v.delete_set("band")
    reloaded = vocab.Vocabulary.load(directory)
    effective = {t.key: t for t in reloaded.effective()}
    assert effective["solo term"].kinds == ("speech.lectern",)  # band's kinds are gone, not an error


# -- overrides and tombstones (S3.2) -----------------------------------------


def test_his_entry_replaces_a_default_with_the_same_folded_key(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("MC", kinds=("speech.lectern",), match="word")  # overrides the default "mc"
    reloaded = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in reloaded.terms()}
    assert terms["mc"].kinds == ("speech.lectern",)
    assert terms["mc"].display_origin == "default, edited"


def test_deleting_a_default_term_tombstones_it_rather_than_reviving_on_update(directory):
    v = vocab.Vocabulary.load(directory)
    v.delete_term("hoa tươi")
    reloaded = vocab.Vocabulary.load(directory)
    assert "hoa tươi" not in {t.key for t in reloaded.terms()}
    doc = cache.read_raw(directory)
    assert doc["cuesheet"]["hoa tươi"]["deleted"] is True


def test_reset_removes_the_tombstone_and_the_default_shows_through_again(directory):
    v = vocab.Vocabulary.load(directory)
    v.delete_term("hoa tươi")
    v.reset_term("hoa tươi")
    reloaded = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in reloaded.terms()}
    assert terms["hoa tươi"].ignore is True
    assert terms["hoa tươi"].origin == "default"


def test_deleting_a_manual_term_that_has_no_default_removes_it_outright(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_term("cajon", kinds=("drums.pad",), match="word")
    v.delete_term("cajon")
    doc = cache.read_raw(directory)
    assert "cajon" not in doc["cuesheet"]


# -- validation ---------------------------------------------------------------


def test_put_term_refuses_an_unknown_kind_naming_it(directory):
    v = vocab.Vocabulary.load(directory)
    with pytest.raises(vocab.UnknownKindError, match="nonsense.kind"):
        v.put_term("x", kinds=("nonsense.kind",), match="word")


def test_put_term_refuses_an_unknown_set_naming_it(directory):
    v = vocab.Vocabulary.load(directory)
    with pytest.raises(vocab.UnknownSetError, match="no such set"):
        v.put_term("x", sets=("no such set",), match="word")


def test_a_term_cannot_be_both_ignore_and_kinds(directory):
    v = vocab.Vocabulary.load(directory)
    with pytest.raises(ValueError, match="ignore"):
        v.put_term("x", kinds=("speech.mc",), ignore=True, match="word")


# -- the old single-kind shape still loads (S3.2) ----------------------------


def test_an_old_shape_cache_remember_entry_loads_as_a_match_exact_term(directory):
    from wing_parser.classifier.matcher import Classification

    cache.remember("guitar solo", "cuesheet",
                   Classification(kind="instrument.guitar", confidence=1.0, origin="manual"),
                   directory=directory)
    v = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in v.terms()}
    assert terms["guitar solo"].kinds == ("instrument.guitar",)
    assert terms["guitar solo"].match == "exact"


# -- effective() feeds keywords.match directly -------------------------------


def test_effective_terms_are_ready_for_keywords_match(directory):
    from wing_parser.showcontext.ingest import keywords

    v = vocab.Vocabulary.load(directory)
    result = keywords.match("Mời MC lên sân khấu", v.effective())
    assert "speech.mc" in result.kinds and "utility.playback" in result.kinds
```

- [ ] **Step 8: Run the tests to verify they fail**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_classifier_vocabulary.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.classifier.vocabulary'`

- [ ] **Step 9: Write the minimal implementation** — `wing_parser/classifier/vocabulary.py`

```python
"""Editable cue-sheet vocabulary: sets, terms, defaults, overrides.

Two kinds of thing a person teaches this tool about a cue sheet (design
spec §3):

* a **set** -- a named bundle of kinds ("Drum kit" is seven drum kinds),
  which may nest other sets (Band contains Drum kit, F13);
* a **term** -- a word or phrase from a real running order, pointing at
  one or more kinds and/or sets, or at `ignore` (F5).

Defaults ship in `data/cuesheet_defaults.yaml`, never edited at runtime.
A person's own edits live in `classifier.yaml`'s `cuesheet` (terms) and
`cuesheet_sets` (sets) domains, read and written through
`cache.read_raw`/`cache.write_raw` so every hand-added comment in that
file survives (cache.py's atomic write). An entry there with the same
folded key as a default REPLACES it; `deleted: true` tombstones a
default so a later app update cannot bring it back; `reset_*` removes
the override or tombstone and lets the default show through again.

Every kind is validated against `matcher.known_kinds("channels")` --
`expects:` refuses anything else (ROADMAP §5 item 7) -- and every named
set must exist among the currently-visible (non-deleted) sets. A set may
nest another; expansion is depth-first, first-seen order, deduplicated,
and a cycle is refused AT WRITE TIME (`CycleError`, naming the path) but
tolerated -- expanded once, never looped -- if one already reached disk
by hand-editing, because `expand_set` also runs at ordinary load time,
where raising would break every fragment behind the cycle, not just the
one entry that is wrong.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

import yaml

from wing_parser.classifier import cache
from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext.ingest import keywords

_DEFAULTS_PATH = Path(__file__).resolve().parent / "data" / "cuesheet_defaults.yaml"


class UnknownKindError(ValueError):
    pass


class UnknownSetError(ValueError):
    pass


class CycleError(ValueError):
    def __init__(self, path: tuple[str, ...]) -> None:
        super().__init__("cycle: " + " -> ".join(path))
        self.path = path


@dataclass(frozen=True)
class SetEntry:
    key: str
    label: str
    kinds: tuple[str, ...] = ()
    sets: tuple[str, ...] = ()
    origin: str = "default"
    shadows_default: bool = False
    deleted: bool = False

    @property
    def display_origin(self) -> str:
        if self.shadows_default and self.origin != "default":
            return "default, edited"
        return self.origin


@dataclass(frozen=True)
class TermEntry:
    key: str
    kinds: tuple[str, ...] = ()
    sets: tuple[str, ...] = ()
    ignore: bool = False
    match: str = "word"
    origin: str = "default"
    shadows_default: bool = False
    deleted: bool = False

    @property
    def display_origin(self) -> str:
        if self.shadows_default and self.origin != "default":
            return "default, edited"
        return self.origin


def _load_defaults() -> tuple[dict, dict]:
    doc = yaml.safe_load(_DEFAULTS_PATH.read_text(encoding="utf-8")) or {}
    return doc.get("sets") or {}, doc.get("terms") or {}


def _set_from_default(key: str, raw: dict) -> SetEntry:
    return SetEntry(
        key=keywords.fold(key), label=str(raw.get("label", key)),
        kinds=tuple(raw.get("kinds", ())), sets=tuple(raw.get("sets", ())),
        origin="default",
    )


def _set_from_user(key: str, raw: dict) -> SetEntry:
    if raw.get("deleted"):
        return SetEntry(key=keywords.fold(key), label="", deleted=True, origin="manual")
    return SetEntry(
        key=keywords.fold(key), label=str(raw.get("label", key)),
        kinds=tuple(raw.get("kinds", ())), sets=tuple(raw.get("sets", ())),
        origin=str(raw.get("origin", "manual")),
    )


def _term_from_default(key: str, raw: dict) -> TermEntry:
    return TermEntry(
        key=keywords.fold(key), kinds=tuple(raw.get("kinds", ())),
        sets=tuple(raw.get("sets", ())), ignore=bool(raw.get("ignore", False)),
        match=str(raw.get("match", "word")), origin="default",
    )


def _term_from_user(key: str, raw: dict) -> TermEntry:
    if raw.get("deleted"):
        return TermEntry(key=keywords.fold(key), deleted=True, origin="manual")
    if "confidence" in raw:
        # Pre-wave-4 shape (guess.offer_terms -> cache.remember): read as
        # kinds: [x], match: exact (design spec S3.2) so it keeps its
        # meaning with no migration step.
        return TermEntry(
            key=keywords.fold(key), kinds=(str(raw["kind"]),), match="exact",
            origin=str(raw.get("origin", "cache")),
        )
    return TermEntry(
        key=keywords.fold(key), kinds=tuple(raw.get("kinds", ())),
        sets=tuple(raw.get("sets", ())), ignore=bool(raw.get("ignore", False)),
        match=str(raw.get("match", "word")), origin=str(raw.get("origin", "manual")),
    )


class Vocabulary:
    """His edits over the shipped defaults, sets expanded on demand."""

    def __init__(self, sets: dict[str, SetEntry], terms: dict[str, TermEntry],
                 directory: Path | None = None) -> None:
        self._sets = sets
        self._terms = terms
        self._directory = directory

    @classmethod
    def load(cls, directory: Path | None = None) -> "Vocabulary":
        default_sets, default_terms = _load_defaults()
        sets = {keywords.fold(k): _set_from_default(k, v) for k, v in default_sets.items()}
        terms = {keywords.fold(k): _term_from_default(k, v) for k, v in default_terms.items()}
        default_set_keys = frozenset(sets)
        default_term_keys = frozenset(terms)

        doc = cache.read_raw(directory)
        for key, raw in (doc.get("cuesheet_sets") or {}).items():
            folded = keywords.fold(key)
            entry = _set_from_user(key, raw)
            if not entry.deleted and folded in default_set_keys:
                entry = replace(entry, shadows_default=True)
            sets[folded] = entry
        for key, raw in (doc.get("cuesheet") or {}).items():
            folded = keywords.fold(key)
            entry = _term_from_user(key, raw)
            if not entry.deleted and folded in default_term_keys:
                entry = replace(entry, shadows_default=True)
            terms[folded] = entry
        return cls(sets, terms, directory)

    # -- reading --------------------------------------------------------

    def sets(self) -> tuple[SetEntry, ...]:
        return tuple(sorted((s for s in self._sets.values() if not s.deleted),
                            key=lambda s: s.key))

    def terms(self) -> tuple[TermEntry, ...]:
        return tuple(sorted((t for t in self._terms.values() if not t.deleted),
                            key=lambda t: t.key))

    def expand_set(self, key: str, _visiting: frozenset[str] = frozenset()) -> tuple[str, ...]:
        folded = keywords.fold(key)
        entry = self._sets.get(folded)
        if entry is None or entry.deleted or folded in _visiting:
            return ()
        visiting = _visiting | {folded}
        kinds: list[str] = list(entry.kinds)
        for nested in entry.sets:
            for kind in self.expand_set(nested, visiting):
                if kind not in kinds:
                    kinds.append(kind)
        return tuple(kinds)

    def effective(self) -> tuple[keywords.Term, ...]:
        out = []
        for term in self.terms():
            kinds: list[str] = list(term.kinds)
            for set_key in term.sets:
                for kind in self.expand_set(set_key):
                    if kind not in kinds:
                        kinds.append(kind)
            out.append(keywords.Term(key=term.key, kinds=tuple(kinds),
                                     ignored=term.ignore, match=term.match))
        return tuple(out)

    # -- validation -------------------------------------------------------

    def _check_kinds(self, kinds) -> None:
        known = set(known_kinds("channels"))
        unknown = [k for k in kinds if k not in known]
        if unknown:
            raise UnknownKindError(f"unknown kind(s) {unknown}")

    def _check_sets(self, set_keys) -> None:
        visible = {s.key for s in self.sets()}
        unknown = [s for s in set_keys if keywords.fold(s) not in visible]
        if unknown:
            raise UnknownSetError(f"no such set(s) {unknown}")

    def _check_cycle(self, key: str, nested_sets: tuple[str, ...]) -> None:
        folded_key = keywords.fold(key)

        def walk(current: str, path: tuple[str, ...]) -> None:
            if current == folded_key:
                raise CycleError(path + (current,))
            entry = self._sets.get(current)
            if entry is None or entry.deleted:
                return
            for nested in entry.sets:
                walk(keywords.fold(nested), path + (current,))

        for nested in nested_sets:
            walk(keywords.fold(nested), (folded_key,))

    # -- writing ----------------------------------------------------------

    def put_set(self, key: str, *, label: str, kinds: tuple[str, ...] = (),
                sets: tuple[str, ...] = (), origin: str = "manual") -> None:
        self._check_kinds(kinds)
        self._check_sets(sets)
        self._check_cycle(key, sets)
        doc = cache.read_raw(self._directory)
        doc.setdefault("cuesheet_sets", {})[key] = {
            "label": label, "kinds": list(kinds), "sets": list(sets), "origin": origin,
        }
        cache.write_raw(doc, self._directory)

    def put_term(self, key: str, *, kinds: tuple[str, ...] = (),
                 sets: tuple[str, ...] = (), ignore: bool = False,
                 match: str = "word", origin: str = "manual") -> None:
        if ignore and (kinds or sets):
            raise ValueError("a term is ignore: true OR kinds/sets, not both")
        self._check_kinds(kinds)
        self._check_sets(sets)
        doc = cache.read_raw(self._directory)
        entry: dict[str, Any] = {"match": match, "origin": origin}
        if ignore:
            entry["ignore"] = True
        else:
            if kinds:
                entry["kinds"] = list(kinds)
            if sets:
                entry["sets"] = list(sets)
        doc.setdefault("cuesheet", {})[key] = entry
        cache.write_raw(doc, self._directory)

    def delete_set(self, key: str) -> None:
        self._tombstone_or_remove("cuesheet_sets", key, had_default=self._had_default_set(key))

    def delete_term(self, key: str) -> None:
        self._tombstone_or_remove("cuesheet", key, had_default=self._had_default_term(key))

    def _had_default_set(self, key: str) -> bool:
        folded = keywords.fold(key)
        entry = self._sets.get(folded)
        return entry is not None and (entry.origin == "default" or entry.shadows_default)

    def _had_default_term(self, key: str) -> bool:
        folded = keywords.fold(key)
        entry = self._terms.get(folded)
        return entry is not None and (entry.origin == "default" or entry.shadows_default)

    def _tombstone_or_remove(self, domain: str, key: str, *, had_default: bool) -> None:
        doc = cache.read_raw(self._directory)
        section = doc.setdefault(domain, {})
        if had_default:
            section[key] = {"deleted": True}
        else:
            section.pop(key, None)
        cache.write_raw(doc, self._directory)

    def reset_set(self, key: str) -> None:
        self._reset("cuesheet_sets", key)

    def reset_term(self, key: str) -> None:
        self._reset("cuesheet", key)

    def _reset(self, domain: str, key: str) -> None:
        doc = cache.read_raw(self._directory)
        section = doc.get(domain) or {}
        section.pop(key, None)
        cache.write_raw(doc, self._directory)
```

- [ ] **Step 10: Run the tests to verify they pass**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_classifier_vocabulary.py -v`
Expected: PASS, all tests including the cycle-tolerance and old-shape-compat ones.

- [ ] **Step 11: Show the cycle-tolerance test red once** — change `expand_set`'s guard from
      `folded in _visiting` to `False` (so it never stops recursing) and confirm
      `test_a_cycle_already_on_disk_expands_once_and_does_not_loop` hangs/raises `RecursionError`; restore,
      rerun to confirm green, paste both outcomes into the task report.

- [ ] **Step 12: Run the full suite**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`
Confirm the tally only grew (no prior test broke) and paste the new numbers into the task report.

- [ ] **Step 13: Commit**

```bash
git add wing_parser/classifier/vocabulary.py wing_parser/classifier/data/cuesheet_defaults.yaml tests/test_classifier_vocabulary.py && git commit -m "$(cat <<'EOF'
feat(classifier): add vocabulary.py and the shipped cuesheet defaults

Spec §3.2-3.3, Appendix A, F13/F14: sets + terms, defaults merged with
his edits and tombstones, nested-set expansion with cycle detection at
write time and tolerance at load time, and the old single-kind cache
shape still reads as a match:exact term.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** that `cuesheet_defaults.yaml`'s every `kinds:` entry is a real
`patterns.yaml` "channels" kind (the `test_every_shipped_default_kind_is_one_patterns_yaml_can_produce`
test in Step 7 IS this check, automated — confirm it actually ran and passed, not just that it exists);
that `Vocabulary.load()` reads `cache.read_raw`, never `cache.load()` (a `grep -n "cache\.load"
wing_parser/classifier/vocabulary.py` should show nothing).

---

### Task 3: `build.resolve_fragment` returns a `Resolution`; every caller updated; acceptance re-pinned

**Files:**
- Modify: `wing_parser/showcontext/ingest/build.py` (218 lines), `wing_parser/showcontext/ingest/emit.py`
  (122 lines), `wing_parser/cli/render.py`, `wing_parser/showcontext/ingest/wizard.py` (227 lines),
  `wing_parser/cli/commands.py`, `wing_parser/ui/import_controller.py` (144 lines),
  `tests/test_ingest_build.py`, `tests/test_ingest_emit.py`, `tests/test_ingest_contract.py`,
  `tests/test_g2b_acceptance.py`

**This task's numbers are measured, not guessed.** Running the planned algorithm (Task 1's `keywords.fold`/
`match` plus Task 2's shipped defaults) against the real fixtures gives:

- `tests/data/ingest-fixture.xlsx` (the synthetic contract fixture): the new default term `ca sĩ` (word
  match, `kinds: [speech.vocal]`) now matches inside the existing fragment `"ca sĩ nữ"` (row 3), which
  today resolves to nothing. Segment `"3"`'s `expects` grows from `("instrument.guitar",)` to
  `("instrument.guitar", "speech.vocal")`; `unreadable_performers` drops from 3 to 2; `expectations` rises
  from 2 to 3. Every other fragment in that fixture (`"nhạc nền"`, `"MC"`, `"guitar"`, `"trống"` — on the
  no-title row 4, never reaches `_expectations` at all — and `"tốp múa"`) is unaffected: `"MC"`/`"guitar"`
  already resolved via `patterns.yaml` to the SAME kind the new default terms also name.
- `tests/data/05102022_vivo_ Event Rundown.xlsx` (sheet `"Rundown"`, header row 4, performers header
  `"On stage"`): **9 fragments total, all 9 resolve, 0 ignored, 0 left unread.**
- `tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx` (sheet `"KB 8.1"`, header row 5, performers header
  `"Thực hiện"`): **31 fragments total: 19 resolve, 8 are ignored, 4 are left unread** — `'Đội'` (a bare
  "team/troupe" noun), `'nhóm'` (a bare "group" noun), `'mời lên SK'` (a stage-direction verb phrase, not a
  performer), `'Đoàn thanh niên BIDV TP. Hồ Chí Minh'` (an organisation's full name). All four name a group
  or a direction, never an instrument or a mic role — genuinely nothing to classify, and exactly the
  "deliberately left unread with a reason" case spec §9 asks the acceptance test to name.

If a future edit to `cuesheet_defaults.yaml` changes these counts, re-run the two probes below and update
the pinned numbers **in the same commit** as the edit — never leave a stale number in a pinned test.

**Interfaces:**
- Consumes: `keywords.Resolution`/`Term` (Task 1); `vocabulary.Vocabulary` — specifically its
  `.effective() -> tuple[keywords.Term, ...]` method (Task 2).
- Produces:
  ```python
  # wing_parser/showcontext/ingest/build.py
  def resolve_fragment(fragment: str, vocabulary) -> keywords.Resolution: ...  # was: str | None
  def build(rows, mapping, vocabulary, blank_rows: int = 0, *,
            headers: dict[str, str] | None = None) -> BuildResult: ...         # param renamed lookup->vocabulary

  @dataclass(frozen=True)
  class BuildResult:
      segments: tuple[BuiltSegment, ...]
      loose_comments: tuple[str, ...]
      data_rows: int
      comment_rows: int
      blank_rows: int
      unreadable_performers: int = 0
      ignored_performers: int = 0          # NEW
  ```
  Task 8's `propose.missing_for_segments` and Task 7's Terms-step redesign both read `BuildResult` as
  before; neither touches `ignored_performers` directly, but Task 7's summary line and Task 8's scene table
  both display it via the same `emit.render`/`ic.preview_text` path this task updates.

- [ ] **Step 1: Write the failing tests for `build.py`** — surgical edits to `tests/test_ingest_build.py`,
      not a rewrite: every call site keeps the name `lookup`, so only two spots change.

Replace lines 1–20 (the imports and the module-level fixture) with:

```python
import pytest

from wing_parser.showcontext.ingest import build as builder
from wing_parser.showcontext.ingest import keywords
from wing_parser.showcontext.ingest.mapping import SheetMapping
from wing_parser.showcontext.ingest.sheet import RawRow

MAPPING = SheetMapping(
    source="test",
    fields={"id": "A", "time": "B", "title": "C", "performers": "D", "note": "E"},
)


class _FakeVocabulary:
    """Stands in for `vocabulary.Vocabulary` -- `resolve_fragment` only
    ever calls `.effective()`, so the fake need not touch a filesystem."""

    def __init__(self, terms):
        self._terms = terms

    def effective(self):
        return self._terms


lookup = _FakeVocabulary((
    keywords.Term(key="ca sĩ nữ", kinds=("speech.vocal",), ignored=False, match="exact"),
    keywords.Term(key="trống", kinds=("drums.kick",), ignored=False, match="exact"),
))
```

Replace the body of `test_the_vocabulary_is_consulted_before_the_pattern_matcher` (currently using a bare
`contradicting(term)` callable, which no longer matches the `vocabulary.effective()` contract):

```python
def test_the_vocabulary_is_consulted_before_the_pattern_matcher():
    """The term must be one the matcher also answers, or order proves nothing.

    'ca sĩ nữ' is unknown to patterns.yaml, so a test using it passed
    whether the vocabulary was consulted first or last -- while carrying
    the name of the ordering the whole cuesheet domain exists to give.
    'guitar' is instrument.guitar at 0.85 in patterns.yaml, so only the
    vocabulary winning can produce speech.vocal here.
    """
    contradicting = _FakeVocabulary((
        keywords.Term(key="guitar", kinds=("speech.vocal",), ignored=False, match="exact"),
    ))

    matched = builder.build([row(5, C="x", D="guitar")], MAPPING, lookup)
    assert matched.segments[0].segment.expects == ("instrument.guitar",)

    result = builder.build([row(5, C="x", D="guitar")], MAPPING, contradicting)
    assert result.segments[0].segment.expects == ("speech.vocal",)
```

Add three new tests for the union/ignore behaviour `_expectations` must now carry, appended after
`test_a_weak_pattern_hit_does_not_satisfy_an_expectation`:

```python
def test_an_ignored_fragment_is_counted_and_produces_no_comment_or_expectation():
    ignoring = _FakeVocabulary((
        keywords.Term(key="hoa tươi", kinds=(), ignored=True, match="exact"),
    ))
    result = builder.build([row(5, C="x", D="hoa tươi")], MAPPING, ignoring)
    assert result.segments[0].segment.expects == ()
    assert result.segments[0].comments == ()
    assert result.ignored_performers == 1
    assert result.unreadable_performers == 0


def test_ignored_and_unresolved_fragments_are_counted_separately():
    ignoring = _FakeVocabulary((
        keywords.Term(key="hoa tươi", kinds=(), ignored=True, match="exact"),
    ))
    result = builder.build(
        [row(5, C="x", D="hoa tươi, tốp múa")], MAPPING, ignoring
    )
    assert result.ignored_performers == 1
    assert result.unreadable_performers == 1


def test_a_fragment_matching_several_word_terms_unions_their_kinds():
    several = _FakeVocabulary((
        keywords.Term(key="BLĐ", kinds=("speech.handheld",), ignored=False, match="word"),
        keywords.Term(key="lên sân khấu", kinds=("utility.playback",), ignored=False, match="word"),
    ))
    result = builder.build(
        [row(5, C="x", D="Mời BLĐ lên sân khấu")], MAPPING, several
    )
    assert result.segments[0].segment.expects == ("speech.handheld", "utility.playback")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ingest_build.py -v`
Expected: FAIL — `AttributeError: 'function' object has no attribute 'effective'` on every test using the
old bare-callable `lookup`, since `build.py` still calls `lookup(term)` directly.

- [ ] **Step 3: Rewrite `build.py`'s resolution logic**

Replace `resolve_fragment` and `_expectations`:

```python
from wing_parser.showcontext.ingest import keywords


def resolve_fragment(fragment: str, vocabulary) -> keywords.Resolution:
    """Vocabulary first (exact, then word — keywords.match's own two
    steps), pattern matcher second, nothing third."""
    target = clean(fragment)
    if not target:
        return keywords.Resolution((), False)

    found = keywords.match(fragment, vocabulary.effective())
    if found.kinds or found.ignored:
        return found

    pattern = matcher.classify(fragment, "channels")
    if matcher.is_confident(pattern):
        return keywords.Resolution((pattern.kind,), False)

    return keywords.Resolution((), False)


def _expectations(text: str, vocabulary, row_number: int) -> tuple[
        tuple[str, ...], tuple[str, ...], int]:
    kinds: list[str] = []
    comments: list[str] = []
    ignored = 0
    for fragment in _SPLIT.split(text):
        stripped = fragment.strip()
        if not stripped:
            continue
        resolution = resolve_fragment(stripped, vocabulary)
        if resolution.ignored and not resolution.kinds:
            ignored += 1
            continue
        if not resolution.kinds:
            comments.append(
                f"row {row_number}: could not read performer {stripped!r}"
            )
            continue
        for kind in resolution.kinds:
            if kind not in kinds:
                kinds.append(kind)
    return tuple(kinds), tuple(comments), ignored
```

Change `build()`'s signature and its one call site of `_expectations`, plus the final `BuildResult(...)`:

```python
def build(rows, mapping, vocabulary, blank_rows: int = 0,
          *, headers: dict[str, str] | None = None) -> BuildResult:
    built: list[BuiltSegment] = []
    loose: list[str] = []
    unreadable = 0
    ignored_total = 0
    generated = 0
    used: set[str] = set()

    for row in rows:
        # ... unchanged: title = _cell(...), performers = _cell(...), etc.

        kinds, comments, ignored = _expectations(performers, vocabulary, row.number)
        unreadable += len(comments)
        ignored_total += ignored
        # ... unchanged from here: notes = list(comments); written_time handling; etc.

    return BuildResult(
        segments=tuple(built),
        loose_comments=tuple(loose),
        data_rows=len(rows),
        comment_rows=len(loose),
        blank_rows=blank_rows,
        unreadable_performers=unreadable,
        ignored_performers=ignored_total,
    )
```

Add the new field to `BuildResult`:

```python
@dataclass(frozen=True)
class BuildResult:
    segments: tuple[BuiltSegment, ...]
    loose_comments: tuple[str, ...]
    data_rows: int
    comment_rows: int
    blank_rows: int
    unreadable_performers: int = 0
    ignored_performers: int = 0
```

- [ ] **Step 4: Run `test_ingest_build.py` to verify it passes**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ingest_build.py -v`
Expected: PASS, all tests including the three new ones.

- [ ] **Step 5: Update `emit.py`'s trailer and its pinned test**

In `wing_parser/showcontext/ingest/emit.py`, change the trailer's f-string list (the last statement of
`render`) to add the ignored clause between "kept as comments" and "blank row(s)":

```python
    trailer.append(
        f"# imported {result.data_rows} data row(s) -> "
        f"{len(result.segments)} segment(s) carrying "
        f"{result.expectations} expectation(s), "
        f"{result.comment_rows} row(s) and "
        f"{result.unreadable_performers} performer fragment(s) kept as "
        f"comments, {result.ignored_performers} ignored, "
        f"{result.blank_rows} blank row(s) skipped"
    )
```

In `tests/test_ingest_emit.py`, update the one pinned trailer string (currently at line 174-176):

```python
        "# imported 1 data row(s) -> 1 segment(s) carrying 1 expectation(s), "
        "0 row(s) and 0 performer fragment(s) kept as comments, 0 ignored, "
        "0 blank row(s) skipped\n"
```

- [ ] **Step 6: Update `render.py`'s CLI summary line**

In `wing_parser/cli/render.py`, change `import_summary` to append the ignored count AFTER "kept as
comments" (never before — `tests/test_ingest_contract.py:58` asserts the literal substring `"row(s) and
{N} performer fragment(s) kept as comments"`, which must stay intact):

```python
def import_summary(destination, result) -> str:
    return (
        f"wrote {destination}: {len(result.segments)} segment(s) carrying "
        f"{result.expectations} expectation(s) from {result.data_rows} data "
        f"row(s), {result.comment_rows} row(s) and "
        f"{result.unreadable_performers} performer fragment(s) kept as "
        f"comments and {result.ignored_performers} ignored. Only Q4 and Q5 "
        f"fire until this file has real cues."
    )
```

- [ ] **Step 7: Update the three real callers of `build.build`**

`wing_parser/showcontext/ingest/wizard.py` — in `_finish`, replace:

```python
    from wing_parser.classifier import cache

    try:
        vocabulary = cache.load().get("cuesheet", {})
        result = build.build(
            read.rows,
            resolved,
            lambda term: vocabulary.get(clean(term)),
            blank_rows=read.blank_rows,
            headers=read.headers,
        )
```

with:

```python
    from wing_parser.classifier import vocabulary as vocab_module

    try:
        vocabulary = vocab_module.Vocabulary.load(knowledge_dir)
        result = build.build(
            read.rows,
            resolved,
            vocabulary,
            blank_rows=read.blank_rows,
            headers=read.headers,
        )
```

and remove the now-unused top-level `from wing_parser.classifier.normalize import clean` (its only call
site in this file was the lambda just removed).

`wing_parser/cli/commands.py` — in `showcontext_import`, replace:

```python
    from wing_parser.classifier import cache
    from wing_parser.classifier.normalize import clean
    from wing_parser.showcontext.ingest import build, emit, mapping, propose, sheet
```

with:

```python
    from wing_parser import config
    from wing_parser.classifier import vocabulary as vocab_module
    from wing_parser.showcontext.ingest import build, emit, mapping, propose, sheet
```

and replace:

```python
        vocabulary = cache.load().get("cuesheet", {})
        result = build.build(
            read.rows,
            resolved,
            lambda term: vocabulary.get(clean(term)),
            blank_rows=read.blank_rows,
            headers=read.headers,
        )
```

with:

```python
        vocabulary = vocab_module.Vocabulary.load(config.knowledge_dir())
        result = build.build(
            read.rows,
            resolved,
            vocabulary,
            blank_rows=read.blank_rows,
            headers=read.headers,
        )
```

`wing_parser/ui/import_controller.py` — replace `build_result` in full:

```python
def build_result(read, resolved):
    """Rows and a resolved mapping become BuiltSegments, the effective
    cuesheet vocabulary (defaults + his edits, Task 2) first.

    `config.knowledge_dir()` is read fresh on every call rather than
    cached: the autouse test fixture points it at a throwaway directory
    per test, and Settings/the Vocabulary window can change what it
    points to while the app is running.
    """
    from wing_parser import config
    from wing_parser.classifier import vocabulary as vocab_module

    vocabulary = vocab_module.Vocabulary.load(config.knowledge_dir())
    return build.build(
        read.rows, resolved, vocabulary,
        blank_rows=read.blank_rows, headers=read.headers,
    )
```

and remove the now-unused top-level `from wing_parser.classifier.normalize import clean` (keep
`from wing_parser.classifier import cache` — `record_term` still calls `cache.remember`).

- [ ] **Step 8: Update the pinned contract-test numbers** — `tests/test_ingest_contract.py`

```python
def test_the_fixture_imports_to_exactly_this(tmp_path):
    out = tmp_path / "tonight.yaml"
    assert main([
        "showcontext", "import", str(DATA / "ingest-fixture.xlsx"),
        "--map", str(DATA / "ingest-fixture-map.yaml"), "-o", str(out),
    ]) == 0

    doc = yaml.safe_load(out.read_text(encoding="utf-8"))
    assert [(s["id"], s["title"], tuple(s["expects"])) for s in doc["segments"]] == [
        ("1", "Đón khách", ()),
        ("2", "MC khai mạc", ("speech.mc",)),
        ("3", "Tiết mục 3 — Guitar", ("instrument.guitar", "speech.vocal")),
        ("5", "Tiết mục 5", ()),
    ]
```

and in `test_the_counts_reconcile_in_the_written_file`:

```python
    assert "imported 5 data row(s) -> 4 segment(s)" in text
    assert "carrying 3 expectation(s)" in text
    assert "1 row(s) and 2 performer fragment(s) kept as comments" in text
    assert "1 blank row(s) skipped" in text
```

Both changes follow directly from the shipped default term `ca sĩ` (Task 2) now matching inside the
fixture's `"ca sĩ nữ"` fragment — see the measured note at the top of this task.

- [ ] **Step 9: Run every ingest test to verify the numbers land exactly as measured**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ingest_build.py tests/test_ingest_emit.py tests/test_ingest_contract.py tests/test_ingest_propose.py tests/test_ingest_guess.py -v`
Expected: PASS. If `test_the_fixture_imports_to_exactly_this` or the counts test still fails, the real
numbers drifted from what this task measured (re-run the probe methodology at the top of this task against
`ingest-fixture.xlsx` rather than guessing a fix).

- [ ] **Step 10: Extend `tests/test_g2b_acceptance.py` with the two real files, defaults included**

Append:

```python
from wing_parser.classifier import vocabulary as vocab_module
from wing_parser.showcontext.ingest import build, mapping as mapping_mod, sheet


def _built(path, sheet_name, header_row, columns, performers_header, tmp_path):
    """The real pipeline: read the sheet, resolve columns, build segments
    against the shipped defaults (an empty tmp_path knowledge dir, so
    nothing but the defaults is in play)."""
    read = sheet.read_sheet(path, sheet_name, header_row)
    raw = mapping_mod.RawMapping(
        source=path.stem, sheet=sheet_name, header_row=header_row,
        columns=columns, headers={"performers": performers_header},
    )
    resolved = mapping_mod.resolve_columns(raw, read.headers, read.last_column)
    vocabulary = vocab_module.Vocabulary.load(tmp_path)
    return build.build(read.rows, resolved, vocabulary, blank_rows=read.blank_rows,
                       headers=read.headers)


def test_vivo_resolves_every_performer_fragment_with_the_shipped_defaults(tmp_path):
    """Spec §9: with the shipped defaults, every VIVO fragment resolves.
    Measured 2026-09-26 against keywords.fold/match + Task 2's defaults:
    9 fragments total, 9 resolved, 0 ignored, 0 left unread."""
    result = _built(VIVO, "Rundown", 4,
                    {"id": "B", "time": "C", "title": "F"}, "On stage", tmp_path)
    assert result.unreadable_performers == 0
    assert result.ignored_performers == 0


def test_bidv_resolves_or_ignores_all_but_four_deliberately_unread_fragments(tmp_path):
    """Measured 2026-09-26: 31 fragments total, 19 resolved, 8 ignored, 4
    left unread. The four are 'Đội' and 'nhóm' (bare group nouns), 'mời
    lên SK' (a stage-direction verb phrase) and the BIDV Youth Union's
    full organisation name -- none of them name an instrument or a mic
    role, so there is genuinely nothing to classify. If this count
    changes, a real default changed underneath it; re-measure, do not
    adjust the number to make the test pass."""
    result = _built(BIDV, "KB 8.1", 5,
                    {"id": "A", "time": "B", "title": "E"}, "Thực hiện", tmp_path)
    assert result.ignored_performers == 8
    assert result.unreadable_performers == 4
```

- [ ] **Step 11: Run the acceptance suite**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_g2b_acceptance.py -v`
Expected: PASS, all 6 tests (4 pre-existing + 2 new).

- [ ] **Step 12: Run the full suite**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`
Paste the tally into the task report; confirm nothing outside the files this task touched went red.

- [ ] **Step 13: Commit**

```bash
git add wing_parser/showcontext/ingest/build.py wing_parser/showcontext/ingest/emit.py wing_parser/cli/render.py wing_parser/showcontext/ingest/wizard.py wing_parser/cli/commands.py wing_parser/ui/import_controller.py tests/test_ingest_build.py tests/test_ingest_emit.py tests/test_ingest_contract.py tests/test_g2b_acceptance.py && git commit -m "$(cat <<'EOF'
feat(ingest): wire the cuesheet vocabulary into build/emit/CLI/UI

build.resolve_fragment now returns a keywords.Resolution (kinds + an
ignored flag) instead of str | None; _expectations unions several
word-matched kinds per fragment and counts ignored ones separately
(BuildResult.ignored_performers). All three real callers (CLI import,
the interactive wizard, the UI's import_controller) now build a
vocabulary.Vocabulary instead of a raw cache dict. Contract-test and
acceptance numbers re-measured against the shipped defaults (Task 2):
ingest-fixture.xlsx's "ca sĩ nữ" now resolves via the new "ca sĩ" term;
VIVO resolves all 9 fragments; BIDV resolves 19, ignores 8, leaves 4
deliberately unread.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** that `tests/test_ingest_propose.py` and `tests/test_ingest_guess.py` still
pass unmodified (neither calls `build.build`, confirmed in this task's own research — a regression there
would mean this task's changes reached further than intended); that `wing_parser/ui/import_controller.py`
still imports `cache` (for `record_term`) after `clean` is removed — a `grep -n "^from\|^import"
wing_parser/ui/import_controller.py` should show `cache` still present and `clean` gone.

---

### Task 4: `provider_errors.py` — one failure vocabulary for every AI surface

**Files:**
- Create: `wing_parser/classifier/provider_errors.py`, `tests/test_provider_errors.py`
- Modify: `wing_parser/ui/settings_dialog.py` (197 lines)

Read `wing_parser/classifier/provider_anthropic.py` and `wing_parser/classifier/provider_openai.py` in
full first — both import their SDK lazily (inside `complete_json`/`_client`), so `provider_errors.py` must
classify a real `anthropic.APIStatusError`/`openai.APIStatusError` **without ever importing either
package** — doing so would force an extra (`llm`/`llm-openai`) onto a `.[ui]`-only build. Both SDKs' status
errors carry a `.status_code` int attribute; that duck type is this module's entire contract with them.

**Why "timeout" needs no branch here.** `wing_parser/ui/workers.py`'s `CallRunner`/`call_button.py`'s
`ButtonRunner` already special-case `CallTimedOut` before it ever reaches an `on_error` callback (see
`call_button.py:_failed`: `if isinstance(exc, CallTimedOut): ...; elif self._on_error is not None:
self._on_error(exc)`) — every existing AI-call surface (Settings' probe, the Terms step's guesses) already
shows the SAME ruled sentence (`text("settings.timeout")`/`text("import.timeout")`) for a timeout, through
that mechanism, not through error classification. `provider_errors.classify` is never called with a
`CallTimedOut` and this task adds no code that would change that.

**Interfaces:**
- Consumes: nothing (duck-types on the exception it is handed).
- Produces:
  ```python
  # wing_parser/classifier/provider_errors.py
  BAD_KEY = "bad_key"; QUOTA = "quota"; NO_NETWORK = "no_network"
  SDK_MISSING = "sdk_missing"; BAD_REPLY = "bad_reply"; OTHER = "other"

  def classify(exc: Exception) -> tuple[str, str]: ...   # (code, human-readable text)
  ```
  Task 6's assistant and Task 9's Try-AI panel both call `classify(exc)` in their own `on_error` handler and
  show the returned text — neither invents its own wording.

- [ ] **Step 1: Write the failing tests** — `tests/test_provider_errors.py`

```python
"""Spec §7: one shared failure vocabulary for Settings' Test connection,
the Mapping step's Try AI, and the Vocabulary window's assistant.

Every exception here is a plain fake -- never a real anthropic/openai
import -- so this module (and this test) work in a build with neither
SDK installed. `status_code` duck-typing mirrors both SDKs' own
`APIStatusError` shape (checked by opening provider_anthropic.py /
provider_openai.py, listed as Task 4's own file reads above).
"""
from __future__ import annotations

from wing_parser.classifier import provider_errors as pe
from wing_parser.classifier.provider import ProviderError


class _FakeStatusError(Exception):
    def __init__(self, status_code, message="boom"):
        super().__init__(message)
        self.status_code = status_code


def test_401_and_403_classify_as_bad_key():
    assert pe.classify(_FakeStatusError(401))[0] == pe.BAD_KEY
    assert pe.classify(_FakeStatusError(403))[0] == pe.BAD_KEY


def test_402_and_429_classify_as_quota():
    assert pe.classify(_FakeStatusError(402))[0] == pe.QUOTA
    assert pe.classify(_FakeStatusError(429))[0] == pe.QUOTA


def test_a_connection_error_classifies_as_no_network():
    assert pe.classify(ConnectionError("no route to host"))[0] == pe.NO_NETWORK


class _FakeAPIConnectionError(Exception):
    """Stands in for anthropic.APIConnectionError / openai.APIConnectionError
    -- both name-match "Connection", neither is a builtin ConnectionError."""


def test_an_sdk_named_connection_error_also_classifies_as_no_network():
    assert pe.classify(_FakeAPIConnectionError("unreachable"))[0] == pe.NO_NETWORK


def test_an_import_error_classifies_as_sdk_missing():
    assert pe.classify(ImportError("no module named anthropic"))[0] == pe.SDK_MISSING


def test_the_lazy_import_runtime_error_text_also_classifies_as_sdk_missing():
    """provider_anthropic.py/provider_openai.py wrap a missing SDK's
    ImportError in RuntimeError/MissingExtra carrying this exact phrase
    (EXTRA_HINT in both modules) -- classify() must recognise it even
    though it is no longer an ImportError by the time it gets here."""
    exc = RuntimeError("talking to Claude needs the anthropic package. "
                       "Install it with:  pip install -e .[llm]")
    assert pe.classify(exc)[0] == pe.SDK_MISSING


def test_a_provider_error_classifies_as_bad_reply():
    assert pe.classify(ProviderError("reply never matched the schema: x"))[0] == pe.BAD_REPLY


def test_anything_else_classifies_as_other_and_keeps_the_original_text():
    code, text = pe.classify(ValueError("something unexpected"))
    assert code == pe.OTHER
    assert "something unexpected" in text


def test_every_code_has_non_empty_human_text():
    for exc in (_FakeStatusError(401), _FakeStatusError(429), ConnectionError("x"),
               ImportError("x"), ProviderError("x"), ValueError("x")):
        code, text = pe.classify(exc)
        assert text.strip() != ""
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_provider_errors.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.classifier.provider_errors'`

- [ ] **Step 3: Write the minimal implementation** — `wing_parser/classifier/provider_errors.py`

```python
"""Classify a provider-call exception into one shared failure vocabulary.

Settings' Test connection, the Mapping step's Try AI (Task 9) and the
Vocabulary window's assistant (Task 6) all call `classify()` and show
its text -- so the same failure reads the same way everywhere, which is
the whole point (design spec §7).

Duck-typed on purpose: `provider_anthropic.py` and `provider_openai.py`
both import their SDK lazily, so this module classifies a real
`anthropic.APIStatusError`/`openai.APIStatusError` without ever
importing either package -- doing so would force an extra onto a
`.[ui]`-only build. Both SDKs' status errors carry a `.status_code` int
(confirmed by reading both provider adapters, 2026-09-26); that duck
type is the entire contract this module leans on.

A `CallTimedOut` is never classified here -- `ui/workers.py`'s
`CallRunner` and `ui/call_button.py`'s `ButtonRunner` already intercept
it before any `on_error` callback runs, and every existing call site
already shows one ruled sentence for it. See this file's own docstring
in the plan for why that stays true after this task.
"""

from __future__ import annotations

from wing_parser.classifier.provider import ProviderError

BAD_KEY = "bad_key"
QUOTA = "quota"
NO_NETWORK = "no_network"
SDK_MISSING = "sdk_missing"
BAD_REPLY = "bad_reply"
OTHER = "other"

_MESSAGES = {
    BAD_KEY: "That key was rejected by the provider. Check it in Settings.",
    QUOTA: "The provider reported no quota or a rate limit. Try again later.",
    NO_NETWORK: "Could not reach the provider -- check the network.",
    SDK_MISSING: "The model SDK for this provider is not installed in this build.",
    BAD_REPLY: "The model's reply could not be read as the expected answer.",
}


def classify(exc: Exception) -> tuple[str, str]:
    """(code, human-readable text)."""
    status = getattr(exc, "status_code", None)
    if status in (401, 403):
        return BAD_KEY, _MESSAGES[BAD_KEY]
    if status in (402, 429):
        return QUOTA, _MESSAGES[QUOTA]

    type_name = type(exc).__name__
    if isinstance(exc, ConnectionError) or "Connection" in type_name:
        return NO_NETWORK, _MESSAGES[NO_NETWORK]
    if isinstance(exc, ImportError) or "pip install -e ." in str(exc):
        return SDK_MISSING, _MESSAGES[SDK_MISSING]
    if isinstance(exc, ProviderError):
        return BAD_REPLY, _MESSAGES[BAD_REPLY]

    return OTHER, str(exc)
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_provider_errors.py -v`
Expected: PASS, all 9 tests.

- [ ] **Step 5: Wire Settings' Test connection through it** — `wing_parser/ui/settings_dialog.py`

Read the existing `_show_probe_error` (near the end of the file, beside `_show_probe_result`) before
editing. Add the import and replace the one method:

```python
from wing_parser.classifier import provider_errors
```

```python
    def _show_probe_error(self, exc) -> None:
        _code, message = provider_errors.classify(exc)
        self._probe_line(False, message)
```

Add a Qt test to `tests/test_ui_settings.py`, reusing the file's own `knowledge` fixture (`tmp_path` +
`$WING_PROVIDER_CONFIG` isolation + a `chdir` so a real repo's `provider.yaml` can never leak in — read its
definition near the top of the file before writing this):

```python
def test_a_401_from_the_probe_shows_the_shared_bad_key_message(qt_app, knowledge, settle):
    from wing_parser.ui.settings_dialog import SettingsDialog

    class _Unauthorized(Exception):
        status_code = 401

    def failing_probe(cfg):
        raise _Unauthorized("nope")

    dlg = SettingsDialog(probe=failing_probe)
    assert dlg.run_probe()
    assert settle(lambda: dlg.status_label.text() != "")
    assert "rejected" in dlg.status_label.text()
```

- [ ] **Step 6: Run the settings suite, then the full suite**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_settings.py tests/test_provider_errors.py -v`
then `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`.
Paste both results into the task report.

- [ ] **Step 7: Commit**

```bash
git add wing_parser/classifier/provider_errors.py wing_parser/ui/settings_dialog.py tests/test_provider_errors.py tests/test_ui_settings.py && git commit -m "$(cat <<'EOF'
feat(classifier): add provider_errors.classify, wire Settings through it

One shared failure vocabulary (bad key / quota / no network / SDK
missing / bad reply / other) for every AI-call surface -- Settings'
Test connection today, Try AI and the Vocabulary assistant in later
tasks. Duck-typed on .status_code so neither SDK needs importing here.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** that `provider_anthropic.py`'s `EXTRA_HINT` and `provider_openai.py`'s
`EXTRA_HINT` both literally contain the substring `"pip install -e ."` (confirms the `SDK_MISSING` string
match in `classify()` actually catches both adapters' wrapped-`ImportError` messages); that
`call_button.py:_failed` still checks `isinstance(exc, CallTimedOut)` before calling `self._on_error` (the
claim this task's docstring rests on).

---

### Task 5: the Vocabulary window — Sets and Terms tabs, reset, broken references

**Files:**
- Create: `wing_parser/ui/texts_import.py`, `wing_parser/ui/vocabulary_window.py`,
  `wing_parser/ui/vocabulary_sets_tab.py`, `wing_parser/ui/vocabulary_terms_tab.py`,
  `wing_parser/ui/vocabulary_set_dialog.py`, `wing_parser/ui/vocabulary_term_dialog.py`,
  `tests/test_ui_vocabulary_window.py`
- Modify: `wing_parser/ui/texts.py` (162 lines), `wing_parser/ui/menus.py` (125 lines),
  `wing_parser/ui/main_window.py` (193 lines), `wing_parser/ui/terms_step.py` (154 lines)

Read `wing_parser/ui/settings_dialog.py` in full first — it is the closest existing precedent for a
top-level `QDialog` opened from the Tools menu (construction, a `QMessageBox` for a hard failure, the
`_save_and_close`-style pattern), and `wing_parser/ui/write_arm_dialog.py`'s general shape for a second
precedent. Read `wing_parser/classifier/vocabulary.py` (Task 2) in full — this task calls `sets()`,
`terms()`, `expand_set()`, `put_set`/`put_term`, `delete_set`/`delete_term`, `reset_set`/`reset_term`,
`UnknownKindError`, `UnknownSetError`, `CycleError` directly; nothing here re-derives their behaviour.

**Naming note, so this is never confused with the existing "Vocabulary" step.** `import_page.py`'s
`STEPS = ("pick", "mapping", "vocabulary", "save")` already uses the word "vocabulary" as the internal name
of what §4 of the spec calls the **Terms step** (`import.step.vocabulary` = "Vocabulary" in the step rail —
pre-existing, wave-1 naming, unrelated to this task). This task's **Vocabulary window** is a separate
modal dialog, opened from the Tools menu and from a button on that Terms step. Do not rename the existing
step; do not name any new file `vocabulary_step.py`.

**Interfaces:**
- Consumes: `vocabulary.Vocabulary`/`SetEntry`/`TermEntry`/`UnknownKindError`/`UnknownSetError`/
  `CycleError` (Task 2); `matcher.known_kinds("channels")` (existing).
- Produces:
  ```python
  # wing_parser/ui/vocabulary_window.py
  class VocabularyWindow(QDialog):
      def __init__(self, parent=None, *, directory=None) -> None: ...
      # test seams:
      sets_tab: VocabularySetsTab
      terms_tab: VocabularyTermsTab

  # wing_parser/ui/vocabulary_sets_tab.py
  class VocabularySetsTab(QWidget):
      def __init__(self, vocabulary, on_changed: Callable[[], None]) -> None: ...
      def set_vocabulary(self, vocabulary) -> None: ...
      table: QTableWidget
      add_button: QPushButton; edit_button: QPushButton
      delete_button: QPushButton; reset_button: QPushButton

  # wing_parser/ui/vocabulary_terms_tab.py — same shape, terms instead of sets

  # wing_parser/ui/vocabulary_set_dialog.py
  class VocabularySetDialog(QDialog):
      def __init__(self, parent=None, *, known_kinds, known_sets, initial=None) -> None: ...
      def result(self) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]: ...  # key, label, kinds, sets

  # wing_parser/ui/vocabulary_term_dialog.py
  class VocabularyTermDialog(QDialog):
      def __init__(self, parent=None, *, known_kinds, known_sets, initial=None) -> None: ...
      def result(self) -> tuple[str, tuple[str, ...], tuple[str, ...], bool, str]: ...  # key, kinds, sets, ignore, match
  ```
  Task 6 adds a third tab (`assistant_tab`) to `VocabularyWindow.tabs` and a `_reload()` call after Apply;
  it does not change any interface above. Task 7's Terms step opens `VocabularyWindow` from its own
  "Vocabulary…" button — the same one this task adds — and nothing else.

- [ ] **Step 1: Write `texts_import.py`** — every string this wave's UI needs, English (W1). Later tasks
      (6-9) ADD keys to this same dict; they do not create a second file.

```python
"""Every wave-4 string: the Vocabulary window, its assistant, the Scene
cross-check step, the lint dialog, and the Mapping step's Try AI. Merged
into TEXTS the way CONSOLE_TEXTS/WRITE_TEXTS already are (texts.py)."""

IMPORT_TEXTS: dict[str, str] = {
    "vocabulary.title": "Vocabulary",
    "vocabulary.open_button": "Vocabulary…",
    "vocabulary.tab.sets": "Sets",
    "vocabulary.tab.terms": "Terms",
    "vocabulary.close": "Close",
    "vocabulary.col.label": "Label",
    "vocabulary.col.kinds": "Kinds",
    "vocabulary.col.nested": "Nested sets",
    "vocabulary.col.source": "Source",
    "vocabulary.col.key": "Term",
    "vocabulary.col.match": "Match",
    "vocabulary.add": "Add…",
    "vocabulary.edit": "Edit…",
    "vocabulary.delete": "Delete",
    "vocabulary.reset": "Reset to default",
    "vocabulary.dialog.name": "Name",
    "vocabulary.dialog.label": "Label",
    "vocabulary.dialog.kinds": "Kinds",
    "vocabulary.dialog.sets": "Sets",
    "vocabulary.dialog.ignore": "Ignore this term (no kind)",
    "vocabulary.dialog.match": "Match",
    "vocabulary.dialog.match.exact": "the whole fragment, exactly",
    "vocabulary.dialog.match.word": "as a whole word inside a sentence",
    "vocabulary.broken": "broken — {names} no longer exists",
}
```

- [ ] **Step 2: Merge it into `texts.py`**

```python
from wing_parser.ui.texts_console import CONSOLE_TEXTS
from wing_parser.ui.texts_import import IMPORT_TEXTS
from wing_parser.ui.texts_write import WRITE_TEXTS

TEXTS: dict[str, str] = {
    # ... every existing entry, unchanged ...
    **CONSOLE_TEXTS,
    **WRITE_TEXTS,
    **IMPORT_TEXTS,
}
```

- [ ] **Step 3: Write the failing Qt tests** — `tests/test_ui_vocabulary_window.py`

```python
"""Spec §8.1: the Vocabulary window's Sets and Terms tabs.

Every test builds a real VocabularyWindow over an isolated tmp_path
directory (no real knowledge/ touched) and drives its real buttons and
tables -- QT_QPA_PLATFORM=offscreen, timeout=2 is not needed here since
nothing in this window makes a network call (that arrives in Task 6).
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")


@pytest.fixture
def window(qt_app, tmp_path):
    from wing_parser.ui.vocabulary_window import VocabularyWindow

    return VocabularyWindow(directory=tmp_path)


def test_the_sets_tab_lists_every_shipped_default(window):
    labels = {window.sets_tab.table.item(r, 0).text()
             for r in range(window.sets_tab.table.rowCount())}
    assert {"Drum kit", "Band", "Award moment"} <= labels


def test_the_terms_tab_lists_every_shipped_default(window):
    keys = {window.terms_tab.table.item(r, 0).text()
           for r in range(window.terms_tab.table.rowCount())}
    assert {"mc", "trống", "hoa tươi"} <= keys


def test_adding_a_set_through_the_dialog_shows_up_after_accept(window, monkeypatch):
    from wing_parser.ui import vocabulary_sets_tab

    monkeypatch.setattr(
        vocabulary_sets_tab, "VocabularySetDialog",
        lambda *a, **k: _AutoAcceptSetDialog("cajon kit", "Cajon kit",
                                             ("drums.pad",), ()),
    )
    window.sets_tab.table.clearSelection()
    window.sets_tab._add()
    labels = {window.sets_tab.table.item(r, 0).text()
             for r in range(window.sets_tab.table.rowCount())}
    assert "Cajon kit" in labels


def test_editing_drum_kit_changes_what_band_shows_as_nested(window, monkeypatch):
    """F13: the Sets tab shows each set's fully expanded kinds beside its
    own list, so editing Drum kit's effect on Band is visible without
    opening Band's own row."""
    from wing_parser.ui import vocabulary_sets_tab

    monkeypatch.setattr(
        vocabulary_sets_tab, "VocabularySetDialog",
        lambda *a, **k: _AutoAcceptSetDialog("drum kit", "Drum kit", ("drums.pad",), ()),
    )
    rows = {window.sets_tab.table.item(r, 0).text(): r
           for r in range(window.sets_tab.table.rowCount())}
    window.sets_tab.table.selectRow(rows["Drum kit"])
    window.sets_tab._edit()

    band_row = {window.sets_tab.table.item(r, 0).text(): r
               for r in range(window.sets_tab.table.rowCount())}["Band"]
    nested_cell = window.sets_tab.table.item(band_row, 2).text()
    assert "drums.pad" in nested_cell


def test_deleting_a_default_term_then_resetting_brings_it_back(window):
    rows = {window.terms_tab.table.item(r, 0).text(): r
           for r in range(window.terms_tab.table.rowCount())}
    window.terms_tab.table.selectRow(rows["hoa tươi"])
    window.terms_tab._delete()
    keys_after_delete = {window.terms_tab.table.item(r, 0).text()
                         for r in range(window.terms_tab.table.rowCount())}
    assert "hoa tươi" not in keys_after_delete

    # Reset needs a fresh vocabulary reload to see the tombstone go away --
    # exactly what _on_changed()/_reload() already does on every write.
    window._reload()
    from wing_parser.classifier import vocabulary as vocab_module
    v = vocab_module.Vocabulary.load(window._directory)
    v.reset_term("hoa tươi")
    window._reload()
    keys_after_reset = {window.terms_tab.table.item(r, 0).text()
                        for r in range(window.terms_tab.table.rowCount())}
    assert "hoa tươi" in keys_after_reset


def test_the_window_opens_from_the_real_main_windows_tools_menu(qt_app, tmp_path, monkeypatch):
    from wing_parser import config
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui import menus

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    opened = {}
    monkeypatch.setattr(menus, "VocabularyWindow",
                        lambda parent: opened.setdefault("parent", parent) or _NullExec())
    window = MainWindow(None)
    window.open_vocabulary()
    assert opened["parent"] is window


class _NullExec:
    def exec(self):
        return 0


class _AutoAcceptSetDialog:
    """Stands in for VocabularySetDialog -- exec() always accepts, result()
    hands back whatever this test wants written."""

    def __init__(self, key, label, kinds, sets_):
        self._payload = (key, label, kinds, sets_)

    def exec(self):
        return 1

    def result(self):
        return self._payload
```

- [ ] **Step 4: Run the tests to verify they fail**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_vocabulary_window.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.vocabulary_window'`

- [ ] **Step 5: Write `vocabulary_set_dialog.py`**

```python
"""Add or edit one set. The name is fixed once created -- renaming would
leave an orphaned key on disk (put_set writes under whatever key it is
given; it does not delete an old one), so this dialog disables the name
field when editing rather than half-supporting a rename."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QDialog, QDialogButtonBox, QFormLayout, QLineEdit,
    QListWidget, QListWidgetItem, QVBoxLayout,
)

from wing_parser.ui.texts import text


class VocabularySetDialog(QDialog):
    def __init__(self, parent=None, *, known_kinds=(), known_sets=(), initial=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("vocabulary.title"))
        self._initial = initial

        self.name_edit = QLineEdit(initial.key if initial else "")
        self.name_edit.setEnabled(initial is None)
        self.label_edit = QLineEdit(initial.label if initial else "")

        self.kinds_list = QListWidget()
        self.kinds_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for kind in known_kinds:
            item = QListWidgetItem(kind)
            self.kinds_list.addItem(item)
            if initial and kind in initial.kinds:
                item.setSelected(True)

        self.sets_list = QListWidget()
        self.sets_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for key in known_sets:
            item = QListWidgetItem(key)
            self.sets_list.addItem(item)
            if initial and key in initial.sets:
                item.setSelected(True)

        form = QFormLayout()
        form.addRow(text("vocabulary.dialog.name"), self.name_edit)
        form.addRow(text("vocabulary.dialog.label"), self.label_edit)
        form.addRow(text("vocabulary.dialog.kinds"), self.kinds_list)
        form.addRow(text("vocabulary.dialog.sets"), self.sets_list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def result(self) -> tuple[str, str, tuple[str, ...], tuple[str, ...]]:
        key = self.name_edit.text().strip() or (self._initial.key if self._initial else "")
        label = self.label_edit.text().strip() or key
        kinds = tuple(item.text() for item in self.kinds_list.selectedItems())
        sets_ = tuple(item.text() for item in self.sets_list.selectedItems())
        return key, label, kinds, sets_
```

- [ ] **Step 6: Write `vocabulary_term_dialog.py`**

```python
"""Add or edit one term. A term is `ignore: true` OR kinds/sets, never
both (vocabulary.put_term already refuses that combination) -- the
Ignore checkbox disables both list widgets while it is ticked so the
dialog cannot even try to send both."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout,
)

from wing_parser.ui.texts import text


class VocabularyTermDialog(QDialog):
    def __init__(self, parent=None, *, known_kinds=(), known_sets=(), initial=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("vocabulary.title"))
        self._initial = initial

        self.name_edit = QLineEdit(initial.key if initial else "")
        self.name_edit.setEnabled(initial is None)

        self.match_box = QComboBox()
        self.match_box.addItem(text("vocabulary.dialog.match.word"), "word")
        self.match_box.addItem(text("vocabulary.dialog.match.exact"), "exact")
        if initial and initial.match == "exact":
            self.match_box.setCurrentIndex(1)

        self.ignore_check = QCheckBox(text("vocabulary.dialog.ignore"))
        self.ignore_check.setChecked(bool(initial and initial.ignore))
        self.ignore_check.toggled.connect(self._apply_ignore_state)

        self.kinds_list = QListWidget()
        self.kinds_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for kind in known_kinds:
            item = QListWidgetItem(kind)
            self.kinds_list.addItem(item)
            if initial and kind in initial.kinds:
                item.setSelected(True)

        self.sets_list = QListWidget()
        self.sets_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for key in known_sets:
            item = QListWidgetItem(key)
            self.sets_list.addItem(item)
            if initial and key in initial.sets:
                item.setSelected(True)

        self._apply_ignore_state(self.ignore_check.isChecked())

        form = QFormLayout()
        form.addRow(text("vocabulary.dialog.name"), self.name_edit)
        form.addRow(text("vocabulary.dialog.match"), self.match_box)
        form.addRow("", self.ignore_check)
        form.addRow(text("vocabulary.dialog.kinds"), self.kinds_list)
        form.addRow(text("vocabulary.dialog.sets"), self.sets_list)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

    def _apply_ignore_state(self, ignored: bool) -> None:
        self.kinds_list.setEnabled(not ignored)
        self.sets_list.setEnabled(not ignored)

    def result(self) -> tuple[str, tuple[str, ...], tuple[str, ...], bool, str]:
        key = self.name_edit.text().strip() or (self._initial.key if self._initial else "")
        ignore = self.ignore_check.isChecked()
        kinds = () if ignore else tuple(item.text() for item in self.kinds_list.selectedItems())
        sets_ = () if ignore else tuple(item.text() for item in self.sets_list.selectedItems())
        match = self.match_box.currentData()
        return key, kinds, sets_, ignore, match
```

- [ ] **Step 7: Write `vocabulary_sets_tab.py`**

```python
"""The Sets tab: a table, Add/Edit/Delete/Reset, and the AI-approved-
looking source column. Each set's own row also shows its fully expanded
kinds (F13) so nesting's effect is visible without opening a second row.
"""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from wing_parser.classifier import vocabulary as vocab_module
from wing_parser.classifier.matcher import known_kinds
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_set_dialog import VocabularySetDialog

_COLUMNS = ("vocabulary.col.label", "vocabulary.col.kinds",
           "vocabulary.col.nested", "vocabulary.col.source")


class VocabularySetsTab(QWidget):
    def __init__(self, vocabulary, on_changed) -> None:
        super().__init__()
        self._vocabulary = vocabulary
        self._on_changed = on_changed

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([text(key) for key in _COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.add_button = QPushButton(text("vocabulary.add"))
        self.edit_button = QPushButton(text("vocabulary.edit"))
        self.delete_button = QPushButton(text("vocabulary.delete"))
        self.reset_button = QPushButton(text("vocabulary.reset"))
        self.add_button.clicked.connect(self._add)
        self.edit_button.clicked.connect(self._edit)
        self.delete_button.clicked.connect(self._delete)
        self.reset_button.clicked.connect(self._reset)

        buttons = QHBoxLayout()
        for button in (self.add_button, self.edit_button, self.delete_button, self.reset_button):
            buttons.addWidget(button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        self._populate()

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary
        self._populate()

    def _populate(self) -> None:
        rows = self._vocabulary.sets()
        self.table.setRowCount(len(rows))
        for r, entry in enumerate(rows):
            expanded = ", ".join(self._vocabulary.expand_set(entry.key))
            nested = ", ".join(entry.sets)
            if entry.sets:
                nested = f"{nested}  ->  {expanded}"
            self.table.setItem(r, 0, QTableWidgetItem(entry.label))
            self.table.setItem(r, 1, QTableWidgetItem(", ".join(entry.kinds)))
            self.table.setItem(r, 2, QTableWidgetItem(nested))
            self.table.setItem(r, 3, QTableWidgetItem(entry.display_origin))

    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self._vocabulary.sets()[row]

    def _add(self) -> None:
        dialog = VocabularySetDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets()),
        )
        if not dialog.exec():
            return
        key, label, kinds, sets_ = dialog.result()
        if not self._write(lambda: self._vocabulary.put_set(
                key, label=label, kinds=kinds, sets=sets_)):
            return
        self._on_changed()

    def _edit(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        dialog = VocabularySetDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets() if s.key != entry.key),
            initial=entry,
        )
        if not dialog.exec():
            return
        key, label, kinds, sets_ = dialog.result()
        if not self._write(lambda: self._vocabulary.put_set(
                key, label=label, kinds=kinds, sets=sets_)):
            return
        self._on_changed()

    def _delete(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        self._vocabulary.delete_set(entry.key)
        self._on_changed()

    def _reset(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        self._vocabulary.reset_set(entry.key)
        self._on_changed()

    def _write(self, action) -> bool:
        try:
            action()
        except (vocab_module.UnknownKindError, vocab_module.UnknownSetError,
                vocab_module.CycleError) as exc:
            QMessageBox.warning(self, text("vocabulary.title"), str(exc))
            return False
        return True
```

- [ ] **Step 8: Write `vocabulary_terms_tab.py`** — the same shape, over terms

```python
"""The Terms tab: a table, Add/Edit/Delete/Reset. A term whose set no
longer exists is shown with '(broken)' after the missing name rather
than crashing the row (design spec §3.2/§8.1)."""

from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QMessageBox, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from wing_parser.classifier import vocabulary as vocab_module
from wing_parser.classifier.matcher import known_kinds
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_term_dialog import VocabularyTermDialog

_COLUMNS = ("vocabulary.col.key", "vocabulary.col.kinds", "vocabulary.col.nested",
           "vocabulary.col.match", "vocabulary.col.source")


class VocabularyTermsTab(QWidget):
    def __init__(self, vocabulary, on_changed) -> None:
        super().__init__()
        self._vocabulary = vocabulary
        self._on_changed = on_changed

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([text(key) for key in _COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)

        self.add_button = QPushButton(text("vocabulary.add"))
        self.edit_button = QPushButton(text("vocabulary.edit"))
        self.delete_button = QPushButton(text("vocabulary.delete"))
        self.reset_button = QPushButton(text("vocabulary.reset"))
        self.add_button.clicked.connect(self._add)
        self.edit_button.clicked.connect(self._edit)
        self.delete_button.clicked.connect(self._delete)
        self.reset_button.clicked.connect(self._reset)

        buttons = QHBoxLayout()
        for button in (self.add_button, self.edit_button, self.delete_button, self.reset_button):
            buttons.addWidget(button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addLayout(buttons)
        self._populate()

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary
        self._populate()

    def _populate(self) -> None:
        set_keys = {s.key for s in self._vocabulary.sets()}
        rows = self._vocabulary.terms()
        self.table.setRowCount(len(rows))
        for r, entry in enumerate(rows):
            if entry.ignore:
                kinds_text = text("vocabulary.dialog.ignore")
            else:
                kinds_text = ", ".join(entry.kinds)
            nested = ", ".join(
                s if s in set_keys else
                text("vocabulary.broken").format(names=s)
                for s in entry.sets
            )
            self.table.setItem(r, 0, QTableWidgetItem(entry.key))
            self.table.setItem(r, 1, QTableWidgetItem(kinds_text))
            self.table.setItem(r, 2, QTableWidgetItem(nested))
            self.table.setItem(r, 3, QTableWidgetItem(entry.match))
            self.table.setItem(r, 4, QTableWidgetItem(entry.display_origin))

    def _selected(self):
        row = self.table.currentRow()
        if row < 0:
            return None
        return self._vocabulary.terms()[row]

    def _add(self) -> None:
        dialog = VocabularyTermDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets()),
        )
        if not dialog.exec():
            return
        key, kinds, sets_, ignore, match = dialog.result()
        if not self._write(lambda: self._vocabulary.put_term(
                key, kinds=kinds, sets=sets_, ignore=ignore, match=match)):
            return
        self._on_changed()

    def _edit(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        dialog = VocabularyTermDialog(
            self, known_kinds=known_kinds("channels"),
            known_sets=tuple(s.key for s in self._vocabulary.sets()), initial=entry,
        )
        if not dialog.exec():
            return
        key, kinds, sets_, ignore, match = dialog.result()
        if not self._write(lambda: self._vocabulary.put_term(
                key, kinds=kinds, sets=sets_, ignore=ignore, match=match)):
            return
        self._on_changed()

    def _delete(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        self._vocabulary.delete_term(entry.key)
        self._on_changed()

    def _reset(self) -> None:
        entry = self._selected()
        if entry is None:
            return
        self._vocabulary.reset_term(entry.key)
        self._on_changed()

    def _write(self, action) -> bool:
        try:
            action()
        except (vocab_module.UnknownKindError, vocab_module.UnknownSetError) as exc:
            QMessageBox.warning(self, text("vocabulary.title"), str(exc))
            return False
        return True
```

- [ ] **Step 9: Write `vocabulary_window.py`**

```python
"""The Vocabulary window: Sets and Terms tabs over one shared Vocabulary.

Opened from the Tools menu (menus.py) and from a button on the Terms
step (Task 7). Task 6 adds a third tab, the AI assistant, without
changing anything below -- `_reload()` is written generically enough
that the assistant's Apply can call it too.
"""

from __future__ import annotations

from PySide6.QtWidgets import QDialog, QHBoxLayout, QPushButton, QTabWidget, QVBoxLayout

from wing_parser.classifier import vocabulary as vocab_module
from wing_parser.ui.texts import text
from wing_parser.ui.vocabulary_sets_tab import VocabularySetsTab
from wing_parser.ui.vocabulary_terms_tab import VocabularyTermsTab


class VocabularyWindow(QDialog):
    def __init__(self, parent=None, *, directory=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("vocabulary.title"))
        self.setMinimumSize(640, 420)
        self._directory = directory
        self.vocabulary = vocab_module.Vocabulary.load(directory)

        self.sets_tab = VocabularySetsTab(self.vocabulary, self._reload)
        self.terms_tab = VocabularyTermsTab(self.vocabulary, self._reload)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.sets_tab, text("vocabulary.tab.sets"))
        self.tabs.addTab(self.terms_tab, text("vocabulary.tab.terms"))

        close_button = QPushButton(text("vocabulary.close"))
        close_button.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addLayout(buttons)

    def _reload(self) -> None:
        """Every write on either tab re-reads the vocabulary and refreshes
        both -- editing Drum kit must be visible in Band's nested-kinds
        cell without closing this window (F13)."""
        self.vocabulary = vocab_module.Vocabulary.load(self._directory)
        self.sets_tab.set_vocabulary(self.vocabulary)
        self.terms_tab.set_vocabulary(self.vocabulary)
```

- [ ] **Step 10: Wire the Tools menu** — `wing_parser/ui/menus.py`

Add the import and the menu action, right after Settings:

```python
from wing_parser.ui.vocabulary_window import VocabularyWindow
```

```python
    tools_menu.addAction(text("menu.settings"), window.open_settings)
    tools_menu.addAction(text("menu.vocabulary"), window.open_vocabulary)
```

Add `open_vocabulary` beside the existing `open_settings`:

```python
def open_vocabulary(window) -> None:
    VocabularyWindow(window).exec()
```

Add the new menu label to `wing_parser/ui/texts.py`'s existing dict (beside `"menu.settings"`):

```python
    "menu.vocabulary": "&Vocabulary...",
```

- [ ] **Step 11: Add the delegating method** — `wing_parser/ui/main_window.py`, beside `open_settings`

```python
    def open_vocabulary(self) -> None:
        menus.open_vocabulary(self)
```

- [ ] **Step 12: Add the Terms-step button** — `wing_parser/ui/terms_step.py`

A minimal addition ahead of Task 7's full redesign of this file — just the button and its handler,
appended near `load_guesses_button` in `__init__`:

```python
        self.vocabulary_button = QPushButton(text("vocabulary.open_button"))
        self.vocabulary_button.clicked.connect(self._open_vocabulary)
```

and add `layout.addWidget(self.vocabulary_button)` beside the existing `layout.addWidget(self.load_guesses_button)`,
plus the handler method:

```python
    def _open_vocabulary(self) -> None:
        from wing_parser.ui.vocabulary_window import VocabularyWindow

        VocabularyWindow(self).exec()
```

- [ ] **Step 13: Run the new tests, then the full suite**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_vocabulary_window.py tests/test_ui_import_page.py tests/test_ui_texts.py -v`
Expected: PASS. Then
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`
— paste the tally.

- [ ] **Step 14: Commit**

```bash
git add wing_parser/ui/texts_import.py wing_parser/ui/texts.py wing_parser/ui/vocabulary_window.py wing_parser/ui/vocabulary_sets_tab.py wing_parser/ui/vocabulary_terms_tab.py wing_parser/ui/vocabulary_set_dialog.py wing_parser/ui/vocabulary_term_dialog.py wing_parser/ui/menus.py wing_parser/ui/main_window.py wing_parser/ui/terms_step.py tests/test_ui_vocabulary_window.py && git commit -m "$(cat <<'EOF'
feat(ui): add the Vocabulary window -- Sets and Terms tabs

Spec §8.1: Add/Edit/Delete/Reset on both tabs, a source column (default/
manual/ai-approved/"default, edited"), F13's nested-kinds preview beside
each set, and a broken-reference marker for a term whose set was
deleted. Opened from Tools > Vocabulary... and from a new button on the
Terms step.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** `tests/test_ui_texts.py::test_no_user_facing_literal_bypasses_texts_py` is
an `ast` scan, not a hand-maintained key list — it flags a bare string literal passed to one of a fixed set
of constructors/setters (`SETTERS`/`CONSTRUCTORS` near the top of that file). Every widget label in this
task's five new files is `text("...")` (a `Call` node, invisible to the scan either way) — confirm none of
the new dialogs' `QCheckBox(...)`/`setWindowTitle(...)` calls slipped in a bare literal instead by grepping
the five new files for `"("` followed by a quote character right after a scanned constructor/setter name.
Also confirm `wing_parser/ui/main_window.py` is still ≤200 lines after Step 11
(`wc -l wing_parser/ui/main_window.py`).

---

### Task 6: `vocab_changes.py` and the Assistant tab

**Files:**
- Create: `wing_parser/classifier/vocab_changes.py`, `wing_parser/ui/vocabulary_assistant.py`,
  `tests/test_classifier_vocab_changes.py`, `tests/test_ui_vocabulary_assistant.py`
- Modify: `wing_parser/classifier/vocabulary.py` (adds `dry_run_set`/`dry_run_term`),
  `wing_parser/ui/vocabulary_window.py` (Task 5's file — adds a third tab and `initial_fragments`),
  `wing_parser/ui/texts_import.py` (Task 5's file — adds the assistant's strings)

Read `wing_parser/classifier/provider.py` in full first — specifically `complete_json`'s dialect docstring
("flat objects whose values are strings or numbers"). **This is why the model is asked for one string
field, not a JSON array directly**: `provider.py`'s schema validator (`_check`) only knows `"string"`/
`"number"`, so a list-of-objects reply cannot be expressed in that dialect without changing `provider.py`
itself (out of scope this wave). The assistant instead asks for `{"changes_json": "<a JSON-encoded array,
as a string>"}` and parses that string with `json.loads` — the model call still goes through the existing,
unmodified `complete_json`/`ProviderError` machinery.

Read `wing_parser/ui/live_snapshot.py`'s `pull_now` (`partial(live_controller.pull, cache=self._schema_cache)`)
before wiring the worker call — `FunctionWorker`/`CallRunner` invoke the given callable with **positional
args only** (`self._function(*self._args)`, `workers.py:81`); `functools.partial` is this codebase's own
idiom for baking keyword arguments in before a call reaches the worker, and this task follows it rather
than inventing a second one.

**Interfaces:**
- Consumes: `vocabulary.Vocabulary` (Task 2, plus this task's two new methods on it);
  `provider.complete_json`/`ProviderError` (existing); `provider_errors.classify` (Task 4).
- Produces:
  ```python
  # wing_parser/classifier/vocabulary.py — additions
  class Vocabulary:
      def dry_run_set(self, key: str, *, kinds=(), sets=()) -> tuple[str, ...]: ...   # problems, empty = OK
      def dry_run_term(self, key: str, *, kinds=(), sets=(), ignore=False) -> tuple[str, ...]: ...

  # wing_parser/classifier/vocab_changes.py
  VALID_OPS = ("add", "edit", "delete"); VALID_TARGETS = ("set", "term")

  @dataclass(frozen=True)
  class Change:
      op: str; target: str; key: str
      before: dict | None; after: dict | None; reason: str

  @dataclass(frozen=True)
  class Validated:
      change: Change; problems: tuple[str, ...]
      @property
      def valid(self) -> bool: ...

  def parse(raw: dict) -> Change: ...                              # raises ValueError naming what's missing
  def validate(change: Change, vocabulary) -> Validated: ...
  def apply(change: Change, vocabulary, *, origin: str = "ai-approved") -> None: ...
  def build_user_prompt(instruction, fragments, vocabulary, known_kinds) -> str: ...
  def propose_changes(provider, *, instruction="", fragments=(), vocabulary, known_kinds) -> list[Change]: ...

  # wing_parser/ui/vocabulary_assistant.py
  class VocabularyAssistant(QWidget):
      def __init__(self, vocabulary, provider_factory, on_applied) -> None: ...
      def set_vocabulary(self, vocabulary) -> None: ...
      def propose_for_fragments(self, fragments: tuple[str, ...]) -> bool: ...  # Task 7's entry point
  ```
  Task 7's Terms step opens `VocabularyWindow(self, initial_fragments=unresolved)`; this task's own change
  to `VocabularyWindow` auto-switches to the Assistant tab and calls `propose_for_fragments` when
  `initial_fragments` is non-empty, so Task 7 needs no new UI of its own for the proposal list.

- [ ] **Step 1: Write the failing tests for `vocabulary.py`'s two new methods** — append to
      `tests/test_classifier_vocabulary.py`

```python
def test_dry_run_set_reports_an_unknown_kind_without_writing(directory):
    v = vocab.Vocabulary.load(directory)
    problems = v.dry_run_set("x", kinds=("nonsense.kind",))
    assert problems and "nonsense.kind" in problems[0]
    assert "x" not in {s.key for s in vocab.Vocabulary.load(directory).sets()}


def test_dry_run_set_reports_a_cycle_without_writing(directory):
    v = vocab.Vocabulary.load(directory)
    v.put_set("loop a", label="Loop A", sets=("band",))
    problems = v.dry_run_set("band", kinds=(), sets=("drum kit", "loop a"))
    assert problems and "loop a" in problems[0]


def test_dry_run_set_is_empty_for_a_writable_set(directory):
    v = vocab.Vocabulary.load(directory)
    assert v.dry_run_set("new one", kinds=("speech.mc",)) == ()


def test_dry_run_term_reports_ignore_with_kinds_as_one_problem(directory):
    v = vocab.Vocabulary.load(directory)
    problems = v.dry_run_term("x", kinds=("speech.mc",), ignore=True)
    assert len(problems) == 1 and "ignore" in problems[0]


def test_dry_run_term_is_empty_for_a_writable_term(directory):
    v = vocab.Vocabulary.load(directory)
    assert v.dry_run_term("cajon", kinds=("drums.pad",)) == ()
```

- [ ] **Step 2: Run, watch them fail, then add the two methods to `vocabulary.py`**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_classifier_vocabulary.py -k dry_run`
Expected: FAIL — `AttributeError: 'Vocabulary' object has no attribute 'dry_run_set'`

Add to the `Vocabulary` class, beside `_check_cycle`:

```python
    def dry_run_set(self, key: str, *, kinds: tuple[str, ...] = (),
                    sets: tuple[str, ...] = ()) -> tuple[str, ...]:
        """Every problem `put_set(key, ...)` would raise, without writing."""
        problems: list[str] = []
        try:
            self._check_kinds(kinds)
        except UnknownKindError as exc:
            problems.append(str(exc))
        try:
            self._check_sets(sets)
        except UnknownSetError as exc:
            problems.append(str(exc))
        if not problems:
            try:
                self._check_cycle(key, sets)
            except CycleError as exc:
                problems.append(str(exc))
        return tuple(problems)

    def dry_run_term(self, key: str, *, kinds: tuple[str, ...] = (),
                     sets: tuple[str, ...] = (), ignore: bool = False) -> tuple[str, ...]:
        if ignore and (kinds or sets):
            return ("a term is ignore: true OR kinds/sets, not both",)
        problems: list[str] = []
        try:
            self._check_kinds(kinds)
        except UnknownKindError as exc:
            problems.append(str(exc))
        try:
            self._check_sets(sets)
        except UnknownSetError as exc:
            problems.append(str(exc))
        return tuple(problems)
```

Run again to verify PASS: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_classifier_vocabulary.py -v`

- [ ] **Step 3: Commit the `vocabulary.py` addition on its own**

```bash
git add wing_parser/classifier/vocabulary.py tests/test_classifier_vocabulary.py && git commit -m "$(cat <<'EOF'
feat(classifier): add Vocabulary.dry_run_set/dry_run_term

Non-writing checks vocab_changes.validate calls to decide whether an
AI-proposed change could be written -- the same rules put_set/put_term
enforce, expressed as a problem list instead of an exception, so a UI
can show why a proposal is invalid rather than catch-and-format.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 4: Write the failing tests for `vocab_changes.py`** — `tests/test_classifier_vocab_changes.py`

```python
"""Spec §8.2: validate a proposed change before anything is written.
Nothing here calls a model -- propose_changes is exercised with a fake
Provider (see the assistant's own Qt test for the worker-threaded path).
"""
from __future__ import annotations

import pytest

from wing_parser.classifier import vocab_changes, vocabulary as vocab


@pytest.fixture
def directory(tmp_path):
    return tmp_path


@pytest.fixture
def loaded(directory):
    return vocab.Vocabulary.load(directory)


# -- parse --------------------------------------------------------------


def test_parse_reads_every_field():
    change = vocab_changes.parse({
        "op": "add", "target": "term", "key": "cajon",
        "before": None, "after": {"kinds": ["drums.pad"]}, "reason": "a hand drum",
    })
    assert change.op == "add" and change.key == "cajon" and change.after["kinds"] == ["drums.pad"]


def test_parse_raises_naming_a_missing_field():
    with pytest.raises(ValueError, match="reason"):
        vocab_changes.parse({"op": "add", "target": "term", "key": "x"})


# -- validate: add/edit ---------------------------------------------------


def test_a_valid_add_term_validates_clean(loaded):
    change = vocab_changes.Change(op="add", target="term", key="cajon", before=None,
                                  after={"kinds": ["drums.pad"]}, reason="a hand drum")
    result = vocab_changes.validate(change, loaded)
    assert result.valid and result.problems == ()


def test_an_unknown_kind_is_invalid_with_a_problem_named(loaded):
    change = vocab_changes.Change(op="add", target="term", key="x", before=None,
                                  after={"kinds": ["nonsense.kind"]}, reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid
    assert any("nonsense.kind" in p for p in result.problems)


def test_a_cycle_making_edit_is_invalid(loaded):
    loaded.put_set("loop a", label="Loop A", sets=("band",))
    change = vocab_changes.Change(op="edit", target="set", key="band", before=None,
                                  after={"label": "Band", "kinds": [], "sets": ["drum kit", "loop a"]},
                                  reason="oops")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid


# -- validate: delete -----------------------------------------------------


def test_deleting_an_existing_term_is_valid(loaded):
    change = vocab_changes.Change(op="delete", target="term", key="mc", before=None,
                                  after=None, reason="unused")
    assert vocab_changes.validate(change, loaded).valid


def test_deleting_a_missing_key_is_invalid(loaded):
    change = vocab_changes.Change(op="delete", target="term", key="no such term",
                                  before=None, after=None, reason="unused")
    result = vocab_changes.validate(change, loaded)
    assert not result.valid


# -- apply ----------------------------------------------------------------


def test_apply_writes_an_add_with_ai_approved_origin(loaded, directory):
    change = vocab_changes.Change(op="add", target="term", key="cajon", before=None,
                                  after={"kinds": ["drums.pad"]}, reason="a hand drum")
    vocab_changes.apply(change, loaded)
    reloaded = vocab.Vocabulary.load(directory)
    terms = {t.key: t for t in reloaded.terms()}
    assert terms["cajon"].kinds == ("drums.pad",)
    assert terms["cajon"].origin == "ai-approved"


def test_apply_writes_a_delete(loaded, directory):
    change = vocab_changes.Change(op="delete", target="term", key="hoa tươi",
                                  before=None, after=None, reason="unused")
    vocab_changes.apply(change, loaded)
    reloaded = vocab.Vocabulary.load(directory)
    assert "hoa tươi" not in {t.key for t in reloaded.terms()}


# -- propose_changes (fake provider, no model) -----------------------------


class _FakeProvider:
    def __init__(self, reply):
        self._reply = reply

    def complete_json(self, system, user, schema):
        return self._reply


def test_propose_changes_parses_the_json_string_field(loaded):
    import json

    reply = {"changes_json": json.dumps([
        {"op": "add", "target": "term", "key": "cajon", "before": None,
         "after": {"kinds": ["drums.pad"]}, "reason": "a hand drum"},
    ])}
    changes = vocab_changes.propose_changes(
        _FakeProvider(reply), vocabulary=loaded, known_kinds=("drums.pad",))
    assert len(changes) == 1 and changes[0].key == "cajon"


def test_propose_changes_raises_on_a_non_json_string():
    with pytest.raises(ValueError, match="did not parse"):
        vocab_changes.propose_changes(
            _FakeProvider({"changes_json": "not json"}),
            vocabulary=vocab.Vocabulary.load(None) if False else None,
            known_kinds=(),
        )
```

The last test passes `vocabulary=None` deliberately — `propose_changes` must fail on the malformed JSON
BEFORE it ever touches `vocabulary` (parsing happens first); if this test needs a real `Vocabulary`, it
means `propose_changes` reads `vocabulary` too early and the ordering is wrong.

- [ ] **Step 5: Run the tests to verify they fail**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_classifier_vocab_changes.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.classifier.vocab_changes'`

- [ ] **Step 6: Write `vocab_changes.py`**

```python
"""Validate and apply an AI-proposed vocabulary change (design spec §8.2).

Two ways in share this module: the Vocabulary window's instruction box
and the Terms step's "AI: propose for unread rows" button (Task 7). Both
call `propose_changes`, both hand every returned Change to `validate`
before showing it, and only `apply` (called per ticked change, from
Apply, never automatically -- F11) writes anything.

The prompt lives here, not in a widget, so it is reviewed and tuned in
one place. `provider.py`'s `complete_json` dialect is flat
strings/numbers only (read that module's own docstring) -- a list of
change objects cannot be expressed in it, so the model is asked for one
string field, `changes_json`, holding a JSON-encoded array; this module
decodes it with `json.loads`, not a second schema layer.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

VALID_OPS = ("add", "edit", "delete")
VALID_TARGETS = ("set", "term")

SYSTEM_PROMPT = (
    "You edit a cue-sheet vocabulary that maps terms and sets to "
    "console-strip kinds for a live-sound tool. Reply with one field, "
    "changes_json: a JSON-encoded string containing a list of objects, "
    'each shaped {"op": "add"|"edit"|"delete", "target": "set"|"term", '
    '"key": str, "before": object|null, "after": object|null, '
    '"reason": str}. For a set, "after" is {"label": str, "kinds": '
    '[str], "sets": [str]}; for a term it is {"kinds": [str], "sets": '
    '[str], "ignore": bool, "match": "exact"|"word"}. Only name a kind '
    "already in the known-kinds list given to you -- never invent one. "
    "You propose; a human approves every change before anything is "
    "written."
)

CHANGES_SCHEMA = {
    "type": "object",
    "properties": {"changes_json": {"type": "string"}},
    "required": ["changes_json"],
}


@dataclass(frozen=True)
class Change:
    op: str
    target: str
    key: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None
    reason: str


@dataclass(frozen=True)
class Validated:
    change: Change
    problems: tuple[str, ...]

    @property
    def valid(self) -> bool:
        return not self.problems


def parse(raw: dict) -> Change:
    missing = [field for field in ("op", "target", "key", "reason") if field not in raw]
    if missing:
        raise ValueError(f"missing field(s): {', '.join(missing)}")
    return Change(
        op=str(raw["op"]), target=str(raw["target"]), key=str(raw["key"]),
        before=raw.get("before"), after=raw.get("after"), reason=str(raw["reason"]),
    )


def validate(change: Change, vocabulary) -> Validated:
    problems: list[str] = []
    if change.op not in VALID_OPS:
        problems.append(f"unknown op {change.op!r}")
    if change.target not in VALID_TARGETS:
        problems.append(f"unknown target {change.target!r}")
    if problems:
        return Validated(change, tuple(problems))

    if change.op == "delete":
        exists = (
            any(s.key == change.key for s in vocabulary.sets())
            if change.target == "set" else
            any(t.key == change.key for t in vocabulary.terms())
        )
        if not exists:
            problems.append(f"no such {change.target} {change.key!r} to delete")
        return Validated(change, tuple(problems))

    after = change.after or {}
    kinds = tuple(after.get("kinds", ()))
    sets_ = tuple(after.get("sets", ()))
    if change.target == "set":
        problems.extend(vocabulary.dry_run_set(change.key, kinds=kinds, sets=sets_))
    else:
        ignore = bool(after.get("ignore", False))
        problems.extend(vocabulary.dry_run_term(change.key, kinds=kinds, sets=sets_, ignore=ignore))
    return Validated(change, tuple(problems))


def apply(change: Change, vocabulary, *, origin: str = "ai-approved") -> None:
    """Write one already-validated change. Callers check `.valid` first;
    vocabulary.py's own validation is the last line of defense here, not
    the first -- this function does not re-check."""
    if change.op == "delete":
        (vocabulary.delete_set if change.target == "set" else vocabulary.delete_term)(change.key)
        return
    after = change.after or {}
    if change.target == "set":
        vocabulary.put_set(
            change.key, label=str(after.get("label", change.key)),
            kinds=tuple(after.get("kinds", ())), sets=tuple(after.get("sets", ())),
            origin=origin,
        )
    else:
        vocabulary.put_term(
            change.key, kinds=tuple(after.get("kinds", ())),
            sets=tuple(after.get("sets", ())), ignore=bool(after.get("ignore", False)),
            match=str(after.get("match", "word")), origin=origin,
        )


def build_user_prompt(instruction: str, fragments: tuple[str, ...], vocabulary,
                      known_kinds: tuple[str, ...]) -> str:
    parts = [
        "Known kinds: " + ", ".join(known_kinds),
        "Current sets: " + ", ".join(s.key for s in vocabulary.sets()),
        "Current terms: " + ", ".join(t.key for t in vocabulary.terms()),
    ]
    if instruction:
        parts.append(f"Instruction: {instruction}")
    if fragments:
        parts.append("Unresolved fragments: " + "; ".join(fragments))
    return "\n".join(parts)


def propose_changes(provider, *, instruction: str = "", fragments: tuple[str, ...] = (),
                    vocabulary, known_kinds: tuple[str, ...]) -> list[Change]:
    from wing_parser.classifier.provider import complete_json

    user = build_user_prompt(instruction, fragments, vocabulary, known_kinds)
    reply = complete_json(provider, SYSTEM_PROMPT, user, CHANGES_SCHEMA)
    try:
        raw_changes = json.loads(reply["changes_json"])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"changes_json did not parse as JSON: {exc}") from exc
    if not isinstance(raw_changes, list):
        raise ValueError("changes_json must decode to a JSON list")
    return [parse(item) for item in raw_changes]
```

- [ ] **Step 7: Run the tests to verify they pass**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_classifier_vocab_changes.py -v`
Expected: PASS, all tests.

- [ ] **Step 8: Commit `vocab_changes.py` on its own**

```bash
git add wing_parser/classifier/vocab_changes.py tests/test_classifier_vocab_changes.py && git commit -m "$(cat <<'EOF'
feat(classifier): add vocab_changes -- validate/apply/propose

Spec §8.2. parse/validate/apply carry no model dependency and are fully
covered by plain pytest; propose_changes is the one function that calls
a Provider, asking for one string field (changes_json) because
provider.py's schema dialect is flat strings/numbers only -- a list of
change objects is decoded from that string with json.loads, not a
second schema layer.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 9: Add the assistant's strings** — append to `wing_parser/ui/texts_import.py`'s `IMPORT_TEXTS`
      dict (Task 5's file)

```python
    "vocabulary.tab.assistant": "Assistant",
    "vocabulary.assistant.placeholder": (
        "e.g. \"my drum kit has no kick out, add a second tom\", "
        "\"cajon is percussion\""
    ),
    "vocabulary.assistant.propose": "Propose",
    "vocabulary.assistant.cancel": "Cancel",
    "vocabulary.assistant.apply": "Apply ticked changes",
    "vocabulary.assistant.running": "Asking the model...",
    "vocabulary.assistant.cancelled": "Cancelled — nothing was applied.",
    "vocabulary.assistant.timeout": "The model did not answer within {seconds} s.",
    "vocabulary.assistant.busy": "A model request is already running — cancel it or wait.",
    "vocabulary.assistant.col.apply": "",
    "vocabulary.assistant.col.before": "Before",
    "vocabulary.assistant.col.after": "After",
    "vocabulary.assistant.col.reason": "Reason",
```

- [ ] **Step 10: Write the failing Qt test for the assistant** — `tests/test_ui_vocabulary_assistant.py`

```python
"""Spec §8.2: propose -> validate -> tick -> Apply, never a write before
Apply (F11). A fake Provider stands in for the model -- no network, no
key, ever."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("PySide6.QtWidgets")


class _FakeProvider:
    def __init__(self, reply):
        self._reply = reply

    def complete_json(self, system, user, schema):
        return self._reply


def _mixed_reply():
    return {"changes_json": json.dumps([
        {"op": "add", "target": "term", "key": "cajon", "before": None,
         "after": {"kinds": ["drums.pad"]}, "reason": "a hand drum"},
        {"op": "add", "target": "term", "key": "x", "before": None,
         "after": {"kinds": ["nonsense.kind"]}, "reason": "bad kind"},
    ])}


@pytest.fixture
def assistant(qt_app, tmp_path):
    from wing_parser.classifier import vocabulary as vocab_module
    from wing_parser.ui.vocabulary_assistant import VocabularyAssistant

    vocabulary = vocab_module.Vocabulary.load(tmp_path)
    applied = []
    widget = VocabularyAssistant(
        vocabulary, lambda: _FakeProvider(_mixed_reply()), lambda: applied.append(True))
    widget._tmp_path = tmp_path  # test-only stash, not a public seam
    widget._applied_log = applied
    return widget


def test_a_mixed_valid_invalid_proposal_only_lets_the_valid_one_be_ticked(assistant, settle):
    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant._propose()
    assert assistant.table.rowCount() == 2
    assert assistant._checks[0].isEnabled() and assistant._checks[0].isChecked()
    assert not assistant._checks[1].isEnabled()


def test_apply_writes_only_the_ticked_valid_change_and_nothing_before(assistant):
    from wing_parser.classifier import vocabulary as vocab_module

    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant._propose()
    assert assistant._tmp_path is not None
    before = vocab_module.Vocabulary.load(assistant._tmp_path).terms()
    assert "cajon" not in {t.key for t in before}   # nothing written before Apply

    assistant._checks[1].setEnabled(True)   # tampering with a disabled box, proving it's ignored anyway
    assistant._checks[1].setChecked(True)
    assistant._apply()

    after = vocab_module.Vocabulary.load(assistant._tmp_path).terms()
    keys = {t.key: t for t in after}
    assert keys["cajon"].origin == "ai-approved"
    assert "x" not in keys   # the invalid one, even force-ticked, is never applied
    assert assistant._applied_log == [True]


def test_propose_for_fragments_is_the_terms_steps_entry_point(assistant):
    assistant._call.run = lambda kind, fn, *a, on_success: on_success(fn(*a)) or True
    assistant.propose_for_fragments(("tốp múa",))
    assert assistant.table.rowCount() == 2   # the fake provider always returns the same fixed reply
```

Note the `_call.run` monkeypatch runs the worker call SYNCHRONOUSLY on the calling thread instead of a
`QThread` — the same shortcut `tests/test_ui_write_dialogs.py` and `tests/test_ui_settings.py` use for a
proposal-shaped call whose only job under test is "did the right thing get built", not thread timing;
`settle` is unused in the first test on purpose (nothing crosses a thread boundary) and may be dropped from
that signature if the linter flags it as unused — keep it if the project's own convention keeps unused
fixtures for readability (check an existing test with the same shape first).

- [ ] **Step 11: Run the test to verify it fails**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_vocabulary_assistant.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.vocabulary_assistant'`

- [ ] **Step 12: Write `vocabulary_assistant.py`**

```python
"""The Vocabulary window's Assistant tab: propose, validate, tick, Apply.

Two ways in (design spec §8.2) share this class: the instruction box
below, and the Terms step's "AI: propose for unread rows" button (Task
7), which calls `propose_for_fragments` on a `VocabularyWindow` opened
with `initial_fragments` set (see vocabulary_window.py). Neither writes
anything before Apply (F11) -- `_show_proposal` only ever populates the
table; `_apply` is the sole call to `vocab_changes.apply`.
"""

from __future__ import annotations

from functools import partial

from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QPlainTextEdit, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
)

from wing_parser.classifier import provider_errors, vocab_changes
from wing_parser.classifier.matcher import known_kinds
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.texts import text
from wing_parser.ui.workers import CallRunner

_COLUMNS = ("vocabulary.assistant.col.apply", "vocabulary.assistant.col.before",
           "vocabulary.assistant.col.after", "vocabulary.assistant.col.reason")


class VocabularyAssistant(QWidget):
    def __init__(self, vocabulary, provider_factory, on_applied) -> None:
        super().__init__()
        self._vocabulary = vocabulary
        self._provider_factory = provider_factory
        self._on_applied = on_applied
        self._validated: list[vocab_changes.Validated] = []
        self._checks: list[QCheckBox] = []

        self.instruction_edit = QPlainTextEdit()
        self.instruction_edit.setPlaceholderText(text("vocabulary.assistant.placeholder"))
        self.propose_button = QPushButton(text("vocabulary.assistant.propose"))
        self.propose_button.clicked.connect(self._propose)
        self.cancel_button = QPushButton(text("vocabulary.assistant.cancel"))
        self.cancel_button.setVisible(False)
        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self._runner = CallRunner(self)
        self._call = ButtonRunner(
            runner=self._runner, primary=self.propose_button, cancel=self.cancel_button,
            report=self.status_label.setText,
            running=text("vocabulary.assistant.running"),
            cancelled=text("vocabulary.assistant.cancelled"),
            timeout_text=text("vocabulary.assistant.timeout"),
            busy_text=text("vocabulary.assistant.busy"), on_error=self._failed,
        )
        self.cancel_button.clicked.connect(self._call.cancel)

        self.table = QTableWidget(0, len(_COLUMNS))
        self.table.setHorizontalHeaderLabels([text(key) for key in _COLUMNS])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.apply_button = QPushButton(text("vocabulary.assistant.apply"))
        self.apply_button.clicked.connect(self._apply)

        buttons = QHBoxLayout()
        buttons.addWidget(self.propose_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.instruction_edit)
        layout.addLayout(buttons)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table)
        layout.addWidget(self.apply_button)

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary

    def propose_for_fragments(self, fragments: tuple[str, ...]) -> bool:
        return self._start(fragments=fragments, instruction="")

    def _propose(self) -> None:
        self._start(fragments=(), instruction=self.instruction_edit.toPlainText().strip())

    def _start(self, *, fragments, instruction) -> bool:
        provider = self._provider_factory()
        call = partial(
            vocab_changes.propose_changes, instruction=instruction, fragments=fragments,
            vocabulary=self._vocabulary, known_kinds=known_kinds("channels"),
        )
        return self._call.run("guesses", call, provider, on_success=self._show_proposal)

    def _show_proposal(self, changes) -> None:
        self._validated = [vocab_changes.validate(c, self._vocabulary) for c in changes]
        self._checks = []
        self.table.setRowCount(len(self._validated))
        for r, validated in enumerate(self._validated):
            change = validated.change
            reason = change.reason if validated.valid else (
                f"{change.reason} — {'; '.join(validated.problems)}"
            )
            check = QCheckBox()
            check.setEnabled(validated.valid)
            check.setChecked(validated.valid)
            self.table.setCellWidget(r, 0, check)
            self.table.setItem(r, 1, QTableWidgetItem("" if change.before is None else str(change.before)))
            self.table.setItem(r, 2, QTableWidgetItem("" if change.after is None else str(change.after)))
            self.table.setItem(r, 3, QTableWidgetItem(reason))
            self._checks.append(check)

    def _apply(self) -> None:
        applied = 0
        for check, validated in zip(self._checks, self._validated):
            if check.isChecked() and validated.valid:
                vocab_changes.apply(validated.change, self._vocabulary)
                applied += 1
        if applied:
            self._on_applied()

    def _failed(self, exc: Exception) -> None:
        _code, message = provider_errors.classify(exc)
        self.status_label.setText(message)
```

- [ ] **Step 13: Run the assistant test to verify it passes**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_vocabulary_assistant.py -v`
Expected: PASS, all 3 tests.

- [ ] **Step 14: Wire the Assistant as `VocabularyWindow`'s third tab** — modify
      `wing_parser/ui/vocabulary_window.py` (Task 5's file)

```python
from wing_parser.ui.vocabulary_assistant import VocabularyAssistant


class VocabularyWindow(QDialog):
    def __init__(self, parent=None, *, directory=None, initial_fragments: tuple[str, ...] = ()) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("vocabulary.title"))
        self.setMinimumSize(640, 420)
        self._directory = directory
        self.vocabulary = vocab_module.Vocabulary.load(directory)

        self.sets_tab = VocabularySetsTab(self.vocabulary, self._reload)
        self.terms_tab = VocabularyTermsTab(self.vocabulary, self._reload)
        self.assistant_tab = VocabularyAssistant(self.vocabulary, self._provider_factory, self._reload)
        self.tabs = QTabWidget()
        self.tabs.addTab(self.sets_tab, text("vocabulary.tab.sets"))
        self.tabs.addTab(self.terms_tab, text("vocabulary.tab.terms"))
        self.tabs.addTab(self.assistant_tab, text("vocabulary.tab.assistant"))

        close_button = QPushButton(text("vocabulary.close"))
        close_button.clicked.connect(self.accept)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)
        layout.addLayout(buttons)

        if initial_fragments:
            self.tabs.setCurrentWidget(self.assistant_tab)
            self.assistant_tab.propose_for_fragments(initial_fragments)

    def _provider_factory(self):
        from wing_parser import config
        from wing_parser.classifier.provider import make_provider, resolve_config

        return make_provider(resolve_config(config.knowledge_dir()))

    def _reload(self) -> None:
        self.vocabulary = vocab_module.Vocabulary.load(self._directory)
        self.sets_tab.set_vocabulary(self.vocabulary)
        self.terms_tab.set_vocabulary(self.vocabulary)
        self.assistant_tab.set_vocabulary(self.vocabulary)
```

- [ ] **Step 15: Add one Qt test proving the third tab is really wired** — append to
      `tests/test_ui_vocabulary_window.py` (Task 5's file)

```python
def test_the_window_has_an_assistant_tab_and_it_shares_the_reload(qt_app, tmp_path):
    from wing_parser.ui.vocabulary_window import VocabularyWindow

    window = VocabularyWindow(directory=tmp_path)
    assert window.tabs.indexOf(window.assistant_tab) >= 0
    assert window.assistant_tab._vocabulary is window.vocabulary
```

- [ ] **Step 16: Run everything touched, then the full suite**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_classifier_vocabulary.py tests/test_classifier_vocab_changes.py tests/test_ui_vocabulary_assistant.py tests/test_ui_vocabulary_window.py -v`
then `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`.
Paste both results.

- [ ] **Step 17: Commit the UI half**

```bash
git add wing_parser/ui/vocabulary_assistant.py wing_parser/ui/vocabulary_window.py wing_parser/ui/texts_import.py tests/test_ui_vocabulary_assistant.py tests/test_ui_vocabulary_window.py && git commit -m "$(cat <<'EOF'
feat(ui): add the Vocabulary window's Assistant tab

Spec §8.2/F11: propose (instruction box or propose_for_fragments),
validate every change, show it ticked-or-greyed with why, and write
only on Apply -- never before. VocabularyWindow gains an
initial_fragments constructor arg so Task 7's Terms-step button can
open straight into a running proposal.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** that `_apply` truly never runs for an unticked or invalid change even if a
test force-enables/-checks its checkbox (`test_apply_writes_only_the_ticked_valid_change_and_nothing_before`
IS this check — confirm it actually exercises the tamper path, not just the happy path); that
`provider.py`'s `complete_json` really validates only `"string"`/`"number"` property types (the reason
`changes_json` is a string, not a nested schema) by re-reading `_check()` in that file.

---

### Task 7: redesign the Terms step — `terms_row.py`, live re-resolve, Ignore (remember)

**Files:**
- Create: `wing_parser/ui/terms_row.py`
- Modify: `wing_parser/ui/terms_step.py` (rewritten in full; Task 5 added a transitional
  `vocabulary_button` to the OLD file — this task supersedes that edit as part of the rewrite),
  `wing_parser/ui/import_steps.py`, `wing_parser/ui/import_controller.py` (144 lines),
  `tests/test_import_controller.py`, `tests/test_ui_import_page.py`

**What this task removes, and why.** The pre-wave-4 `TermsStep` prefilled a plain `QLineEdit` per row from
`ic.guesses_for` (one model call per unresolved term) and wrote through `ic.record_term` →
`cache.remember(..., "cuesheet", Classification(...))` — the OLD single-`kind` shape. Design spec §4 says
outright: **"The existing `load_guesses` prefill is replaced by the §8.2 proposal list."** This task deletes
`ic.guesses_for` and `ic.record_term` from `import_controller.py` (nothing else calls either — confirmed by
`grep -rn "ic\.guesses_for\|ic\.record_term" wing_parser/ tests/` before this task showed only
`terms_step.py` and `test_import_controller.py`) and removes their three now-orphaned tests. `ic.context_for`
is KEPT — nothing about it changes; each `TermsRow` still shows up to two example rows from the sheet for
its fragment, exactly as before, because that context is still useful and Task 6 did not touch it.

**Interfaces:**
- Consumes: `keywords.Resolution` (Task 1); `vocabulary.Vocabulary`/`put_term` (Task 2);
  `build.resolve_fragment` (Task 3); `vocabulary_window.VocabularyWindow` (Tasks 5-6, specifically its
  `initial_fragments` constructor argument); `matcher.known_kinds` (existing); `ic.unresolved`/`ic.context_for`
  (existing, unchanged).
- Produces:
  ```python
  # wing_parser/ui/terms_row.py
  class TermsRow(QGroupBox):
      def __init__(self, fragment: str, *, vocabulary, known_kinds, known_sets,
                   context_lines: tuple[str, ...] = (), on_written: Callable[[], None]) -> None: ...
      def set_vocabulary(self, vocabulary) -> None: ...
      def mark_resolved(self) -> None: ...        # re-resolve found this row now resolves elsewhere
      state: str                                   # "pending" | "recorded" | "skipped" | "resolved"
      key_edit: QLineEdit; word_match_check: QCheckBox
      kinds_list: QListWidget; sets_list: QListWidget
      record_button: QPushButton; ignore_button: QPushButton; skip_button: QPushButton

  # wing_parser/ui/terms_step.py — same public seams import_page.py already delegates to
  class TermsStep(QWidget):
      def __init__(self) -> None: ...              # no provider_factory/fail/runner/report anymore
      directory: Path | None
      def populate(self, result) -> None: ...
      def set_rows(self, rows: tuple) -> None: ...
      def record_button_for(self, term: str) -> QPushButton: ...
      def skip_button_for(self, term: str) -> QPushButton: ...
      def kind_editor_for(self, term: str) -> QListWidget: ...   # WAS QLineEdit; now the picker
      def term_row_state(self, term: str) -> str: ...
  ```
  `import_page.py`'s four delegating methods (`record_button_for`, `skip_button_for`, `kind_editor_for`,
  `term_row_state`) are unchanged — they already just forward to `self.terms_step.*` — only what
  `kind_editor_for` returns changes shape.

- [ ] **Step 1: Remove the two superseded functions from `import_controller.py`**

Delete `guesses_for` and `record_term` in full from `wing_parser/ui/import_controller.py`. Leave `sample`,
`proposal_for`, `read_with`, `build_result`, `preview_text`, `unresolved`, `context_for` exactly as Task 3
left them.

- [ ] **Step 2: Remove their three orphaned tests** — `tests/test_import_controller.py`

Delete `test_guesses_swallow_errors_per_term`, `test_guesses_respect_the_kill_switch` and
`test_record_term_writes_through_cache` in full. `test_context_for_collects_up_to_two_rows_per_term` and
every other test in that file stay untouched.

- [ ] **Step 3: Run to confirm the deletions leave a clean, green file**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_import_controller.py -v`
Expected: PASS, every remaining test.

- [ ] **Step 4: Write `terms_row.py`**

```python
"""One Terms-step row: an unresolved fragment, taught in one click.

Record writes through vocabulary.put_term (kinds and/or sets picked from
lists built off patterns.yaml's known kinds and the current sets --
never typed, so nothing expects: would refuse can be saved, W6). Ignore
(remember) writes put_term(..., ignore=True). Skip writes nothing --
this import only (design spec §4). The key field prefills with the
WHOLE fragment; "match inside a sentence" auto-ticks the moment the
operator shortens it below the fragment's own length, because a
shortened key almost always means "match this word wherever it
appears", not "this exact sentence, verbatim" -- the operator can still
tick it by hand for an unshortened key (e.g. to make a single word like
"trống" match inside a longer sibling fragment too).
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QPushButton, QVBoxLayout,
)

from wing_parser.ui.texts import text


class TermsRow(QGroupBox):
    def __init__(self, fragment: str, *, vocabulary, known_kinds, known_sets,
                 context_lines: tuple[str, ...] = (), on_written: Callable[[], None]) -> None:
        super().__init__(fragment)
        self.fragment = fragment
        self._vocabulary = vocabulary
        self._on_written = on_written
        self.state = "pending"

        self.key_edit = QLineEdit(fragment)
        self.key_edit.textChanged.connect(self._auto_check_word_match)
        self.word_match_check = QCheckBox(text("import.terms.match_word"))

        self.kinds_list = QListWidget()
        self.kinds_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for kind in known_kinds:
            self.kinds_list.addItem(QListWidgetItem(kind))

        self.sets_list = QListWidget()
        self.sets_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        for key in known_sets:
            self.sets_list.addItem(QListWidgetItem(key))

        self.record_button = QPushButton(text("import.record"))
        self.record_button.clicked.connect(self._record)
        self.ignore_button = QPushButton(text("import.terms.ignore_remember"))
        self.ignore_button.clicked.connect(self._ignore)
        self.skip_button = QPushButton(text("import.skip"))
        self.skip_button.clicked.connect(self._skip)

        top = QHBoxLayout()
        top.addWidget(QLabel(text("import.terms.key")))
        top.addWidget(self.key_edit, 1)
        top.addWidget(self.word_match_check)

        context_label = QLabel("\n".join(context_lines))
        context_label.setWordWrap(True)

        pickers = QHBoxLayout()
        pickers.addWidget(self.kinds_list)
        pickers.addWidget(self.sets_list)

        buttons = QHBoxLayout()
        buttons.addWidget(self.record_button)
        buttons.addWidget(self.ignore_button)
        buttons.addWidget(self.skip_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(context_label)
        layout.addLayout(pickers)
        layout.addLayout(buttons)

    def set_vocabulary(self, vocabulary) -> None:
        self._vocabulary = vocabulary

    def mark_resolved(self) -> None:
        """A sibling row's Record/Ignore made this fragment resolve too
        (design spec §4: 're-resolved immediately, so one keyword can
        clear several rows below it'). Disable, do not remove -- the
        operator can still see what happened to it."""
        self.state = "resolved"
        self.setEnabled(False)

    def _picked_kinds(self) -> tuple[str, ...]:
        return tuple(item.text() for item in self.kinds_list.selectedItems())

    def _picked_sets(self) -> tuple[str, ...]:
        return tuple(item.text() for item in self.sets_list.selectedItems())

    def _match_mode(self) -> str:
        return "word" if self.word_match_check.isChecked() else "exact"

    def _auto_check_word_match(self, current_text: str) -> None:
        if len(current_text.strip()) < len(self.fragment):
            self.word_match_check.setChecked(True)

    def _record(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            return
        self._vocabulary.put_term(
            key, kinds=self._picked_kinds(), sets=self._picked_sets(),
            match=self._match_mode(), origin="manual",
        )
        self.state = "recorded"
        self.setEnabled(False)
        self._on_written()

    def _ignore(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            return
        self._vocabulary.put_term(key, ignore=True, match=self._match_mode(), origin="manual")
        self.state = "recorded"
        self.setEnabled(False)
        self._on_written()

    def _skip(self) -> None:
        self.state = "skipped"
        self.setEnabled(False)
```

- [ ] **Step 5: Rewrite `terms_step.py` in full**

```python
"""The Terms step: one row per unresolved fragment, taught in one click.

Each row (terms_row.TermsRow) owns its own key field, "match inside a
sentence" checkbox, kind/set pickers and Record/Ignore(remember)/Skip
buttons -- moved there so this file stays under the 200-line ceiling
(docs/tech-debt.md#d-29's own reason). Record and Ignore write straight
through vocabulary.py; after either, every remaining PENDING row is
re-resolved against the reloaded vocabulary, because one new keyword can
clear several rows below it (design spec §4). The pre-wave-4
load_guesses/_apply_guesses flow is gone -- "AI: propose for unread
rows" opens the Vocabulary window's Assistant tab (Tasks 5-6)
pre-loaded with every still-pending fragment.
"""

from __future__ import annotations

from PySide6.QtWidgets import QPushButton, QScrollArea, QVBoxLayout, QWidget

from wing_parser.classifier import vocabulary as vocab_module
from wing_parser.classifier.matcher import known_kinds
from wing_parser.showcontext.ingest import build
from wing_parser.ui import import_controller as ic
from wing_parser.ui.terms_row import TermsRow
from wing_parser.ui.texts import text


class TermsStep(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self._rows: dict[str, TermsRow] = {}
        self._result = None
        self._rows_data: tuple = ()
        self._vocabulary = None
        # record/ignore's write target; tests point this at tmp_path, None = cache default.
        self.directory = None

        self.vocabulary_button = QPushButton(text("vocabulary.open_button"))
        self.vocabulary_button.clicked.connect(self._open_vocabulary)
        self.ai_propose_button = QPushButton(text("import.terms.ai_propose"))
        self.ai_propose_button.clicked.connect(self._ai_propose)

        self._rows_container = QWidget()
        self._rows_layout = QVBoxLayout(self._rows_container)
        self._rows_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._rows_container)

        layout = QVBoxLayout(self)
        layout.addWidget(self.vocabulary_button)
        layout.addWidget(self.ai_propose_button)
        layout.addWidget(scroll, 1)

    # -- building -----------------------------------------------------------

    def populate(self, result) -> None:
        """One row per unresolved fragment; rebuilt fresh for every result."""
        for row in self._rows.values():
            row.setParent(None)
        self._rows.clear()
        self._result = result
        self._vocabulary = vocab_module.Vocabulary.load(self.directory)
        kinds = known_kinds("channels")
        sets_ = tuple(s.key for s in self._vocabulary.sets())
        terms = ic.unresolved(result)
        context_by_term = ic.context_for(terms, self._rows_data)
        for fragment in terms:
            row = TermsRow(
                fragment, vocabulary=self._vocabulary, known_kinds=kinds, known_sets=sets_,
                context_lines=tuple(context_by_term.get(fragment, ())),
                on_written=self._reresolve,
            )
            self._rows_layout.insertWidget(self._rows_layout.count() - 1, row)
            self._rows[fragment] = row

    def set_rows(self, rows: tuple) -> None:
        self._rows_data = rows

    # -- re-resolution ----------------------------------------------------

    def _reresolve(self) -> None:
        self._vocabulary = vocab_module.Vocabulary.load(self.directory)
        for fragment, row in self._rows.items():
            if row.state != "pending":
                continue
            row.set_vocabulary(self._vocabulary)
            resolution = build.resolve_fragment(fragment, self._vocabulary)
            if resolution.kinds or resolution.ignored:
                row.mark_resolved()

    # -- AI / Vocabulary entry points --------------------------------------

    def _open_vocabulary(self) -> None:
        from wing_parser.ui.vocabulary_window import VocabularyWindow

        VocabularyWindow(self, directory=self.directory).exec()
        self._reresolve()

    def _ai_propose(self) -> None:
        from wing_parser.ui.vocabulary_window import VocabularyWindow

        pending = tuple(f for f, row in self._rows.items() if row.state == "pending")
        VocabularyWindow(self, directory=self.directory, initial_fragments=pending).exec()
        self._reresolve()

    # -- test seams -----------------------------------------------------------

    def record_button_for(self, term: str) -> QPushButton:
        return self._rows[term].record_button

    def skip_button_for(self, term: str) -> QPushButton:
        return self._rows[term].skip_button

    def kind_editor_for(self, term: str):
        return self._rows[term].kinds_list

    def term_row_state(self, term: str) -> str:
        return self._rows[term].state
```

- [ ] **Step 6: Update `import_steps.py`'s `_terms` wiring**

Replace the `_terms` function:

```python
def _terms(page) -> QWidget:
    page.terms_step = TermsStep()
    page.preview_button = QPushButton(text("import.preview"))
    page.preview_button.clicked.connect(lambda: show_preview(page))

    step = QWidget()
    layout = QVBoxLayout(step)
    layout.addWidget(page.terms_step)
    layout.addWidget(page.preview_button)
    return step
```

(`page.load_guesses_button` is no longer set — nothing else in `import_page.py`/`import_steps.py`
references it; confirm with `grep -rn "load_guesses_button" wing_parser/` after this edit shows nothing.)

- [ ] **Step 7: Add the two new strings** — append to `wing_parser/ui/texts_import.py`'s `IMPORT_TEXTS`

```python
    "import.terms.key": "Key",
    "import.terms.match_word": "match inside a sentence",
    "import.terms.ignore_remember": "Ignore (remember)",
    "import.terms.ai_propose": "AI: propose for unread rows",
```

- [ ] **Step 8: Rewrite the affected tests in `tests/test_ui_import_page.py`**

Delete `test_record_writes_vocabulary_only_on_click` (163-194), `test_raising_provider_factory_degrades_to_status_label`
(215-233) and `test_guesses_cancel_leaves_the_terms_step_retriable` (446-478) in full — the first two test a
write/failure path that moved entirely into `vocabulary.put_term`/`TermsRow` (no provider call happens on
this step any more) and the Vocabulary Assistant (already covered by Task 6's `test_ui_vocabulary_assistant.py`);
`test_a_slow_proposal_times_out_with_a_message_naming_seconds` and
`test_starting_a_second_call_while_one_runs_is_queue_rejected` test the PICK step's `proposal_for` call and
are untouched by this task.

Replace `test_skip_marks_the_row_without_writing` (still valid, drop the now-nonexistent `guesses_for`
monkeypatch) and add four new tests in its place:

```python
def test_skip_marks_the_row_without_writing(page, tmp_path, monkeypatch):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'múa rối'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("múa rối",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())
    page.skip_button_for("múa rối").click()
    assert page.term_row_state("múa rối") == "skipped"
    assert not (tmp_path / "classifier.yaml").exists()


def test_record_writes_the_picked_kinds_through_vocabulary_put_term(page, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'ca trống'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("ca trống",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())
    vocab = tmp_path / "classifier.yaml"

    assert page.term_row_state("ca trống") == "pending"
    assert not vocab.exists()

    row = page.terms_step._rows["ca trống"]
    hit = row.kinds_list.findItems("speech.mc", Qt.MatchFlag.MatchExactly)[0]
    hit.setSelected(True)
    page.record_button_for("ca trống").click()

    assert page.term_row_state("ca trống") == "recorded"
    assert vocab.exists()
    doc = yaml.safe_load(vocab.read_text(encoding="utf-8"))
    assert doc["cuesheet"]["ca trống"]["kinds"] == ["speech.mc"]


def test_ignore_remember_writes_ignore_true(page, tmp_path, monkeypatch):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'hoa tươi'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("hoa tươi",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    page.terms_step._rows["hoa tươi"].ignore_button.click()
    assert page.term_row_state("hoa tươi") == "recorded"
    doc = yaml.safe_load((tmp_path / "classifier.yaml").read_text(encoding="utf-8"))
    assert doc["cuesheet"]["hoa tươi"]["ignore"] is True


def test_recording_one_term_re_resolves_a_pending_sibling(page, tmp_path, monkeypatch):
    from PySide6.QtCore import Qt
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'trống'",
            "row 2: could not read performer 'dàn trống'",
        ]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("trống", "dàn trống"))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    row = page.terms_step._rows["trống"]
    row.word_match_check.setChecked(True)   # "trống" alone equals the fragment; tick by hand
    hit = row.kinds_list.findItems("drums.kick", Qt.MatchFlag.MatchExactly)[0]
    hit.setSelected(True)
    page.record_button_for("trống").click()

    assert page.term_row_state("trống") == "recorded"
    assert page.term_row_state("dàn trống") == "resolved"


def test_a_shortened_key_auto_ticks_match_inside_a_sentence(page, tmp_path, monkeypatch):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'Mời BLĐ lên sân khấu'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved",
                        lambda result: ("Mời BLĐ lên sân khấu",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    row = page.terms_step._rows["Mời BLĐ lên sân khấu"]
    assert row.word_match_check.isChecked() is False
    row.key_edit.setText("BLĐ")
    assert row.word_match_check.isChecked() is True


def test_the_ai_propose_button_opens_the_vocabulary_window_with_pending_fragments(
        page, tmp_path, monkeypatch):
    from wing_parser.ui import import_page

    class FakeResult:
        segments = [type("S", (), {"comments": [
            "row 1: could not read performer 'tốp múa'"]})()]

    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ("tốp múa",))
    page.set_output_directory(tmp_path)
    page.show_terms_step(FakeResult())

    seen = {}

    class _NullDialog:
        def exec(self):
            return 0

    def fake_window(parent, *, directory=None, initial_fragments=()):
        seen["fragments"] = initial_fragments
        return _NullDialog()

    import wing_parser.ui.vocabulary_window as vw_module

    monkeypatch.setattr(vw_module, "VocabularyWindow", fake_window)
    page.terms_step.ai_propose_button.click()
    assert seen["fragments"] == ("tốp múa",)
```

`terms_step._ai_propose` does `from wing_parser.ui.vocabulary_window import VocabularyWindow` INSIDE the
method, at call time — patching the name on the `vocabulary_window` module itself (not on `terms_step`,
which never binds the name at import time) is what that local import then picks up.

- [ ] **Step 9: Run the import-page suite, then the full suite**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_import_page.py tests/test_import_controller.py -v`
Expected: PASS. Then
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`
— paste the tally, and confirm `wing_parser/ui/terms_step.py` and `wing_parser/ui/terms_row.py` are both
≤200 lines (`wc -l`).

- [ ] **Step 10: Commit**

```bash
git add wing_parser/ui/terms_row.py wing_parser/ui/terms_step.py wing_parser/ui/import_steps.py wing_parser/ui/import_controller.py wing_parser/ui/texts_import.py tests/test_import_controller.py tests/test_ui_import_page.py && git commit -m "$(cat <<'EOF'
feat(ui): redesign the Terms step onto vocabulary.py

Spec §4: a key field (prefilled with the whole fragment), an
auto-ticking "match inside a sentence" checkbox, kind/set pickers built
from patterns.yaml and the current sets (never typed, W6), Record and a
new Ignore (remember), and live re-resolution after either so one
keyword can clear several rows below it. The pre-wave-4 load_guesses/
record-a-single-kind flow (ic.guesses_for/ic.record_term) is removed --
superseded by the Vocabulary window's Assistant tab (Tasks 5-6).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** that `grep -rn "load_guesses_button\|ic\.guesses_for\|ic\.record_term"
wing_parser/ tests/` shows nothing left anywhere (confirms the removal is complete, not partial); that
`test_ui_import_page.py`'s `bidv_terms` fixture (near the top of the file, uses
`monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ())`) still passes unmodified — it never
touched `guesses_for`, so it should need no change, and if it does need one this task's blast radius was
larger than analysed.

---

### Task 8: `missing_for_segments` and the Scene cross-check step

**Files:**
- Modify: `wing_parser/showcontext/ingest/propose.py`, `wing_parser/ui/import_controller.py` (144 lines),
  `wing_parser/ui/import_page.py`, `wing_parser/ui/import_steps.py`, `wing_parser/ui/main_window.py`,
  `tests/test_ingest_propose.py`, `tests/test_ui_import_page.py`
- Create: `wing_parser/ui/scene_step.py`, `tests/test_ui_scene_step.py`

Read `wing_parser/showcontext/ingest/propose.py` (`for_segments`, `channels_of`'s `HIGH` threshold) and
`wing_parser/ui/session.py` (`Session.scene`, the attribute Doctor's currently-open scene lives on) and
`wing_parser/ui/live_snapshot.py` (`SnapshotPanel.session_pulled`, re-emitted whole by `ConsolePage` —
`console_page.py:64`) in full before writing anything — this task's "Console's last Pull" source is a
SEPARATE listener on that same signal `live_wiring.wire_console` already connects to `adopt_pulled_session`;
it does not read `window.session` after a pull, because `window.session` can change again (opening a
different file) while the Import page should keep offering the scene it was actually pulled from that run
(W4: in-memory only, nothing new persisted).

**Interfaces:**
- Consumes: `BuildResult`/`BuiltSegment` (Task 3, unchanged shape plus `ignored_performers`);
  `view.channels_of`/`HIGH` (existing); `Session.scene` (existing).
- Produces:
  ```python
  # wing_parser/showcontext/ingest/propose.py — addition
  def missing_for_segments(result, scene) -> dict[str, tuple[str, ...]]: ...
     # segment id -> kinds it expects that the scene has no confident channel of

  # wing_parser/ui/import_controller.py
  def preview_text(xlsx, result, scene=None) -> str: ...   # scene param is NEW

  # wing_parser/ui/scene_step.py
  class SceneStep(QWidget):
      continue_requested = Signal(object)   # the chosen scene, or None (Skip)
      skip_requested = Signal()
      def __init__(self, *, doctor_scene_provider: Callable[[], object | None]) -> None: ...
      def set_result(self, result) -> None: ...
      def set_pulled_session(self, session) -> None: ...

  # wing_parser/ui/import_page.py
  class ImportPage(QWidget):
      def set_session(self, session) -> None: ...   # WAS "accepted but unused"; now stores it
      def set_last_pull(self, session) -> None: ...  # NEW seam, wired from MainWindow
  ```
  `import_steps.py`'s `_scene(page)` builder wires `page.scene_step`'s two signals to two new module
  functions, `show_scene_step`/`finish_scene`, replacing the old `show_preview`.

- [ ] **Step 1: Write the failing tests for `missing_for_segments`** — append to `tests/test_ingest_propose.py`
      (reuses that file's own `scene`/`_result`/`_results`/`_a_confident_kind`/`_two_confident_kinds`
      fixtures — read them first, they are the file's existing pattern, not new scaffolding)

```python
def test_missing_for_segments_is_empty_when_every_expectation_is_found(scene):
    kind = _a_confident_kind(scene)
    assert propose.missing_for_segments(_result((kind,)), scene) == {}


def test_missing_for_segments_names_the_kind_with_no_confident_channel(scene):
    result = _result(("instrument.theremin",))
    assert propose.missing_for_segments(result, scene) == {"S1": ("instrument.theremin",)}


def test_missing_for_segments_reports_only_the_gap_not_the_found_kind(scene):
    kind = _a_confident_kind(scene)
    result = _result((kind, "instrument.theremin"))
    assert propose.missing_for_segments(result, scene) == {"S1": ("instrument.theremin",)}


def test_missing_for_segments_omits_a_segment_with_no_gap_at_all(scene):
    first, second = _two_confident_kinds(scene)
    result = _results([("S1", (first,)), ("S2", (second, "instrument.theremin"))])
    assert propose.missing_for_segments(result, scene) == {"S2": ("instrument.theremin",)}
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ingest_propose.py -k missing_for_segments`
Expected: FAIL — `AttributeError: module 'wing_parser.showcontext.ingest.propose' has no attribute 'missing_for_segments'`

- [ ] **Step 3: Add `missing_for_segments`** — `wing_parser/showcontext/ingest/propose.py`

```python
def missing_for_segments(result, scene) -> dict[str, tuple[str, ...]]:
    """What `for_segments` found nothing for: kinds a segment expects
    that the scene has no confidently-classified channel of (design spec
    §5). The same `channels_of` walk and the same HIGH threshold as
    `for_segments`, so the two can never disagree about what "found"
    means -- a kind missing here is exactly a kind that produced no
    `--scene:` line there.
    """
    missing: dict[str, tuple[str, ...]] = {}
    for built in result.segments:
        gaps = tuple(kind for kind in built.segment.expects if not channels_of(scene, kind))
        if gaps:
            missing[built.segment.id] = gaps
    return missing
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ingest_propose.py -v`
Expected: PASS, all tests (pre-existing plus the four new ones).

- [ ] **Step 5: Commit the pure half**

```bash
git add wing_parser/showcontext/ingest/propose.py tests/test_ingest_propose.py && git commit -m "$(cat <<'EOF'
feat(ingest): add propose.missing_for_segments

Spec §5: the pure counterpart to for_segments -- kinds a segment
expects with no confidently-classified channel in the scene, walking
channels_of with the same HIGH threshold so the two functions can never
disagree about what "found" means.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 6: `import_controller.preview_text` gains an optional `scene`**

```python
from wing_parser.showcontext.ingest import build, emit, guess, mapping, propose, sheet


def preview_text(xlsx, result, scene=None) -> str:
    """The rendered YAML document, under the workbook's stem as show
    name. `scene`, given, adds the --scene cross-check proposals exactly
    as the CLI's --scene does (design spec §5) -- commented-out cues,
    never live ones."""
    proposals = propose.for_segments(result, scene) if scene is not None else None
    return emit.render(Path(xlsx).stem, result, proposals)
```

(`propose` joins the existing import list at the top of `import_controller.py`; every other function in
that file is unchanged.)

- [ ] **Step 7: Write `wing_parser/ui/scene_step.py`**

```python
"""The Scene cross-check step: what a segment's expects: needs against a
scene, from one of three sources (design spec §5, F6). Read-only --
nothing here writes to a live console. Skip leaves the emitted file
exactly as it is today (no proposals); Continue passes the chosen scene
through to import_steps.finish_scene, which threads it into
ic.preview_text exactly as the CLI's --scene does.
"""

from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QComboBox, QFileDialog, QHBoxLayout, QLabel, QPushButton, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from wing_parser import WingScene
from wing_parser.showcontext.ingest import propose
from wing_parser.ui.texts import text

DOCTOR = "doctor"
FILE = "file"
PULL = "pull"


class SceneStep(QWidget):
    continue_requested = Signal(object)
    skip_requested = Signal()

    def __init__(self, *, doctor_scene_provider: Callable[[], object | None]) -> None:
        super().__init__()
        self._doctor_scene_provider = doctor_scene_provider
        self._pulled_session = None
        self._file_scene = None
        self._result = None

        self.source_box = QComboBox()
        self.source_box.addItem(text("import.scene.source.doctor"), DOCTOR)
        self.source_box.addItem(text("import.scene.source.file"), FILE)
        self.source_box.addItem(text("import.scene.source.pull"), PULL)
        self.source_box.currentIndexChanged.connect(self._source_changed)

        self.open_file_button = QPushButton(text("import.scene.open_file"))
        self.open_file_button.clicked.connect(self._open_file)
        self.open_file_button.setVisible(False)

        self.status_label = QLabel("")
        self.status_label.setWordWrap(True)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([
            text("import.scene.col.segment"), text("import.scene.col.needed"),
            text("import.scene.col.found"), text("import.scene.col.missing"),
        ])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        self.skip_button = QPushButton(text("import.scene.skip"))
        self.skip_button.clicked.connect(lambda: self.skip_requested.emit())
        self.continue_button = QPushButton(text("import.scene.continue"))
        self.continue_button.clicked.connect(self._continue)

        top = QHBoxLayout()
        top.addWidget(QLabel(text("import.scene.source")))
        top.addWidget(self.source_box)
        top.addWidget(self.open_file_button)

        buttons = QHBoxLayout()
        buttons.addWidget(self.skip_button)
        buttons.addWidget(self.continue_button)
        buttons.addStretch(1)

        layout = QVBoxLayout(self)
        layout.addLayout(top)
        layout.addWidget(self.status_label)
        layout.addWidget(self.table, 1)
        layout.addLayout(buttons)
        self._source_changed()

    def set_result(self, result) -> None:
        self._result = result
        self._refresh_table()

    def set_pulled_session(self, session) -> None:
        """The Console page's last successful Pull this app run (W4:
        in-memory only). Read only when the 'Console's last Pull' source
        is actually selected -- see _refresh_table's own message when
        it is selected but nothing has been pulled yet."""
        self._pulled_session = session
        self._refresh_table()

    def _source_changed(self) -> None:
        self.open_file_button.setVisible(self.source_box.currentData() == FILE)
        self._refresh_table()

    def _open_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, text("import.scene.open_file"), "", text("menu.scene_filter"))
        if not path:
            return
        try:
            self._file_scene = WingScene.load(path)
        except (OSError, ValueError) as exc:
            self.status_label.setText(str(exc))
            return
        self._refresh_table()

    def _current_scene(self):
        source = self.source_box.currentData()
        if source == DOCTOR:
            return self._doctor_scene_provider()
        if source == FILE:
            return self._file_scene
        if source == PULL:
            return self._pulled_session.scene if self._pulled_session else None
        return None

    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        if self._result is None:
            return
        if self.source_box.currentData() == PULL and self._pulled_session is None:
            self.status_label.setText(text("import.scene.no_pull_yet"))
            return
        scene = self._current_scene()
        if scene is None:
            self.status_label.setText(text("import.scene.no_scene"))
            return
        self.status_label.setText("")
        missing = propose.missing_for_segments(self._result, scene)
        rows = [built for built in self._result.segments if built.segment.expects]
        self.table.setRowCount(len(rows))
        for r, built in enumerate(rows):
            gaps = missing.get(built.segment.id, ())
            found = tuple(kind for kind in built.segment.expects if kind not in gaps)
            self.table.setItem(r, 0, QTableWidgetItem(built.segment.id))
            self.table.setItem(r, 1, QTableWidgetItem(", ".join(built.segment.expects)))
            self.table.setItem(r, 2, QTableWidgetItem(", ".join(found)))
            self.table.setItem(r, 3, QTableWidgetItem(", ".join(gaps)))

    def _continue(self) -> None:
        self.continue_requested.emit(self._current_scene())
```

- [ ] **Step 8: Add the Scene step's strings** — append to `wing_parser/ui/texts_import.py`'s `IMPORT_TEXTS`

```python
    "import.scene.source": "Scene",
    "import.scene.source.doctor": "Doctor's scene",
    "import.scene.source.file": "Open .snap…",
    "import.scene.source.pull": "Console's last Pull",
    "import.scene.open_file": "Open .snap…",
    "import.scene.col.segment": "Segment",
    "import.scene.col.needed": "Kinds needed",
    "import.scene.col.found": "Found",
    "import.scene.col.missing": "Missing",
    "import.scene.skip": "Skip",
    "import.scene.continue": "Continue",
    "import.scene.no_scene": "No scene loaded for this source yet.",
    "import.scene.no_pull_yet": "Nothing pulled from a console this run yet.",
    "import.step.scene": "Scene check",
```

- [ ] **Step 9: Wire the step into `import_page.py`**

```python
STEPS = ("pick", "mapping", "vocabulary", "scene", "save")
```

Add `self._session = None` to `__init__`, and change `set_session`:

```python
    def set_session(self, session) -> None:
        """The window's current session -- offered as the Scene step's
        default cross-check source, 'Doctor's scene' (design spec §5).
        Was previously accepted but unused; import is no longer fully
        scene-independent once the Scene step exists."""
        self._session = session

    def set_last_pull(self, session) -> None:
        """The Console page's last successful Pull this app run (W4).
        Wired from MainWindow, not from set_session — a pull can arrive
        and be superseded by a different file being opened on Doctor
        without losing what was pulled. Note the seam on SceneStep is
        named `set_pulled_session`, not `set_last_pull_session` — do not
        introduce a second name for the same thing."""
        self.scene_step.set_pulled_session(session)
```

- [ ] **Step 10: Wire `import_steps.py`** — add the new step, replace `show_preview`

```python
def build_steps(page) -> tuple[QWidget, ...]:
    return (_pick(page), _mapping(page), _terms(page), _scene(page), _save(page))
```

In `_terms(page)`, change the preview button's target:

```python
    page.preview_button.clicked.connect(lambda: show_scene_step(page))
```

Add the new builder and the two transition functions:

```python
def _scene(page) -> QWidget:
    page.scene_step = SceneStep(
        doctor_scene_provider=lambda: page._session.scene if page._session else None)
    page.scene_step.continue_requested.connect(lambda scene: finish_scene(page, scene))
    page.scene_step.skip_requested.connect(lambda: finish_scene(page, None))
    return page.scene_step


def show_scene_step(page) -> None:
    """Step 3 -> step 4: hand the scene step the just-built result."""
    page.scene_step.set_result(page._result)
    page.step_area.setCurrentIndex(3)


def finish_scene(page, scene) -> None:
    """Step 4 -> step 5: render the YAML, with the chosen scene's
    cross-check proposals if any -- Skip passes scene=None, and the file
    is byte-for-byte what today's (pre-wave-4) Save produces."""
    try:
        page.preview_pane.setPlainText(ic.preview_text(page._xlsx, page._result, scene=scene))
    except (OSError, ValueError) as exc:
        page._fail(exc)
        return
    page.step_area.setCurrentIndex(4)
```

Delete the old `show_preview` function in full (superseded by the two above) and add
`from wing_parser.ui.scene_step import SceneStep` to the imports.

- [ ] **Step 11: Wire "Console's last Pull" from `MainWindow`**

In `wing_parser/ui/main_window.py`'s `_build_body`, immediately after the existing
`live_wiring.wire_console(self, self.pages["console"])`:

```python
        self.pages["console"].session_pulled.connect(self.pages["import_"].set_last_pull)
```

- [ ] **Step 12: Update the two broken assertions in `tests/test_ui_import_page.py`**

`test_the_wizard_has_a_step_rail_starting_at_pick`:

```python
def test_the_wizard_has_a_step_rail_starting_at_pick(page):
    assert page.step_rail.step == 0
    assert page.step_rail.names == ("pick", "mapping", "vocabulary", "scene", "save")
    assert page.step_rail.labels[0].isEnabled()
```

`test_preview_renders_and_save_writes_utf8` — the old single click now lands on the Scene step, not a
rendered preview; Skip from there reaches Save exactly as before:

```python
def test_preview_renders_and_save_writes_utf8(bidv_terms, tmp_path):
    bidv_terms.preview_button.click()
    assert bidv_terms.step_area.currentIndex() == 3        # the new Scene step
    bidv_terms.scene_step.skip_button.click()
    assert bidv_terms.step_area.currentIndex() == 4         # Save, unchanged content
    rendered = bidv_terms.preview_pane.toPlainText()
    assert rendered != ""
    out = tmp_path / "out.yaml"
    assert bidv_terms.save_as(str(out))
    assert out.read_text(encoding="utf-8") == rendered
```

- [ ] **Step 13: Write the failing Qt tests for `SceneStep`** — `tests/test_ui_scene_step.py`

```python
"""Spec §5, F6: three sources, read-only, Skip leaves the file unchanged."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

from wing_parser.showcontext.ingest.build import BuildResult, BuiltSegment
from wing_parser.showcontext.models import Segment


def _result(kinds):
    return BuildResult(
        segments=(BuiltSegment(segment=Segment(id="S1", title="t", expects=kinds), comments=()),),
        loose_comments=(), data_rows=1, comment_rows=0, blank_rows=0,
    )


@pytest.fixture
def step(qt_app):
    from wing_parser.ui.scene_step import SceneStep

    return SceneStep(doctor_scene_provider=lambda: None)


def test_with_no_scene_at_all_the_status_line_says_so(step):
    step.set_result(_result(("speech.mc",)))
    assert step.status_label.text() != ""
    assert step.table.rowCount() == 0


def test_doctors_scene_populates_the_table(qt_app, vu_path):
    from wing_parser import WingScene
    from wing_parser.showcontext.ingest.build import BuildResult, BuiltSegment
    from wing_parser.showcontext.models import Segment
    from wing_parser.showcontext.view import channels_of
    from wing_parser.ui.scene_step import SceneStep

    scene = WingScene.load(vu_path)
    kind = next(c.source_type.kind for c in scene.channels()
               if c.source_type.confidence >= 0.8)
    result = BuildResult(
        segments=(BuiltSegment(segment=Segment(id="S1", title="t", expects=(kind,)), comments=()),),
        loose_comments=(), data_rows=1, comment_rows=0, blank_rows=0,
    )
    step = SceneStep(doctor_scene_provider=lambda: scene)
    step.set_result(result)
    assert step.table.rowCount() == 1
    assert step.table.item(0, 2).text() == kind         # found, no gap
    assert step.table.item(0, 3).text() == ""            # nothing missing


def test_selecting_pull_with_nothing_pulled_yet_says_so(step):
    step.set_result(_result(("speech.mc",)))
    step.source_box.setCurrentIndex(step.source_box.findData("pull"))
    assert "pulled" in step.status_label.text() or "Pull" in step.status_label.text()


def test_a_set_pulled_session_populates_the_table_once_pull_is_selected(qt_app, vu_path):
    """Source 3 of 3 (F6): the Console's last Pull, faked as a Session-shaped
    stand-in carrying a real .scene -- set_pulled_session is the seam
    live_wiring wires ConsolePage.session_pulled to (Task 8)."""
    from wing_parser import WingScene
    from wing_parser.ui.scene_step import SceneStep

    scene = WingScene.load(vu_path)
    kind = next(c.source_type.kind for c in scene.channels()
               if c.source_type.confidence >= 0.8)
    fake_session = type("FakeSession", (), {"scene": scene})()

    step = SceneStep(doctor_scene_provider=lambda: None)
    step.set_result(_result((kind,)))
    step.source_box.setCurrentIndex(step.source_box.findData("pull"))
    assert step.table.rowCount() == 0   # nothing pulled yet

    step.set_pulled_session(fake_session)
    assert step.table.rowCount() == 1
    assert step.table.item(0, 2).text() == kind


def test_opening_a_snap_file_populates_the_table(qt_app, vu_path, step):
    """Source 2 of 3 (F6): 'Open .snap…'. Sets the private `_file_scene`
    directly rather than driving the real `QFileDialog` -- `_open_file`
    itself is three lines wrapping that dialog and a `WingScene.load`
    call already covered by `net`/`WingScene`'s own tests; what this test
    proves is that once a file scene is present, `_refresh_table` reads
    it exactly like the other two sources."""
    from wing_parser import WingScene

    scene = WingScene.load(vu_path)
    kind = next(c.source_type.kind for c in scene.channels()
               if c.source_type.confidence >= 0.8)
    step.set_result(_result((kind,)))
    step.source_box.setCurrentIndex(step.source_box.findData("file"))
    assert step.open_file_button.isVisible()

    step._file_scene = scene
    step._refresh_table()

    assert step.table.rowCount() == 1
    assert step.table.item(0, 2).text() == kind


def test_skip_emits_the_skip_signal_not_continue(step, qt_app):
    seen = []
    step.skip_requested.connect(lambda: seen.append("skip"))
    step.continue_requested.connect(lambda scene: seen.append(("continue", scene)))
    step.set_result(_result(("speech.mc",)))
    step.skip_button.click()
    assert seen == ["skip"]


def test_continue_emits_the_currently_selected_scenes_value(qt_app, vu_path):
    from wing_parser import WingScene
    from wing_parser.ui.scene_step import SceneStep

    scene = WingScene.load(vu_path)
    step = SceneStep(doctor_scene_provider=lambda: scene)
    step.set_result(_result(("speech.mc",)))
    seen = []
    step.continue_requested.connect(lambda s: seen.append(s))
    step.continue_button.click()
    assert seen == [scene]


def test_the_full_wizard_reaches_save_through_the_scene_step_with_a_real_scene(
        qt_app, tmp_path, monkeypatch, vu_path, settle):
    """End-to-end through the real MainWindow: pick a real workbook,
    finish mapping, skip Terms straight to Preview, choose 'Doctor's
    scene' (a real loaded Session), Continue, and the rendered YAML
    carries a --scene proposal exactly as the CLI's --scene does."""
    from wing_parser import config
    from wing_parser.ui import import_page
    from wing_parser.ui.main_window import MainWindow
    from wing_parser.ui.session import Session

    monkeypatch.setenv(config.ENV_VAR, str(tmp_path))
    monkeypatch.setenv("WING_DISABLE_LLM", "1")
    monkeypatch.setattr(import_page.ic, "unresolved", lambda result: ())

    window = MainWindow(Session.open(vu_path))
    window._refresh()   # fans window.session out to every page's set_session
    page = window.pages["import_"]
    BIDV = "tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx"
    page.pick_file(BIDV)
    assert settle(lambda: page.step_area.currentIndex() == 1)
    for field, letter in (("id", "A"), ("time", "B"), ("title", "E")):
        page.letter_edit(field).setText(letter)
    page.header_edit("performers").setText("Thực hiện")
    page.sheet_edit.setText("KB 8.1")
    page.header_row_spin.setValue(5)
    page.next_button.click()
    assert page.step_area.currentIndex() == 2

    page.preview_button.click()
    assert page.step_area.currentIndex() == 3
    assert page.scene_step.source_box.currentData() == "doctor"
    page.scene_step.continue_button.click()
    assert page.step_area.currentIndex() == 4
    assert page.preview_pane.toPlainText() != ""
```

- [ ] **Step 14: Run the new tests, then everything Task 8 touched, then the full suite**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_scene_step.py tests/test_ui_import_page.py tests/test_ingest_propose.py -v`
Expected: PASS. Then
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`
— paste the tally, and confirm `wing_parser/ui/scene_step.py` is ≤200 lines.

- [ ] **Step 15: Commit**

```bash
git add wing_parser/showcontext/ingest/propose.py wing_parser/ui/import_controller.py wing_parser/ui/import_page.py wing_parser/ui/import_steps.py wing_parser/ui/main_window.py wing_parser/ui/scene_step.py wing_parser/ui/texts_import.py tests/test_ingest_propose.py tests/test_ui_import_page.py tests/test_ui_scene_step.py && git commit -m "$(cat <<'EOF'
feat(ui): add the Scene cross-check step between Terms and Save

Spec §5/F6: three sources (Doctor's scene, an opened .snap, the
Console's last Pull this run), a table of segment/needed/found/missing,
Skip leaving the file byte-identical to today's, Continue threading the
chosen scene into ic.preview_text exactly as the CLI's --scene does.
"Console's last Pull" is wired straight off ConsolePage.session_pulled,
independent of window.session, so a later file open on Doctor cannot
make the Import wizard forget what was just pulled (W4).

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** that `wing_parser/ui/session.py`'s `Session` really exposes `.scene` as a
plain attribute (not a method) — `doctor_scene_provider=lambda: page._session.scene if page._session else None`
depends on that; that `live_wiring.wire_console`'s existing `adopt_pulled_session` still sets
`window.session = session` (confirms why this task cannot reuse `window.session` for the Pull source and
needs its own signal connection instead); that `ConsolePage.session_pulled` is re-emitted from
`SnapshotPanel.session_pulled` with the SAME `Session`-shaped object `Session.open`/`WingScene.load`
produce elsewhere (a mismatched shape would make `self._pulled_session.scene` in `scene_step.py` raise).

---

### Task 9: lint an existing file from the Pick step; Try AI on the Mapping step

**Files:**
- Create: `wing_parser/ui/lint_dialog.py`, `wing_parser/ui/mapping_try_ai.py`,
  `tests/test_ui_lint_dialog.py`, `tests/test_ui_mapping_try_ai.py`
- Modify: `wing_parser/ui/pick_step.py` (39 lines), `wing_parser/ui/import_steps.py`,
  `wing_parser/ui/texts_import.py`

Read `wing_parser/showcontext/rewrite.py` (`apply_repairs`, and its own docstring's "only a genuine repair
is written back") and `wing_parser/cli/commands.py:239-257` (`showcontext_lint` — the CLI's own lint/`--fix`
flow this dialog must read exactly the same data as, per spec §6's "no second lint implementation") before
writing `lint_dialog.py`. Read `wing_parser/showcontext/ingest/suggest.py`'s `propose_mapping` before
writing `mapping_try_ai.py`.

**A spec-wording ambiguity, resolved.** Spec §7 says Try AI "runs the real mapping proposal
(`ic.proposal_for`)". `import_controller.proposal_for` **swallows** `ProviderError`/`ValueError`/`OSError`/
`zipfile.BadZipFile` into a bare `None` (`import_controller.py`, read in Task 1's file list) — that is
exactly right for the wizard's silent auto-assist, and exactly wrong for Try AI, which spec §7 also requires
to show "a classified failure" (bad key / quota / no network / SDK missing / bad reply / other) — a
swallowed exception cannot be classified. This task calls `suggest.propose_mapping` directly instead — the
same function `ic.proposal_for` wraps — so a real failure reaches `provider_errors.classify` as itself.
`ic.proposal_for` is left completely unchanged; nothing else in this codebase is affected by this reading.

**Interfaces:**
- Consumes: `load_show_context`/`apply_repairs` (existing); `suggest.propose_mapping` (existing);
  `provider.resolve_config`/`ProviderConfig` (existing); `provider_errors.classify` (Task 4);
  `classifier.llm.kill_switch_on` (existing).
- Produces:
  ```python
  # wing_parser/ui/lint_dialog.py
  class LintDialog(QDialog):
      def __init__(self, parent=None) -> None: ...
      def open_path(self, path: str) -> None: ...   # public seam, no file dialog

  # wing_parser/ui/mapping_try_ai.py
  class MappingTryAi(QWidget):
      def __init__(self, runner, provider_factory, xlsx_provider: Callable[[], str | None]) -> None: ...
  ```
  `import_steps.py`'s `_mapping(page)` constructs one `MappingTryAi` per page, reusing `page._runner` (the
  SAME single-call-at-a-time runner Pick and Terms already share — no second `CallRunner` on this page).

- [ ] **Step 1: Write the failing Qt tests for the lint dialog** — `tests/test_ui_lint_dialog.py`

```python
"""Spec §6: lint reads exactly what `wing showcontext lint` reads; Fix
writes a .bak before apply_repairs (W2), then re-lints."""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")

CLEAN = "tests/data/ingest-fixture.xlsx"   # any real file stands in below; see fixtures written per test


@pytest.fixture
def dialog(qt_app):
    from wing_parser.ui.lint_dialog import LintDialog

    return LintDialog()


def _show_context_yaml() -> str:
    """Two genuinely repairable typos -- edit-distance-1 from a real kind
    and a real action (design spec's radius-1 rule, showcontext/vocabulary.py):
    'gutiar' is a transposition of 'guitar', 'colse' of 'close'. A pure
    case difference like 'Speech.MC' would NOT anomaly here -- normalise()
    lowercases it silently (vocabulary.py:31-42) with repaired=False, so
    it must not be used as this fixture's "auto-fixable" example. Verified
    2026-09-26 against the real loader/rewrite pipeline: both repair, and
    a second lint after apply_repairs shows zero anomalies."""
    return (
        "show: t\n"
        "segments:\n"
        "  - id: S1\n"
        "    title: A\n"
        "    expects: [instrument.gutiar]\n"
        "    cues:\n"
        "      - {id: c1, action: colse}\n"
    )


def test_a_clean_file_says_nothing_to_repair(dialog, tmp_path):
    path = tmp_path / "clean.yaml"
    path.write_text("show: t\nsegments:\n  - id: S1\n    title: A\n    expects: []\n",
                    encoding="utf-8")
    dialog.open_path(str(path))
    assert "nothing to repair" in dialog.output.toPlainText()
    assert not dialog.fix_button.isEnabled()


def test_a_file_with_anomalies_lists_them_and_enables_fix(dialog, tmp_path):
    path = tmp_path / "messy.yaml"
    path.write_text(_show_context_yaml(), encoding="utf-8")
    dialog.open_path(str(path))
    assert dialog.output.toPlainText() != ""
    assert dialog.fix_button.isEnabled()


def test_a_malformed_file_shows_the_message_not_a_crash(dialog, tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("not: [valid, show, context", encoding="utf-8")
    dialog.open_path(str(path))    # must not raise
    assert dialog.output.toPlainText() != ""
    assert not dialog.fix_button.isEnabled()


def test_fix_writes_a_bak_then_re_lints(dialog, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "messy.yaml"
    original = _show_context_yaml()
    path.write_text(original, encoding="utf-8")
    dialog.open_path(str(path))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))

    dialog.fix_button.click()

    backup = tmp_path / "messy.yaml.bak"
    assert backup.exists()
    assert backup.read_text(encoding="utf-8") == original
    assert "fixed" in dialog.output.toPlainText().lower() or "Speech.MC" in dialog.output.toPlainText()
    assert not dialog.fix_button.isEnabled()   # re-lint found nothing left to fix


def test_an_older_bak_is_overwritten_not_appended_to(dialog, tmp_path, monkeypatch):
    from PySide6.QtWidgets import QMessageBox

    path = tmp_path / "messy.yaml"
    path.write_text(_show_context_yaml(), encoding="utf-8")
    (tmp_path / "messy.yaml.bak").write_text("stale backup", encoding="utf-8")
    dialog.open_path(str(path))
    monkeypatch.setattr(QMessageBox, "question",
                        staticmethod(lambda *a, **k: QMessageBox.StandardButton.Yes))
    dialog.fix_button.click()
    assert "stale backup" not in (tmp_path / "messy.yaml.bak").read_text(encoding="utf-8")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_lint_dialog.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.lint_dialog'`

- [ ] **Step 3: Write `lint_dialog.py`**

```python
"""Lint an existing show-context file from the Pick step (design spec
§6). Reads exactly what `wing showcontext lint` reads
(`load_show_context`, `context.anomalies`) -- no second lint
implementation. Fix writes `<file>.bak` (overwriting an older one, W2)
before `apply_repairs`, which itself keeps no backup of its own, then
re-lints and shows what changed and what remains.
"""

from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QMessageBox, QPushButton, QTextEdit,
    QVBoxLayout,
)

from wing_parser.showcontext import load_show_context
from wing_parser.showcontext.rewrite import apply_repairs
from wing_parser.ui.texts import text


class LintDialog(QDialog):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(text("import.lint.title"))
        self.setMinimumSize(560, 400)
        self._path: Path | None = None

        self.open_button = QPushButton(text("import.lint.open"))
        self.open_button.clicked.connect(self._open)
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.fix_button = QPushButton(text("import.lint.fix"))
        self.fix_button.setEnabled(False)
        self.fix_button.clicked.connect(self._fix)
        close_button = QPushButton(text("import.lint.close"))
        close_button.clicked.connect(self.accept)

        buttons = QHBoxLayout()
        buttons.addWidget(self.open_button)
        buttons.addWidget(self.fix_button)
        buttons.addStretch(1)
        buttons.addWidget(close_button)

        layout = QVBoxLayout(self)
        layout.addWidget(self.output, 1)
        layout.addLayout(buttons)

    def open_path(self, path: str) -> None:
        self._path = Path(path)
        self._lint()

    def _open(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self, text("import.lint.open"), "", text("import.yaml_filter"))
        if path:
            self.open_path(path)

    def _lint(self) -> None:
        try:
            context = load_show_context(self._path)
        except ValueError as exc:
            self.output.setPlainText(str(exc))
            self.fix_button.setEnabled(False)
            return
        if not context.anomalies:
            self.output.setPlainText(
                text("import.lint.clean").format(count=len(context.segments)))
            self.fix_button.setEnabled(False)
            return
        self.output.setPlainText("\n".join(context.anomalies))
        self.fix_button.setEnabled(True)

    def _fix(self) -> None:
        answer = QMessageBox.question(
            self, text("import.lint.title"), text("import.lint.confirm"))
        if answer != QMessageBox.StandardButton.Yes:
            return
        backup = Path(str(self._path) + ".bak")
        shutil.copyfile(self._path, backup)
        repairs = apply_repairs(self._path)
        lines = [text("import.lint.fixed").format(n=len(repairs)), *repairs]
        self.output.setPlainText("\n".join(lines))
        self._lint()
```

- [ ] **Step 4: Add the lint dialog's strings** — append to `wing_parser/ui/texts_import.py`

```python
    "import.lint.title": "Check a show-context file",
    "import.lint.open": "Check an existing show-context file…",
    "import.lint.fix": "Fix",
    "import.lint.close": "Close",
    "import.lint.confirm": "Write repairs into this file? A .bak copy is made first.",
    "import.lint.clean": "{count} segments, nothing to repair.",
    "import.lint.fixed": "fixed {n} item(s):",
```

- [ ] **Step 5: Run the lint tests to verify they pass**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_lint_dialog.py -v`
Expected: PASS, all 6 tests.

- [ ] **Step 6: Wire the lint button onto the Pick step** — `wing_parser/ui/pick_step.py`

```python
from wing_parser.ui.lint_dialog import LintDialog
```

Add to `__init__`, right after `self.choose_button`:

```python
        self.lint_button = QPushButton(text("import.lint.open"))
        self.lint_button.clicked.connect(self._open_lint)
```

and `layout.addWidget(self.lint_button)` beside `layout.addWidget(self.choose_button)`, plus:

```python
    def _open_lint(self) -> None:
        LintDialog(self).exec()
```

- [ ] **Step 7: Add one Qt test proving the button is really wired** — append to `tests/test_ui_import_page.py`

```python
def test_the_pick_steps_lint_button_opens_a_lint_dialog(page, monkeypatch):
    opened = []
    monkeypatch.setattr(
        "wing_parser.ui.pick_step.LintDialog",
        lambda parent: type("D", (), {"exec": lambda self: opened.append(True) or 0})(),
    )
    page.pick_step.lint_button.click()
    assert opened == [True]
```

- [ ] **Step 8: Run the pick-step suite**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_import_page.py tests/test_ui_lint_dialog.py -v`
Expected: PASS.

- [ ] **Step 9: Commit the lint half**

```bash
git add wing_parser/ui/lint_dialog.py wing_parser/ui/pick_step.py wing_parser/ui/texts_import.py tests/test_ui_lint_dialog.py tests/test_ui_import_page.py && git commit -m "$(cat <<'EOF'
feat(ui): add a lint dialog for an existing show-context file

Spec §6: opened from the Pick step, reads exactly what `wing showcontext
lint` reads (load_show_context/context.anomalies, no second
implementation), Fix writes <file>.bak before apply_repairs (W2) and
re-lints. A malformed file shows the message, never a crash.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

- [ ] **Step 10: Write the failing Qt tests for Try AI** — `tests/test_ui_mapping_try_ai.py`

```python
"""Spec §7: Try AI reports provider/model/elapsed/proposal or a
classified failure -- the same classifier Settings' Test connection
uses (Task 4). A fake provider stands in for the model; propose_mapping
is monkeypatched directly so no real xlsx sampling or model call runs.
"""
from __future__ import annotations

import pytest

pytest.importorskip("PySide6.QtWidgets")


class _Proposal:
    sheet = "Rundown"; header_row = 4
    columns = {"id": "B"}; headers = {"performers": "On stage"}
    problems = ()


@pytest.fixture
def panel(qt_app):
    from wing_parser.ui.mapping_try_ai import MappingTryAi
    from wing_parser.ui.workers import CallRunner

    return MappingTryAi(CallRunner(), lambda: object(), lambda: "some.xlsx")


def test_a_successful_try_shows_provider_model_and_the_proposal(panel, monkeypatch, settle):
    from wing_parser.ui import mapping_try_ai

    monkeypatch.setattr(mapping_try_ai.suggest, "propose_mapping",
                        lambda xlsx, provider: _Proposal())
    panel.try_button.click()
    assert settle(lambda: panel.proposal_view.toPlainText() != "")
    assert "Rundown" in panel.proposal_view.toPlainText()


def test_a_401_shows_the_shared_bad_key_message(panel, monkeypatch, settle):
    from wing_parser.ui import mapping_try_ai

    class _Unauthorized(Exception):
        status_code = 401

    def boom(xlsx, provider):
        raise _Unauthorized("nope")

    monkeypatch.setattr(mapping_try_ai.suggest, "propose_mapping", boom)
    panel.try_button.click()
    assert settle(lambda: panel.result_label.text() != "")
    assert "rejected" in panel.result_label.text()


def test_no_xlsx_yet_does_nothing(qt_app):
    from wing_parser.ui.mapping_try_ai import MappingTryAi
    from wing_parser.ui.workers import CallRunner

    panel = MappingTryAi(CallRunner(), lambda: object(), lambda: None)
    assert panel._try() is False
```

- [ ] **Step 11: Run the tests to verify they fail**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_mapping_try_ai.py`
Expected: FAIL — `ModuleNotFoundError: No module named 'wing_parser.ui.mapping_try_ai'`

- [ ] **Step 12: Write `mapping_try_ai.py`**

```python
"""The Mapping step's 'Try AI on this file' panel (design spec §7).

Calls suggest.propose_mapping DIRECTLY, not import_controller.proposal_for
-- the latter swallows every provider-shaped failure into None (correct
for the wizard's silent auto-assist, wrong here: this panel exists to
SHOW a classified failure, which a swallowed exception cannot be).
Reuses the page's one shared CallRunner -- never a second one on this
page.
"""

from __future__ import annotations

import time
from collections.abc import Callable

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QTextEdit, QVBoxLayout, QWidget

from wing_parser import config
from wing_parser.classifier import provider_errors
from wing_parser.classifier.llm import kill_switch_on
from wing_parser.classifier.provider import resolve_config
from wing_parser.showcontext.ingest import suggest
from wing_parser.ui.call_button import ButtonRunner
from wing_parser.ui.texts import text


class MappingTryAi(QWidget):
    def __init__(self, runner, provider_factory, xlsx_provider: Callable[[], str | None]) -> None:
        super().__init__()
        self._provider_factory = provider_factory
        self._xlsx_provider = xlsx_provider
        self._started_at = 0.0
        self._provider_line = ""

        self.try_button = QPushButton(text("import.try_ai.button"))
        self.try_button.clicked.connect(self._try)
        self.cancel_button = QPushButton(text("import.try_ai.cancel"))
        self.cancel_button.setVisible(False)
        self.result_label = QLabel("")
        self.result_label.setWordWrap(True)
        self.proposal_view = QTextEdit()
        self.proposal_view.setReadOnly(True)

        self._call = ButtonRunner(
            runner=runner, primary=self.try_button, cancel=self.cancel_button,
            report=self.result_label.setText,
            running=text("import.try_ai.running"),
            cancelled=text("import.try_ai.cancelled"),
            timeout_text=text("import.try_ai.timeout"),
            busy_text=text("import.try_ai.busy"), on_error=self._failed,
        )
        self.cancel_button.clicked.connect(self._call.cancel)

        buttons = QHBoxLayout()
        buttons.addWidget(self.try_button)
        buttons.addWidget(self.cancel_button)

        layout = QVBoxLayout(self)
        layout.addLayout(buttons)
        layout.addWidget(self.result_label)
        layout.addWidget(self.proposal_view)

    def _try(self) -> bool:
        xlsx = self._xlsx_provider()
        if not xlsx:
            return False
        if kill_switch_on():
            self.result_label.setText(text("import.try_ai.disabled"))
            return False
        cfg = resolve_config(config.knowledge_dir())
        self._provider_line = f"{cfg.name}/{cfg.model}"
        self._started_at = time.monotonic()
        return self._call.run(
            "proposal", suggest.propose_mapping, xlsx, self._provider_factory(),
            on_success=self._succeeded,
        )

    def _succeeded(self, proposal) -> None:
        elapsed = round(time.monotonic() - self._started_at, 1)
        self.result_label.setText(
            text("import.try_ai.result").format(provider=self._provider_line, seconds=elapsed))
        lines = [
            f"sheet: {proposal.sheet}", f"header_row: {proposal.header_row}",
            f"columns: {proposal.columns}", f"headers: {proposal.headers}",
        ]
        if proposal.problems:
            lines.append("problems: " + "; ".join(proposal.problems))
        self.proposal_view.setPlainText("\n".join(lines))

    def _failed(self, exc: Exception) -> None:
        _code, message = provider_errors.classify(exc)
        self.result_label.setText(message)
        self.proposal_view.setPlainText("")
```

- [ ] **Step 13: Add Try AI's strings** — append to `wing_parser/ui/texts_import.py`

```python
    "import.try_ai.button": "Try AI on this file",
    "import.try_ai.cancel": "Cancel",
    "import.try_ai.running": "Asking the model...",
    "import.try_ai.cancelled": "Cancelled.",
    "import.try_ai.timeout": "The model did not answer within {seconds} s.",
    "import.try_ai.busy": "A model request is already running — cancel it or wait.",
    "import.try_ai.disabled": "(model assist disabled: WING_DISABLE_LLM is set)",
    "import.try_ai.result": "{provider}, {seconds}s",
```

- [ ] **Step 14: Run the Try AI tests to verify they pass**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_mapping_try_ai.py -v`
Expected: PASS, all 3 tests.

- [ ] **Step 15: Wire the panel into the Mapping step** — `wing_parser/ui/import_steps.py`

```python
from wing_parser.ui.mapping_try_ai import MappingTryAi
```

Replace `_mapping`:

```python
def _mapping(page) -> QWidget:
    page.mapping_step = MappingStep()
    for name in MAPPING_WIDGETS:
        setattr(page, name, getattr(page.mapping_step, name))

    page.back_button.clicked.connect(lambda: page.step_area.setCurrentIndex(0))
    page.next_button.clicked.connect(lambda: finish_mapping(page))

    page.try_ai_panel = MappingTryAi(
        page._runner, page._provider_factory, lambda: page._xlsx)

    step = QWidget()
    layout = QVBoxLayout(step)
    layout.addWidget(page.mapping_step)
    layout.addWidget(page.try_ai_panel)
    return step
```

- [ ] **Step 16: Add one end-to-end Qt test** — append to `tests/test_ui_import_page.py`

```python
def test_try_ai_on_the_mapping_step_is_reachable_and_uses_the_pages_xlsx(page, monkeypatch, settle):
    from wing_parser.ui import mapping_try_ai

    page.pick_file("tests/data/BIDV TPHCM - KỊCH BẢN SK YEP 2025..xlsx")
    seen = {}

    def fake_propose(xlsx, provider):
        seen["xlsx"] = xlsx
        return type("P", (), {"sheet": "KB 8.1", "header_row": 5, "columns": {},
                              "headers": {}, "problems": ()})()

    monkeypatch.setattr(mapping_try_ai.suggest, "propose_mapping", fake_propose)
    page.try_ai_panel.try_button.click()
    assert settle(lambda: "xlsx" in seen)
    assert seen["xlsx"].endswith(".xlsx")
```

- [ ] **Step 17: Run everything Task 9 touched, then the full suite**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest tests/test_ui_mapping_try_ai.py tests/test_ui_import_page.py tests/test_ui_lint_dialog.py -v`
then `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`
— paste the tally, and confirm both new UI files are ≤200 lines.

- [ ] **Step 18: Commit**

```bash
git add wing_parser/ui/mapping_try_ai.py wing_parser/ui/import_steps.py wing_parser/ui/texts_import.py tests/test_ui_mapping_try_ai.py tests/test_ui_import_page.py && git commit -m "$(cat <<'EOF'
feat(ui): add Try AI on the Mapping step

Spec §7: provider, model, elapsed seconds and the proposal, or a
classified failure through provider_errors.classify (Task 4) -- the
same classifier Settings' Test connection uses. Calls
suggest.propose_mapping directly rather than import_controller's
proposal_for, which swallows every provider-shaped failure into None
and so cannot supply what this panel exists to show.

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
)"
```

**Claims to check by opening:** that `import_controller.proposal_for`'s except clause really does swallow
`(ProviderError, ValueError, OSError, zipfile.BadZipFile)` into `None` (the exact claim this task's opening
paragraph rests its whole design choice on); that `apply_repairs` (`rewrite.py`) really keeps no backup of
its own (confirms the dialog's own `.bak` write is not redundant); that `wing_parser/ui/pick_step.py` and
`wing_parser/ui/mapping_try_ai.py` stay ≤200 lines after this task's edits.

---

### Task 10: exe rebuild, bundle check, screenshots

**Files:** none created or modified — this task builds and inspects the existing
`packaging/wing-ui.spec`/`packaging/make-debug-spec.py` output. It runs only after Tasks 1-9 are merged to
`main` (see "How to start"), from a checkout of `main` at the merge commit, not from this feature branch.

This is wave 1's own closing gate, repeated every wave since (2026-08-26 memory: "no page is done if ToanAZ
hasn't looked at a screenshot from the exe") — nothing here is optional polish.

- [ ] **Step 1: Confirm the editable install points at the checkout you are building from**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -c "import wing_parser; print(wing_parser.__file__)"`
Expected: a path inside the `main` checkout you are building from. If it prints a worktree path instead,
run `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pip install -e .` from that
checkout first — the memory file's own recorded pitfall (2026-09-18: "editable install in `.venv` points to
the checkout that last ran `pip install -e`, not the one you meant to build").

- [ ] **Step 2: Install every extra the release build needs**

Run:
`"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pip install -e ".[ui,ingest,llm,llm-openai]"`
(memory 2026-09-25: the release exe ships both SDKs; `mcp` stays intentionally excluded, both here and in
`packaging/wing-ui.spec`'s `EXCLUDES`).

- [ ] **Step 3: Run the full suite one more time from `main` at the merge commit**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m pytest --junitxml=dist-reports/suite.xml`
Paste the tally into the task report — this is the number that belongs in the wave's closing handoff, not
any single task's mid-wave figure.

- [ ] **Step 4: Build the exe**

Run: `"D:/DEV CAVE EP3/PROJECT008-SOUNDTECH-ASSIST/.venv/Scripts/python.exe" -m PyInstaller packaging/wing-ui.spec --noconfirm`

- [ ] **Step 5: Confirm the shipped defaults are actually in the bundle**

Run (PowerShell, since this is a lookup the user could also run, not a destructive action):
```powershell
Select-String -Path "build\wing-ui\Analysis-00.toc" -Pattern "cuesheet_defaults.yaml"
```
Expected: at least one match. `packaging/wing-ui.spec`'s `DATAS` already bundles
`wing_parser/classifier/data` whole (confirmed by reading that file in this plan's own research — the line
bundling `wing_parser/classifier/data` predates this wave), so a miss here means the spec's glob stopped
matching the new file, not that the file is missing from the source tree.

- [ ] **Step 6: Launch and confirm it stays alive**

Run (PowerShell):
```powershell
Start-Process "dist\wing-ui.exe"; Start-Sleep -Seconds 8; Get-Process wing-ui -ErrorAction SilentlyContinue
```
Expected: a live `wing-ui` process after 8 seconds. If it exited silently, rebuild with
`packaging/make-debug-spec.py`'s debug spec (`console=True`) and re-launch to read the traceback in a real
console.

- [ ] **Step 7: Screenshot every new surface, from the exe, for ToanAZ**

With the exe running: the Import wizard's Pick step (showing the new "Check an existing show-context
file…" button), the lint dialog over a real messy file, the Mapping step (showing the new "Try AI on this
file" panel), the Terms step (showing a `TermsRow` with its key field, match checkbox and pickers, plus the
"Vocabulary…" and "AI: propose for unread rows" buttons), the Scene cross-check step with each of its three
sources selected in turn, the Save step (unchanged), the Vocabulary window's Sets tab, Terms tab and
Assistant tab. That is nine screenshots. Save them under a path the human hand-off can point at (follow
this repo's own convention from the previous wave's handoff for where screenshots live — check
`docs/handoff/2026-09-18-gui-write-wave3-complete.md` for the pattern rather than inventing a new location).

- [ ] **Step 8: Human-only, cannot be completed by an agent — name it, do not silently skip it**

Try AI and the Vocabulary assistant with ToanAZ's real DeepSeek key, from the built exe (closes the
2026-09-25 Test-connection gap the memory file names). One real cue sheet from his next show through the
whole wizard, start to finish, including the Scene cross-check against a real console pull. Record both as
open items in the wave's closing handoff — do not mark the wave "done" while they are outstanding; they are
exactly the kind of acceptance CLAUDE.md's `task-closeout` skill and this project's own
`docs/acceptance/2026-09-wave3-desk-acceptance.md` precedent require a human, not an agent, to close.

- [ ] **Step 9: Update `docs/tech-debt.md` and the ROADMAP status table**

Follow this repo's `task-closeout` skill, Path C (`CLAUDE.md` rule 9: "Finish a phase in public") — status
updated where the roadmap lives, what a human can try and how, and a handoff for whatever wave 5 turns out
to be, written now while this wave's context is still fresh. This step is process, not code; there is no
test for it, only the three deliverables rule 9 names.

**Claims to check by opening:** that `packaging/wing-ui.spec`'s `DATAS` list still reads
`("../wing_parser/classifier/data", "wing_parser/classifier/data")` unchanged (confirms the new YAML file
needs no spec edit — it rides in with the directory it already bundles whole); that `packaging/wing-ui.spec`'s
`EXCLUDES` still names `mcp` (confirms this wave did not accidentally reintroduce it via a new import
somewhere in `wing_parser/ui/`).

---

## Out of scope

Durable write log and post-show report (a later wave — the design doc calls this out as overturning wave 3's
W8). Mixing-taste advisory, and any new `patterns.yaml` kind — W6 makes that the advisory wave's job, not
this one's. Counts in a set ("3 toms") — W5, a later show-context format change. Reading `.docx`/`.pdf`
cue sheets. The CLI's `--map`/`--no-assist`/`--one-shot` flags reaching the UI. Classifying the free-text
`Sound`/`Âm thanh` column. A Vietnamese UI — W1, its own wave if ToanAZ ever asks for it, because every page
would have to follow, not just this one's new strings.
