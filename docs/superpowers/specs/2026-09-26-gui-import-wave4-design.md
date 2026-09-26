# GUI wave 4 — better cue-sheet import — design

**Date:** 2026-09-26 · **Status:** draft, awaiting ToanAZ's read · **Cycle:** Đợt 4 (import) · **Follows:**
ROADMAP §5 item 10.2 and §5 item 2 ("the `cuesheet:` vocabulary ships empty").

ToanAZ picked this direction first of the three he named on 2026-09-25 (the durable write log and the mixing-taste
advisory become later waves, each with its own spec). Everything marked **F…** was decided by him in the brainstorm
on 2026-09-26 and is FIXED. Everything marked **W…** is the orchestrator's, ASSUMED, with what changes if he overturns it.

## 1. Goal

A cue sheet he actually gets — a corporate rundown like `tests/data/` vivo and BIDV, or a concert running order — should
come out of the Import wizard with most performer cells already read, the remainder teachable in one click each, and a
check against the scene that says what the sheet needs and the desk does not have. What the app knows about cue-sheet
words is **data he edits in the app**, with an AI assistant that proposes changes he approves — not something fixed at
build time. All of it from buttons; nothing new is CLI-only.

Measured baseline (2026-09-26, `build.resolve_fragment` over the two real `.xlsx`, empty vocabulary): **11 of 21**
non-empty performer cells resolve, all through `patterns.yaml`'s `\bmc\b`. The other 21 distinct fragments are
full-sentence stage directions ("Mời BLĐ lên sân khấu quay số", "Trao giải", "Band nhạc chơi những bài nhạc nhẹ",
"hoa tươi") that an exact-key vocabulary can never match.

## 2. Decisions

| # | Decision | Source |
|---|---|---|
| F1 | Wave 4 is import only. Order after it: (a) durable write log, (c) mixing-taste advisory. | ToanAZ |
| F2 | Scope: default vocabulary + keyword matching, scene cross-check in the UI, lint in the UI, in-app AI diagnosis. All four. | ToanAZ |
| F3 | The defaults cover both corporate rundowns and concerts. | ToanAZ |
| F4 | Concert defaults are drafted by the orchestrator, marked "not checked against a real file", and ToanAZ strikes/edits them (§A). | ToanAZ |
| F5 | A term maps to **several** kinds, or to **ignore**. | ToanAZ |
| F6 | Scene source: the scene open in Doctor (default), a `.snap` file, or the Console page's last Pull. All three. | ToanAZ |
| F7 | Matching approach A: whole-word keywords, no regex, teachable from the Terms step. | ToanAZ |
| F8 | Design sections 1–6 approved as presented in chat. | ToanAZ |
| F9 | Lists like "a drum kit is kick, snare, tom, hi-hat, overheads" are **not hard-coded**: they are editable in an in-app Vocabulary window, and extendable through an AI assistant living in the app. | ToanAZ |
| F10 | **Sets** are separate from terms: define "Drum kit" once; "trống", "drum", "dàn trống" all point at it. | ToanAZ |
| F11 | The AI assistant **proposes; he approves** each change. It never writes on its own. | ToanAZ |
| F12 | Section 7 (editor + assistant) approved as presented in chat. | ToanAZ |
| F13 | **Nested sets**: a set may contain other sets (Band contains Drum kit), so editing Drum kit changes Band too. Built now "because it will be needed". | ToanAZ |
| F14 | Appendix A ships as drafted; he corrects defaults in the Vocabulary window afterwards (F9), so §A does not block task 2. | orchestrator, from F9 |
| W1 | New UI strings are English, like every existing string in `texts*.py`; the AI-diagnosis reasons are plain-language English. *If overturned:* a Vietnamese string table is its own wave — every page would have to follow. | orchestrator |
| W2 | Lint's **Fix** writes `<file>.bak` (overwriting an older `.bak`) before `apply_repairs`, which itself keeps no backup. *If overturned to "Save As":* one dialog more, no `.bak`. | orchestrator |
| W3 | Diacritic folding applies to the match only; stored keys keep what the user typed. *If overturned:* keys stored folded, and the YAML stops being readable Vietnamese. | orchestrator |
| W4 | The Console "last Pull" source is in-memory only for this app run; nothing new is persisted. | orchestrator |
| W5 | A set lists **kinds, not counts**: "3 toms" is `drums.tom` once, because `expects:` is a set. *If overturned:* counts need a show-context format change and a counting cross-check — a later wave. | orchestrator |
| W6 | Neither the editor nor the assistant can invent a **new kind**; kinds come from `patterns.yaml`. *If overturned:* that belongs with the advisory wave (c), which owns the classifier. | orchestrator |

