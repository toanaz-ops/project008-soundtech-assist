# GUI wave 4 — better cue-sheet import — design

**Date:** 2026-09-26 · **Status:** draft, awaiting ToanAZ's read · **Cycle:** Đợt 4 (import) · **Follows:**
ROADMAP §5 item 10.2 and §5 item 2 ("the `cuesheet:` vocabulary ships empty").

ToanAZ picked this direction first of the three he named on 2026-09-25 (the durable write log and the mixing-taste
advisory become later waves, each with its own spec). Everything marked **F1–F8** was decided by him in the brainstorm
on 2026-09-26 and is FIXED. Everything marked **W…** is the orchestrator's, ASSUMED, with what changes if he overturns it.

## 1. Goal

A cue sheet he actually gets — a corporate rundown like `tests/data/` vivo and BIDV, or a concert running order — should
come out of the Import wizard with most performer cells already read, the remainder teachable in one click each, and a
check against the scene that says what the sheet needs and the desk does not have. All of it from buttons; nothing
new is CLI-only.

Measured baseline (2026-09-26, `build.resolve_fragment` over the two real `.xlsx`, empty vocabulary): **11 of 21**
non-empty performer cells resolve, all through `patterns.yaml`'s `\bmc\b`. The other 21 distinct fragments are
full-sentence stage directions ("Mời BLĐ lên sân khấu quay số", "Trao giải", "Band nhạc chơi những bài nhạc nhẹ",
"hoa tươi") that an exact-key vocabulary can never match.

## 2. Decisions

| # | Decision | Source |
|---|---|---|
| F1 | Wave 4 is import only. Order after it: (a) durable write log, (c) mixing-taste advisory. | ToanAZ |
| F2 | Scope: seed + keyword matching, scene cross-check in the UI, lint in the UI, in-app AI diagnosis. All four. | ToanAZ |
| F3 | The seed covers both corporate rundowns and concerts. | ToanAZ |
| F4 | Concert terms are drafted by the orchestrator, marked "not checked against a real file", and ToanAZ strikes/edits them (§A). | ToanAZ |
| F5 | A vocabulary term maps to **several** kinds, or to **ignore**. | ToanAZ |
| F6 | Scene source: the scene open in Doctor (default), a `.snap` file, or the Console page's last Pull. All three. | ToanAZ |
| F7 | Matching approach A: whole-word keywords inside `cuesheet:`, no regex, teachable from the Terms step. | ToanAZ |
| F8 | Design sections 1–6 approved as presented in chat. | ToanAZ |
| W1 | New UI strings are English, like every existing string in `texts*.py`. The AI-diagnosis reasons are plain-language English. *If overturned:* a Vietnamese string table is its own wave — every page would have to follow. | orchestrator |
| W2 | Lint's **Fix** writes `<file>.bak` (overwriting an older `.bak`) before `apply_repairs`, which itself keeps no backup. *If overturned to "Save As":* one dialog more, no `.bak`. | orchestrator |
| W3 | Diacritic folding applies to the match only; the stored key keeps what the user typed, folded form computed on load. *If overturned:* keys stored folded, and the YAML stops being readable Vietnamese. | orchestrator |
| W4 | The Console "last Pull" source is in-memory only for this app run; nothing new is persisted. | orchestrator |

## 3. Data and matching (F5, F7)

### 3.1 Where the seed lives

The user's `classifier.yaml` already exists with `cuesheet: {}` (created from the template at
`wing_parser/classifier/cache.py:25-44`), so a seed added to that template would never reach him. The seed is a new
shipped file, **`wing_parser/classifier/data/cuesheet_seed.yaml`**; `packaging/wing-ui.spec` already bundles
`wing_parser/classifier/data` whole (`DATAS`, line 33), so no spec change is needed — but the exe check in §8 confirms it.

### 3.2 Entry shape

```yaml
cuesheet:
  trao giải:  {kinds: [speech.mc, utility.playback], match: word, origin: seed}
  BLĐ:        {kinds: [speech.handheld], match: word, origin: seed}
  hoa tươi:   {ignore: true, match: word, origin: seed}
  guitar solo: {kind: instrument.guitar, confidence: 1.0, origin: manual, matched: ...}   # old shape
```