## 3. Data and matching (F5, F7, F10)

### 3.1 Defaults and overrides

The user's `classifier.yaml` already exists with `cuesheet: {}` (created from the template at
`wing_parser/classifier/cache.py:25-44`), so defaults added to that template would never reach him. Defaults are a new
shipped file, **`wing_parser/classifier/data/cuesheet_defaults.yaml`** (sets and terms, §A). `packaging/wing-ui.spec`
already bundles `wing_parser/classifier/data` whole (`DATAS`, line 33); the exe check in §9 confirms it.

His edits live in `classifier.yaml`: terms under the existing `cuesheet:` domain, sets under a new
`cuesheet_sets:` domain. An entry of his with the same folded key as a default **replaces** it. Deleting a default
writes a tombstone (`deleted: true`) so the next app update cannot bring it back. **Reset to default** removes his
entry (or tombstone) and the default shows through again.

### 3.2 Shapes

```yaml
cuesheet_sets:
  drum kit:
    label: Drum kit
    kinds: [drums.kick.in, drums.kick.out, drums.snare.top, drums.snare.bottom, drums.tom, drums.hihat, drums.overhead]
    origin: default            # default | manual | ai-approved
  band:
    label: Band
    sets: [drum kit]           # nested (F13)
    kinds: [speech.vocal, instrument.guitar, instrument.bass, instrument.keys]
    origin: default
cuesheet:
  trống:     {sets: [drum kit], match: word, origin: default}
  trao giải: {kinds: [speech.mc, utility.playback], match: word, origin: default}
  hoa tươi:  {ignore: true, match: word, origin: default}
  cajon:     {kinds: [drums.pad], match: word, origin: ai-approved}
  guitar solo: {kind: instrument.guitar, confidence: 1.0, origin: manual, matched: ...}   # pre-wave-4 shape
```

- A term has `sets:` and/or `kinds:`, or `ignore: true` (exclusive with both). Resolving a term = the union of its
  own kinds and every kind of every set it names, first-seen order, no duplicates.
- The old `kind:` (single) still loads, read as `kinds: [x]`, `match: exact`. New writes use the new shape.
- `match: exact | word`, default `exact` — every entry written before wave 4 keeps its meaning.
- Every kind must be one `patterns.yaml` can produce — `expects:` refuses anything else (ROADMAP §5 item 7). The loader
  rejects an unknown kind or an unknown set name, naming the key; a test runs that check over the shipped defaults.
  A term pointing at a set he later deleted is shown in the editor as broken, and resolves to its remaining kinds.
- **Nested sets (F13).** A set has `kinds:` and/or `sets:`. Expansion is recursive, depth-first, first-seen order, no
  duplicates. A **cycle** (A contains B contains A) is refused at save in the editor and by `vocab_changes.validate`,
  naming the path (`band → drum kit → band`); if one reaches disk by hand-editing, the loader reports it and expands
  each set on the cycle once, never looping. A nested reference to a deleted set is broken exactly like a term's.
  The editor shows each set's fully expanded kinds beside its own list, so the effect of nesting is visible.

### 3.3 Lookup order (per performer fragment)

1. the effective vocabulary (his entries over defaults, tombstones removed), `match: exact`
2. the effective vocabulary, `match: word`
3. `patterns.yaml` (unchanged, `matcher.classify(fragment, "channels")`)
4. nothing → the existing verbatim comment `row N: could not read performer '...'`

### 3.4 Normalisation (W3)

Folded form = NFC → casefold → strip combining marks → `đ`→`d` → punctuation to space → collapse whitespace. "BLĐ",
"Bld" and "bld" fold to `bld`; "phát biểu" and "phat bieu" to `phat bieu`. Matching is on **whole words** of the folded
text: `band` does not hit `bandana`. Folding can collide two words that differ only by tone (`bàn`/`bạn`); every
single-syllable key in §A (`hát`, `bass`, `kèn`, `beat`, `trống`) is a deliberate exception he should look at twice.

### 3.5 Several keywords in one cell

- Collect every matching keyword; a keyword wholly contained in a longer matching one is dropped (`nhạc nhẹ` loses to
  `band nhạc nhẹ` if both exist).
- Union the kinds, first-seen order, no duplicates.
- Ignore wins only when no non-ignore keyword matched.
- `ImportResult` gains `ignored_performers: int`, counted and shown in the summary line next to
  `unreadable_performers`, so ignored cells are never invisible.

### 3.6 Units

- New `wing_parser/showcontext/ingest/keywords.py` — pure: `fold(text)`, `match(text, vocabulary) -> Resolution` where
  `Resolution = (kinds: tuple[str, ...], ignored: bool)`. No I/O.
- New `wing_parser/classifier/vocabulary.py` — loads defaults + his domains, applies overrides and tombstones, expands
  sets, validates kinds; exposes `effective()` and the write operations (`put_term`, `put_set`, `delete`, `reset`) that
  go through the cache's existing atomic write (`cache.py:90-108`).
- `wing_parser/classifier/cache.py` — new `cuesheet_sets` domain; new entry shape round-trips.
- `build.resolve_fragment` returns a `Resolution` instead of `str | None`; `_expectations` handles several kinds and
  ignore. Its CLI and UI callers are updated together.

## 4. Terms step (UI)

Each unresolved row gets:

- a **key** field, prefilled with the whole fragment; he shortens it to the keyword;
- a **"match inside a sentence"** checkbox, ticked automatically once the key is shorter than the fragment;
- a **picker for sets and kinds** (several of each);
- **Record** (writes the term), **Ignore (remember)** (writes `ignore: true`), and the existing **Skip** (this import
  only, writes nothing);
- **"AI: propose for unread rows"** above the list (§8.2).

After Record or Ignore the remaining rows are re-resolved immediately, so one keyword can clear several rows below it.
The existing `load_guesses` prefill is replaced by the §8.2 proposal list.

`terms_step.py` is at 153 lines; the per-row widget moves to a new `terms_row.py` so both stay under 200.

## 5. Scene cross-check — new optional step between Terms and Save (F6)

- **Source** picker: *Doctor's scene* (default and preselected when Doctor has one loaded), *Open .snap…*, *Console's
  last Pull* (enabled only once a Pull has completed this run — W4). Read-only; nothing goes to a desk.
- **Table**, one row per segment: segment, kinds needed, channels found (number + name), **kinds missing** (warning
  colour). `propose.for_segments` returns only what it found; a new pure function in `propose.py`,
  `missing_for_segments(result, scene) -> dict[str, tuple[str, ...]]`, supplies the rest.
- The emitted YAML carries the proposals exactly as the CLI's `--scene` does today: commented-out cues, never live ones.
  `import_controller.preview_text` passes the chosen scene to `emit.render` instead of `None`.
- **Skip** goes straight to Save, and the file is the same as today's.

## 6. Lint an existing show-context file

- The Pick step gains **"Check an existing show-context file…"**. It loads the file with `load_show_context` and lists
  `context.anomalies`, each marked auto-fixable or not — the same data `wing showcontext lint` prints.
- **Fix** asks for confirmation, writes `<file>.bak` (W2), runs `apply_repairs`, lists what it changed, then re-lints
  and shows the result.
- A load error (`ValueError`) is shown as a message, not a crash. No second lint implementation.

## 7. AI diagnosis in the app

- The Mapping step gains **"Try AI on this file"**. It runs the real mapping proposal (`ic.proposal_for`) on the open
  file through the Settings provider and reports provider, model, elapsed seconds, and the proposal — or a classified
  failure:

  | Class | Recognised from |
  |---|---|
  | bad key | HTTP 401/403 from either SDK |
  | quota / rate limit | HTTP 402/429 |
  | timeout | the worker's timeout budget (existing 120/180/30 s) |
  | no network | connection errors from either SDK |
  | SDK missing | `ImportError` on the lazy SDK import in `provider.py` — the frozen-exe case |
  | bad reply | the model's JSON fails to parse or validate |
  | other | anything else, with the exception's text |