- `kinds:` (list) or the old `kind:` (single, read as a one-item list). Both shapes load; new writes use `kinds:`.
- `match: exact | word`, default `exact` — every entry written before wave 4 keeps its meaning.
- `ignore: true` excludes `kinds:`. A cell resolved only by ignore entries yields no kind and no comment.
- Every kind must be one `patterns.yaml` can produce — `expects:` refuses anything else (ROADMAP §5 item 7). The seed
  loader rejects an unknown kind at load, naming the key; a test runs that check over the shipped seed.

### 3.3 Lookup order (per performer fragment)

1. user vocabulary, `match: exact`
2. user vocabulary, `match: word`
3. seed, exact, then word
4. `patterns.yaml` (unchanged, `matcher.classify(fragment, "channels")`)
5. nothing → the existing verbatim comment `row N: could not read performer '...'`

A user entry with the same folded key as a seed entry replaces it outright, so he corrects the seed by recording over it.

### 3.4 Normalisation (W3)

Folded form = NFC → casefold → strip combining marks → `đ`→`d` → punctuation to space → collapse whitespace. "BLĐ",
"Bld" and "bld" fold to `bld`; "phát biểu" and "phat bieu" to `phat bieu`. Matching is on **whole words** of the folded
text: `band` does not hit `bandana`. Folding can collide two words that differ only by tone (`bàn`/`bạn`); every
single-syllable key in §A (`hát`, `bass`, `kèn`, `beat`, `trống`) is a deliberate exception he should look at twice.

### 3.5 Several keywords in one cell

- Collect every matching keyword; a keyword wholly contained in a longer matching one is dropped (`nhạc nhẹ` loses to
  `ban nhạc nhẹ`).
- Union the kinds, first-seen order, no duplicates.
- Ignore wins only when no non-ignore keyword matched.
- `ImportResult` gains `ignored_performers: int`, counted and shown in the summary line next to
  `unreadable_performers`, so ignored cells are never invisible.

### 3.6 Units

- New `wing_parser/showcontext/ingest/keywords.py` — pure: `fold(text)`, `match(text, entries) -> Resolution` where
  `Resolution = (kinds: tuple[str, ...], ignored: bool)`. No I/O.
- `wing_parser/classifier/cache.py` — read/write the new entry shape; `remember` takes `kinds`, `match`, `ignore`.
- New seed loader beside the cache (`cuesheet_seed.py`), lru-cached, validates kinds.
- `build.resolve_fragment` → returns a `Resolution` instead of `str | None`; `_expectations` handles several kinds and
  ignore. Its callers in the CLI and UI are updated together.

## 4. Terms step (UI)

Each unresolved row gets:

- a **key** field, prefilled with the whole fragment; he shortens it to the keyword;
- a **"match inside a sentence"** checkbox, ticked automatically once the key is shorter than the fragment;
- a **multi-kind picker** (the existing kind editor becomes a list with add/remove);
- **Record** (writes `kinds:` + `match:`), **Ignore (remember)** (writes `ignore: true`), and the existing **Skip**
  (this import only, writes nothing).

After Record or Ignore the remaining rows are re-resolved immediately, so one keyword can clear several rows below it.
The model's guess (`load_guesses`) still only prefills the kind — unchanged.

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

- New pure `wing_parser/classifier/provider_errors.py`: `classify(exc) -> (code, text)`. Settings ▸ Test connection uses
  the same classifier, so both surfaces say the same thing for the same failure.
- The key stays wherever Settings stores it today; nothing in code, tests or logs carries one.

## 8. Tests and acceptance

**Plain pytest:** `fold` (tones, `Đ`, punctuation, whole-word); `match` (union, longest-wins, ignore-only-alone, user over
seed); old single-`kind` entries still load; the shipped seed validates against `patterns.yaml` kinds;
`missing_for_segments`; `provider_errors.classify` for every row of §7 with fake exceptions.

**Acceptance on real files:** extend `tests/test_g2b_acceptance.py` to pin the resolved/ignored/unreadable counts for vivo
and BIDV **with** the seed. Target: every one of the 21 unresolved fragments listed in §1 either resolves or is
ignored, or is listed in the test as deliberately left unread with a reason.