- New pure `wing_parser/classifier/provider_errors.py`: `classify(exc) -> (code, text)`. Settings ▸ Test connection and
  the §8 assistant use the same classifier, so every surface says the same thing for the same failure.
- The key stays wherever Settings stores it today; nothing in code, tests or logs carries one.

## 8. Vocabulary window and AI assistant (F9–F12)

### 8.1 The window

- Opened from the same place as Settings, and from a **Vocabulary…** button on the Terms step.
- Two tabs, **Sets** and **Terms**. Each is a searchable table with Add / Edit / Delete / **Reset to default**, and a
  **source** column: default, manual, ai-approved, or "default, edited".
- Kinds are chosen from a list built from `patterns.yaml` (W6) — never typed — so nothing `expects:` would refuse can
  be saved. Terms pick sets from the Sets tab's names.
- A term whose set no longer exists shows as broken (§3.2) with a one-click fix: pick another set or drop the reference.
- Saving goes through `vocabulary.py`; the Import wizard re-reads the effective vocabulary when the window closes.
- The window works fully with no key and no network; only the assistant greys out, saying why (§7 classes).

### 8.2 The assistant

Two ways in, one result shape:

1. **Instruction box** in the Vocabulary window — free text, e.g. "my drum kit has no kick out, add a second tom",
   "cajon is percussion".
2. **"AI: propose for unread rows"** on the Terms step — sends the unresolved fragments and the current vocabulary.

The model is asked for JSON: a list of changes, each `{op: add|edit|delete, target: set|term, key, before, after,
reason}`. A new pure `wing_parser/classifier/vocab_changes.py` validates every change against the known kinds (W6) and
the current sets. The **proposal list** shows each change as before → after with the reason and a tickbox; an invalid
change is shown greyed with why and cannot be ticked. **Apply** writes the ticked ones through `vocabulary.py` with
`origin: ai-approved`. Nothing is written before Apply (F11). The call runs on the existing cancellable worker with the
180 s budget; failures use §7's classifier.

The prompt text lives in one module, not scattered through widgets, so it can be reviewed and tuned in one place.

## 9. Tests and acceptance

**Plain pytest:** `fold` (tones, `Đ`, punctuation, whole-word); `match` (union, longest-wins, ignore-only-alone);
`vocabulary.effective` (his entry over default, tombstone hides default, reset restores it, set expansion, nested
expansion, a cycle detected and not looped, broken set reference at both levels, old single-`kind` entries); the shipped defaults validate against `patterns.yaml` kinds;
`vocab_changes.validate` (valid, unknown kind, unknown set, a change that would create a cycle, delete of a missing key); `missing_for_segments`;
`provider_errors.classify` for every row of §7 with fake exceptions.

**Acceptance on real files:** extend `tests/test_g2b_acceptance.py` to pin the resolved/ignored/unreadable counts for vivo
and BIDV **with** the defaults. Target: every one of the 21 unresolved fragments in §1 either resolves or is ignored, or
is listed in the test as deliberately left unread with a reason.

**Qt, offscreen, real MainWindow, `timeout=2`:** Terms Record with a shortened key clears several rows; Ignore (remember)
persists and a re-import shows no comment; Vocabulary window add/edit/delete/reset on both tabs, and editing Drum kit
changes what a "band" term resolves to (nesting); saving a cycle is refused with the path shown; the assistant with a fake provider returning a mixed valid/invalid change list —
only ticked valid changes are written, nothing before Apply; scene step with each of the three sources (a fake Pull for
the Console one); lint Fix writes `.bak` and re-lints; Try AI with a fake provider raising each §7 class. Suite tally
read from `--junitxml`. Every `wing_parser/ui/*.py` stays ≤200 lines.

**Exe:** rebuild from `main` after merge with `.[ui,ingest,llm,llm-openai]`; confirm `cuesheet_defaults.yaml` is in
`build/wing-ui/Analysis-00.toc`; screenshot every new surface from the exe for ToanAZ — wave 1's gate.

**Human-only:** Try AI and the assistant with his real DeepSeek key from the exe (closes the 2026-09-25 Test-connection
gap); one real cue sheet from his next show through the whole wizard.

## 10. Task sketch