**Qt, offscreen, real MainWindow, `timeout=2`:** Terms Record with a shortened key clears several rows; Ignore
(remember) persists and re-import shows no comment; scene step with each of the three sources (a fake Pull for the
Console one); lint Fix writes `.bak` and re-lints; Try AI with a fake provider raising each §7 class. Suite tally read
from `--junitxml`.

**Exe:** rebuild from `main` after merge with `.[ui,ingest,llm,llm-openai]`; confirm `cuesheet_seed.yaml` is in
`build/wing-ui/Analysis-00.toc`; screenshot every new surface from the exe for ToanAZ — wave 1's gate.

**Human-only:** Try AI with his real DeepSeek key from the exe (closes the 2026-09-25 Test-connection gap); one real
cue sheet from his next show through the whole wizard.

## 9. Task sketch

1. `keywords.py` + tests.
2. Cache entry shape + seed loader + seed file (§A after ToanAZ's edits) + tests.
3. `build.resolve_fragment`/`_expectations` → `Resolution`; `ignored_performers`; CLI + UI callers; acceptance counts.
4. Terms step: `terms_row.py`, key field, checkbox, multi-kind, Ignore (remember), live re-resolve.
5. `missing_for_segments` + scene step with three sources.
6. Lint surface on the Pick step.
7. `provider_errors.py` + Try AI + Settings reuse.
8. Exe rebuild, bundle check, screenshots.

## 10. Out of scope

Durable write log and post-show report (next wave, overturns wave-3 W8). Mixing-taste advisory (the wave after).
Reading `.docx`/`.pdf` scripts. The CLI's `--map`/`--no-assist`/`--one-shot` in the UI. Classifying the free-text
`Sound`/`Âm thanh` column. A Vietnamese UI (W1).

## A. Seed draft — ToanAZ strikes or edits before task 2

Corporate rows come from the two real sheets. Concert rows are **not checked against a real file** (F4).

| Key | match | kinds / ignore | Group |
|---|---|---|---|
| MC | word | speech.mc | corporate (already caught by patterns; listed so the seed is complete) |
| dẫn chương trình | word | speech.mc | corporate |
| BLĐ | word | speech.handheld | corporate |
| ban lãnh đạo | word | speech.handheld | corporate |
| phát biểu | word | speech.lectern | corporate |
| đại diện | word | speech.handheld | corporate |
| khách mời | word | speech.handheld | corporate |
| giám đốc | word | speech.lectern | corporate |
| trao giải | word | speech.mc, utility.playback | corporate |
| vinh danh | word | speech.mc, utility.playback | corporate |
| quay số | word | speech.mc, utility.playback | corporate |
| tặng kỉ niệm chương | word | speech.mc, utility.playback | corporate |
| lên sân khấu | word | utility.playback | corporate (walk-up music) |
| loto | word | speech.handheld, utility.playback | corporate |
| band nhạc | word | speech.vocal, instrument.guitar, instrument.bass, instrument.keys, drums.kick, drums.snare | corporate — **which kinds a "band" implies is his call** |
| nhạc nhẹ | word | utility.playback | corporate — loses to "band nhạc" when both match |
| hoa tươi | word | ignore | corporate |
| huy chương | word | ignore | corporate |
| chụp hình | word | ignore | corporate |
| quay phim | word | ignore | corporate |
| check in | word | ignore | corporate |
| phòng ban | word | ignore | corporate |
| tiết mục | word | ignore | corporate — a numbered slot with no performer yet |
| ca sĩ | word | speech.vocal | concert |
| vocal | word | speech.vocal | concert |
| hát | word | speech.vocal | concert — single syllable, collision risk low but real |
| guitar điện | word | instrument.guitar.electric | concert |
| guitar thùng | word | instrument.guitar.acoustic | concert |
| bass | word | instrument.bass | concert |
| keyboard | word | instrument.keys | concert |
| piano | word | instrument.keys | concert |
| trống | word | drums.kick, drums.snare, drums.overhead | concert — which drum kinds is his call |
| kèn | word | instrument.horns | concert |
| violin | word | instrument.strings | concert |
| backing track | word | utility.playback | concert |
| beat | word | utility.playback | concert |
| playback | word | utility.playback | concert |