1. `keywords.py` + tests.
2. Cache domains and entry shape; `vocabulary.py` (defaults, overrides, tombstones, sets); `cuesheet_defaults.yaml`
   (§A as drafted, F14) + nested sets and cycle detection + tests.
3. `build.resolve_fragment`/`_expectations` → `Resolution`; `ignored_performers`; CLI + UI callers; acceptance counts.
4. `provider_errors.py`; Settings ▸ Test connection reuses it.
5. Vocabulary window (Sets, Terms, reset, broken references).
6. `vocab_changes.py` + the assistant (instruction box, proposal list, Apply).
7. Terms step: `terms_row.py`, key field, checkbox, set/kind picker, Ignore (remember), live re-resolve, "AI: propose".
8. `missing_for_segments` + scene step with three sources.
9. Lint surface on the Pick step; Try AI on the Mapping step.
10. Exe rebuild, bundle check, screenshots.

## 11. Out of scope

Durable write log and post-show report (next wave, overturns wave-3 W8). Mixing-taste advisory (the wave after), which
also owns new kinds (W6). Counts in sets (W5). Reading `.docx`/`.pdf` scripts. The CLI's `--map`/`--no-assist`/
`--one-shot` in the UI. Classifying the free-text `Sound`/`Âm thanh` column. A Vietnamese UI (W1).

## A. Defaults draft — ToanAZ strikes or edits before task 2

These ship as defaults; after this wave he changes them in the Vocabulary window, not here. Corporate rows come from the
two real sheets. Concert rows are **not checked against a real file** (F4).

### A.1 Sets

| Set | Kinds |
|---|---|
| Drum kit | drums.kick.in, drums.kick.out, drums.snare.top, drums.snare.bottom, drums.tom, drums.hihat, drums.overhead |
| Band | sets: Drum kit · kinds: speech.vocal, instrument.guitar, instrument.bass, instrument.keys |
| Speech, handheld | speech.handheld |
| Award moment | speech.mc, utility.playback |

Band contains Drum kit (F13): editing Drum kit changes Band.

### A.2 Terms

| Key | match | sets / kinds / ignore | Group |
|---|---|---|---|
| MC | word | speech.mc | corporate (already caught by patterns; listed so the defaults are complete) |
| dẫn chương trình | word | speech.mc | corporate |
| BLĐ | word | Speech, handheld | corporate |
| ban lãnh đạo | word | Speech, handheld | corporate |
| phát biểu | word | speech.lectern | corporate |
| đại diện | word | Speech, handheld | corporate |
| khách mời | word | Speech, handheld | corporate |
| giám đốc | word | speech.lectern | corporate |
| trao giải | word | Award moment | corporate |
| vinh danh | word | Award moment | corporate |
| quay số | word | Award moment | corporate |
| tặng kỉ niệm chương | word | Award moment | corporate |
| lên sân khấu | word | utility.playback | corporate (walk-up music) |
| loto | word | speech.handheld, utility.playback | corporate |
| band nhạc | word | Band | corporate |
| nhạc nhẹ | word | utility.playback | corporate |
| hoa tươi | word | ignore | corporate |
| huy chương | word | ignore | corporate |
| chụp hình | word | ignore | corporate |
| quay phim | word | ignore | corporate |
| check in | word | ignore | corporate |
| phòng ban | word | ignore | corporate |
| tiết mục | word | ignore | corporate — a numbered slot with no performer yet |
| ca sĩ | word | speech.vocal | concert |
| vocal | word | speech.vocal | concert |
| hát | word | speech.vocal | concert — single syllable |
| band | word | Band | concert |
| trống | word | Drum kit | concert — single syllable |
| drum | word | Drum kit | concert |
| dàn trống | word | Drum kit | concert |
| guitar điện | word | instrument.guitar.electric | concert |
| guitar thùng | word | instrument.guitar.acoustic | concert |
| bass | word | instrument.bass | concert — single syllable |
| keyboard | word | instrument.keys | concert |
| piano | word | instrument.keys | concert |
| kèn | word | instrument.horns | concert — single syllable |
| violin | word | instrument.strings | concert |
| backing track | word | utility.playback | concert |
| beat | word | utility.playback | concert — single syllable |
| playback | word | utility.playback | concert |
